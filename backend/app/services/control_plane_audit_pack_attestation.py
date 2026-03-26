from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.control_plane_governance_attestation import _sign_message, _verify_signature
from app.services.redis_client import redis_client

AUDIT_PACK_MANIFEST_ATTEST_STREAM_KEY = "control_plane_external_audit_pack_manifest_attestation"
AUDIT_PACK_MANIFEST_ATTEST_STATE_KEY = "control_plane_external_audit_pack_manifest_attestation:last_signature"
MANIFEST_ATTESTATION_BUNDLE_NAME = "manifest_attestation_bundle.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _canonical_message(generated_at: str, pack_id: str, manifest_sha256: str, prev_signature: str) -> str:
    return f"{generated_at}|{pack_id}|{manifest_sha256}|{prev_signature}"


def _bundle_from_record(record: dict[str, str], attestation_id: str) -> dict[str, Any]:
    generated_at = record.get("generated_at", "")
    pack_id = record.get("pack_id", "")
    manifest_sha256 = record.get("manifest_sha256", "")
    prev_signature = record.get("prev_signature", "")
    message = _canonical_message(generated_at, pack_id, manifest_sha256, prev_signature)

    return {
        "bundle_version": "1.0",
        "attestation_id": attestation_id,
        "generated_at": generated_at,
        "message": message,
        "message_fields": {
            "generated_at": generated_at,
            "pack_id": pack_id,
            "manifest_sha256": manifest_sha256,
            "prev_signature": prev_signature,
        },
        "signature": {
            "value": record.get("signature", ""),
            "provider": record.get("signer_provider", "hmac"),
            "algorithm": record.get("signing_algorithm", "HMAC_SHA256"),
            "encoding": record.get("signature_encoding", "hex"),
            "key_ref": record.get("key_ref", "local_hmac"),
        },
        "artifacts": {
            "pack_id": pack_id,
            "manifest_path": record.get("manifest_path", ""),
            "manifest_sha256": manifest_sha256,
        },
    }


def create_audit_pack_manifest_attestation(pack_id: str, manifest_path: str) -> dict[str, Any]:
    target = Path(manifest_path)
    if not target.exists():
        return {"status": "not_found", "manifest_path": manifest_path, "pack_id": pack_id}

    generated_at = datetime.now(timezone.utc).isoformat()
    manifest_sha256 = _sha256_file(target)
    prev_signature = redis_client.get(AUDIT_PACK_MANIFEST_ATTEST_STATE_KEY) or ""
    message = _canonical_message(generated_at, pack_id, manifest_sha256, prev_signature)

    signed = _sign_message(message)
    record = {
        "pack_id": pack_id,
        "generated_at": generated_at,
        "manifest_path": str(target),
        "manifest_sha256": manifest_sha256,
        "prev_signature": prev_signature,
        "signature": signed["signature"],
        "signer_provider": signed["signer_provider"],
        "signing_algorithm": signed["signing_algorithm"],
        "signature_encoding": signed["signature_encoding"],
        "key_ref": signed["key_ref"],
    }

    event_id = redis_client.xadd(AUDIT_PACK_MANIFEST_ATTEST_STREAM_KEY, record, maxlen=200000, approximate=True)
    redis_client.set(AUDIT_PACK_MANIFEST_ATTEST_STATE_KEY, signed["signature"])

    bundle = _bundle_from_record(record, attestation_id=event_id)
    bundle_path = target.parent / MANIFEST_ATTESTATION_BUNDLE_NAME
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=True, indent=2), encoding="utf-8")

    return {
        "status": "attested",
        "attestation_id": event_id,
        "pack_id": pack_id,
        "generated_at": generated_at,
        "manifest_path": str(target),
        "manifest_sha256": manifest_sha256,
        "signature": signed["signature"],
        "signer_provider": signed["signer_provider"],
        "signing_algorithm": signed["signing_algorithm"],
        "key_ref": signed["key_ref"],
        "prev_signature": prev_signature,
        "path": str(bundle_path),
        "bundle_sha256": _sha256_file(bundle_path),
        "bundle": bundle,
    }


