def test_mcp_discovers_bundled_tools_over_stdio(client):
    response = client.get("/api/mcp/tools")

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected"] is True
    assert {"get_current_time", "calculate"} <= {
        tool["name"] for tool in payload["tools"]
    }


def test_mcp_calculator_executes_addition_over_stdio(client):
    response = client.post(
        "/api/mcp/execute",
        json={
            "name": "calculate",
            "arguments": {"operation": "add", "a": 25, "b": 35},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_error"] is False
    assert float(payload["result"][0]["text"]) == 60


def test_mcp_rejects_invalid_tool_arguments(client):
    response = client.post(
        "/api/mcp/execute",
        json={
            "name": "calculate",
            "arguments": {"operation": "power", "a": 25, "b": 35},
        },
    )

    assert response.status_code == 422
    assert "rejected the supplied arguments" in response.json()["detail"]
