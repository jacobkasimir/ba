import sqlite3
from datetime import datetime, timezone

AUDIT_PATH = "/app/audit/events.sqlite"


def initialize_audit():
    """Create local audit storage if it does not already exist."""
    with sqlite3.connect(AUDIT_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                request_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                outcome TEXT NOT NULL
            )
            """
        )


def record_event(request_id: str, action: str, outcome: str):
    """Persist an event before a result is released to the caller."""
    with sqlite3.connect(AUDIT_PATH) as connection:
        connection.execute(
            """
            INSERT INTO events
                (request_id, timestamp, action, outcome)
            VALUES (?, ?, ?, ?)
            """,
            (
                request_id,
                datetime.now(timezone.utc).isoformat(),
                action,
                outcome,
            ),
        )