from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.redis_client import redis_client

OFFLOAD_STATE_KEY = "control_plane_audit_offload:last_id"
OFFLOAD_STATS_KEY = "control_plane_audit_offload:stats"
ARCHIVE_STREAM_KEY = "control_plane_audit_archive"


def _filesystem_offload(record: dict[str, Any]) -> str:
    root = Path(settings.control_plane_offload_filesystem_dir)
    root.mkdir(parents=True, exist_ok=True)

    day = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    target_dir = root / day
    target_dir.mkdir(parents=True, exist_ok=True)

    signature = str(record.get("signature", ""))
    name = f"offload_{signature[:16]}.json"
    target = target_dir / name

    if not target.exists():
        target.write_text(json.dumps(record, ensure_ascii=True, sort_keys=True), encoding="utf-8")
        target.chmod(0o444)

    return str(target)


def _s3_offload(record: dict[str, Any]) -> str:
    import boto3

    if not settings.control_plane_offload_s3_bucket:
        raise RuntimeError("s3_bucket_not_configured")

    session = boto3.session.Session(
        aws_access_key_id=settings.control_plane_offload_s3_access_key or None,
        aws_secret_access_key=settings.control_plane_offload_s3_secret_key or None,
        region_name=settings.control_plane_offload_s3_region or None,
    )
    client = session.client("s3", endpoint_url=settings.control_plane_offload_s3_endpoint_url or None)

    key = f"audit/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/offload_{str(record.get('signature', ''))[:16]}.json"
    body = json.dumps(record, ensure_ascii=True, sort_keys=True).encode("utf-8")

    kwargs: dict[str, Any] = {
        "Bucket": settings.control_plane_offload_s3_bucket,
        "Key": key,
        "Body": body,
        "ContentType": "application/json",
    }

    if settings.control_plane_offload_s3_object_lock_enabled:
        retain_until = datetime.now(timezone.utc) + timedelta(days=max(1, settings.control_plane_offload_s3_retention_days))
        kwargs["ObjectLockMode"] = "COMPLIANCE"
        kwargs["ObjectLockRetainUntilDate"] = retain_until

    client.put_object(**kwargs)
    return f"s3://{settings.control_plane_offload_s3_bucket}/{key}"


def _offload_record(record: dict[str, Any]) -> str:
    mode = settings.control_plane_offload_mode.lower().strip()
    if mode == "s3":
        return _s3_offload(record)
    return _filesystem_offload(record)


def offload_archive_batches(limit: int = 100) -> dict[str, Any]:
    last_id = redis_client.get(OFFLOAD_STATE_KEY) or "0-0"
    entries = redis_client.xrange(ARCHIVE_STREAM_KEY, min=f"({last_id}", max="+", count=max(1, limit))

    if not entries:
        return {"status": "no_new_records", "offloaded": 0, "last_id": last_id}

    offloaded = 0
    new_last_id = last_id
    last_object_path = ""

    for event_id, fields in entries:
        record = dict(fields)
        object_path = _offload_record(record)
        offloaded += 1
        new_last_id = event_id
        last_object_path = object_path

    redis_client.set(OFFLOAD_STATE_KEY, new_last_id)
    redis_client.hincrby(OFFLOAD_STATS_KEY, "offloaded_records", offloaded)
    redis_client.hset(
        OFFLOAD_STATS_KEY,
        mapping={
            "last_id": new_last_id,
            "last_object_path": last_object_path,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "mode": settings.control_plane_offload_mode,
        },
    )

    return {
        "status": "success",
        "offloaded": offloaded,
        "last_id": new_last_id,
        "last_object_path": last_object_path,
        "mode": settings.control_plane_offload_mode,
    }


def offload_status() -> dict[str, Any]:
    stats = redis_client.hgetall(OFFLOAD_STATS_KEY)
    return {
        "mode": stats.get("mode", settings.control_plane_offload_mode),
        "last_id": redis_client.get(OFFLOAD_STATE_KEY) or stats.get("last_id", "0-0"),
        "offloaded_records": int(stats.get("offloaded_records", "0")),
        "last_object_path": stats.get("last_object_path", ""),
        "updated_at": stats.get("updated_at", ""),
    }
