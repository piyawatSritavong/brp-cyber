from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from app.core.config import settings
from app.services.audit_archive import archive_export_batch
from app.services.audit_recovery import write_failed_batch
from app.services.dead_letter import write_dead_letter
from app.services.redis_client import redis_client

from app.services.audit import CONTROL_PLANE_AUDIT_STREAM

LAST_EXPORTED_ID_KEY = "control_plane_audit:last_exported_id"
EXPORT_STATS_KEY = "control_plane_audit:export_stats"


def _default_sender(payload: dict[str, Any]) -> int:
    if not settings.control_plane_siem_webhook_url:
        raise RuntimeError("siem_webhook_not_configured")

    headers = {"content-type": "application/json"}
    if settings.control_plane_siem_api_key:
        headers["authorization"] = f"Bearer {settings.control_plane_siem_api_key}"

    with httpx.Client(timeout=10.0) as client:
        response = client.post(settings.control_plane_siem_webhook_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.status_code


def export_control_plane_audit_to_siem(
    batch_size: int | None = None,
    sender: Callable[[dict[str, Any]], int] | None = None,
) -> dict[str, Any]:
    sender_fn = sender or _default_sender
    max_batch = max(1, batch_size or settings.control_plane_audit_export_batch_size)

    last_id = redis_client.get(LAST_EXPORTED_ID_KEY) or "0-0"
    entries = redis_client.xrange(CONTROL_PLANE_AUDIT_STREAM, min=f"({last_id}", max="+", count=max_batch)

    if not entries:
        return {"status": "no_new_events", "exported": 0, "last_id": last_id}

    payload_events = []
    new_last_id = last_id
    for event_id, fields in entries:
        event = {"id": event_id}
        event.update(fields)
        details = event.get("details")
        if details and isinstance(details, str):
            try:
                event["details"] = json.loads(details)
            except json.JSONDecodeError:
                pass
        payload_events.append(event)
        new_last_id = event_id

    payload = {
        "source": "brp-cyber-control-plane",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "events": payload_events,
    }

    try:
        status_code = sender_fn(payload)
    except Exception as exc:
        write_failed_batch(payload=payload, error=str(exc))
        write_dead_letter(
            component="audit_export",
            operation="export_control_plane_audit_to_siem",
            payload={"count": len(payload_events), "last_id": last_id},
            error=str(exc),
        )
        redis_client.hincrby(EXPORT_STATS_KEY, "failed_batches", 1)
        redis_client.hset(EXPORT_STATS_KEY, mapping={"last_error": str(exc), "updated_at": datetime.now(timezone.utc).isoformat()})
        return {"status": "failed", "exported": 0, "error": str(exc), "last_id": last_id}

    redis_client.set(LAST_EXPORTED_ID_KEY, new_last_id)
    redis_client.hincrby(EXPORT_STATS_KEY, "successful_batches", 1)
    redis_client.hincrby(EXPORT_STATS_KEY, "exported_events", len(payload_events))
    redis_client.hset(
        EXPORT_STATS_KEY,
        mapping={
            "last_status_code": str(status_code),
            "last_exported_id": new_last_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    archive = archive_export_batch(payload=payload, exported_count=len(payload_events))

    return {
        "status": "success",
        "exported": len(payload_events),
        "last_id": new_last_id,
        "status_code": status_code,
        "archive_signature": archive["signature"],
        "archive_file": archive["archive_file"],
    }


def get_export_status() -> dict[str, Any]:
    stats = redis_client.hgetall(EXPORT_STATS_KEY)
    return {
        "last_exported_id": redis_client.get(LAST_EXPORTED_ID_KEY) or "0-0",
        "successful_batches": int(stats.get("successful_batches", "0")),
        "failed_batches": int(stats.get("failed_batches", "0")),
        "exported_events": int(stats.get("exported_events", "0")),
        "last_status_code": stats.get("last_status_code", ""),
        "last_error": stats.get("last_error", ""),
        "updated_at": stats.get("updated_at", ""),
    }
