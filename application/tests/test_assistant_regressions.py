import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import main


def test_application_starts_without_model_configuration(tmp_path, monkeypatch):
    config_path = tmp_path / "mcp_servers.json"
    config_path.write_text(
        json.dumps({
            "servers": {
                "schema": {
                    "transport": "streamable_http",
                    "url": "http://mcp-schema:8000/mcp",
                    "tools": ["get_schema"],
                    "timeout_seconds": 2,
                }
            }
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("MCP_CONFIG_PATH", str(config_path))
    monkeypatch.setenv("APP_LOG_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setenv("LLM_ENABLED", "false")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("APP_GATEWAY_URL", raising=False)
    monkeypatch.delenv("APP_GATEWAY_KEY", raising=False)

    with TestClient(main.app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_explicit_query_contract_remains_available():
    app = FastAPI()
    app.include_router(main.query_router)
    app.state.gateway = None

    with TestClient(app) as client:
        response = client.post(
            "/api/query",
            json={"sql": "SELECT 1"},
            headers={"X-Query-Action": "submit"},
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "gateway_unavailable"
