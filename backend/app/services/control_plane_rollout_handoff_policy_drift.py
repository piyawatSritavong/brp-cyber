from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Tenant
from app.services.notifier import send_telegram_message
from app.services.redis_client import redis_client
from app.services.rollout_handoff_auth import get_rollout_handoff_policy, upsert_rollout_handoff_policy

ROLLOUT_HANDOFF_POLICY_DRIFT_BASELINE_KEY = "control_plane_rollout_handoff_policy_drift:baseline"
ROLLOUT_HANDOFF_POLICY_DRIFT_STREAM_PREFIX = "control_plane_rollout_handoff_policy_drift"

_DEFAULT_POLICY: dict[str, Any] = {
    "anomaly_detection_enabled": True,
    "auto_revoke_on_ip_mismatch": True,
    "max_denied_attempts_before_revoke": 3,
    "adaptive_hardening_enabled": True,
    "risk_threshold_block": 85,
    "risk_threshold_harden": 60,
    "harden_session_ttl_seconds": 300,
    "containment_playbook_enabled": True,
    "containment_high_threshold": 60,
    "containment_critical_threshold": 85,
    "containment_action_high": "harden_session",
    "containment_action_critical": "revoke_token",
}
_CRITICAL_FIELDS = {
    "adaptive_hardening_enabled",
    "risk_threshold_block",
    "containment_playbook_enabled",
    "containment_action_critical",
}


def _list_tenants(db: Session, limit: int) -> list[Tenant]:
    return db.query(Tenant).limit(max(1, limit)).all()


def _stream_key(tenant_code: str) -> str:
    return f"{ROLLOUT_HANDOFF_POLICY_DRIFT_STREAM_PREFIX}:{tenant_code.lower().strip()}"


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    if value is None:
        return default
    return bool(value)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_policy_value(field: str, value: Any) -> Any:
    baseline = _DEFAULT_POLICY.get(field)
    if isinstance(baseline, bool):
        return _as_bool(value, baseline)
    if isinstance(baseline, int):
        return _as_int(value, baseline)
    return str(value if value is not None else baseline)


