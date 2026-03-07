from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.control_plane_assurance_evidence_package_signing import verify_signed_tenant_evidence_package_chain
from app.services.control_plane_governance_attestation import _sign_message, _verify_signature
from app.services.redis_client import redis_client

EXTERNAL_VERIFIER_STREAM_PREFIX = "control_plane_external_verifier_bundle"
EXTERNAL_VERIFIER_POLICY_PREFIX = "control_plane_external_verifier_policy"
ZERO_TRUST_ATTESTATION_STREAM_PREFIX = "control_plane_zero_trust_attestation"
ZERO_TRUST_ATTESTATION_GLOBAL_STREAM = "control_plane_zero_trust_attestation_global"
VERIFIER_RECEIPT_STREAM_PREFIX = "control_plane_external_verifier_receipt_signed"
VERIFIER_RECEIPT_STATE_PREFIX = "control_plane_external_verifier_receipt_signed:last_signature"


def _external_key(tenant_code: str) -> str:
    return f"{EXTERNAL_VERIFIER_STREAM_PREFIX}:{tenant_code.lower().strip()}"


def _policy_key(tenant_code: str) -> str:
    return f"{EXTERNAL_VERIFIER_POLICY_PREFIX}:{tenant_code.lower().strip()}"


def _attestation_key(tenant_code: str) -> str:
    return f"{ZERO_TRUST_ATTESTATION_STREAM_PREFIX}:{tenant_code.lower().strip()}"


def _receipt_key(tenant_code: str) -> str:
    return f"{VERIFIER_RECEIPT_STREAM_PREFIX}:{tenant_code.lower().strip()}"


def _receipt_state_key(tenant_code: str) -> str:
    return f"{VERIFIER_RECEIPT_STATE_PREFIX}:{tenant_code.lower().strip()}"


def _canonical_receipt_message(
    imported_at: str,
    tenant_code: str,
    bundle_id: str,
    valid: bool,
    prev_signature: str,
) -> str:
    valid_flag = "1" if valid else "0"
    return f"{imported_at}|{tenant_code.lower().strip()}|{bundle_id}|{valid_flag}|{prev_signature}"


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "valid", "passed"}


