from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.services.control_plane_governance_attestation import _sign_message, _verify_signature
from app.services.control_plane_rollout_handoff_federation import rollout_handoff_federation_executive_digest
from app.services.redis_client import redis_client

ROLL_HANDOFF_FED_DIGEST_SIGNED_STREAM = "control_plane_rollout_handoff_federation_digest_signed"
ROLL_HANDOFF_FED_DIGEST_SIGNED_STATE = "control_plane_rollout_handoff_federation_digest_signed:last_signature"


def _payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_message(generated_at: str, payload_hash: str, prev_signature: str, limit: int, scope: str) -> str:
    return f"{generated_at}|{payload_hash}|{prev_signature}|{limit}|{scope}"


def _bundle(record: dict[str, str], artifacts: dict[str, Any], snapshot_id: str, scope: str) -> dict[str, Any]:
    generated_at = record.get("generated_at", "")
    payload_hash = record.get("payload_hash", "")
    prev_signature = record.get("prev_signature", "")
    limit = int(record.get("limit", "0") or 0)
    message = _canonical_message(generated_at, payload_hash, prev_signature, limit, scope)
    return {
        "bundle_version": "1.0",
        "snapshot_id": snapshot_id,
        "scope": scope,
        "generated_at": generated_at,
        "message": message,
        "message_fields": {
            "generated_at": generated_at,
            "payload_hash": payload_hash,
            "prev_signature": prev_signature,
            "limit": limit,
            "scope": scope,
        },
        "signature": {
            "value": record.get("signature", ""),
            "provider": record.get("signer_provider", "hmac"),
            "algorithm": record.get("signing_algorithm", "HMAC_SHA256"),
            "encoding": record.get("signature_encoding", "hex"),
            "key_ref": record.get("key_ref", "local_hmac"),
        },
        "artifacts": artifacts,
    }


def create_signed_rollout_handoff_federation_digest(
    db: Session,
    destination_dir: str = "./tmp/compliance/rollout_handoff_federation_digest",
    limit: int = 200,
) -> dict[str, Any]:
    digest = rollout_handoff_federation_executive_digest(db, limit=limit)
    generated_at = datetime.now(timezone.utc).isoformat()
    scope = "rollout_handoff_federation_executive_digest"
    artifact = {"executive_digest": digest}
    payload_hash = _payload_hash(artifact)
    prev_signature = redis_client.get(ROLL_HANDOFF_FED_DIGEST_SIGNED_STATE) or ""
    message = _canonical_message(generated_at, payload_hash, prev_signature, limit, scope)

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
        "scope": scope,
    }

    event_id = redis_client.xadd(ROLL_HANDOFF_FED_DIGEST_SIGNED_STREAM, record, maxlen=200000, approximate=True)
    redis_client.set(ROLL_HANDOFF_FED_DIGEST_SIGNED_STATE, signed["signature"])

    root = Path(destination_dir)
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    bundle = _bundle(record, artifact, snapshot_id=event_id, scope=scope)
    target = root / f"rollout_handoff_federation_digest_signed_{ts}.json"
    target.write_text(json.dumps(bundle, ensure_ascii=True, indent=2), encoding="utf-8")

    return {
        "status": "signed",
        "snapshot_id": event_id,
        "scope": scope,
        "payload_hash": payload_hash,
        "generated_at": generated_at,
        "path": str(target),
    }


def signed_rollout_handoff_federation_digest_status(limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(ROLL_HANDOFF_FED_DIGEST_SIGNED_STREAM, count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"count": len(rows), "last_signature": redis_client.get(ROLL_HANDOFF_FED_DIGEST_SIGNED_STATE) or "", "rows": rows}


def verify_signed_rollout_handoff_federation_digest_chain(limit: int = 1000) -> dict[str, Any]:
    entries = redis_client.xrange(ROLL_HANDOFF_FED_DIGEST_SIGNED_STREAM, min="-", max="+", count=max(1, limit))
    prev_signature = ""
    scope = "rollout_handoff_federation_executive_digest"
    for idx, (_, fields) in enumerate(entries):
        generated_at = str(fields.get("generated_at", ""))
        payload_hash = str(fields.get("payload_hash", ""))
        limit_value = int(fields.get("limit", "0") or 0)
        message = _canonical_message(generated_at, payload_hash, str(fields.get("prev_signature", "")), limit_value, scope)

        if str(fields.get("prev_signature", "")) != prev_signature:
            return {"valid": False, "index": idx, "reason": "prev_signature_mismatch"}
        if str(fields.get("scope", "")) != scope:
            return {"valid": False, "index": idx, "reason": "scope_mismatch"}
        try:
            sig_ok = _verify_signature(
                message=message,
                signature=str(fields.get("signature", "")),
                signer_provider=str(fields.get("signer_provider", "hmac")),
                signature_encoding=str(fields.get("signature_encoding", "hex")),
                signing_algorithm=str(fields.get("signing_algorithm", "HMAC_SHA256")),
                key_ref=str(fields.get("key_ref", "local_hmac")),
            )
        except Exception as exc:
            return {"valid": False, "index": idx, "reason": f"signature_verify_error:{exc}"}
        if not sig_ok:
            return {"valid": False, "index": idx, "reason": "signature_mismatch"}
        prev_signature = str(fields.get("signature", ""))

    return {"valid": True, "checked": len(entries), "last_signature": prev_signature}


def public_rollout_handoff_federation_digest_bundle(limit: int = 1000) -> dict[str, Any]:
    status = signed_rollout_handoff_federation_digest_status(limit=1)
    verify = verify_signed_rollout_handoff_federation_digest_chain(limit=limit)
    latest = status.get("rows", [{}])[0] if status.get("rows") else {}
    return {
        "scope": "rollout_handoff_federation_executive_digest",
        "status": status,
        "verify": verify,
        "latest": latest,
    }


def verify_signed_rollout_handoff_federation_digest_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    latest = dict(bundle.get("latest", {}))
    if not latest:
        return {"valid": False, "reason": "missing_latest"}
    required = [
        "generated_at",
        "payload_hash",
        "prev_signature",
        "signature",
        "signer_provider",
        "signing_algorithm",
        "signature_encoding",
        "key_ref",
        "limit",
        "scope",
    ]
    missing = [key for key in required if key not in latest]
    if missing:
        return {"valid": False, "reason": "missing_fields", "missing": missing}

    if str(latest.get("scope", "")) != "rollout_handoff_federation_executive_digest":
        return {"valid": False, "reason": "scope_mismatch"}

    message = _canonical_message(
        str(latest.get("generated_at", "")),
        str(latest.get("payload_hash", "")),
        str(latest.get("prev_signature", "")),
        int(latest.get("limit", "0") or 0),
        str(latest.get("scope", "")),
    )
    try:
        ok = _verify_signature(
            message=message,
            signature=str(latest.get("signature", "")),
            signer_provider=str(latest.get("signer_provider", "hmac")),
            signature_encoding=str(latest.get("signature_encoding", "hex")),
            signing_algorithm=str(latest.get("signing_algorithm", "HMAC_SHA256")),
            key_ref=str(latest.get("key_ref", "local_hmac")),
        )
    except Exception as exc:
        return {"valid": False, "reason": f"signature_verify_error:{exc}"}
    return {"valid": bool(ok), "reason": "ok" if ok else "signature_mismatch"}
