from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.control_plane_assurance_bulletin_delivery import bulletin_delivery_receipts
from app.services.control_plane_assurance_digest_signing import (
    signed_tenant_risk_bulletin_status,
    verify_signed_tenant_risk_bulletin_chain,
)
from app.services.control_plane_governance_attestation import _sign_message, _verify_signature
from app.services.redis_client import redis_client

ASSURANCE_DELIVERY_PROOF_STREAM_PREFIX = "control_plane_assurance_delivery_proof_signed"
ASSURANCE_DELIVERY_PROOF_STATE_PREFIX = "control_plane_assurance_delivery_proof_signed:last_signature"


def _stream_key(tenant_code: str) -> str:
    return f"{ASSURANCE_DELIVERY_PROOF_STREAM_PREFIX}:{tenant_code.lower().strip()}"


def _state_key(tenant_code: str) -> str:
    return f"{ASSURANCE_DELIVERY_PROOF_STATE_PREFIX}:{tenant_code.lower().strip()}"


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


def export_signed_delivery_proof_bundle(
    tenant_code: str,
    destination_dir: str = "./tmp/compliance/assurance_delivery_proofs",
    limit: int = 100,
) -> dict[str, Any]:
    receipts = bulletin_delivery_receipts(tenant_code, limit=max(1, limit))
    latest_receipt = receipts.get("rows", [{}])[0] if receipts.get("rows") else {}

    bulletin = signed_tenant_risk_bulletin_status(tenant_code, limit=1)
    latest_bulletin = bulletin.get("rows", [{}])[0] if bulletin.get("rows") else {}
    bulletin_verify = verify_signed_tenant_risk_bulletin_chain(tenant_code, limit=max(1, limit))

    artifacts = {
        "tenant_code": tenant_code,
        "latest_receipt": latest_receipt,
        "latest_bulletin": latest_bulletin,
        "bulletin_chain_verify": bulletin_verify,
    }

    generated_at = datetime.now(timezone.utc).isoformat()
    scope = f"assurance_delivery_proof:{tenant_code.lower().strip()}"
    payload_hash = _payload_hash(artifacts)
    prev_signature = redis_client.get(_state_key(tenant_code)) or ""
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
        "scope": scope,
        "limit": str(limit),
        "tenant_code": tenant_code,
        "receipt_status": str(latest_receipt.get("status", "")),
    }

    event_id = redis_client.xadd(_stream_key(tenant_code), record, maxlen=200000, approximate=True)
    redis_client.set(_state_key(tenant_code), signed["signature"])

    root = Path(destination_dir)
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    bundle = _bundle(record, artifacts, snapshot_id=event_id, scope=scope)
    target = root / f"assurance_delivery_proof_{tenant_code}_{ts}.json"
    target.write_text(json.dumps(bundle, ensure_ascii=True, indent=2), encoding="utf-8")

    return {
        "status": "exported",
        "tenant_code": tenant_code,
        "snapshot_id": event_id,
        "scope": scope,
        "generated_at": generated_at,
        "path": str(target),
    }


def signed_delivery_proof_status(tenant_code: str, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_stream_key(tenant_code), count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"tenant_code": tenant_code, "count": len(rows), "last_signature": redis_client.get(_state_key(tenant_code)) or "", "rows": rows}


def verify_signed_delivery_proof_chain(tenant_code: str, limit: int = 1000) -> dict[str, Any]:
    entries = redis_client.xrange(_stream_key(tenant_code), min="-", max="+", count=max(1, limit))
    prev_signature = ""
    scope = f"assurance_delivery_proof:{tenant_code.lower().strip()}"

    for idx, (_, fields) in enumerate(entries):
        row_scope = str(fields.get("scope", ""))
        limit_value = int(fields.get("limit", "0") or 0)
        message = _canonical_message(
            fields.get("generated_at", ""),
            fields.get("payload_hash", ""),
            fields.get("prev_signature", ""),
            limit_value,
            row_scope,
        )
        if fields.get("prev_signature", "") != prev_signature:
            return {"tenant_code": tenant_code, "valid": False, "index": idx, "reason": "prev_signature_mismatch"}
        if row_scope != scope:
            return {"tenant_code": tenant_code, "valid": False, "index": idx, "reason": "scope_mismatch"}

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
            return {"tenant_code": tenant_code, "valid": False, "index": idx, "reason": f"signature_verify_error:{exc}"}

        if not valid_sig:
            return {"tenant_code": tenant_code, "valid": False, "index": idx, "reason": "signature_mismatch"}
        prev_signature = fields.get("signature", "")

    return {"tenant_code": tenant_code, "valid": True, "checked": len(entries), "last_signature": prev_signature}
