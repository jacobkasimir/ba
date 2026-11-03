from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway_client import GatewayClient
from app.query_api import router


SQL = "SELECT COUNT(*) FROM public.patient_dimension"
HEADERS = {"X-Query-Action": "submit"}


def make_test_app(handler):
    @asynccontextmanager
    async def lifespan(app):
        gateway = GatewayClient(
            base_url="http://gateway.test",
            api_key="test-only-key",
            transport=httpx.MockTransport(handler),
        )
        app.state.gateway = gateway
        try:
            yield
        finally:
            await gateway.aclose()

    app = FastAPI(lifespan=lifespan)
    app.include_router(router)
    return app


@pytest.mark.parametrize(
    "gateway_body",
    [
        {"status": "ok", "count": 20},
        {"status": "suppressed", "count": None},
    ],
)
def test_success_response_is_preserved(gateway_body):
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/query"
        assert request.headers["X-Gateway-Key"] == "test-only-key"

        import json

        # Update this assertion if the real gateway contract differs.
        assert json.loads(request.content) == {"sql": SQL}

        return httpx.Response(200, json=gateway_body)

    with TestClient(make_test_app(handler)) as client:
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
    upstream_status,
    expected_status,
    expected_code,
):
    def handler(request):
        return httpx.Response(
            upstream_status,
            json={"detail": "private upstream diagnostic"},
        )

    with TestClient(make_test_app(handler)) as client:
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
def test_transport_errors(error_type, expected_status, expected_code):
    def handler(request):
        raise error_type("Simulated failure", request=request)

    with TestClient(make_test_app(handler)) as client:
        response = client.post(
            "/api/query",
            json={"sql": SQL},
            headers=HEADERS,
        )

    assert response.status_code == expected_status
    assert response.json()["detail"]["code"] == expected_code


def test_explicit_action_header_is_required():
    def handler(request):
        pytest.fail("The gateway must not be called")

    with TestClient(make_test_app(handler)) as client:
        response = client.post(
            "/api/query",
            json={"sql": SQL},
        )

    assert response.status_code == 403