def _parse_csv(value: Any) -> list[str]:
    raw = str(value or "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_iso8601(raw: str) -> datetime | None:
    if not raw:
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_weights(raw: Any) -> dict[str, float]:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            payload = {}
        else:
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = {}
    elif isinstance(raw, dict):
        payload = raw
    else:
        payload = {}

    normalized: dict[str, float] = {}
    for key, value in payload.items():
        name = str(key).strip().lower()
        if not name:
            continue
        weight = max(0.0, _as_float(value, 1.0))
        normalized[name] = weight
    return normalized


def _normalize_policy(payload: dict[str, Any]) -> dict[str, Any]:
    allowed_verifiers = payload.get("allowed_verifiers", [])
    if isinstance(allowed_verifiers, str):
        allowed = _parse_csv(allowed_verifiers)
    elif isinstance(allowed_verifiers, list):
        allowed = [str(item).strip().lower() for item in allowed_verifiers if str(item).strip()]
    else:
        allowed = []
    weights = _normalize_weights(payload.get("verifier_weights", {}))

    return {
        "enabled": _to_bool(payload.get("enabled", True)),
        "min_quorum": max(1, int(payload.get("min_quorum", 1) or 1)),
        "freshness_hours": max(1, int(payload.get("freshness_hours", 24) or 24)),
        "min_weighted_score": max(0.0, min(1.0, _as_float(payload.get("min_weighted_score", 0.0), 0.0))),
        "require_internal_signature": _to_bool(payload.get("require_internal_signature", True)),
        "require_distinct_verifiers": _to_bool(payload.get("require_distinct_verifiers", True)),
        "block_on_disagreement": _to_bool(payload.get("block_on_disagreement", False)),
        "allowed_verifiers": sorted(set(allowed)),
        "verifier_weights": weights,
    }


def upsert_external_verifier_policy(tenant_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    policy = _normalize_policy(payload)
    redis_client.hset(
        _policy_key(tenant_code),
        mapping={
            "enabled": "1" if policy["enabled"] else "0",
            "min_quorum": str(policy["min_quorum"]),
            "freshness_hours": str(policy["freshness_hours"]),
            "min_weighted_score": str(policy["min_weighted_score"]),
            "require_internal_signature": "1" if policy["require_internal_signature"] else "0",
            "require_distinct_verifiers": "1" if policy["require_distinct_verifiers"] else "0",
            "block_on_disagreement": "1" if policy["block_on_disagreement"] else "0",
            "allowed_verifiers": ",".join(policy["allowed_verifiers"]),
            "verifier_weights": json.dumps(policy["verifier_weights"], ensure_ascii=True, sort_keys=True),
        },
    )
    return {"status": "upserted", "tenant_code": tenant_code, "policy": policy}


def get_external_verifier_policy(tenant_code: str) -> dict[str, Any]:
    raw = redis_client.hgetall(_policy_key(tenant_code))
    if not raw:
        return {"status": "default", "tenant_code": tenant_code, "policy": _normalize_policy({})}

    policy = _normalize_policy(
        {
            "enabled": raw.get("enabled", "1"),
            "min_quorum": raw.get("min_quorum", "1"),
            "freshness_hours": raw.get("freshness_hours", "24"),
            "min_weighted_score": raw.get("min_weighted_score", "0"),
            "require_internal_signature": raw.get("require_internal_signature", "1"),
            "require_distinct_verifiers": raw.get("require_distinct_verifiers", "1"),
            "block_on_disagreement": raw.get("block_on_disagreement", "0"),
            "allowed_verifiers": _parse_csv(raw.get("allowed_verifiers", "")),
            "verifier_weights": _normalize_weights(raw.get("verifier_weights", "{}")),
        }
    )
    return {"status": "ok", "tenant_code": tenant_code, "policy": policy}


def import_external_verifier_bundle(
    tenant_code: str,
    verifier_payload: dict[str, Any],
    source: str = "external_auditor",
) -> dict[str, Any]:
    imported_at = datetime.now(timezone.utc).isoformat()
    valid = _to_bool(
        verifier_payload.get("valid", verifier_payload.get("verified", verifier_payload.get("verification_passed", False)))
    )

    fields = {
        "tenant_code": tenant_code,
        "source": source,
        "imported_at": imported_at,
        "bundle_id": str(verifier_payload.get("bundle_id", verifier_payload.get("snapshot_id", ""))),
        "evidence_snapshot_id": str(verifier_payload.get("snapshot_id", verifier_payload.get("evidence_snapshot_id", ""))),
        "verifier": str(verifier_payload.get("verifier", source)),
        "verifier_signature": str(verifier_payload.get("signature", verifier_payload.get("verifier_signature", ""))),
        "reported_at": str(verifier_payload.get("reported_at", "")),
        "valid": "1" if valid else "0",
        "reason": str(verifier_payload.get("reason", "")),
    }
    event_id = redis_client.xadd(_external_key(tenant_code), fields, maxlen=100000, approximate=True)

    prev_signature = redis_client.get(_receipt_state_key(tenant_code)) or ""
    message = _canonical_receipt_message(
        imported_at=imported_at,
        tenant_code=tenant_code,
        bundle_id=fields["bundle_id"],
        valid=valid,
        prev_signature=prev_signature,
    )
    signed = _sign_message(message)
    receipt_fields = {
        "tenant_code": tenant_code,
        "import_event_id": event_id,
        "imported_at": imported_at,
        "bundle_id": fields["bundle_id"],
        "valid": "1" if valid else "0",
        "prev_signature": prev_signature,
        "signature": signed["signature"],
        "signer_provider": signed["signer_provider"],
        "signing_algorithm": signed["signing_algorithm"],
        "signature_encoding": signed["signature_encoding"],
        "key_ref": signed["key_ref"],
    }
    receipt_id = redis_client.xadd(_receipt_key(tenant_code), receipt_fields, maxlen=100000, approximate=True)
    redis_client.set(_receipt_state_key(tenant_code), signed["signature"])

    return {
        "status": "imported",
        "tenant_code": tenant_code,
        "event_id": event_id,
        "receipt_id": receipt_id,
        "valid": valid,
        "imported_at": imported_at,
    }


def external_verifier_status(tenant_code: str, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_external_key(tenant_code), count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        row["valid"] = str(fields.get("valid", "0")) == "1"
        rows.append(row)
    return {"tenant_code": tenant_code, "count": len(rows), "rows": rows}


def compute_zero_trust_attestation(
    tenant_code: str,
    limit: int = 100,
    freshness_hours: int = 24,
) -> dict[str, Any]:
    policy_resp = get_external_verifier_policy(tenant_code)
    policy = policy_resp.get("policy", _normalize_policy({}))
    effective_freshness_hours = max(1, int(freshness_hours or int(policy.get("freshness_hours", 24))))

    internal_verify = verify_signed_tenant_evidence_package_chain(tenant_code=tenant_code, limit=limit)
    ext = external_verifier_status(tenant_code=tenant_code, limit=max(1, limit))
    latest = (ext.get("rows", [{}]) or [{}])[0]
    now_dt = datetime.now(timezone.utc)
    freshness_deadline = now_dt - timedelta(hours=effective_freshness_hours)
    allowed_verifiers = {name.lower().strip() for name in policy.get("allowed_verifiers", []) if str(name).strip()}
    require_distinct = bool(policy.get("require_distinct_verifiers", True))
    verifier_weights = policy.get("verifier_weights", {}) if isinstance(policy.get("verifier_weights", {}), dict) else {}
    min_weighted_score = max(0.0, min(1.0, _as_float(policy.get("min_weighted_score", 0.0), 0.0)))
    block_on_disagreement = bool(policy.get("block_on_disagreement", False))

    ext_rows = ext.get("rows", [])
    if require_distinct:
        latest_by_verifier: dict[str, dict[str, Any]] = {}
        for row in ext_rows:
            verifier_name = str(row.get("verifier", row.get("source", ""))).lower().strip()
            if not verifier_name or verifier_name in latest_by_verifier:
                continue
            latest_by_verifier[verifier_name] = row
        evaluate_rows = list(latest_by_verifier.values())
    else:
        evaluate_rows = list(ext_rows)

    quorum_count = 0
    freshness_ok_any = False
    external_valid_any = False
    valid_signal = False
    invalid_signal = False
    total_weight = 0.0
    valid_weight = 0.0
    for row in evaluate_rows:
        imported_at_row = str(row.get("imported_at", ""))
        imported_dt = _parse_iso8601(imported_at_row)
        fresh = bool(imported_dt and imported_dt >= freshness_deadline)
        verifier_name = str(row.get("verifier", row.get("source", ""))).lower().strip()
        valid = _to_bool(row.get("valid", False))
        allowed = (not allowed_verifiers) or (verifier_name in allowed_verifiers)
        if not (fresh and allowed):
            continue

        weight = max(0.0, _as_float(verifier_weights.get(verifier_name, 1.0), 1.0))
        total_weight += weight
        if valid:
            valid_weight += weight
            external_valid_any = True
            freshness_ok_any = True
            valid_signal = True
            quorum_count += 1
        else:
            freshness_ok_any = True
            invalid_signal = True

    min_quorum = int(policy.get("min_quorum", 1) or 1)
    external_quorum_met = quorum_count >= max(1, min_quorum)
    external_weighted_score = (valid_weight / total_weight) if total_weight > 0 else 0.0
    external_weighted_pass = external_weighted_score >= min_weighted_score
    disagreement_detected = valid_signal and invalid_signal
    external_valid = external_valid_any
    freshness_ok = freshness_ok_any
    internal_valid = _to_bool(internal_verify.get("valid", False))
    require_internal = bool(policy.get("require_internal_signature", True))
    policy_enabled = bool(policy.get("enabled", True))
    external_policy_ok = external_quorum_met and external_weighted_pass and (not block_on_disagreement or not disagreement_detected)
    trusted = (internal_valid or not require_internal) and external_policy_ok if policy_enabled else (internal_valid and external_valid and freshness_ok)

    now = now_dt.isoformat()
    fields = {
        "tenant_code": tenant_code,
        "attested_at": now,
        "internal_valid": "1" if internal_valid else "0",
        "external_valid": "1" if external_valid else "0",
        "freshness_ok": "1" if freshness_ok else "0",
        "external_quorum_met": "1" if external_quorum_met else "0",
        "external_quorum_count": str(quorum_count),
        "external_min_quorum": str(min_quorum),
        "external_weighted_score": f"{external_weighted_score:.6f}",
        "external_min_weighted_score": f"{min_weighted_score:.6f}",
        "external_weighted_pass": "1" if external_weighted_pass else "0",
        "external_disagreement_detected": "1" if disagreement_detected else "0",
        "trusted": "1" if trusted else "0",
        "freshness_hours": str(effective_freshness_hours),
        "policy_enabled": "1" if policy_enabled else "0",
        "policy_require_internal_signature": "1" if require_internal else "0",
        "policy_require_distinct_verifiers": "1" if require_distinct else "0",
        "policy_block_on_disagreement": "1" if block_on_disagreement else "0",
        "policy_allowed_verifiers": ",".join(sorted(allowed_verifiers)),
        "external_bundle_id": str(latest.get("bundle_id", "")),
        "external_source": str(latest.get("source", "")),
        "external_imported_at": str(latest.get("imported_at", "")),
    }
    event_id = redis_client.xadd(_attestation_key(tenant_code), fields, maxlen=100000, approximate=True)
    redis_client.xadd(ZERO_TRUST_ATTESTATION_GLOBAL_STREAM, fields, maxlen=500000, approximate=True)

    return {
        "status": "attested",
        "tenant_code": tenant_code,
        "event_id": event_id,
        "trusted": trusted,
        "internal_valid": internal_valid,
        "external_valid": external_valid,
        "freshness_ok": freshness_ok,
        "external_quorum_met": external_quorum_met,
        "external_quorum_count": quorum_count,
        "external_min_quorum": min_quorum,
        "external_weighted_score": round(external_weighted_score, 6),
        "external_min_weighted_score": round(min_weighted_score, 6),
        "external_weighted_pass": external_weighted_pass,
        "external_disagreement_detected": disagreement_detected,
        "policy": policy,
        "external_bundle_id": fields["external_bundle_id"],
    }


def zero_trust_attestation_status(tenant_code: str, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_attestation_key(tenant_code), count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        row["internal_valid"] = str(fields.get("internal_valid", "0")) == "1"
        row["external_valid"] = str(fields.get("external_valid", "0")) == "1"
        row["freshness_ok"] = str(fields.get("freshness_ok", "0")) == "1"
        row["external_quorum_met"] = str(fields.get("external_quorum_met", "0")) == "1"
        row["external_weighted_pass"] = str(fields.get("external_weighted_pass", "0")) == "1"
        row["external_disagreement_detected"] = str(fields.get("external_disagreement_detected", "0")) == "1"
        row["external_weighted_score"] = _as_float(fields.get("external_weighted_score", "0"), 0.0)
        row["external_min_weighted_score"] = _as_float(fields.get("external_min_weighted_score", "0"), 0.0)
        row["trusted"] = str(fields.get("trusted", "0")) == "1"
        rows.append(row)
    return {"tenant_code": tenant_code, "count": len(rows), "rows": rows}


def zero_trust_overview(limit: int = 200) -> dict[str, Any]:
    entries = redis_client.xrevrange(ZERO_TRUST_ATTESTATION_GLOBAL_STREAM, count=max(1, limit * 20))
    latest_by_tenant: dict[str, dict[str, Any]] = {}
    for event_id, fields in entries:
        tenant_code = str(fields.get("tenant_code", "")).lower().strip()
        if not tenant_code or tenant_code in latest_by_tenant:
            continue

        row = {"id": event_id}
        row.update(fields)
        row["internal_valid"] = str(fields.get("internal_valid", "0")) == "1"
        row["external_valid"] = str(fields.get("external_valid", "0")) == "1"
        row["freshness_ok"] = str(fields.get("freshness_ok", "0")) == "1"
        row["trusted"] = str(fields.get("trusted", "0")) == "1"
        latest_by_tenant[tenant_code] = row

        if len(latest_by_tenant) >= max(1, limit):
            break

    rows = list(latest_by_tenant.values())
    trusted_count = len([row for row in rows if row.get("trusted", False)])

    return {
        "count": len(rows),
        "trusted_tenants": trusted_count,
        "untrusted_tenants": len(rows) - trusted_count,
        "rows": rows,
    }


def verifier_receipt_status(tenant_code: str, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_receipt_key(tenant_code), count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        row["valid"] = str(fields.get("valid", "0")) == "1"
        rows.append(row)
    return {
        "tenant_code": tenant_code,
        "count": len(rows),
        "last_signature": redis_client.get(_receipt_state_key(tenant_code)) or "",
        "rows": rows,
    }


def verify_verifier_receipt_chain(tenant_code: str, limit: int = 1000) -> dict[str, Any]:
    entries = redis_client.xrange(_receipt_key(tenant_code), min="-", max="+", count=max(1, limit))
    prev_signature = ""
    for idx, (_, fields) in enumerate(entries):
        valid = str(fields.get("valid", "0")) == "1"
        message = _canonical_receipt_message(
            imported_at=str(fields.get("imported_at", "")),
            tenant_code=tenant_code,
            bundle_id=str(fields.get("bundle_id", "")),
            valid=valid,
            prev_signature=str(fields.get("prev_signature", "")),
        )
        if str(fields.get("prev_signature", "")) != prev_signature:
            return {"tenant_code": tenant_code, "valid": False, "index": idx, "reason": "prev_signature_mismatch"}

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
            return {"tenant_code": tenant_code, "valid": False, "index": idx, "reason": f"signature_verify_error:{exc}"}
        if not sig_ok:
            return {"tenant_code": tenant_code, "valid": False, "index": idx, "reason": "signature_mismatch"}

        prev_signature = str(fields.get("signature", ""))

    return {"tenant_code": tenant_code, "valid": True, "checked": len(entries), "last_signature": prev_signature}
