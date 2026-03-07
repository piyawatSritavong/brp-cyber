from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.redis_client import redis_client

IMMUTABLE_STORE_ROOT = "control_plane_immutable_store"


def _store_dir() -> Path:
    root = Path(settings.control_plane_immutable_store_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _day_partition() -> str:
    return datetime.now(timezone.utc).strftime("%Y/%m/%d")


def persist_archive_record(record: dict[str, Any]) -> dict[str, str]:
    root = _store_dir() / _day_partition()
    root.mkdir(parents=True, exist_ok=True)

    signature = str(record.get("signature", ""))
    filename = f"audit_batch_{signature[:16]}.json"
    target = root / filename
    metadata_file = root / f"{filename}.meta"

    if target.exists():
        return {
            "status": "exists",
            "object_path": str(target),
            "metadata_path": str(metadata_file),
        }

    target.write_text(json.dumps(record, ensure_ascii=True, sort_keys=True), encoding="utf-8")
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "immutable": "true",
        "signature": signature,
        "payload_hash": str(record.get("payload_hash", "")),
    }
    metadata_file.write_text(json.dumps(metadata, ensure_ascii=True, sort_keys=True), encoding="utf-8")

    # WORM-like local behavior: mark readonly.
    target.chmod(0o444)
    metadata_file.chmod(0o444)

    redis_client.hset(
        IMMUTABLE_STORE_ROOT,
        mapping={
            "last_object_path": str(target),
            "last_signature": signature,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "status": "stored",
        "object_path": str(target),
        "metadata_path": str(metadata_file),
    }


def immutable_store_status() -> dict[str, str]:
    data = redis_client.hgetall(IMMUTABLE_STORE_ROOT)
    return {
        "last_object_path": data.get("last_object_path", ""),
        "last_signature": data.get("last_signature", ""),
        "updated_at": data.get("updated_at", ""),
        "store_root": str(_store_dir()),
    }


def export_store_snapshot(destination_dir: str) -> dict[str, str]:
    src = _store_dir()
    dst = Path(destination_dir)
    dst.mkdir(parents=True, exist_ok=True)

    snapshot_name = f"immutable_snapshot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    snapshot_path = dst / snapshot_name
    shutil.copytree(src, snapshot_path)

    return {"status": "ok", "snapshot_path": str(snapshot_path)}