def audit_pack_manifest_attestation_status(limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(AUDIT_PACK_MANIFEST_ATTEST_STREAM_KEY, count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)

    return {
        "count": len(rows),
        "last_signature": redis_client.get(AUDIT_PACK_MANIFEST_ATTEST_STATE_KEY) or "",
        "rows": rows,
    }


def verify_audit_pack_manifest_attestation_chain(limit: int = 1000) -> dict[str, Any]:
    entries = redis_client.xrange(AUDIT_PACK_MANIFEST_ATTEST_STREAM_KEY, min="-", max="+", count=max(1, limit))
    prev_signature = ""

    for idx, (_, fields) in enumerate(entries):
        message = _canonical_message(
            fields.get("generated_at", ""),
            fields.get("pack_id", ""),
            fields.get("manifest_sha256", ""),
            fields.get("prev_signature", ""),
        )

        if fields.get("prev_signature", "") != prev_signature:
            return {"valid": False, "index": idx, "reason": "prev_signature_mismatch"}

        try:
            valid_sig = _verify_signature(
                message=message,
                signature=fields.get("signature", ""),
                signer_provider=fields.get("signer_provider", "hmac"),
                signature_encoding=fields.get("signature_encoding", "hex"),
                signing_algorithm=fields.get("signing_algorithm", "HMAC_SHA256"),
                key_ref=fields.get("key_ref", "local_hmac"),
            )
        except Exception as exc:
            return {"valid": False, "index": idx, "reason": f"signature_verify_error:{exc}"}

        if not valid_sig:
            return {"valid": False, "index": idx, "reason": "signature_mismatch"}

        prev_signature = fields.get("signature", "")

    return {"valid": True, "checked": len(entries), "last_signature": prev_signature}


def verify_audit_pack_manifest_attestation_bundle(
    bundle: dict[str, Any],
    expected_manifest_path: str | None = None,
    hmac_key_override: str | None = None,
) -> dict[str, Any]:
    fields = bundle.get("message_fields", {}) if isinstance(bundle, dict) else {}
    signature = bundle.get("signature", {}) if isinstance(bundle, dict) else {}
    artifacts = bundle.get("artifacts", {}) if isinstance(bundle, dict) else {}

    generated_at = str(fields.get("generated_at", ""))
    pack_id = str(fields.get("pack_id", ""))
    manifest_sha256 = str(fields.get("manifest_sha256", ""))
    prev_signature = str(fields.get("prev_signature", ""))

    message = _canonical_message(generated_at, pack_id, manifest_sha256, prev_signature)
    if message != str(bundle.get("message", "")):
        return {"valid": False, "reason": "message_mismatch"}

    if pack_id != str(artifacts.get("pack_id", "")) or manifest_sha256 != str(artifacts.get("manifest_sha256", "")):
        return {"valid": False, "reason": "artifact_metadata_mismatch"}

    manifest_path = expected_manifest_path or str(artifacts.get("manifest_path", ""))
    if not manifest_path:
        return {"valid": False, "reason": "manifest_path_missing"}

    target = Path(manifest_path)
    if not target.exists():
        return {"valid": False, "reason": "manifest_missing", "manifest_path": str(target)}

    actual_manifest_sha256 = _sha256_file(target)
    if actual_manifest_sha256 != manifest_sha256:
        return {
            "valid": False,
            "reason": "manifest_sha256_mismatch",
            "manifest_path": str(target),
            "manifest_sha256": actual_manifest_sha256,
        }

    try:
        manifest = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"valid": False, "reason": "manifest_json_invalid", "manifest_path": str(target)}

    if pack_id and str(manifest.get("pack_id", "")) != pack_id:
        return {"valid": False, "reason": "pack_id_mismatch", "manifest_path": str(target)}

    try:
        valid = _verify_signature(
            message=message,
            signature=str(signature.get("value", "")),
            signer_provider=str(signature.get("provider", "hmac")),
            signature_encoding=str(signature.get("encoding", "hex")),
            signing_algorithm=str(signature.get("algorithm", "HMAC_SHA256")),
            key_ref=str(signature.get("key_ref", "local_hmac")),
            hmac_key_override=hmac_key_override,
        )
    except Exception as exc:
        return {"valid": False, "reason": f"signature_verify_error:{exc}"}

    if not valid:
        return {"valid": False, "reason": "signature_mismatch", "manifest_path": str(target)}

    return {
        "valid": valid,
        "attestation_id": bundle.get("attestation_id", ""),
        "provider": signature.get("provider", "hmac"),
        "pack_id": pack_id,
        "manifest_path": str(target),
        "manifest_sha256": actual_manifest_sha256,
    }
