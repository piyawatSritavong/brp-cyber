from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.services.redis_client import redis_client

logger = logging.getLogger("brp_cyber.dead_letter")
DEAD_LETTER_STREAM_KEY = "dead_letter_events"


def write_dead_letter(component: str, operation: str, payload: dict[str, object], error: str) -> None:
    message = {
        "component": component,
        "operation": operation,
        "payload": json.dumps(payload),
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        redis_client.xadd(DEAD_LETTER_STREAM_KEY, message, maxlen=50000, approximate=True)
    except Exception:
        logger.exception("dead_letter_write_failed", extra={"component": component, "operation": operation})
