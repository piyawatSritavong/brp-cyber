from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from app.services.control_plane_compliance_package_index import export_tenant_compliance_package_index
from app.services.control_plane_governance_attestation import _sign_message, _verify_signature
from app.services.redis_client import redis_client

ASSURANCE_TENANT_EVIDENCE_PACKAGE_SIGNED_STREAM_PREFIX = "control_plane_assurance_tenant_evidence_package_signed"
ASSURANCE_TENANT_EVIDENCE_PACKAGE_SIGNED_STATE_PREFIX = "control_plane_assurance_tenant_evidence_package_signed:last_signature"


def _tenant_stream_key(tenant_code: str) -> str:
    return f"{ASSURANCE_TENANT_EVIDENCE_PACKAGE_SIGNED_STREAM_PREFIX}:{tenant_code.lower().strip()}"


def _tenant_state_key(tenant_code: str) -> str:
    return f"{ASSURANCE_TENANT_EVIDENCE_PACKAGE_SIGNED_STATE_PREFIX}:{tenant_code.lower().strip()}"


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


def create_signed_tenant_evidence_package(
    tenant_id: UUID,
    tenant_code: str,
    destination_dir: str = "./tmp/compliance/assurance_tenant_evidence_package_signed",
    limit: int = 100,
) -> dict[str, Any]:
    scope = f"assurance_tenant_evidence_package:{tenant_code.lower().strip()}"
    package = export_tenant_compliance_package_index(
        tenant_id=tenant_id,
        tenant_code=tenant_code,
        destination_dir=destination_dir,
        limit=limit,
    )

    artifact = {
        "tenant_code": tenant_code,
        "evidence_package_index": {
            "index_id": package.get("index_id", ""),
            "path": package.get("path", ""),
            "package": package.get("package", {}),
        },
    }

    generated_at = datetime.now(timezone.utc).isoformat()
    payload_hash = _payload_hash(artifact)

    state_key = _tenant_state_key(tenant_code)
    stream_key = _tenant_stream_key(tenant_code)
    prev_signature = redis_client.get(state_key) or ""
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
        "tenant_code": tenant_code,
        "evidence_index_id": str(package.get("index_id", "")),
        "evidence_index_path": str(package.get("path", "")),
    }
    event_id = redis_client.xadd(stream_key, record, maxlen=200000, approximate=True)
    redis_client.set(state_key, signed["signature"])

    root = Path(destination_dir)
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    bundle = _bundle(record, artifact, snapshot_id=event_id, scope=scope)
    target = root / f"assurance_tenant_evidence_package_signed_{tenant_code}_{ts}.json"
    target.write_text(json.dumps(bundle, ensure_ascii=True, indent=2), encoding="utf-8")

    return {
        "status": "signed",
        "snapshot_id": event_id,
        "tenant_code": tenant_code,
        "scope": scope,
        "generated_at": generated_at,
        "payload_hash": payload_hash,
        "path": str(target),
        "evidence_package_path": package.get("path", ""),
        "evidence_index_id": package.get("index_id", ""),
    }


def signed_tenant_evidence_package_status(tenant_code: str, limit: int = 100) -> dict[str, Any]:
    stream_key = _tenant_stream_key(tenant_code)
    state_key = _tenant_state_key(tenant_code)
    entries = redis_client.xrevrange(stream_key, count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"tenant_code": tenant_code, "count": len(rows), "last_signature": redis_client.get(state_key) or "", "rows": rows}


def verify_signed_tenant_evidence_package_chain(tenant_code: str, limit: int = 1000) -> dict[str, Any]:
    stream_key = _tenant_stream_key(tenant_code)
    scope = f"assurance_tenant_evidence_package:{tenant_code.lower().strip()}"

    entries = redis_client.xrange(stream_key, min="-", max="+", count=max(1, limit))
    prev_signature = ""
    for idx, (_, fields) in enumerate(entries):
        generated_at = fields.get("generated_at", "")
        payload_hash = fields.get("payload_hash", "")
        row_scope = fields.get("scope", scope)
        limit_value = int(fields.get("limit", "0") or 0)
        message = _canonical_message(generated_at, payload_hash, fields.get("prev_signature", ""), limit_value, row_scope)

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
