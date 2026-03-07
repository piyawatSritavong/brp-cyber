from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.services.control_plane_governance_attestation import _sign_message, _verify_signature
from app.services.control_plane_orchestration_cost_guardrail import orchestration_cost_guardrail_enterprise_snapshot
from app.services.redis_client import redis_client

ORCH_COST_GUARDRAIL_SIGNED_STREAM = "control_plane_orchestration_cost_guardrail_signed"
ORCH_COST_GUARDRAIL_SIGNED_STATE = "control_plane_orchestration_cost_guardrail_signed:last_signature"


def _payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_message(generated_at: str, payload_hash: str, prev_signature: str, limit: int, scope: str) -> str:
    return f"{generated_at}|{payload_hash}|{prev_signature}|{limit}|{scope}"


def create_signed_orchestration_cost_guardrail_report(
    db: Session,
    destination_dir: str = "./tmp/compliance/orchestration_cost_guardrail",
    limit: int = 200,
) -> dict[str, Any]:
    scope = "orchestration_cost_guardrail_report"
    artifact = {"enterprise_snapshot": orchestration_cost_guardrail_enterprise_snapshot(db, limit=max(1, limit), apply_actions=False)}
    generated_at = datetime.now(timezone.utc).isoformat()
    payload_hash = _payload_hash(artifact)
    prev_signature = redis_client.get(ORCH_COST_GUARDRAIL_SIGNED_STATE) or ""
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
    event_id = redis_client.xadd(ORCH_COST_GUARDRAIL_SIGNED_STREAM, record, maxlen=200000, approximate=True)
    redis_client.set(ORCH_COST_GUARDRAIL_SIGNED_STATE, signed["signature"])

    root = Path(destination_dir)
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    target = root / f"orchestration_cost_guardrail_signed_{ts}.json"
    target.write_text(
        json.dumps(
            {
                "bundle_version": "1.0",
                "snapshot_id": event_id,
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
                    "value": record["signature"],
                    "provider": record["signer_provider"],
                    "algorithm": record["signing_algorithm"],
                    "encoding": record["signature_encoding"],
                    "key_ref": record["key_ref"],
                },
                "artifacts": artifact,
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {
        "status": "signed",
        "snapshot_id": event_id,
        "scope": scope,
        "payload_hash": payload_hash,
        "generated_at": generated_at,
        "path": str(target),
    }


def signed_orchestration_cost_guardrail_report_status(limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(ORCH_COST_GUARDRAIL_SIGNED_STREAM, count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"count": len(rows), "last_signature": redis_client.get(ORCH_COST_GUARDRAIL_SIGNED_STATE) or "", "rows": rows}


def verify_signed_orchestration_cost_guardrail_report_chain(limit: int = 1000) -> dict[str, Any]:
    scope = "orchestration_cost_guardrail_report"
    entries = redis_client.xrange(ORCH_COST_GUARDRAIL_SIGNED_STREAM, min="-", max="+", count=max(1, limit))
    prev_signature = ""
    for idx, (_, fields) in enumerate(entries):
        message = _canonical_message(
            str(fields.get("generated_at", "")),
            str(fields.get("payload_hash", "")),
            str(fields.get("prev_signature", "")),
            int(fields.get("limit", "0") or 0),
            str(fields.get("scope", "")),
        )
        if str(fields.get("prev_signature", "")) != prev_signature:
            return {"valid": False, "index": idx, "reason": "prev_signature_mismatch"}
        if str(fields.get("scope", "")) != scope:
            return {"valid": False, "index": idx, "reason": "scope_mismatch"}
        try:
            ok = _verify_signature(
                message=message,
                signature=str(fields.get("signature", "")),
                signer_provider=str(fields.get("signer_provider", "hmac")),
                signature_encoding=str(fields.get("signature_encoding", "hex")),
                signing_algorithm=str(fields.get("signing_algorithm", "HMAC_SHA256")),
                key_ref=str(fields.get("key_ref", "local_hmac")),
            )
        except Exception as exc:
            return {"valid": False, "index": idx, "reason": f"signature_verify_error:{exc}"}
        if not ok:
            return {"valid": False, "index": idx, "reason": "signature_mismatch"}
        prev_signature = str(fields.get("signature", ""))
    return {"valid": True, "checked": len(entries), "last_signature": prev_signature}


def public_orchestration_cost_guardrail_report_bundle(limit: int = 1000) -> dict[str, Any]:
    status = signed_orchestration_cost_guardrail_report_status(limit=1)
    verify = verify_signed_orchestration_cost_guardrail_report_chain(limit=limit)
    latest = status.get("rows", [None])[0] if status.get("rows") else None
    return {
        "scope": "orchestration_cost_guardrail_report",
        "status": status,
        "verify": verify,
        "latest": latest or {},
    }


def verify_signed_orchestration_cost_guardrail_report_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    latest = dict(bundle.get("latest", {}))
    required = {
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
    }
    if not required.issubset(set(latest.keys())):
        return {"valid": False, "reason": "missing_required_fields"}
    if str(latest.get("scope", "")) != "orchestration_cost_guardrail_report":
        return {"valid": False, "reason": "scope_mismatch"}

    try:
        limit_value = int(str(latest.get("limit", "0")) or 0)
    except ValueError:
        return {"valid": False, "reason": "invalid_limit"}
    message = _canonical_message(
        str(latest.get("generated_at", "")),
        str(latest.get("payload_hash", "")),
        str(latest.get("prev_signature", "")),
        limit_value,
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
