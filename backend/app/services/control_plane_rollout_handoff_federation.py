from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Tenant
from app.services.notifier import send_telegram_message
from app.services.rollout_handoff_auth import (
    get_rollout_handoff_policy,
    rollout_handoff_governance_snapshot,
    upsert_rollout_handoff_policy,
)

RISK_TIERS = ("low", "medium", "high", "critical")
RISK_TIER_SCORE = {"low": 1, "medium": 2, "high": 3, "critical": 4}
HANDOFF_RISK_SLO_PROFILE_PREFIX = "rollout_handoff_federation_slo_profile"
HANDOFF_RISK_SLO_BUDGET_PREFIX = "rollout_handoff_federation_slo_budget"
HANDOFF_RISK_SLO_BREACH_STREAM_PREFIX = "rollout_handoff_federation_slo_breaches"

from app.services.redis_client import redis_client


def _list_tenants(db: Session, limit: int) -> list[Tenant]:
    return db.query(Tenant).limit(max(1, limit)).all()


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    if value is None:
        return default
    return bool(value)


def _risk_tier(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def _escalation_plan_for_tier(tier: str) -> dict[str, Any]:
    if tier == "critical":
        return {
            "severity": "critical",
            "escalation_mode": "contain_immediately",
            "recommended_actions": ["revoke_handoff_tokens", "require_dual_approval", "notify_exec_channel"],
        }
    if tier == "high":
        return {
            "severity": "high",
            "escalation_mode": "tighten_controls",
            "recommended_actions": ["lower_risk_thresholds", "enforce_containment_playbook", "notify_soc_lead"],
        }
    if tier == "medium":
        return {
            "severity": "medium",
            "escalation_mode": "watch_and_harden",
            "recommended_actions": ["harden_sessions", "monitor_containment_stream"],
        }
    return {
        "severity": "low",
        "escalation_mode": "observe",
        "recommended_actions": ["keep_current_policy"],
    }


def _slo_profile_key(tenant_code: str) -> str:
    return f"{HANDOFF_RISK_SLO_PROFILE_PREFIX}:{tenant_code.lower().strip()}"


def _slo_budget_key(tenant_code: str) -> str:
    period = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{HANDOFF_RISK_SLO_BUDGET_PREFIX}:{tenant_code.lower().strip()}:{period}"


def _slo_breach_stream_key(tenant_code: str) -> str:
    return f"{HANDOFF_RISK_SLO_BREACH_STREAM_PREFIX}:{tenant_code.lower().strip()}"


def _normalize_slo_profile(payload: dict[str, Any]) -> dict[str, Any]:
    max_tier = str(payload.get("max_allowed_risk_tier", "medium")).strip().lower()
    if max_tier not in RISK_TIER_SCORE:
        max_tier = "medium"
    min_escalation_tier = str(payload.get("min_escalation_tier", "high")).strip().lower()
    if min_escalation_tier not in RISK_TIER_SCORE:
        min_escalation_tier = "high"
    return {
        "profile_version": str(payload.get("profile_version", "1.0")),
        "owner": str(payload.get("owner", "security")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "max_breaches_per_day": max(1, _as_int(payload.get("max_breaches_per_day"), 5)),
        "max_federated_risk_score": max(0, min(100, _as_int(payload.get("max_federated_risk_score"), 50))),
        "max_allowed_risk_tier": max_tier,
        "max_blocked_count": max(0, _as_int(payload.get("max_blocked_count"), 1)),
        "max_containment_events": max(0, _as_int(payload.get("max_containment_events"), 5)),
        "auto_escalate_on_breach": _as_bool(payload.get("auto_escalate_on_breach"), True),
        "notify_on_breach": _as_bool(payload.get("notify_on_breach"), True),
        "min_escalation_tier": min_escalation_tier,
    }


def upsert_rollout_handoff_federation_slo_profile(tenant_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    profile = _normalize_slo_profile(payload)
    redis_client.set(_slo_profile_key(tenant_code), json.dumps(profile, ensure_ascii=True, sort_keys=True))
    return {"status": "upserted", "tenant_code": tenant_code, "profile": profile}


def get_rollout_handoff_federation_slo_profile(tenant_code: str) -> dict[str, Any]:
    raw = redis_client.get(_slo_profile_key(tenant_code))
    if not raw:
        return {"status": "default", "tenant_code": tenant_code, "profile": _normalize_slo_profile({})}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "corrupted", "tenant_code": tenant_code}
    return {"status": "ok", "tenant_code": tenant_code, "profile": _normalize_slo_profile(loaded)}


def _apply_tenant_escalation(
    tenant_id: UUID,
    profile: dict[str, Any],
    risk_tier: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    policy = get_rollout_handoff_policy(tenant_id).get("policy", {})
    next_policy = {
        "anomaly_detection_enabled": bool(policy.get("anomaly_detection_enabled", True)),
        "auto_revoke_on_ip_mismatch": bool(policy.get("auto_revoke_on_ip_mismatch", True)),
        "max_denied_attempts_before_revoke": int(policy.get("max_denied_attempts_before_revoke", 3)),
        "adaptive_hardening_enabled": bool(policy.get("adaptive_hardening_enabled", True)),
        "risk_threshold_harden": max(10, min(int(policy.get("risk_threshold_harden", 60)), 50)),
        "risk_threshold_block": max(15, min(int(policy.get("risk_threshold_block", 85)), 70)),
        "harden_session_ttl_seconds": int(policy.get("harden_session_ttl_seconds", 300)),
        "containment_playbook_enabled": True,
        "containment_high_threshold": max(10, min(int(policy.get("containment_high_threshold", 60)), 45)),
        "containment_critical_threshold": max(20, min(int(policy.get("containment_critical_threshold", 85)), 70)),
        "containment_action_high": str(policy.get("containment_action_high", "harden_session")),
        "containment_action_critical": "revoke_token" if risk_tier in {"high", "critical"} else str(policy.get("containment_action_critical", "revoke_token")),
    }
    if dry_run:
        return {"status": "dry_run", "tenant_id": str(tenant_id), "risk_tier": risk_tier, "policy": next_policy}
    applied = upsert_rollout_handoff_policy(tenant_id=tenant_id, **next_policy)
    return {"status": "applied", "tenant_id": str(tenant_id), "risk_tier": risk_tier, "policy": applied.get("policy", {})}


def rollout_handoff_federation_heatmap(db: Session, limit: int = 200) -> dict[str, Any]:
    tenants = _list_tenants(db, limit=limit)
    tier_counts = {tier: 0 for tier in RISK_TIERS}
    rows: list[dict[str, Any]] = []

    for tenant in tenants:
        gov = rollout_handoff_governance_snapshot(tenant.id, limit=200)
        risk = dict(gov.get("risk_snapshot", {}))
        max_risk = int(risk.get("max_risk_score", 0) or 0)
        blocked_count = int(risk.get("blocked_count", 0) or 0)
        containment_count = int(gov.get("containment_event_count", 0) or 0)
        score = min(100, max_risk + min(20, blocked_count * 5) + min(15, containment_count * 2))
        tier = _risk_tier(score)
        tier_counts[tier] += 1

        rows.append(
            {
                "tenant_id": str(tenant.id),
                "tenant_code": tenant.tenant_code,
                "federated_risk_score": score,
                "risk_tier": tier,
                "max_risk_score": max_risk,
                "blocked_count": blocked_count,
                "containment_event_count": containment_count,
            }
        )

    rows.sort(key=lambda row: (-int(row["federated_risk_score"]), row["tenant_code"]))
    return {"count": len(rows), "tier_counts": tier_counts, "rows": rows}


def rollout_handoff_escalation_matrix(db: Session, limit: int = 200) -> dict[str, Any]:
    heatmap = rollout_handoff_federation_heatmap(db, limit=limit)
    rows: list[dict[str, Any]] = []
    for row in heatmap.get("rows", []):
        tier = str(row.get("risk_tier", "low"))
        rows.append(
            {
                **row,
                "escalation_plan": _escalation_plan_for_tier(tier),
            }
        )
    return {"count": len(rows), "tier_counts": heatmap.get("tier_counts", {}), "rows": rows}


def apply_rollout_handoff_escalation_matrix(
    db: Session,
    limit: int = 200,
    min_tier: str = "high",
    dry_run: bool = True,
) -> dict[str, Any]:
    min_tier_value = RISK_TIER_SCORE.get(min_tier, RISK_TIER_SCORE["high"])
    matrix = rollout_handoff_escalation_matrix(db, limit=limit).get("rows", [])
    applied: list[dict[str, Any]] = []

    for row in matrix:
        tier = str(row.get("risk_tier", "low"))
        if RISK_TIER_SCORE.get(tier, 0) < min_tier_value:
            continue

        tenant_id = row.get("tenant_id", "")
        if not tenant_id:
            continue
        try:
            tenant_uuid = UUID(str(tenant_id))
        except ValueError:
            continue
        policy_row = get_rollout_handoff_policy(tenant_uuid).get("policy", {})
        payload = {
            "tenant_id": tenant_id,
            "risk_tier": tier,
            "federated_risk_score": row.get("federated_risk_score", 0),
        }
        if dry_run:
            payload["status"] = "dry_run"
            payload["policy_delta"] = {
                "risk_threshold_harden": max(10, min(int(policy_row.get("risk_threshold_harden", 60)), 50)),
                "risk_threshold_block": max(15, min(int(policy_row.get("risk_threshold_block", 85)), 70)),
                "containment_playbook_enabled": True,
                "containment_action_critical": "revoke_token",
            }
            applied.append(payload)
            continue

        result = upsert_rollout_handoff_policy(
            tenant_id=tenant_uuid,
            anomaly_detection_enabled=bool(policy_row.get("anomaly_detection_enabled", True)),
            auto_revoke_on_ip_mismatch=bool(policy_row.get("auto_revoke_on_ip_mismatch", True)),
            max_denied_attempts_before_revoke=int(policy_row.get("max_denied_attempts_before_revoke", 3)),
            adaptive_hardening_enabled=bool(policy_row.get("adaptive_hardening_enabled", True)),
            risk_threshold_harden=max(10, min(int(policy_row.get("risk_threshold_harden", 60)), 50)),
            risk_threshold_block=max(15, min(int(policy_row.get("risk_threshold_block", 85)), 70)),
            harden_session_ttl_seconds=int(policy_row.get("harden_session_ttl_seconds", 300)),
            containment_playbook_enabled=True,
            containment_high_threshold=max(10, min(int(policy_row.get("containment_high_threshold", 60)), 45)),
            containment_critical_threshold=max(20, min(int(policy_row.get("containment_critical_threshold", 85)), 70)),
            containment_action_high=str(policy_row.get("containment_action_high", "harden_session")),
            containment_action_critical="revoke_token",
        )
        payload["status"] = "applied"
        payload["policy"] = result.get("policy", {})
        applied.append(payload)

    return {"count": len(applied), "dry_run": dry_run, "rows": applied}


def evaluate_rollout_handoff_federation_slo(
    db: Session,
    tenant_code: str,
    limit: int = 200,
    dry_run_escalation: bool = False,
) -> dict[str, Any]:
    tenant = db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}

    profile_resp = get_rollout_handoff_federation_slo_profile(tenant_code)
    if profile_resp.get("status") == "corrupted":
        return profile_resp
    profile = profile_resp.get("profile", _normalize_slo_profile({}))

    heatmap = rollout_handoff_federation_heatmap(db, limit=max(1, limit)).get("rows", [])
    heat_by_code = {str(row.get("tenant_code", "")): row for row in heatmap}
    row = heat_by_code.get(tenant_code, {})
    if not row:
        row = {
            "tenant_id": str(tenant.id),
            "tenant_code": tenant_code,
            "federated_risk_score": 0,
            "risk_tier": "low",
            "blocked_count": 0,
            "containment_event_count": 0,
        }

    risk_score = int(row.get("federated_risk_score", 0) or 0)
    risk_tier = str(row.get("risk_tier", "low"))
    blocked_count = int(row.get("blocked_count", 0) or 0)
    containment_count = int(row.get("containment_event_count", 0) or 0)
    breaches: list[dict[str, Any]] = []

    if risk_score > int(profile.get("max_federated_risk_score", 50)):
        breaches.append(
            {
                "clause": "max_federated_risk_score",
                "required": int(profile.get("max_federated_risk_score", 50)),
                "actual": risk_score,
            }
        )
    if RISK_TIER_SCORE.get(risk_tier, 1) > RISK_TIER_SCORE.get(str(profile.get("max_allowed_risk_tier", "medium")), 2):
        breaches.append(
            {
                "clause": "max_allowed_risk_tier",
                "required": str(profile.get("max_allowed_risk_tier", "medium")),
                "actual": risk_tier,
            }
        )
    if blocked_count > int(profile.get("max_blocked_count", 1)):
        breaches.append(
            {
                "clause": "max_blocked_count",
                "required": int(profile.get("max_blocked_count", 1)),
                "actual": blocked_count,
            }
        )
    if containment_count > int(profile.get("max_containment_events", 5)):
        breaches.append(
            {
                "clause": "max_containment_events",
                "required": int(profile.get("max_containment_events", 5)),
                "actual": containment_count,
            }
        )

    breach = len(breaches) > 0
    budget_key = _slo_budget_key(tenant_code)
    consumed = _as_int(redis_client.get(budget_key), 0)
    escalation: dict[str, Any] = {"status": "not_triggered"}

    if breach:
        consumed += 1
        redis_client.set(budget_key, str(consumed))
        if bool(profile.get("auto_escalate_on_breach", True)):
            min_tier = str(profile.get("min_escalation_tier", "high"))
            if RISK_TIER_SCORE.get(risk_tier, 0) >= RISK_TIER_SCORE.get(min_tier, 3):
                escalation = _apply_tenant_escalation(tenant.id, profile, risk_tier, dry_run=dry_run_escalation)
            else:
                escalation = {"status": "skipped_tier", "risk_tier": risk_tier, "min_escalation_tier": min_tier}

        redis_client.xadd(
            _slo_breach_stream_key(tenant_code),
            {
                "tenant_id": str(tenant.id),
                "tenant_code": tenant_code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "risk_score": str(risk_score),
                "risk_tier": risk_tier,
                "breaches": json.dumps(breaches, ensure_ascii=True),
                "blocked_count": str(blocked_count),
                "containment_event_count": str(containment_count),
                "escalation_status": str(escalation.get("status", "none")),
            },
            maxlen=100000,
            approximate=True,
        )
        if bool(profile.get("notify_on_breach", True)):
            send_telegram_message(
                f"[BRP-Cyber] Handoff risk SLO breach tenant={tenant_code} "
                f"tier={risk_tier} score={risk_score} breaches={len(breaches)} escalation={escalation.get('status','none')}"
            )

    budget_total = int(profile.get("max_breaches_per_day", 5))
    remaining = max(0, budget_total - consumed)
    exhausted = consumed >= budget_total

    return {
        "status": "ok",
        "tenant_id": str(tenant.id),
        "tenant_code": tenant_code,
        "profile": profile,
        "metrics": {
            "federated_risk_score": risk_score,
            "risk_tier": risk_tier,
            "blocked_count": blocked_count,
            "containment_event_count": containment_count,
        },
        "breach": breach,
        "breaches": breaches,
        "escalation": escalation,
        "breach_budget": {
            "period": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "total": budget_total,
            "consumed": consumed,
            "remaining": remaining,
            "exhausted": exhausted,
        },
    }


def rollout_handoff_federation_slo_breach_history(tenant_code: str, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_slo_breach_stream_key(tenant_code), count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row: dict[str, Any] = {"id": event_id}
        row.update(fields)
        raw = fields.get("breaches", "[]")
        try:
            row["breaches"] = json.loads(raw)
        except json.JSONDecodeError:
            row["breaches"] = []
        rows.append(row)
    return {"tenant_code": tenant_code, "count": len(rows), "rows": rows}


def rollout_handoff_federation_executive_digest(db: Session, limit: int = 200) -> dict[str, Any]:
    tenants = _list_tenants(db, limit=max(1, limit))
    heatmap = rollout_handoff_federation_heatmap(db, limit=max(1, limit)).get("rows", [])
    heat_by_code = {str(row.get("tenant_code", "")): row for row in heatmap}
    rows: list[dict[str, Any]] = []
    exhausted_count = 0

    for tenant in tenants:
        tenant_code = tenant.tenant_code
        profile = get_rollout_handoff_federation_slo_profile(tenant_code).get("profile", _normalize_slo_profile({}))
        budget_total = int(profile.get("max_breaches_per_day", 5))
        consumed = _as_int(redis_client.get(_slo_budget_key(tenant_code)), 0)
        exhausted = consumed >= budget_total
        if exhausted:
            exhausted_count += 1
        heat = heat_by_code.get(
            tenant_code,
            {
                "federated_risk_score": 0,
                "risk_tier": "low",
                "blocked_count": 0,
                "containment_event_count": 0,
            },
        )
        rows.append(
            {
                "tenant_id": str(tenant.id),
                "tenant_code": tenant_code,
                "risk_tier": heat.get("risk_tier", "low"),
                "federated_risk_score": int(heat.get("federated_risk_score", 0) or 0),
                "breach_budget_total": budget_total,
                "breach_budget_consumed": consumed,
                "breach_budget_remaining": max(0, budget_total - consumed),
                "breach_budget_exhausted": exhausted,
            }
        )
    rows.sort(key=lambda r: (not bool(r["breach_budget_exhausted"]), -int(r["federated_risk_score"])))
    return {"count": len(rows), "breach_budget_exhausted_count": exhausted_count, "rows": rows}
