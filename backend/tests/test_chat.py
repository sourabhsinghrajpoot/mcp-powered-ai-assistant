import asyncio
import json

import httpx
import pytest

from backend.app import main
from backend.app.llm import LLMError, OpenAICompatibleProvider


def configure_provider(monkeypatch):
    monkeypatch.setattr(main.settings, "llm_base_url", "https://llm.example/v1")
    monkeypatch.setattr(main.settings, "llm_api_key", "test-api-key")
    monkeypatch.setattr(main.settings, "llm_model", "test-model")


@pytest.mark.parametrize("missing_setting", ["llm_base_url", "llm_api_key", "llm_model"])
def test_chat_requires_provider_configuration(client, monkeypatch, missing_setting):
    configure_provider(monkeypatch)
    monkeypatch.setattr(main.settings, missing_setting, "")

    response = client.post(
        "/api/chat",
        json={"conversation_id": 1, "message": "Hello"},
    )

    assert response.status_code == 503, response.text
    assert "LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL" in response.json()["detail"]
    assert client.get("/api/conversations/1").json()["messages"] == [
        {"role": "user", "content": "Hello"}
    ]


def test_chat_uses_mocked_provider_and_persists_history(client, monkeypatch):
    configure_provider(monkeypatch)
    received_messages = []
    answers = iter(["Hello from the mocked model.", "The answer is 42."])

    def provider_response(request):
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-api-key"
        payload = json.loads(request.content)
        received_messages.append(payload["messages"])
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": next(answers)}}]},
        )

    provider = OpenAICompatibleProvider(
        main.settings.llm_base_url,
        main.settings.llm_api_key,
        main.settings.llm_model,
    )
    transport = httpx.MockTransport(provider_response)

    async def mocked_call_llm(messages):
        return await provider.complete(messages, transport=transport)

    monkeypatch.setattr(main, "call_llm", mocked_call_llm)
    first = client.post(
        "/api/chat",
        json={"conversation_id": 1, "message": "Hello"},
    )
    second = client.post(
        "/api/chat",
        json={"conversation_id": 1, "message": "What is the answer to life?"},
    )

    assert first.status_code == 200
    assert first.json()["answer"] == "Hello from the mocked model."
    assert second.status_code == 200
    assert second.json()["answer"] == "The answer is 42."
    assert [message["role"] for message in received_messages[1]] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    history = client.get("/api/conversations/1").json()["messages"]
    assert history[-1] == {"role": "assistant", "content": "The answer is 42."}


@pytest.mark.parametrize(
    ("provider_status", "api_status", "detail"),
    [
        (401, 502, "rejected the API key"),
        (400, 502, "Check that LLM_MODEL"),
        (404, 502, "endpoint or model was not found"),
        (429, 429, "rate limit or quota"),
        (503, 502, "unsuccessful response"),
    ],
)
def test_chat_reports_provider_errors(
    client, monkeypatch, provider_status, api_status, detail
):
    configure_provider(monkeypatch)
    provider = OpenAICompatibleProvider(
        main.settings.llm_base_url,
        main.settings.llm_api_key,
        main.settings.llm_model,
    )

    async def failing_call_llm(messages):
        return await provider.complete(
            messages,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(provider_status, json={"error": "mock"})
            ),
        )

    monkeypatch.setattr(main, "call_llm", failing_call_llm)
    response = client.post(
        "/api/chat",
        json={"conversation_id": 1, "message": "Hello"},
    )

    assert response.status_code == api_status
    assert detail in response.json()["detail"]


def test_provider_reports_network_failures():
    provider = OpenAICompatibleProvider(
        "https://llm.example/v1",
        "test-api-key",
        "test-model",
    )

    def fail_request(request):
        raise httpx.ConnectError("mock connection failure", request=request)

    async def request():
        return await provider.complete(
            [{"role": "user", "content": "Hello"}],
            transport=httpx.MockTransport(fail_request),
        )

    with pytest.raises(LLMError, match="Could not connect"):
        asyncio.run(request())
