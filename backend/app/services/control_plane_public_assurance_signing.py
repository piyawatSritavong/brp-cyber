from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.control_plane_governance_attestation import _sign_message, _verify_signature
from app.services.control_plane_orchestration_assurance import orchestration_objectives_status
from app.services.control_plane_public_assurance import public_assurance_summary
from app.services.redis_client import redis_client

PUBLIC_ASSURANCE_SIGNED_STREAM_KEY = "control_plane_public_assurance_signed"
PUBLIC_ASSURANCE_SIGNED_STATE_KEY = "control_plane_public_assurance_signed:last_signature"


def _canonical_message(generated_at: str, payload_hash: str, prev_signature: str, limit: int) -> str:
    return f"{generated_at}|{payload_hash}|{prev_signature}|{limit}"


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _bundle_from_record(record: dict[str, str], artifact: dict[str, Any], snapshot_id: str) -> dict[str, Any]:
    limit = int(record.get("limit", "0") or 0)
    generated_at = record.get("generated_at", "")
    payload_hash = record.get("payload_hash", "")
    prev_signature = record.get("prev_signature", "")
    message = _canonical_message(generated_at, payload_hash, prev_signature, limit)

    return {
        "bundle_version": "1.0",
        "snapshot_id": snapshot_id,
        "generated_at": generated_at,
        "message": message,
        "message_fields": {
            "generated_at": generated_at,
            "payload_hash": payload_hash,
            "prev_signature": prev_signature,
            "limit": limit,
        },
        "signature": {
            "value": record.get("signature", ""),
            "provider": record.get("signer_provider", "hmac"),
            "algorithm": record.get("signing_algorithm", "HMAC_SHA256"),
            "encoding": record.get("signature_encoding", "hex"),
            "key_ref": record.get("key_ref", "local_hmac"),
        },
        "artifacts": artifact,
    }


def create_signed_public_assurance_snapshot(
    destination_dir: str = "./tmp/compliance/public_assurance",
    limit: int = 1000,
) -> dict[str, Any]:
    summary = public_assurance_summary()
    objectives = orchestration_objectives_status(limit=limit)
    generated_at = datetime.now(timezone.utc).isoformat()

    artifact = {"public_summary": summary, "orchestration_objectives": objectives}
    payload_hash = _payload_hash(artifact)
    prev_signature = redis_client.get(PUBLIC_ASSURANCE_SIGNED_STATE_KEY) or ""
    message = _canonical_message(generated_at, payload_hash, prev_signature, limit)

    signed = _sign_message(message)
    record = {
        "generated_at": generated_at,
        "payload_hash": payload_hash,
        "prev_signature": prev_signature,
        "signature": signed["signature"],
        "signer_provider": signed["signer_provider"],
        "signing_algorithm": signed["signing_algorithm"],
        "signature_encoding": signed["signature_encoding"],
        "key_ref": signed["key_ref"],
        "limit": str(limit),
        "enterprise_ready": "1" if objectives.get("enterprise_readiness", {}).get("ready", False) else "0",
    }

    event_id = redis_client.xadd(PUBLIC_ASSURANCE_SIGNED_STREAM_KEY, record, maxlen=200000, approximate=True)
    redis_client.set(PUBLIC_ASSURANCE_SIGNED_STATE_KEY, signed["signature"])

    root = Path(destination_dir)
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    bundle = _bundle_from_record(record, artifact, snapshot_id=event_id)
    bundle_path = root / f"public_assurance_signed_bundle_{ts}.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=True, indent=2), encoding="utf-8")

    return {
        "status": "signed",
        "snapshot_id": event_id,
        "generated_at": generated_at,
        "payload_hash": payload_hash,
        "signature": signed["signature"],
        "signer_provider": signed["signer_provider"],
        "signing_algorithm": signed["signing_algorithm"],
        "key_ref": signed["key_ref"],
        "prev_signature": prev_signature,
        "path": str(bundle_path),
        "enterprise_ready": objectives.get("enterprise_readiness", {}).get("ready", False),
    }


def signed_public_assurance_status(limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(PUBLIC_ASSURANCE_SIGNED_STREAM_KEY, count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row: dict[str, Any] = {"id": event_id}
        row.update(fields)
        row["enterprise_ready"] = str(fields.get("enterprise_ready", "0")) == "1"
        rows.append(row)
    return {"count": len(rows), "last_signature": redis_client.get(PUBLIC_ASSURANCE_SIGNED_STATE_KEY) or "", "rows": rows}


def verify_signed_public_assurance_chain(limit: int = 1000) -> dict[str, Any]:
    entries = redis_client.xrange(PUBLIC_ASSURANCE_SIGNED_STREAM_KEY, min="-", max="+", count=max(1, limit))
    prev_signature = ""
    for idx, (_, fields) in enumerate(entries):
        limit_value = int(fields.get("limit", "0") or 0)
        message = _canonical_message(
            fields.get("generated_at", ""),
            fields.get("payload_hash", ""),
            fields.get("prev_signature", ""),
            limit_value,
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


def verify_signed_public_assurance_bundle(bundle: dict[str, Any], hmac_key_override: str | None = None) -> dict[str, Any]:
    fields = bundle.get("message_fields", {}) if isinstance(bundle, dict) else {}
    signature = bundle.get("signature", {}) if isinstance(bundle, dict) else {}

    generated_at = str(fields.get("generated_at", ""))
    payload_hash = str(fields.get("payload_hash", ""))
    prev_signature = str(fields.get("prev_signature", ""))
    limit = int(fields.get("limit", 0) or 0)

    message = _canonical_message(generated_at, payload_hash, prev_signature, limit)
    if message != str(bundle.get("message", "")):
        return {"valid": False, "reason": "message_mismatch"}

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

    return {
        "valid": valid,
        "snapshot_id": bundle.get("snapshot_id", ""),
        "provider": signature.get("provider", "hmac"),
    }
