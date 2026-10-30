import os
import secrets
import sqlite3
from contextlib import asynccontextmanager
from uuid import uuid4

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException

from .audit import initialize_audit, record_event
from .database import open_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize required local storage before accepting requests."""
    initialize_audit()
    yield


app = FastAPI(lifespan=lifespan)

API_KEY = os.environ["GATEWAY_API_KEY"]
MIN_CELL_COUNT = int(os.environ.get("MIN_CELL_COUNT", "5"))

if MIN_CELL_COUNT < 5:
    raise RuntimeError("MIN_CELL_COUNT must be at least 5")


def require_gateway_key(
    x_gateway_key: str = Header(default=""),
):
    """Authenticate internal callers, independently of the LLM."""
    if not secrets.compare_digest(x_gateway_key, API_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health/live")
def live():
    """Liveness: the HTTP application is running."""
    return {"status": "running"}


@app.get(
    "/health/ready",
    dependencies=[Depends(require_gateway_key)],
)
def ready():
    """Readiness: the gateway can communicate with PostgreSQL."""
    try:
        with open_database() as connection:
            connection.execute("SELECT 1")
    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )

    return {"status": "ready"}


@app.get(
    "/demo/patient-count",
    dependencies=[Depends(require_gateway_key)],
)
def patient_count():
    """
    Execute a fixed aggregate.

    No client-provided SQL is accepted at this implementation stage.
    """

    request_id = str(uuid4())

    try:
        with open_database() as connection:
            with connection.transaction():
                # Defense in depth alongside the restricted DB role.
                connection.execute("SET TRANSACTION READ ONLY")
                connection.execute(
                    "SET LOCAL statement_timeout = '5s'"
                )

                row = connection.execute(
                    "SELECT COUNT(*) "
                    "FROM public.patient_dimension"
                ).fetchone()

                count = int(row[0])

    except psycopg.Error:
        raise HTTPException(
            status_code=503,
            detail="Database query failed",
        )

    # Demonstration only:
    # Zero and small positive values have different meanings.
    suppressed = 0 < count < MIN_CELL_COUNT

    result = {
        "request_id": request_id,
        "status": "suppressed" if suppressed else "ok",
        "count": None if suppressed else count,
        "executed_sql": (
            "SELECT COUNT(*) FROM public.patient_dimension"
        ),
    }

    try:
        record_event(
            request_id=request_id,
            action="demo_patient_count",
            outcome=result["status"],
        )
    except sqlite3.Error:
        # Fail closed: do not release results without required auditing.
        raise HTTPException(
            status_code=503,
            detail="Audit storage unavailable",
        )

    return result