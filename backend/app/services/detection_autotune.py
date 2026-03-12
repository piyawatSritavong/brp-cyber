from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    BlueDetectionAutotunePolicy,
    BlueDetectionAutotuneRun,
    BlueEventLog,
    RedExploitPathRun,
    Site,
    Tenant,
)
from app.db.session import SessionLocal
from app.services.action_center import dispatch_manual_alert
from app.services.competitive_engine import run_detection_copilot_tuning
from schemas.competitive import DetectionCopilotTuneRequest

RISK_TIER_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _as_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _safe_json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _safe_iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _normalize_tier(value: str) -> str:
    tier = str(value or "").strip().lower()
    return tier if tier in RISK_TIER_ORDER else "high"


def _tier_rank(value: str) -> int:
    return RISK_TIER_ORDER.get(_normalize_tier(value), 2)


def _site_risk_signal(db: Session, site_id: UUID, *, lookback_events: int = 500) -> dict[str, Any]:
    latest_exploit = db.scalar(
        select(RedExploitPathRun).where(RedExploitPathRun.site_id == site_id).order_by(desc(RedExploitPathRun.created_at)).limit(1)
    )
    blue_events = db.scalars(
        select(BlueEventLog)
        .where(BlueEventLog.site_id == site_id)
        .order_by(desc(BlueEventLog.created_at))
        .limit(max(1, min(lookback_events, 2000)))
    ).all()

    suspicious = [
        event
        for event in blue_events
        if event.ai_severity in {"high", "medium"}
        or "brute" in event.payload_json.lower()
        or "ransom" in event.payload_json.lower()
        or "sql" in event.payload_json.lower()
    ]
    detected = [event for event in suspicious if event.ai_severity in {"high", "medium"}]
    open_suspicious = [event for event in suspicious if event.status == "open"]
    applied_suspicious = [event for event in suspicious if event.status == "applied"]

    detection_coverage = round((len(detected) / len(suspicious)), 4) if suspicious else 0.5
    apply_rate = round((len(applied_suspicious) / len(suspicious)), 4) if suspicious else 0.0

    exploit_risk = int(latest_exploit.risk_score or 0) if latest_exploit else 0
    score = min(
        100,
        int(
            (exploit_risk * 0.45)
            + (len(open_suspicious) * 7)
            + ((1.0 - detection_coverage) * 40)
            + ((1.0 - apply_rate) * 20)
        ),
    )
    if score >= 80:
        tier = "critical"
    elif score >= 60:
        tier = "high"
    elif score >= 35:
        tier = "medium"
    else:
        tier = "low"

    return {
        "risk_score": score,
        "risk_tier": tier,
        "exploit_risk": exploit_risk,
        "blue_event_count": len(blue_events),
        "suspicious_event_count": len(suspicious),
        "open_suspicious_count": len(open_suspicious),
        "applied_suspicious_count": len(applied_suspicious),
        "detection_coverage": detection_coverage,
        "apply_rate": apply_rate,
    }


