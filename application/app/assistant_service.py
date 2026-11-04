import asyncio

from .assistant_bindings import normalize_gateway_result
from .assistant_models import (
    AssistantError,
    AssistantReply,
)
from .gateway_client import GatewayError


class AssistantService:
    def __init__(self, context_loader, llm, gateway) -> None:
        self._context_loader = context_loader
        self._llm = llm
        self._gateway = gateway

        # Per-process bound, not a distributed admission-control system.
        self._slots = asyncio.Semaphore(2)

    async def answer(self, question: str) -> AssistantReply:
        try:
            async with asyncio.timeout(0.25):
                await self._slots.acquire()
        except TimeoutError:
            raise AssistantError(
                503,
                "assistant_busy",
            ) from None

        try:
            async with asyncio.timeout(45):
                return await self._answer(question)
        except TimeoutError:
            raise AssistantError(
                504,
                "assistant_timeout",
            ) from None
        finally:
            self._slots.release()

    async def _answer(self, question: str) -> AssistantReply:
        context = await self._context_loader.load()
        decision = await self._llm.propose(question, context)

        if decision.action == "unsupported":
            return AssistantReply(status="unsupported")

        # LLMDecision validation guarantees a non-empty string here.
        sql = decision.sql
        assert sql is not None

        try:
            payload = await self._gateway.submit(sql)

        except GatewayError as exc:
            if exc.code == "query_rejected":
                return AssistantReply(
                    status="rejected",
                    proposed_sql=sql,
                )

            raise AssistantError(
                exc.status_code,
                exc.code,
            ) from None

        try:
            outcome = normalize_gateway_result(payload)
        except (ValueError, TypeError, KeyError):
            raise AssistantError(
                502,
                "invalid_gateway_response",
            ) from None

        return AssistantReply(
            status=outcome.status,
            proposed_sql=sql,
            count=outcome.count,
        )