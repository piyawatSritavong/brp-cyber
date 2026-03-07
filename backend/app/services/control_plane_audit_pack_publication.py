from __future__ import annotations

import hashlib
import json
import tarfile
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.control_plane_audit_pack import audit_pack_status, verify_external_audit_pack
from app.services.redis_client import redis_client

PUBLICATION_STREAM_KEY = "control_plane_external_audit_pack_publication"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _parse_manifest(path: str) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {}
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _build_public_metadata(row: dict[str, Any], verification: dict[str, Any]) -> dict[str, Any]:
    manifest = _parse_manifest(str(row.get("manifest_path", "")))
    artifacts = manifest.get("artifacts", []) if isinstance(manifest, dict) else []

    trust_anchor: dict[str, Any] = {"type": "unknown"}
    for artifact in artifacts:
        name = str(artifact.get("name", ""))
        if "governance_attestation_bundle" not in name:
            continue
        path = str(artifact.get("path", ""))
        target = Path(path)
        if not target.exists():
            continue
        try:
            bundle = json.loads(target.read_text(encoding="utf-8"))
            signature = bundle.get("signature", {}) if isinstance(bundle, dict) else {}
            trust_anchor = {
                "type": "governance_attestation",
                "provider": signature.get("provider", "unknown"),
                "algorithm": signature.get("algorithm", "unknown"),
                "key_ref": signature.get("key_ref", "unknown"),
            }
            break
        except json.JSONDecodeError:
            continue

    return {
        "pack_id": row.get("pack_id", ""),
        "generated_at": row.get("generated_at", ""),
        "manifest_sha256": row.get("manifest_sha256", ""),
        "overall_pass": bool(row.get("overall_pass", False)),
        "verification": {
            "valid": bool(verification.get("valid", False)),
            "failure_count": int(verification.get("failure_count", 0)),
        },
        "trust_anchor": trust_anchor,
    }


def _filesystem_publish(pack_id: str, pack_dir: str, metadata: dict[str, Any]) -> dict[str, str]:
    root = Path(settings.control_plane_audit_pack_publication_filesystem_dir)
    root.mkdir(parents=True, exist_ok=True)

    day = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    target_dir = root / day
    target_dir.mkdir(parents=True, exist_ok=True)

    tar_path = target_dir / f"{pack_id}.tar.gz"
    metadata_path = target_dir / f"{pack_id}.metadata.json"

    if not tar_path.exists():
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(pack_dir, arcname=Path(pack_dir).name)
        tar_path.chmod(0o444)

    if not metadata_path.exists():
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=True, indent=2), encoding="utf-8")
        metadata_path.chmod(0o444)

    return {
        "archive_object": str(tar_path),
        "metadata_object": str(metadata_path),
    }


def _s3_publish(pack_id: str, pack_dir: str, metadata: dict[str, Any]) -> dict[str, str]:
    import boto3

    bucket = settings.control_plane_audit_pack_publication_s3_bucket
    if not bucket:
        raise RuntimeError("audit_pack_publication_s3_bucket_not_configured")

    session = boto3.session.Session(
        aws_access_key_id=settings.control_plane_audit_pack_publication_s3_access_key or None,
        aws_secret_access_key=settings.control_plane_audit_pack_publication_s3_secret_key or None,
        region_name=settings.control_plane_audit_pack_publication_s3_region or None,
    )
    client = session.client("s3", endpoint_url=settings.control_plane_audit_pack_publication_s3_endpoint_url or None)

    prefix = settings.control_plane_audit_pack_publication_s3_prefix.strip("/")
    base_key = f"{prefix}/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{pack_id}" if prefix else f"audit-pack/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{pack_id}"

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        temp_tar = Path(tmp.name)

    try:
        with tarfile.open(temp_tar, "w:gz") as tar:
            tar.add(pack_dir, arcname=Path(pack_dir).name)

        archive_key = f"{base_key}.tar.gz"
        metadata_key = f"{base_key}.metadata.json"

        archive_kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Key": archive_key,
            "Body": temp_tar.read_bytes(),
            "ContentType": "application/gzip",
        }
        metadata_kwargs: dict[str, Any] = {
            "Bucket": bucket,
            "Key": metadata_key,
            "Body": json.dumps(metadata, ensure_ascii=True, sort_keys=True).encode("utf-8"),
            "ContentType": "application/json",
        }

        if settings.control_plane_audit_pack_publication_s3_object_lock_enabled:
            retain_until = datetime.now(timezone.utc) + timedelta(
                days=max(1, settings.control_plane_audit_pack_publication_s3_retention_days)
            )
            archive_kwargs["ObjectLockMode"] = "COMPLIANCE"
            archive_kwargs["ObjectLockRetainUntilDate"] = retain_until
            metadata_kwargs["ObjectLockMode"] = "COMPLIANCE"
            metadata_kwargs["ObjectLockRetainUntilDate"] = retain_until

        client.put_object(**archive_kwargs)
        client.put_object(**metadata_kwargs)
    finally:
        temp_tar.unlink(missing_ok=True)

    return {
        "archive_object": f"s3://{bucket}/{archive_key}",
        "metadata_object": f"s3://{bucket}/{metadata_key}",
    }


def publish_latest_audit_pack(dry_run: bool = False) -> dict[str, Any]:
    latest = audit_pack_status(limit=1)
    rows = latest.get("rows", [])
    if not rows:
        return {"status": "no_pack"}

    row = rows[0]
    manifest_path = str(row.get("manifest_path", ""))
    pack_dir = str(row.get("pack_dir", ""))
    pack_id = str(row.get("pack_id", ""))

    verification = verify_external_audit_pack(manifest_path)
    valid = bool(verification.get("valid", False))

    if settings.control_plane_audit_pack_publication_require_valid_pack and not valid:
        return {
            "status": "blocked_invalid_pack",
            "pack_id": pack_id,
            "verification": verification,
        }

    metadata = _build_public_metadata(row=row, verification=verification)
    metadata["published_at"] = datetime.now(timezone.utc).isoformat()
    metadata["publication_mode"] = settings.control_plane_audit_pack_publication_mode

    if dry_run:
        return {
            "status": "dry_run",
            "pack_id": pack_id,
            "pack_dir": pack_dir,
            "manifest_path": manifest_path,
            "verification": verification,
            "metadata": metadata,
        }

    mode = settings.control_plane_audit_pack_publication_mode.lower().strip()
    if mode == "s3":
        published = _s3_publish(pack_id=pack_id, pack_dir=pack_dir, metadata=metadata)
    else:
        published = _filesystem_publish(pack_id=pack_id, pack_dir=pack_dir, metadata=metadata)

    publication_id = f"pub-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    redis_client.xadd(
        PUBLICATION_STREAM_KEY,
        {
            "publication_id": publication_id,
            "pack_id": pack_id,
            "manifest_path": manifest_path,
            "archive_object": published["archive_object"],
            "metadata_object": published["metadata_object"],
            "mode": mode,
            "valid": "1" if valid else "0",
            "published_at": metadata["published_at"],
        },
        maxlen=50000,
        approximate=True,
    )

    return {
        "status": "published",
        "publication_id": publication_id,
        "pack_id": pack_id,
        "mode": mode,
        "archive_object": published["archive_object"],
        "metadata_object": published["metadata_object"],
        "verification": verification,
        "metadata": metadata,
    }


def publication_status(limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(PUBLICATION_STREAM_KEY, count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        row["valid"] = str(fields.get("valid", "0")) == "1"
        rows.append(row)
    return {"count": len(rows), "rows": rows}
