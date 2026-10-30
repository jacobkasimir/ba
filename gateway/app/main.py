import hashlib
import logging
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager
from uuid import uuid4

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException

from .audit import initialize_audit, record_event
from .database import open_database
from .execution import execute_plan, suppress_count
from .policy import (
    EXECUTED_SQL,
    POLICY_VERSION,
    SUPPORTED_PROPOSAL,
    PolicyViolation,
    approve_query,
)
from .schemas import CountRow, QueryRequest, QueryResponse


logger = logging.getLogger("uvicorn.error")

API_KEY = os.environ["GATEWAY_API_KEY"]
MIN_CELL_COUNT = int(os.environ.get("MIN_CELL_COUNT", "5"))

if not API_KEY:
    raise RuntimeError("GATEWAY_API_KEY must not be empty")

if MIN_CELL_COUNT < 5:
    raise RuntimeError("MIN_CELL_COUNT must be at least 5")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail startup if required audit storage cannot be initialized.
    initialize_audit()
    yield


app = FastAPI(
    title="Local AKTIN Query Gateway",
    lifespan=lifespan,
)


def require_gateway_key(
    x_gateway_key: str = Header(default=""),
):
    """Authenticate the application calling the gateway."""

    if not secrets.compare_digest(x_gateway_key, API_KEY):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
        )


def audit_or_fail(**event):
    """Do not continue or release results if required auditing fails."""

    try:
        record_event(**event)
    except sqlite3.Error:
        logger.error(
            "Audit write failed for request %s",
            event.get("request_id"),
        )

        raise HTTPException(
            status_code=503,
            detail="Audit storage unavailable",
        ) from None


def process_query(request: QueryRequest) -> QueryResponse:
    """Run the complete deterministic enforcement pipeline."""

    request_id = str(uuid4())

    # Hash the input instead of storing the complete submitted SQL.
    query_hash = hashlib.sha256(
        request.sql.encode("utf-8")
    ).hexdigest()

    common_audit_fields = {
        "request_id": request_id,
        "policy_version": POLICY_VERSION,
        "query_hash": query_hash,
    }

    # Persist receipt before attempting validation or database execution.
    audit_or_fail(
        **common_audit_fields,
        event="received",
    )

    try:
        plan = approve_query(request.sql)
    except PolicyViolation as error:
        audit_or_fail(
            **common_audit_fields,
            event="blocked",
            reason_code=error.code,
        )

        raise HTTPException(
            status_code=422,
            detail={
                "request_id": request_id,
                "code": error.code,
                "message": error.message,
            },
        ) from None

    try:
        actual_count = execute_plan(plan)

    except psycopg.Error as error:
        # Log only diagnostic metadata, not credentials or raw row data.
        logger.error(
            "Database failure: request=%s sqlstate=%s",
            request_id,
            error.sqlstate,
        )

        audit_or_fail(
            **common_audit_fields,
            event="execution_failed",
            reason_code="database_error",
        )

        raise HTTPException(
            status_code=503,
            detail="Database query failed",
        ) from None

    released_count = suppress_count(
        actual_count,
        MIN_CELL_COUNT,
    )

    status = (
        "suppressed"
        if released_count is None
        else "ok"
    )

    # This event must be durable before we return the approved result.
    audit_or_fail(
        **common_audit_fields,
        event=status,
        executed_sql=EXECUTED_SQL,
    )

    return QueryResponse(
        request_id=request_id,
        status=status,
        columns=["patient_count"],
        rows=[
            CountRow(patient_count=released_count)
        ],
        executed_sql=EXECUTED_SQL,
        policy_version=POLICY_VERSION,
    )


@app.get("/health/live")
def live():
    """Liveness checks the application, not the database."""
    return {"status": "running"}


@app.get(
    "/health/ready",
    dependencies=[Depends(require_gateway_key)],
)
def ready():
    """Readiness checks basic database connectivity."""

    try:
        with open_database() as connection:
            connection.execute("SELECT 1")
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from None

    return {"status": "ready"}


@app.post(
    "/query",
    response_model=QueryResponse,
    dependencies=[Depends(require_gateway_key)],
)
def query(request: QueryRequest):
    """Accept an untrusted proposal and enforce the gateway policy."""
    return process_query(request)


@app.get(
    "/demo/patient-count",
    dependencies=[Depends(require_gateway_key)],
)
def demo_patient_count():
    """Keep the old demo URL, but route it through the new enforcement."""

    result = process_query(
        QueryRequest(sql=SUPPORTED_PROPOSAL)
    )

    # Preserve the basic response shape of your Stage 7 demo.
    return {
        "request_id": result.request_id,
        "status": result.status,
        "count": result.rows[0].patient_count,
        "executed_sql": result.executed_sql,
    }