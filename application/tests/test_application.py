import json
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app, parse_tool_command
from app.mcp_client import MCPManager, MCPUnavailable, UnknownTool


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Use temporary configuration and logs for every test."""

    config = {
        "servers": {
            "schema": {
                "transport": "streamable_http",
                "url": "http://mcp-schema:8000/mcp",
                "tools": ["get_schema"],
                "timeout_seconds": 2,
            }
        }
    }

    config_path = tmp_path / "mcp_servers.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    monkeypatch.setenv("MCP_CONFIG_PATH", str(config_path))
    monkeypatch.setenv(
        "APP_LOG_PATH",
        str(tmp_path / "events.jsonl"),
    )
    monkeypatch.delenv("APP_GATEWAY_URL", raising=False)
    monkeypatch.delenv("APP_GATEWAY_KEY", raising=False)
    monkeypatch.setenv("ENABLE_DEBUG_TOOLS", "true")

    with TestClient(app) as test_client:
        yield test_client


def test_tool_command_parser():
    tool, arguments = parse_tool_command(
        "/tool schema__get_schema {}"
    )

    assert tool == "schema__get_schema"
    assert arguments == {}


@pytest.mark.parametrize(
    "message",
    [
        "/tool",
        "/tool schema__get_schema",
        "/tool schema__get_schema not-json",
        "/tool schema__get_schema []",
    ],
)
def test_invalid_tool_commands(message):
    with pytest.raises(ValueError):
        parse_tool_command(message)


def test_live_endpoint(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["mode"] == "echo"


def test_query_gateway_can_be_unconfigured(client):
    response = client.post(
        "/api/query",
        json={"sql": "SELECT 1"},
        headers={"X-Query-Action": "submit"},
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "gateway_unavailable"


def test_ordinary_message_is_only_echoed(client, monkeypatch):
    call = AsyncMock()
    monkeypatch.setattr(MCPManager, "call_tool", call)

    response = client.post(
        "/api/chat",
        json={"message": "Hello"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "echo"
    call.assert_not_awaited()


def test_tool_response_is_returned(client, monkeypatch):
    call = AsyncMock(
        return_value={"context_version": "test-v1"}
    )
    monkeypatch.setattr(MCPManager, "call_tool", call)

    response = client.post(
        "/api/chat",
        json={
            "message": "/tool schema__get_schema {}"
        },
    )

    assert response.status_code == 200
    assert response.json()["result"] == {
        "context_version": "test-v1"
    }

    call.assert_awaited_once_with(
        "schema__get_schema",
        {},
    )


def test_unknown_tool_returns_404(client, monkeypatch):
    monkeypatch.setattr(
        MCPManager,
        "call_tool",
        AsyncMock(side_effect=UnknownTool()),
    )

    response = client.post(
        "/api/chat",
        json={"message": "/tool unknown__tool {}"},
    )

    assert response.status_code == 404


def test_unavailable_server_returns_503(client, monkeypatch):
    monkeypatch.setattr(
        MCPManager,
        "call_tool",
        AsyncMock(side_effect=MCPUnavailable()),
    )

    response = client.post(
        "/api/chat",
        json={"message": "/tool schema__get_schema {}"},
    )

    assert response.status_code == 503


def test_debug_commands_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(app.state, "debug_tools", False)

    response = client.post(
        "/api/chat",
        json={"message": "/tool schema__get_schema {}"},
    )

    assert response.status_code == 403


def test_status_reports_each_server(client, monkeypatch):
    monkeypatch.setattr(
        MCPManager,
        "inspect_all",
        AsyncMock(
            return_value=[
                {
                    "server": "schema",
                    "status": "available",
                    "tools": ["schema__get_schema"],
                },
                {
                    "server": "examples",
                    "status": "unavailable",
                    "tools": [],
                },
            ]
        ),
    )

    response = client.get("/api/mcp/status")

    assert response.status_code == 200
    assert len(response.json()["servers"]) == 2

def test_frontend_index_is_served(client):
    """The browser entry point must return the HTML document."""

    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="message-form"' in response.text
    assert "/static/app.js" in response.text


def test_frontend_javascript_is_served(client):
    """The browser must be able to download the frontend logic."""

    response = client.get("/static/app.js")

    assert response.status_code == 200
    assert 'const CHAT_URL = "/api/chat"' in response.text


def test_frontend_stylesheet_is_served(client):
    """The stylesheet must be available from the same application."""

    response = client.get("/static/style.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_unknown_static_file_returns_404(client):
    """Missing assets must not masquerade as successful HTML responses."""

    response = client.get("/static/does-not-exist.js")

    assert response.status_code == 404