def _policy_row(row: BlueDetectionAutotunePolicy) -> dict[str, Any]:
    return {
        "policy_id": str(row.id),
        "site_id": str(row.site_id),
        "min_risk_score": row.min_risk_score,
        "min_risk_tier": row.min_risk_tier,
        "target_detection_coverage_pct": row.target_detection_coverage_pct,
        "max_rules_per_run": row.max_rules_per_run,
        "auto_apply": bool(row.auto_apply),
        "route_alert": bool(row.route_alert),
        "schedule_interval_minutes": row.schedule_interval_minutes,
        "enabled": bool(row.enabled),
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _default_policy(site_id: UUID) -> dict[str, Any]:
    return {
        "policy_id": "",
        "site_id": str(site_id),
        "min_risk_score": 60,
        "min_risk_tier": "high",
        "target_detection_coverage_pct": 90,
        "max_rules_per_run": 3,
        "auto_apply": False,
        "route_alert": True,
        "schedule_interval_minutes": 60,
        "enabled": True,
        "owner": "system",
        "created_at": "",
        "updated_at": "",
    }


def _run_row(row: BlueDetectionAutotuneRun) -> dict[str, Any]:
    return {
        "run_id": str(row.id),
        "site_id": str(row.site_id),
        "status": row.status,
        "dry_run": bool(row.dry_run),
        "risk_score": row.risk_score,
        "risk_tier": row.risk_tier,
        "coverage_before_pct": row.coverage_before_pct,
        "coverage_after_pct": row.coverage_after_pct,
        "recommendation_count": row.recommendation_count,
        "applied_count": row.applied_count,
        "alert_routed": bool(row.alert_routed),
        "details": _safe_json_dict(row.details_json),
        "created_at": _safe_iso(row.created_at),
    }


def get_detection_autotune_policy(db: Session, site_id: UUID) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    row = db.scalar(select(BlueDetectionAutotunePolicy).where(BlueDetectionAutotunePolicy.site_id == site.id))
    if row:
        return {"status": "ok", "policy": _policy_row(row)}
    return {"status": "default", "policy": _default_policy(site.id)}


def upsert_detection_autotune_policy(
    db: Session,
    *,
    site_id: UUID,
    min_risk_score: int,
    min_risk_tier: str,
    target_detection_coverage_pct: int,
    max_rules_per_run: int,
    auto_apply: bool,
    route_alert: bool,
    schedule_interval_minutes: int,
    enabled: bool,
    owner: str,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}

    row = db.scalar(select(BlueDetectionAutotunePolicy).where(BlueDetectionAutotunePolicy.site_id == site.id))
    now = datetime.now(timezone.utc)
    if row:
        row.min_risk_score = max(1, min(int(min_risk_score), 100))
        row.min_risk_tier = _normalize_tier(min_risk_tier)
        row.target_detection_coverage_pct = max(1, min(int(target_detection_coverage_pct), 100))
        row.max_rules_per_run = max(1, min(int(max_rules_per_run), 10))
        row.auto_apply = bool(auto_apply)
        row.route_alert = bool(route_alert)
        row.schedule_interval_minutes = max(5, min(int(schedule_interval_minutes), 1440))
        row.enabled = bool(enabled)
        row.owner = owner.strip()[:64] or "security"
        row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"status": "updated", "policy": _policy_row(row)}

    created = BlueDetectionAutotunePolicy(
        site_id=site.id,
        min_risk_score=max(1, min(int(min_risk_score), 100)),
        min_risk_tier=_normalize_tier(min_risk_tier),
        target_detection_coverage_pct=max(1, min(int(target_detection_coverage_pct), 100)),
        max_rules_per_run=max(1, min(int(max_rules_per_run), 10)),
        auto_apply=bool(auto_apply),
        route_alert=bool(route_alert),
        schedule_interval_minutes=max(5, min(int(schedule_interval_minutes), 1440)),
        enabled=bool(enabled),
        owner=owner.strip()[:64] or "security",
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"status": "created", "policy": _policy_row(created)}


