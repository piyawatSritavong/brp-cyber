from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services import audit_immutable_store as _audit_immutable_store
from app.services.audit_immutable_store import persist_archive_record
from app.services.redis_client import redis_client

ARCHIVE_STATE_KEY = "control_plane_audit_archive:last_signature"
ARCHIVE_STREAM_KEY = "control_plane_audit_archive"


def _archive_dir() -> Path:
    path = Path(settings.control_plane_audit_archive_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sign(message: str) -> str:
    key = settings.control_plane_audit_archive_hmac_key.encode("utf-8")
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()


def archive_export_batch(payload: dict[str, Any], exported_count: int) -> dict[str, str | int]:
    _audit_immutable_store.redis_client = redis_client
    generated_at = datetime.now(timezone.utc).isoformat()
    payload_hash = _payload_hash(payload)
    prev_signature = redis_client.get(ARCHIVE_STATE_KEY) or ""

    message = f"{generated_at}|{payload_hash}|{prev_signature}|{exported_count}"
    signature = _sign(message)

    record = {
        "generated_at": generated_at,
        "payload_hash": payload_hash,
        "prev_signature": prev_signature,
        "signature": signature,
        "exported_count": str(exported_count),
    }

    redis_client.xadd(ARCHIVE_STREAM_KEY, record, maxlen=200000, approximate=True)
    redis_client.set(ARCHIVE_STATE_KEY, signature)

    archive_file = _archive_dir() / f"audit_export_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
    with archive_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=True) + "\n")

    immutable = persist_archive_record(record)

    return {
        "generated_at": generated_at,
        "payload_hash": payload_hash,
        "signature": signature,
        "prev_signature": prev_signature,
        "archive_file": str(archive_file),
        "exported_count": exported_count,
        "immutable_object_path": immutable.get("object_path", ""),
        "immutable_metadata_path": immutable.get("metadata_path", ""),
    }


def archive_status(limit: int = 20) -> dict[str, Any]:
    entries = redis_client.xrevrange(ARCHIVE_STREAM_KEY, count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)

    return {
        "last_signature": redis_client.get(ARCHIVE_STATE_KEY) or "",
        "count": len(rows),
        "rows": rows,
    }


def verify_archive_chain(limit: int = 1000) -> dict[str, Any]:
    entries = redis_client.xrange(ARCHIVE_STREAM_KEY, min="-", max="+", count=max(1, limit))
    prev_signature = ""

    for idx, (_, fields) in enumerate(entries):
        message = f"{fields.get('generated_at','')}|{fields.get('payload_hash','')}|{fields.get('prev_signature','')}|{fields.get('exported_count','0')}"
        expected_signature = _sign(message)

        if fields.get("prev_signature", "") != prev_signature:
            return {"valid": False, "index": idx, "reason": "prev_signature_mismatch"}
        if fields.get("signature", "") != expected_signature:
            return {"valid": False, "index": idx, "reason": "signature_mismatch"}

        prev_signature = fields.get("signature", "")

    return {"valid": True, "checked": len(entries), "last_signature": prev_signature}
