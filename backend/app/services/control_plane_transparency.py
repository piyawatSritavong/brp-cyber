from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.control_plane_audit_pack_publication import publication_status
from app.services.redis_client import redis_client

TRANSPARENCY_STREAM_KEY = "control_plane_transparency_log"
TRANSPARENCY_STATE_KEY = "control_plane_transparency_log:last_hash"


def _entry_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _filesystem_append(entry: dict[str, Any]) -> str:
    root = Path(settings.control_plane_transparency_filesystem_dir)
    root.mkdir(parents=True, exist_ok=True)

    path = root / f"transparency_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=True) + "\n")
    return str(path)


def _s3_append(entry: dict[str, Any]) -> str:
    import boto3

    bucket = settings.control_plane_transparency_s3_bucket
    if not bucket:
        raise RuntimeError("transparency_s3_bucket_not_configured")

    session = boto3.session.Session(
        aws_access_key_id=settings.control_plane_transparency_s3_access_key or None,
        aws_secret_access_key=settings.control_plane_transparency_s3_secret_key or None,
        region_name=settings.control_plane_transparency_s3_region or None,
    )
    client = session.client("s3", endpoint_url=settings.control_plane_transparency_s3_endpoint_url or None)

    prefix = settings.control_plane_transparency_s3_prefix.strip("/")
    key = f"{prefix}/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/entry_{entry['entry_hash'][:16]}.json" if prefix else f"transparency/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/entry_{entry['entry_hash'][:16]}.json"

    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(entry, ensure_ascii=True, sort_keys=True).encode("utf-8"),
        ContentType="application/json",
    )
    return f"s3://{bucket}/{key}"


def publish_transparency_entry(dry_run: bool = False) -> dict[str, Any]:
    latest = publication_status(limit=1)
    rows = latest.get("rows", [])
    if not rows:
        return {"status": "no_publication"}

    row = rows[0]
    prev_hash = redis_client.get(TRANSPARENCY_STATE_KEY) or ""

    base = {
        "publication_id": row.get("publication_id", ""),
        "pack_id": row.get("pack_id", ""),
        "manifest_path": row.get("manifest_path", ""),
        "archive_object": row.get("archive_object", ""),
        "metadata_object": row.get("metadata_object", ""),
        "mode": row.get("mode", ""),
        "published_at": row.get("published_at", ""),
        "valid": bool(row.get("valid", False)),
        "prev_hash": prev_hash,
        "transparency_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    entry_hash = _entry_hash(base)
    entry = {**base, "entry_hash": entry_hash}

    if dry_run:
        return {"status": "dry_run", "entry": entry}

    mode = settings.control_plane_transparency_mode.lower().strip()
    if mode == "s3":
        target = _s3_append(entry)
    else:
        target = _filesystem_append(entry)

    event_id = redis_client.xadd(
        TRANSPARENCY_STREAM_KEY,
        {
            "publication_id": str(entry["publication_id"]),
            "pack_id": str(entry["pack_id"]),
            "entry_hash": str(entry_hash),
            "prev_hash": str(prev_hash),
            "target": str(target),
            "timestamp": str(entry["transparency_timestamp"]),
            "mode": mode,
        },
        maxlen=200000,
        approximate=True,
    )
    redis_client.set(TRANSPARENCY_STATE_KEY, entry_hash)

    return {
        "status": "published",
        "event_id": event_id,
        "entry_hash": entry_hash,
        "prev_hash": prev_hash,
        "target": target,
        "mode": mode,
    }


def transparency_status(limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(TRANSPARENCY_STREAM_KEY, count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)

    return {
        "last_hash": redis_client.get(TRANSPARENCY_STATE_KEY) or "",
        "count": len(rows),
        "rows": rows,
    }