def run_detection_autotune(
    db: Session,
    *,
    site_id: UUID,
    dry_run: bool | None = None,
    force: bool = False,
    actor: str = "blue_autotune_ai",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}

    policy_resp = get_detection_autotune_policy(db, site_id)
    policy = policy_resp.get("policy", {}) if isinstance(policy_resp, dict) else {}
    if not policy:
        return {"status": "policy_not_found", "site_id": str(site_id)}
    if not bool(policy.get("enabled", True)):
        return {"status": "disabled", "site_id": str(site_id), "policy": policy}

    risk = _site_risk_signal(db, site_id, lookback_events=500)
    coverage_before_pct = int(round(float(risk.get("detection_coverage", 0.0)) * 100))

    threshold_score = int(policy.get("min_risk_score", 60) or 60)
    threshold_tier = _normalize_tier(str(policy.get("min_risk_tier", "high")))
    target_coverage_pct = int(policy.get("target_detection_coverage_pct", 90) or 90)

    risk_trigger = int(risk.get("risk_score", 0)) >= threshold_score and _tier_rank(str(risk.get("risk_tier", "low"))) >= _tier_rank(
        threshold_tier
    )
    coverage_trigger = coverage_before_pct < target_coverage_pct
    should_tune = bool(force or risk_trigger or coverage_trigger)

    resolved_dry_run = (not bool(policy.get("auto_apply", False))) if dry_run is None else bool(dry_run)

    tuning = {
        "status": "skipped",
        "recommendations": [],
        "before_metrics": {"detection_coverage": round(coverage_before_pct / 100.0, 4)},
        "after_metrics": {"detection_coverage": round(coverage_before_pct / 100.0, 4)},
    }
    status = "no_action"
    reason = "risk_and_coverage_below_policy_threshold"
    if should_tune:
        tuning = run_detection_copilot_tuning(
            db,
            site_id,
            DetectionCopilotTuneRequest(
                rule_count=max(1, min(int(policy.get("max_rules_per_run", 3) or 3), 10)),
                auto_apply=bool(policy.get("auto_apply", False)),
                dry_run=resolved_dry_run,
            ),
        )
        status = "ok" if tuning.get("status") in {"completed", "dry_run"} else str(tuning.get("status", "unknown"))
        reason = "policy_triggered_autotune"

    recommendations = tuning.get("recommendations", []) if isinstance(tuning, dict) else []
    recommendation_count = len(recommendations) if isinstance(recommendations, list) else 0
    coverage_after = (tuning.get("after_metrics", {}) or {}).get("detection_coverage", coverage_before_pct / 100.0)
    try:
        coverage_after_pct = int(round(float(coverage_after) * 100))
    except Exception:
        coverage_after_pct = coverage_before_pct

    applied_count = 0
    if should_tune and not resolved_dry_run and bool(policy.get("auto_apply", False)):
        applied_count = recommendation_count

    alert = {"status": "skipped"}
    should_alert = bool(policy.get("route_alert", True)) and (
        _tier_rank(str(risk.get("risk_tier", "low"))) >= _tier_rank("high") or (should_tune and recommendation_count > 0)
    )
    if should_alert:
        tenant = db.get(Tenant, site.tenant_id)
        if tenant:
            severity = "critical" if str(risk.get("risk_tier", "low")) == "critical" else "high"
            alert = dispatch_manual_alert(
                db,
                tenant_code=tenant.tenant_code,
                site_code=site.site_code,
                source="blue_detection_autotune",
                severity=severity,
                title=f"Blue Detection Autotune {status}",
                message=(
                    f"site={site.site_code} risk={risk.get('risk_tier')} score={risk.get('risk_score')} "
                    f"dry_run={resolved_dry_run} recommendations={recommendation_count} applied={applied_count}"
                ),
                payload={
                    "site_id": str(site.id),
                    "site_code": site.site_code,
                    "risk": risk,
                    "policy": policy,
                    "status": status,
                    "recommendation_count": recommendation_count,
                    "applied_count": applied_count,
                    "dry_run": resolved_dry_run,
                },
            )

    run = BlueDetectionAutotuneRun(
        site_id=site.id,
        status=status,
        dry_run=resolved_dry_run,
        risk_score=int(risk.get("risk_score", 0) or 0),
        risk_tier=str(risk.get("risk_tier", "low") or "low"),
        coverage_before_pct=coverage_before_pct,
        coverage_after_pct=coverage_after_pct,
        recommendation_count=recommendation_count,
        applied_count=applied_count,
        alert_routed=alert.get("status") == "ok",
        details_json=_as_json(
            {
                "reason": reason,
                "force": force,
                "actor": actor,
                "risk": risk,
                "policy": policy,
                "tuning_status": tuning.get("status", "skipped") if isinstance(tuning, dict) else "skipped",
                "tuning_run_id": str(tuning.get("tuning_run_id", "")) if isinstance(tuning, dict) else "",
                "expected_detection_coverage_delta": tuning.get("expected_detection_coverage_delta", 0.0)
                if isinstance(tuning, dict)
                else 0.0,
            }
        ),
        created_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return {
        "status": status,
        "site_id": str(site.id),
        "site_code": site.site_code,
        "policy": policy,
        "risk": risk,
        "execution": {
            "should_tune": should_tune,
            "dry_run": resolved_dry_run,
            "recommendation_count": recommendation_count,
            "applied_count": applied_count,
            "reason": reason,
        },
        "tuning": tuning,
        "alert": alert,
        "run": _run_row(run),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def list_detection_autotune_runs(db: Session, *, site_id: UUID, limit: int = 100) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"count": 0, "rows": []}

    rows = db.scalars(
        select(BlueDetectionAutotuneRun)
        .where(BlueDetectionAutotuneRun.site_id == site.id)
        .order_by(desc(BlueDetectionAutotuneRun.created_at))
        .limit(max(1, min(limit, 1000)))
    ).all()
    return {
        "site_id": str(site.id),
        "count": len(rows),
        "rows": [_run_row(row) for row in rows],
    }


def _is_schedule_due(policy: BlueDetectionAutotunePolicy, last_run: BlueDetectionAutotuneRun | None, now: datetime) -> bool:
    if not bool(policy.enabled):
        return False
    if last_run is None:
        return True
    if last_run.created_at is None:
        return True
    created_at = last_run.created_at if last_run.created_at.tzinfo else last_run.created_at.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(minutes=max(5, int(policy.schedule_interval_minutes or 60)))
    return created_at <= cutoff


def run_detection_autotune_scheduler(
    db: Session,
    *,
    limit: int = 200,
    dry_run_override: bool | None = None,
    actor: str = "blue_autotune_ai",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    policies = db.scalars(
        select(BlueDetectionAutotunePolicy)
        .where(BlueDetectionAutotunePolicy.enabled.is_(True))
        .order_by(desc(BlueDetectionAutotunePolicy.updated_at))
        .limit(max(1, min(limit, 2000)))
    ).all()

    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for policy in policies:
        site = db.get(Site, policy.site_id)
        if not site:
            skipped.append({"site_id": str(policy.site_id), "site_code": "", "reason": "site_not_found"})
            continue

        last_run = db.scalar(
            select(BlueDetectionAutotuneRun)
            .where(BlueDetectionAutotuneRun.site_id == site.id)
            .order_by(desc(BlueDetectionAutotuneRun.created_at))
            .limit(1)
        )
        if not _is_schedule_due(policy, last_run, now):
            skipped.append({"site_id": str(site.id), "site_code": site.site_code, "reason": "schedule_not_due"})
            continue

        result = run_detection_autotune(
            db,
            site_id=site.id,
            dry_run=dry_run_override,
            force=False,
            actor=actor,
        )
        executed.append(
            {
                "site_id": str(site.id),
                "site_code": site.site_code,
                "status": str(result.get("status", "unknown")),
                "run_id": str((result.get("run", {}) or {}).get("run_id", "")),
                "risk_tier": str((result.get("risk", {}) or {}).get("risk_tier", "")),
            }
        )

    return {
        "timestamp": now.isoformat(),
        "scheduled_policy_count": len(policies),
        "executed_count": len(executed),
        "skipped_count": len(skipped),
        "executed": executed,
        "skipped": skipped,
    }


def process_detection_autotune_schedules(limit: int = 100) -> dict[str, Any]:
    with SessionLocal() as db:
        return run_detection_autotune_scheduler(
            db,
            limit=limit,
            dry_run_override=None,
            actor="blue_autotune_ai",
        )
