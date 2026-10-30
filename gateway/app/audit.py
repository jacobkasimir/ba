import os
import sqlite3
from datetime import datetime, timezone


AUDIT_PATH = os.getenv(
    "AUDIT_PATH",
    "/app/audit/events.sqlite",
)


def initialize_audit():
    """Create a new event table without deleting previous audit records."""

    with sqlite3.connect(AUDIT_PATH, timeout=5) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS query_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                query_hash TEXT NOT NULL,
                reason_code TEXT,
                executed_sql TEXT
            )
            """
        )


def record_event(
    *,
    request_id: str,
    event: str,
    policy_version: str,
    query_hash: str,
    reason_code: str | None = None,
    executed_sql: str | None = None,
):
    """Persist one event.

    Do not store raw result values or the complete submitted SQL.
    Only gateway-owned executed SQL may be recorded here.
    """

    with sqlite3.connect(AUDIT_PATH, timeout=5) as connection:
        connection.execute(
            """
            INSERT INTO query_events (
                request_id,
                timestamp,
                event,
                policy_version,
                query_hash,
                reason_code,
                executed_sql
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                datetime.now(timezone.utc).isoformat(),
                event,
                policy_version,
                query_hash,
                reason_code,
                executed_sql,
            ),
        )