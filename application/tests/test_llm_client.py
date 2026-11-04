import asyncio
import json

import httpx
import pytest

from app.assistant_models import AssistantError
from app.llm_client import LLMClient


BASE_URL = "https://llm.test/v1"
GOOD_DECISION = {"action": "propose", "sql": "SELECT COUNT(*) FROM public.patient_dimension"}


def completion(content, *, finish_reason="stop", message_extra=None, choice_extra=None):
    message = {"role": "assistant", "content": content, **(message_extra or {})}
    choice = {"finish_reason": finish_reason, "message": message, **(choice_extra or {})}
    return {"choices": [choice]}


def make_client(handler):
    return LLMClient(
        BASE_URL,
        "test-key",
        "test-model",
        transport=httpx.MockTransport(handler),
    )


def test_valid_structured_decision():
    def handler(request):
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer test-key"
        payload = json.loads(request.content)
        assert payload["model"] == "test-model"
        assert payload["response_format"]["type"] == "json_schema"
        assert payload["max_completion_tokens"] == 512
        assert "max_tokens" not in payload
        return httpx.Response(200, json=completion(json.dumps(GOOD_DECISION)))

    async def run():
        client = make_client(handler)
        try:
            decision = await client.propose("Count rows", {})
            assert decision.action == "propose"
            assert decision.sql == GOOD_DECISION["sql"]
        finally:
            await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize(
    "body",
    [
        completion("not-json"),
        completion(json.dumps({"action": "propose"})),
        completion(json.dumps({**GOOD_DECISION, "extra": True})),
        completion(json.dumps({"action": "unsupported", "sql": "SELECT 1"})),
        completion(json.dumps(GOOD_DECISION), finish_reason="length"),
        completion(json.dumps(GOOD_DECISION), message_extra={"refusal": "No."}),
        completion(json.dumps(GOOD_DECISION), message_extra={"tool_calls": [{"id": "x"}]}),
    ],
    ids=["invalid-json", "missing-field", "extra-field", "unsupported-with-sql", "truncated", "refusal", "tool-call"],
)
def test_invalid_provider_decisions_are_rejected(body):
    def handler(request):
        return httpx.Response(200, json=body)

    async def run():
        client = make_client(handler)
        try:
            with pytest.raises(AssistantError) as error:
                await client.propose("Count rows", {})
            assert error.value.code == "invalid_llm_response"
        finally:
            await client.aclose()

    asyncio.run(run())


def test_provider_timeout_is_sanitized():
    def handler(request):
        raise httpx.ReadTimeout("private timeout details", request=request)

    async def run():
        client = make_client(handler)
        try:
            with pytest.raises(AssistantError) as error:
                await client.propose("Count rows", {})
            assert error.value.status_code == 504
            assert error.value.code == "llm_timeout"
        finally:
            await client.aclose()

    asyncio.run(run())


def test_provider_authentication_error_is_sanitized():
    def handler(request):
        return httpx.Response(401, json={"detail": "private provider diagnostic"})

    async def run():
        client = make_client(handler)
        try:
            with pytest.raises(AssistantError) as error:
                await client.propose("Count rows", {})
            assert error.value.status_code == 502
            assert error.value.code == "llm_provider_error"
            assert error.value.provider_status_code == 401
            assert "private" not in str(error.value)
        finally:
            await client.aclose()

    asyncio.run(run())


def test_provider_request_error_retains_bounded_diagnostic_fields():
    def handler(request):
        return httpx.Response(
            400,
            json={
                "error": {
                    "type": "invalid_request_error",
                    "code": "unsupported_parameter",
                    "param": "response_format",
                    "message": "This deployment does not support response_format.",
                }
            },
        )

    async def run():
        client = make_client(handler)
        try:
            with pytest.raises(AssistantError) as error:
                await client.propose("Count rows", {})
            assert error.value.provider_status_code == 400
            assert error.value.provider_error_code == "unsupported_parameter"
            assert error.value.provider_error_param == "response_format"
            assert "does not support" in error.value.provider_error_message
        finally:
            await client.aclose()

    asyncio.run(run())


def test_oversized_provider_response_is_rejected():
    def handler(request):
        return httpx.Response(200, content=b" " * (64 * 1024 + 1))

    async def run():
        client = make_client(handler)
        try:
            with pytest.raises(AssistantError) as error:
                await client.propose("Count rows", {})
            assert error.value.code == "invalid_llm_response"
        finally:
            await client.aclose()

    asyncio.run(run())


