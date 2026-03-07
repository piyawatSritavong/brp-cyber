from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.control_plane_governance import governance_dashboard
from app.services.redis_client import redis_client

ATTEST_STREAM_KEY = "control_plane_governance_attestation"
ATTEST_STATE_KEY = "control_plane_governance_attestation:last_signature"


def _attest_dir() -> Path:
    path = Path(settings.control_plane_governance_attestation_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_message(generated_at: str, report_hash: str, prev_signature: str, limit: int) -> str:
    return f"{generated_at}|{report_hash}|{prev_signature}|{limit}"


def _provider() -> str:
    provider = settings.control_plane_governance_signer_provider.lower().strip()
    return provider if provider in {"hmac", "aws_kms"} else "hmac"


def _kms_client():
    import boto3

    session = boto3.session.Session(
        aws_access_key_id=settings.control_plane_governance_signer_kms_access_key or None,
        aws_secret_access_key=settings.control_plane_governance_signer_kms_secret_key or None,
        region_name=settings.control_plane_governance_signer_kms_region or None,
    )
    return session.client("kms", endpoint_url=settings.control_plane_governance_signer_kms_endpoint_url or None)


def _sign_hmac(message: str) -> dict[str, str]:
    key = settings.control_plane_governance_attestation_hmac_key.encode("utf-8")
    signature = hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "signature": signature,
        "signer_provider": "hmac",
        "signing_algorithm": "HMAC_SHA256",
        "signature_encoding": "hex",
        "key_ref": "local_hmac",
    }


def _sign_kms(message: str) -> dict[str, str]:
    if not settings.control_plane_governance_signer_kms_key_id:
        raise RuntimeError("kms_key_id_not_configured")

    client = _kms_client()
    response = client.sign(
        KeyId=settings.control_plane_governance_signer_kms_key_id,
        Message=message.encode("utf-8"),
        SigningAlgorithm=settings.control_plane_governance_signer_kms_signing_algorithm,
        MessageType="RAW",
    )
    signature = base64.b64encode(response["Signature"]).decode("utf-8")

    return {
        "signature": signature,
        "signer_provider": "aws_kms",
        "signing_algorithm": settings.control_plane_governance_signer_kms_signing_algorithm,
        "signature_encoding": "base64",
        "key_ref": settings.control_plane_governance_signer_kms_key_id,
    }


def _sign_message(message: str) -> dict[str, str]:
    if _provider() == "aws_kms":
        return _sign_kms(message)
    return _sign_hmac(message)


def _verify_hmac(message: str, signature: str, hmac_key_override: str | None = None) -> bool:
    key = (hmac_key_override or settings.control_plane_governance_attestation_hmac_key).encode("utf-8")
    expected = hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _verify_kms(message: str, signature: str, key_ref: str, signing_algorithm: str) -> bool:
    client = _kms_client()
    response = client.verify(
        KeyId=key_ref,
        Message=message.encode("utf-8"),
        Signature=base64.b64decode(signature.encode("utf-8")),
        SigningAlgorithm=signing_algorithm,
        MessageType="RAW",
    )
    return bool(response.get("SignatureValid", False))


def _verify_signature(
    message: str,
    signature: str,
    signer_provider: str,
    signature_encoding: str,
    signing_algorithm: str,
    key_ref: str,
    hmac_key_override: str | None = None,
) -> bool:
    provider = signer_provider.lower().strip()
    if provider == "aws_kms":
        if signature_encoding != "base64":
            return False
        return _verify_kms(message, signature, key_ref, signing_algorithm)

    if signature_encoding != "hex":
        return False
    return _verify_hmac(message, signature, hmac_key_override=hmac_key_override)


