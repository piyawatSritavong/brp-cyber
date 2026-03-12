from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import ActionCenterDispatchEvent, ConnectorSlaBreachEvent, Tenant


def _risk_tier(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _recommended_action(tier: str) -> str:
    if tier == "critical":
        return "Require dual-approval on containment and tighten connector SLA thresholds immediately."
    if tier == "high":
        return "Increase scan cadence, enforce stricter action-center routing, and review connector reliability daily."
    if tier == "medium":
        return "Monitor trend and tune thresholds for noisy connectors."
    return "Maintain baseline and keep weekly validation."


def action_center_sla_federation_snapshot(
    db: Session,
    *,
    lookback_hours: int = 24,
    limit: int = 200,
) -> dict[str, object]:
    window_hours = max(1, min(lookback_hours, 24 * 30))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    max_rows = max(1, min(limit, 2000))

    tenants = db.scalars(select(Tenant).order_by(Tenant.created_at.desc()).limit(max_rows)).all()
    tenant_index: dict[str, dict[str, Any]] = {
        str(tenant.id): {
            "tenant_id": str(tenant.id),
            "tenant_code": tenant.tenant_code,
            "breach_count": 0,
            "critical_breach_count": 0,
            "high_breach_count": 0,
            "routed_breach_count": 0,
            "dispatch_count": 0,
            "dispatch_high_or_critical_count": 0,
            "failed_channel_count": 0,
            "last_breach_at": "",
            "last_dispatch_at": "",
            "risk_score": 0,
            "risk_tier": "low",
            "recommended_action": "",
        }
        for tenant in tenants
    }

    breach_rows = db.scalars(
        select(ConnectorSlaBreachEvent)
        .where(ConnectorSlaBreachEvent.created_at >= cutoff)
        .order_by(desc(ConnectorSlaBreachEvent.created_at))
        .limit(max_rows * 20)
    ).all()
    dispatch_rows = db.scalars(
        select(ActionCenterDispatchEvent)
        .where(ActionCenterDispatchEvent.created_at >= cutoff)
        .order_by(desc(ActionCenterDispatchEvent.created_at))
        .limit(max_rows * 30)
    ).all()

    for row in breach_rows:
        key = str(row.tenant_id)
        if key not in tenant_index:
            continue
        bucket = tenant_index[key]
        bucket["breach_count"] += 1
        if row.severity == "critical":
            bucket["critical_breach_count"] += 1
        if row.severity == "high":
            bucket["high_breach_count"] += 1
        if row.routed:
            bucket["routed_breach_count"] += 1
        if not bucket["last_breach_at"]:
            bucket["last_breach_at"] = row.created_at.isoformat() if row.created_at else ""

    for row in dispatch_rows:
        key = str(row.tenant_id)
        if key not in tenant_index:
            continue
        bucket = tenant_index[key]
        bucket["dispatch_count"] += 1
        if row.severity in {"high", "critical"}:
            bucket["dispatch_high_or_critical_count"] += 1
        if row.telegram_status == "failed" or row.line_status == "failed":
            bucket["failed_channel_count"] += 1
        if not bucket["last_dispatch_at"]:
            bucket["last_dispatch_at"] = row.created_at.isoformat() if row.created_at else ""

    rows: list[dict[str, Any]] = []
    for bucket in tenant_index.values():
        if bucket["breach_count"] == 0 and bucket["dispatch_count"] == 0:
            continue
        score = 0
        score += min(50, int(bucket["breach_count"]) * 10)
        score += min(30, int(bucket["dispatch_high_or_critical_count"]) * 5)
        score += min(20, int(bucket["failed_channel_count"]) * 10)
        bucket["risk_score"] = min(100, score)
        bucket["risk_tier"] = _risk_tier(bucket["risk_score"])
        bucket["recommended_action"] = _recommended_action(bucket["risk_tier"])
        rows.append(bucket)

    rows.sort(key=lambda item: (item["risk_score"], item["breach_count"], item["dispatch_count"]), reverse=True)
    rows = rows[:max_rows]

    tier_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for row in rows:
        tier_counts[row["risk_tier"]] = tier_counts.get(row["risk_tier"], 0) + 1

    return {
        "window_hours": window_hours,
        "count": len(rows),
        "tier_counts": tier_counts,
        "rows": rows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
