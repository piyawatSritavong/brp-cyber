from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from app.core.config import settings
from app.services.redis_client import redis_client

FAILED_BATCH_STREAM = "control_plane_audit:failed_batches"
RECOVERY_HISTORY_STREAM = "control_plane_audit:recovery_history"
ACK_HISTORY_STREAM = "control_plane_audit:ack_history"


def _sender(payload: dict[str, Any]) -> int:
    if not settings.control_plane_siem_webhook_url:
        raise RuntimeError("siem_webhook_not_configured")

    headers = {"content-type": "application/json"}
    if settings.control_plane_siem_api_key:
        headers["authorization"] = f"Bearer {settings.control_plane_siem_api_key}"

    with httpx.Client(timeout=10.0) as client:
        response = client.post(settings.control_plane_siem_webhook_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.status_code


def write_failed_batch(payload: dict[str, Any], error: str) -> str:
    return redis_client.xadd(
        FAILED_BATCH_STREAM,
        {
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "payload": json.dumps(payload),
            "error": error,
            "replayed": "0",
        },
        maxlen=200000,
        approximate=True,
    )


def list_failed_batches(limit: int = 100) -> list[dict[str, str]]:
    entries = redis_client.xrevrange(FAILED_BATCH_STREAM, count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return rows


def replay_failed_batches(limit: int = 50, sender: Callable[[dict[str, Any]], int] | None = None) -> dict[str, Any]:
    sender_fn = sender or _sender
    entries = redis_client.xrange(FAILED_BATCH_STREAM, min="-", max="+", count=max(1, limit))

    replayed = 0
    skipped = 0
    failed = 0

    for event_id, fields in entries:
        replay_key = f"control_plane_audit:failed_batch:replayed:{event_id}"
        if redis_client.exists(replay_key):
            skipped += 1
            continue

        payload_raw = fields.get("payload", "{}")
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError:
            failed += 1
            continue

        try:
            status = sender_fn(payload)
            redis_client.xadd(
                RECOVERY_HISTORY_STREAM,
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "failed_batch_id": event_id,
                    "status": "replayed",
                    "status_code": str(status),
                },
                maxlen=100000,
                approximate=True,
            )
            redis_client.set(replay_key, "1")
            replayed += 1
        except Exception:
            failed += 1

    return {
        "replayed": replayed,
        "skipped": skipped,
        "failed": failed,
    }


def acknowledge_failed_batch(failed_batch_id: str, ack_ref: str) -> dict[str, str]:
    ack_key = f"control_plane_audit:failed_batch:acked:{failed_batch_id}"
    redis_client.set(ack_key, ack_ref)
    redis_client.xadd(
        ACK_HISTORY_STREAM,
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "failed_batch_id": failed_batch_id,
            "ack_ref": ack_ref,
        },
        maxlen=100000,
        approximate=True,
    )
    return {"status": "acked", "failed_batch_id": failed_batch_id, "ack_ref": ack_ref}


def reconcile_failed_batches(limit: int = 1000) -> dict[str, Any]:
    entries = redis_client.xrange(FAILED_BATCH_STREAM, min="-", max="+", count=max(1, limit))

    total = len(entries)
    replayed = 0
    acked = 0
    unresolved = 0

    unresolved_rows: list[dict[str, str]] = []

    for event_id, fields in entries:
        replay_key = f"control_plane_audit:failed_batch:replayed:{event_id}"
        ack_key = f"control_plane_audit:failed_batch:acked:{event_id}"

        is_replayed = bool(redis_client.exists(replay_key))
        is_acked = bool(redis_client.exists(ack_key))

        if is_replayed:
            replayed += 1
        if is_acked:
            acked += 1
        if not is_replayed and not is_acked:
            unresolved += 1
            unresolved_rows.append(
                {
                    "failed_batch_id": event_id,
                    "failed_at": fields.get("failed_at", ""),
                    "error": fields.get("error", ""),
                }
            )

    return {
        "total_failed_batches": total,
        "replayed_count": replayed,
        "acked_count": acked,
        "unresolved_count": unresolved,
        "unresolved_rows": unresolved_rows[:100],
    }


def recovery_status(limit: int = 100) -> dict[str, Any]:
    history_entries = redis_client.xrevrange(RECOVERY_HISTORY_STREAM, count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in history_entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)

    ack_entries = redis_client.xrevrange(ACK_HISTORY_STREAM, count=max(1, limit))
    ack_rows: list[dict[str, str]] = []
    for event_id, fields in ack_entries:
        row = {"id": event_id}
        row.update(fields)
        ack_rows.append(row)

    return {
        "failed_batches_count": len(list_failed_batches(limit=1000)),
        "history_count": len(rows),
        "history": rows,
        "ack_history_count": len(ack_rows),
        "ack_history": ack_rows,
    }
