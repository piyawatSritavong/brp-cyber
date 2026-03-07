from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.services.redis_client import redis_client

CONTROL_PLANE_AUDIT_STREAM = "control_plane_audit"


def write_control_plane_audit(
    actor: str,
    action: str,
    status: str,
    target: str,
    details: dict[str, Any] | None = None,
) -> str:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "status": status,
        "target": target,
        "details": json.dumps(details or {}),
    }
    return redis_client.xadd(CONTROL_PLANE_AUDIT_STREAM, payload, maxlen=200000, approximate=True)


def list_control_plane_audit(limit: int = 100) -> list[dict[str, str]]:
    entries = redis_client.xrevrange(CONTROL_PLANE_AUDIT_STREAM, count=max(1, limit))
    result: list[dict[str, str]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        result.append(row)
    return result