def _normalize_baseline(payload: dict[str, Any]) -> dict[str, Any]:
    monitored_fields_raw = payload.get("monitored_fields", list(_DEFAULT_POLICY.keys()))
    monitored_fields = [str(f).strip() for f in monitored_fields_raw if str(f).strip() in _DEFAULT_POLICY]
    if not monitored_fields:
        monitored_fields = list(_DEFAULT_POLICY.keys())

    baseline_policy = dict(_DEFAULT_POLICY)
    candidate = dict(payload.get("baseline_policy", {}))
    for field in monitored_fields:
        if field in candidate:
            baseline_policy[field] = _coerce_policy_value(field, candidate[field])

    return {
        "profile_version": str(payload.get("profile_version", "1.0")),
        "owner": str(payload.get("owner", "security")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "notify_on_high_critical": _as_bool(payload.get("notify_on_high_critical"), True),
        "monitored_fields": monitored_fields,
        "baseline_policy": baseline_policy,
    }


def upsert_rollout_handoff_policy_drift_baseline(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_baseline(payload)
    redis_client.set(ROLLOUT_HANDOFF_POLICY_DRIFT_BASELINE_KEY, json.dumps(normalized, ensure_ascii=True, sort_keys=True))
    return {"status": "upserted", "baseline": normalized}


def get_rollout_handoff_policy_drift_baseline() -> dict[str, Any]:
    raw = redis_client.get(ROLLOUT_HANDOFF_POLICY_DRIFT_BASELINE_KEY)
    if not raw:
        return {"status": "default", "baseline": _normalize_baseline({})}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "corrupted"}
    return {"status": "ok", "baseline": _normalize_baseline(loaded)}


def _drift_severity(weighted_score: int) -> str:
    if weighted_score >= 60:
        return "critical"
    if weighted_score >= 30:
        return "high"
    if weighted_score > 0:
        return "low"
    return "none"


def evaluate_rollout_handoff_policy_drift(
    tenant_id: Any,
    tenant_code: str,
    *,
    notify: bool = True,
) -> dict[str, Any]:
    baseline_resp = get_rollout_handoff_policy_drift_baseline()
    if baseline_resp.get("status") == "corrupted":
        return {"status": "corrupted_baseline", "tenant_id": str(tenant_id), "tenant_code": tenant_code}
    baseline = baseline_resp.get("baseline", _normalize_baseline({}))
    expected = dict(baseline.get("baseline_policy", _DEFAULT_POLICY))
    monitored = list(baseline.get("monitored_fields", list(_DEFAULT_POLICY.keys())))

    policy = get_rollout_handoff_policy(tenant_id).get("policy", {})
    mismatches: list[dict[str, Any]] = []
    weighted_score = 0
    for field in monitored:
        exp = _coerce_policy_value(field, expected.get(field, _DEFAULT_POLICY[field]))
        act = _coerce_policy_value(field, policy.get(field, _DEFAULT_POLICY[field]))
        if act != exp:
            mismatches.append({"field": field, "expected": exp, "actual": act})
            weighted_score += 20 if field in _CRITICAL_FIELDS else 10

    weighted_score = min(100, weighted_score)
    severity = _drift_severity(weighted_score)
    drift = len(mismatches) > 0
    result = {
        "status": "ok",
        "tenant_id": str(tenant_id),
        "tenant_code": tenant_code,
        "drift_detected": drift,
        "drift_score": weighted_score,
        "drift_severity": severity,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }

    if drift:
        redis_client.xadd(
            _stream_key(tenant_code),
            {
                "tenant_id": str(tenant_id),
                "tenant_code": tenant_code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "drift_score": str(weighted_score),
                "drift_severity": severity,
                "mismatch_count": str(len(mismatches)),
                "mismatches": json.dumps(mismatches, ensure_ascii=True),
            },
            maxlen=100000,
            approximate=True,
        )
        if notify and bool(baseline.get("notify_on_high_critical", True)) and severity in {"high", "critical"}:
            send_telegram_message(
                f"[BRP-Cyber] Rollout handoff policy drift tenant={tenant_code} "
                f"severity={severity} score={weighted_score} mismatches={len(mismatches)}"
            )
    return result


def rollout_handoff_policy_drift_history(tenant_code: str, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_stream_key(tenant_code), count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row: dict[str, Any] = {"id": event_id}
        row.update(fields)
        try:
            row["mismatches"] = json.loads(str(fields.get("mismatches", "[]")))
        except json.JSONDecodeError:
            row["mismatches"] = []
        rows.append(row)
    return {"tenant_code": tenant_code, "count": len(rows), "rows": rows}


def rollout_handoff_policy_drift_heatmap(db: Session, limit: int = 200, *, notify: bool = False) -> dict[str, Any]:
    tenants = _list_tenants(db, limit=max(1, limit))
    rows: list[dict[str, Any]] = []
    severity_counts = {"none": 0, "low": 0, "high": 0, "critical": 0}
    drifted = 0

    for tenant in tenants:
        row = evaluate_rollout_handoff_policy_drift(tenant.id, tenant.tenant_code, notify=notify)
        severity = str(row.get("drift_severity", "none"))
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if bool(row.get("drift_detected", False)):
            drifted += 1
        rows.append(row)

    rows.sort(key=lambda r: (-int(r.get("drift_score", 0) or 0), str(r.get("tenant_code", ""))))
    return {"count": len(rows), "drifted_count": drifted, "severity_counts": severity_counts, "rows": rows}


def apply_rollout_handoff_policy_drift_reconciliation(
    db: Session,
    *,
    limit: int = 200,
    min_severity: str = "high",
    dry_run: bool = True,
) -> dict[str, Any]:
    threshold = {"none": 0, "low": 1, "high": 2, "critical": 3}.get(min_severity, 2)
    heatmap = rollout_handoff_policy_drift_heatmap(db, limit=max(1, limit), notify=False).get("rows", [])
    baseline = get_rollout_handoff_policy_drift_baseline().get("baseline", _normalize_baseline({}))
    expected = dict(baseline.get("baseline_policy", _DEFAULT_POLICY))
    monitored = list(baseline.get("monitored_fields", list(_DEFAULT_POLICY.keys())))
    severity_rank = {"none": 0, "low": 1, "high": 2, "critical": 3}

    rows: list[dict[str, Any]] = []
    for row in heatmap:
        severity = str(row.get("drift_severity", "none"))
        if severity_rank.get(severity, 0) < threshold:
            continue
        tenant_id = str(row.get("tenant_id", ""))
        tenant_code = str(row.get("tenant_code", ""))
        if not tenant_id or not tenant_code:
            continue
        try:
            tenant_uuid = UUID(tenant_id)
        except ValueError:
            continue

        current = get_rollout_handoff_policy(tenant_uuid).get("policy", {})
        payload = dict(current)
        for field in monitored:
            payload[field] = _coerce_policy_value(field, expected.get(field, _DEFAULT_POLICY[field]))

        if dry_run:
            rows.append(
                {
                    "tenant_id": tenant_id,
                    "tenant_code": tenant_code,
                    "status": "dry_run",
                    "drift_severity": severity,
                    "reconciled_policy": payload,
                }
            )
            continue

        applied = upsert_rollout_handoff_policy(
            tenant_id=tenant_uuid,
            anomaly_detection_enabled=bool(payload.get("anomaly_detection_enabled", True)),
            auto_revoke_on_ip_mismatch=bool(payload.get("auto_revoke_on_ip_mismatch", True)),
            max_denied_attempts_before_revoke=int(payload.get("max_denied_attempts_before_revoke", 3)),
            adaptive_hardening_enabled=bool(payload.get("adaptive_hardening_enabled", True)),
            risk_threshold_block=int(payload.get("risk_threshold_block", 85)),
            risk_threshold_harden=int(payload.get("risk_threshold_harden", 60)),
            harden_session_ttl_seconds=int(payload.get("harden_session_ttl_seconds", 300)),
            containment_playbook_enabled=bool(payload.get("containment_playbook_enabled", True)),
            containment_high_threshold=int(payload.get("containment_high_threshold", 60)),
            containment_critical_threshold=int(payload.get("containment_critical_threshold", 85)),
            containment_action_high=str(payload.get("containment_action_high", "harden_session")),
            containment_action_critical=str(payload.get("containment_action_critical", "revoke_token")),
        )
        rows.append(
            {
                "tenant_id": tenant_id,
                "tenant_code": tenant_code,
                "status": "applied",
                "drift_severity": severity,
                "policy": applied.get("policy", {}),
            }
        )
    return {"count": len(rows), "dry_run": dry_run, "min_severity": min_severity, "rows": rows}
