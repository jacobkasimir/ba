from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from .gateway_client import GatewayError


router = APIRouter()


class QueryProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Application-side input bound; align with the gateway's actual limit.
    sql: str = Field(min_length=1, max_length=10_000)


@router.post("/api/query")
async def submit_query(
    proposal: QueryProposal,
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
                    "message": "Use the application's query submission action.",
                }
            },
        )

    try:
        result = await request.app.state.gateway.submit(proposal.sql)
    except GatewayError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": {
                    "code": exc.code,
                    "message": exc.message,
                }
            },
        )

    return JSONResponse(content=result)