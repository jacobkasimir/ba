import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


logger = logging.getLogger("uvicorn.error")


class EventLog:
    """Append small, sanitized operational events as JSON Lines.

    This is separate from the gateway's query audit database.
    """

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def write(self, event: str, **fields):
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **fields,
        }

        try:
            # The lock coordinates writes within this single process.
            with self._lock:
                with self.path.open(
                    "a",
                    encoding="utf-8",
                ) as file:
                    file.write(
                        json.dumps(record, ensure_ascii=False)
                        + "\n"
                    )

        except OSError:
            # Operational logging is best effort in this stage.
            # This does NOT change the gateway's fail-closed audit rule.
            logger.error("Application event log write failed")