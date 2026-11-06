from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.assistant_api import router
from app.assistant_models import AssistantError, LLMDecision
from app.assistant_service import AssistantService
from app.gateway_client import GatewayError


SQL = "SELECT COUNT(*) FROM public.patient_dimension"
HEADERS = {"X-Query-Action": "submit"}


def build_test_app(
    decision,
    gateway_payload=None,
    gateway_error=None,
    context_error=False,
):
    calls = {"context": 0, "llm": 0, "gateway": [], "language": None}

    async def load_context():
        calls["context"] += 1
        if context_error:
            raise AssistantError(503, "context_unavailable")
        return {"schema": {}, "policy": {}, "examples": {}}

    async def propose(question, context, language="de"):
        calls["llm"] += 1
        calls["language"] = language
        return decision

    async def submit(sql):
        calls["gateway"].append(sql)
        if gateway_error is not None:
            raise gateway_error
        return gateway_payload

    service = AssistantService(
        context_loader=SimpleNamespace(load=load_context),
        llm=SimpleNamespace(propose=propose),
        gateway=SimpleNamespace(submit=submit),
    )
    app = FastAPI()
    app.state.assistant = service
    app.include_router(router)
    return app, calls


@pytest.mark.parametrize("count", [0, 20])
def test_supported_question_returns_gateway_count(count):
    app, calls = build_test_app(
        decision=LLMDecision(action="propose", sql=SQL),
        gateway_payload={
            "request_id": "test-request",
            "status": "ok",
            "columns": ["patient_count"],
            "rows": [{"patient_count": count}],
            "executed_sql": SQL,
            "policy_version": "demo-patient-count-v1",
        },
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant",
            json={"question": "How many synthetic records exist?"},
            headers=HEADERS,
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "completed",
        "proposed_sql": SQL,
        "reason": None,
        "answer": None,
        "count": count,
    }
    assert calls["gateway"] == [SQL]
    assert calls["llm"] == 1


def test_unsupported_question_does_not_call_gateway():
    app, calls = build_test_app(
        decision=LLMDecision(action="unsupported", sql=None),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant",
            json={"question": "How many patients have diabetes?"},
            headers=HEADERS,
        )

    assert response.status_code == 200
    assert response.json()["status"] == "unsupported"
    assert calls["gateway"] == []


def test_unsupported_candidate_is_returned_without_calling_gateway():
    candidate = "SELECT * FROM public.patient_dimension"
    app, calls = build_test_app(
        decision=LLMDecision(
            action="unsupported",
            sql=candidate,
            reason="Individual patient rows are outside the supported scope.",
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant",
            json={"question": "Show patient rows", "language": "en"},
            headers=HEADERS,
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "unsupported",
        "proposed_sql": candidate,
        "reason": "Individual patient rows are outside the supported scope.",
        "answer": None,
        "count": None,
    }
    assert calls["gateway"] == []
    assert calls["language"] == "en"


def test_suppression_remains_null():
    app, calls = build_test_app(
        decision=LLMDecision(action="propose", sql=SQL),
        gateway_payload={
            "request_id": "test-request",
            "status": "suppressed",
            "columns": ["patient_count"],
            "rows": [{"patient_count": None}],
            "executed_sql": SQL,
            "policy_version": "demo-patient-count-v1",
        },
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant",
            json={"question": "Count the synthetic records."},
            headers=HEADERS,
        )

    assert response.json()["status"] == "suppressed"
    assert response.json()["count"] is None
    assert calls["gateway"] == [SQL]


def test_gateway_rejection_is_not_retried():
    proposed_sql = "SELECT * FROM public.patient_dimension"
    app, calls = build_test_app(
        decision=LLMDecision(action="propose", sql=proposed_sql),
        gateway_error=GatewayError(422, "query_rejected", "Rejected"),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant",
            json={"question": "Show records."},
            headers=HEADERS,
        )

    assert response.json()["status"] == "rejected"
    assert calls["gateway"] == [proposed_sql]


def test_missing_context_stops_before_llm():
    app, calls = build_test_app(
        decision=LLMDecision(action="propose", sql=SQL),
        context_error=True,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant",
            json={"question": "Count records."},
            headers=HEADERS,
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "context_unavailable"
    assert calls["llm"] == 0
    assert calls["gateway"] == []


def test_disabled_assistant_returns_503():
    app = FastAPI()
    app.state.assistant = None
    app.include_router(router)

    with TestClient(app) as client:
        response = client.post(
            "/api/assistant",
            json={"question": "Count records."},
            headers=HEADERS,
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "assistant_not_configured"
