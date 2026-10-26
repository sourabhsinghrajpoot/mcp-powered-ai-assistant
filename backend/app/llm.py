from typing import Any

import httpx


class LLMError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.strip().rstrip("/")
        self.api_key = api_key.strip()
        self.model = model.strip()

    async def complete(
        self,
        messages: list[dict[str, str]],
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> str:
        if not self.base_url or not self.api_key or not self.model:
            raise LLMError(
                503,
                "AI provider is not configured. Set LLM_BASE_URL, LLM_API_KEY, "
                "and LLM_MODEL in backend/.env.",
            )

        try:
            async with httpx.AsyncClient(timeout=60, transport=transport) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "messages": messages},
                )
        except httpx.TimeoutException as exc:
            raise LLMError(504, "The AI provider request timed out.") from exc
        except httpx.RequestError as exc:
            raise LLMError(502, "Could not connect to the configured AI provider.") from exc

        if response.status_code in (401, 403):
            raise LLMError(
                502,
                "The AI provider rejected the API key or the key lacks permission.",
            )
        if response.status_code == 429:
            raise LLMError(429, "The AI provider rate limit or quota has been reached.")
        if response.status_code == 404:
            raise LLMError(
                502,
                "The AI provider endpoint or model was not found. Check LLM_BASE_URL "
                "and LLM_MODEL.",
            )
        if response.status_code == 400:
            raise LLMError(
                502,
                "The AI provider rejected the request. Check that LLM_MODEL is "
                "supported by this endpoint.",
            )
        if response.is_error:
            raise LLMError(502, "The AI provider returned an unsuccessful response.")

        try:
            payload: Any = response.json()
            content = payload["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError(502, "The AI provider returned an invalid response.") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMError(502, "The AI provider returned an empty response.")
        return content
