from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from .assistant_models import (
    AssistantError,
    AssistantReply,
    AssistantRequest,
)


router = APIRouter()


@router.post(
    "/api/assistant",
    response_model=AssistantReply,
)
async def ask_assistant(
    body: AssistantRequest,
    request: Request,
    query_action: str | None = Header(
        default=None,
        alias="X-Query-Action",
    ),
):
    if query_action != "submit":
        return JSONResponse(
            status_code=403,
            content={
                "detail": {
                    "code": "explicit_query_action_required",
                }
            },
        )

    assistant = getattr(
        request.app.state,
        "assistant",
        None,
    )

    if assistant is None:
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": "assistant_not_configured",
                }
            },
        )

    try:
        return await assistant.answer(body.question, body.language)

    except AssistantError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": {
                    "code": exc.code,
                }
            },
        )