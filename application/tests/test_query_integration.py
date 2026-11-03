import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main
from app.gateway_client import GatewayClient


SQL = "SELECT COUNT(*) FROM public.patient_dimension"
HEADERS = {"X-Query-Action": "submit"}


@pytest.fixture
def client_factory(tmp_path, monkeypatch):
    """Use the application with a mocked gateway for every test."""

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
    monkeypatch.setenv("APP_LOG_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setenv("APP_GATEWAY_URL", "http://gateway.test")
    monkeypatch.setenv("APP_GATEWAY_KEY", "test-only-key")

    def make_client(handler):
        def gateway_factory(**kwargs):
            return GatewayClient(
                base_url=kwargs["base_url"],
                api_key=kwargs["api_key"],
                timeout_seconds=kwargs["timeout_seconds"],
                transport=httpx.MockTransport(handler),
            )

        monkeypatch.setattr(main, "GatewayClient", gateway_factory)
        return TestClient(main.app)

    return make_client


@pytest.mark.parametrize(
    "gateway_body",
    [
        {"status": "ok", "count": 20},
        {"status": "suppressed", "count": None},
    ],
)
def test_success_response_is_preserved(client_factory, gateway_body):
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/query"
        assert request.headers["X-Gateway-Key"] == "test-only-key"
        assert json.loads(request.content) == {"sql": SQL}

        return httpx.Response(200, json=gateway_body)

    with client_factory(handler) as client:
        response = client.post(
            "/api/query",
            json={"sql": SQL},
            headers=HEADERS,
        )

    assert response.status_code == 200
    assert response.json() == gateway_body
    assert "X-Gateway-Key" not in response.headers


@pytest.mark.parametrize(
    ("upstream_status", "expected_status", "expected_code"),
    [
        (400, 422, "query_rejected"),
        (422, 422, "query_rejected"),
        (401, 502, "gateway_authentication_failed"),
        (403, 502, "gateway_authentication_failed"),
        (429, 503, "gateway_busy"),
        (500, 502, "gateway_error"),
    ],
)
def test_upstream_errors_are_sanitized(
    client_factory,
    upstream_status,
    expected_status,
    expected_code,
):
    def handler(request):
        return httpx.Response(
            upstream_status,
            json={"detail": "private upstream diagnostic"},
        )

    with client_factory(handler) as client:
        response = client.post(
            "/api/query",
            json={"sql": SQL},
            headers=HEADERS,
        )

    assert response.status_code == expected_status
    assert response.json()["detail"]["code"] == expected_code
    assert "private upstream diagnostic" not in response.text


@pytest.mark.parametrize(
    ("error_type", "expected_status", "expected_code"),
    [
        (httpx.ReadTimeout, 504, "gateway_timeout"),
        (httpx.ConnectError, 502, "gateway_unavailable"),
    ],
)
def test_transport_errors(
    client_factory,
    error_type,
    expected_status,
    expected_code,
):
    def handler(request):
        raise error_type("Simulated failure", request=request)

    with client_factory(handler) as client:
        response = client.post(
            "/api/query",
            json={"sql": SQL},
            headers=HEADERS,
        )

    assert response.status_code == expected_status
    assert response.json()["detail"]["code"] == expected_code


def test_explicit_action_header_is_required(client_factory):
    def handler(request):
        pytest.fail("The gateway must not be called")

    with client_factory(handler) as client:
        response = client.post(
            "/api/query",
            json={"sql": SQL},
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "explicit_query_action_required"
