from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    """An untrusted SQL proposal received from an authenticated caller."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    # Limit request size before parsing.
    # This is not a full resource-control policy, but it bounds this input.
    sql: str = Field(
        min_length=1,
        max_length=4000,
        strict=True,
    )


class CountRow(BaseModel):
    """One approved aggregate row.

    None means that the value was suppressed.
    It must not be interpreted as zero.
    """

    patient_count: int | None


class QueryResponse(BaseModel):
    """The information permitted to leave the gateway."""

    request_id: str
    status: Literal["ok", "suppressed"]
    columns: list[str]
    rows: list[CountRow]

    # This is the SQL actually executed by the gateway.
    executed_sql: str

    # Records which validation policy produced the decision.
    policy_version: str