def _record_to_bundle(record: dict[str, str], attestation_id: str) -> dict[str, Any]:
    limit = int(record.get("limit", "0") or 0)
    generated_at = record.get("generated_at", "")
    report_hash = record.get("report_hash", "")
    prev_signature = record.get("prev_signature", "")
    message = _canonical_message(generated_at, report_hash, prev_signature, limit)

    summary_raw = record.get("summary", "{}")
    try:
        summary = json.loads(summary_raw)
    except json.JSONDecodeError:
        summary = {}

    return {
        "bundle_version": "1.0",
        "attestation_id": attestation_id,
        "generated_at": generated_at,
        "message": message,
        "message_fields": {
            "generated_at": generated_at,
            "report_hash": report_hash,
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
        "artifacts": {
            "report_hash": report_hash,
            "summary": summary,
        },
    }


def create_governance_attestation(limit: int = 5000) -> dict[str, Any]:
    report = governance_dashboard(limit=limit)
    generated_at = datetime.now(timezone.utc).isoformat()
    report_hash = _payload_hash(report)
    prev_signature = redis_client.get(ATTEST_STATE_KEY) or ""

    message = _canonical_message(generated_at, report_hash, prev_signature, limit)
    signed = _sign_message(message)

    record = {
        "generated_at": generated_at,
        "report_hash": report_hash,
        "prev_signature": prev_signature,
        "signature": signed["signature"],
        "signer_provider": signed["signer_provider"],
        "signing_algorithm": signed["signing_algorithm"],
        "signature_encoding": signed["signature_encoding"],
        "key_ref": signed["key_ref"],
        "limit": str(limit),
        "summary": json.dumps(report.get("summary", {}), ensure_ascii=True, sort_keys=True),
    }

    event_id = redis_client.xadd(ATTEST_STREAM_KEY, record, maxlen=200000, approximate=True)
    redis_client.set(ATTEST_STATE_KEY, signed["signature"])

    file_path = _attest_dir() / f"governance_attestation_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
    with file_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"id": event_id, **record}, ensure_ascii=True) + "\n")

    return {
        "status": "success",
        "event_id": event_id,
        "generated_at": generated_at,
        "report_hash": report_hash,
        "signature": signed["signature"],
        "signer_provider": signed["signer_provider"],
        "signing_algorithm": signed["signing_algorithm"],
        "key_ref": signed["key_ref"],
        "prev_signature": prev_signature,
        "file_path": str(file_path),
        "summary": report.get("summary", {}),
    }


def governance_attestation_status(limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(ATTEST_STREAM_KEY, count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)

    return {
        "last_signature": redis_client.get(ATTEST_STATE_KEY) or "",
        "count": len(rows),
        "rows": rows,
    }


def verify_governance_attestation_chain(limit: int = 1000) -> dict[str, Any]:
    entries = redis_client.xrange(ATTEST_STREAM_KEY, min="-", max="+", count=max(1, limit))
    prev_signature = ""

    for idx, (_, fields) in enumerate(entries):
        limit_value = int(fields.get("limit", "0") or 0)
        message = _canonical_message(
            fields.get("generated_at", ""),
            fields.get("report_hash", ""),
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


def export_latest_governance_attestation(destination_dir: str = "./tmp/compliance/exports") -> dict[str, Any]:
    status = governance_attestation_status(limit=1)
    rows = status.get("rows", [])
    if not rows:
        return {"status": "no_attestation"}

    latest = rows[0]
    bundle = _record_to_bundle(latest, attestation_id=str(latest.get("id", "")))

    root = Path(destination_dir)
    root.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    target = root / f"governance_attestation_bundle_{ts}.json"
    target.write_text(json.dumps(bundle, ensure_ascii=True, indent=2), encoding="utf-8")

    return {"status": "exported", "path": str(target), "id": latest.get("id", ""), "bundle": bundle}


def verify_detached_attestation_bundle(
    bundle: dict[str, Any],
    hmac_key_override: str | None = None,
) -> dict[str, Any]:
    fields = bundle.get("message_fields", {}) if isinstance(bundle, dict) else {}
    signature = bundle.get("signature", {}) if isinstance(bundle, dict) else {}

    generated_at = str(fields.get("generated_at", ""))
    report_hash = str(fields.get("report_hash", ""))
    prev_signature = str(fields.get("prev_signature", ""))
    limit = int(fields.get("limit", 0) or 0)

    message = _canonical_message(generated_at, report_hash, prev_signature, limit)
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
        "attestation_id": bundle.get("attestation_id", ""),
        "provider": signature.get("provider", "hmac"),
    }
