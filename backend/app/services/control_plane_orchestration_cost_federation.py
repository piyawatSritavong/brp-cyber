from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Tenant
from app.services.control_plane_orchestration_cost_guardrail import (
    evaluate_orchestration_cost_guardrail,
    get_orchestration_cost_guardrail_profile,
    upsert_orchestration_cost_guardrail_profile,
)


def _list_tenants(db: Session, limit: int) -> list[Tenant]:
    return db.query(Tenant).limit(max(1, limit)).all()


def _risk_tier(*, breached: bool, anomaly: bool, pressure_ratio: float) -> str:
    if breached:
        return "critical"
    if anomaly or pressure_ratio >= 1.1:
        return "high"
    if pressure_ratio >= 0.8:
        return "medium"
    return "low"


def orchestration_cost_anomaly_federation_heatmap(db: Session, limit: int = 200) -> dict[str, Any]:
    tenants = _list_tenants(db, limit=max(1, limit))
    rows: list[dict[str, Any]] = []

    for tenant in tenants:
        evaluated = evaluate_orchestration_cost_guardrail(tenant.id, tenant.tenant_code, apply_actions=False)
        state = dict(evaluated.get("state", {}))
        metrics = dict(evaluated.get("metrics", {}))
        pressure_ratio = float(metrics.get("pressure_ratio", 0.0) or 0.0)
        row = {
            "tenant_id": str(tenant.id),
            "tenant_code": tenant.tenant_code,
            "risk_tier": _risk_tier(
                breached=bool(state.get("breached", False)),
                anomaly=bool(state.get("anomaly", False)),
                pressure_ratio=pressure_ratio,
            ),
            "severity": str(state.get("severity", "normal")),
            "breached": bool(state.get("breached", False)),
            "anomaly": bool(state.get("anomaly", False)),
            "pressure": bool(state.get("pressure", False)),
            "pressure_ratio": pressure_ratio,
            "cost_ratio": float(metrics.get("cost_ratio", 0.0) or 0.0),
            "token_ratio": float(metrics.get("token_ratio", 0.0) or 0.0),
            "monthly_cost_usd": float(metrics.get("monthly_cost_usd", 0.0) or 0.0),
            "monthly_tokens": int(metrics.get("monthly_tokens", 0) or 0),
        }
        rows.append(row)

    tier_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    rows.sort(key=lambda r: (-tier_rank.get(str(r.get("risk_tier", "low")), 1), -float(r.get("pressure_ratio", 0.0))))

    return {
        "count": len(rows),
        "critical_count": sum(1 for r in rows if r["risk_tier"] == "critical"),
        "high_count": sum(1 for r in rows if r["risk_tier"] == "high"),
        "medium_count": sum(1 for r in rows if r["risk_tier"] == "medium"),
        "low_count": sum(1 for r in rows if r["risk_tier"] == "low"),
        "rows": rows,
    }


def orchestration_cost_policy_tightening_matrix(db: Session, limit: int = 200) -> dict[str, Any]:
    heatmap = orchestration_cost_anomaly_federation_heatmap(db, limit=limit)
    rows: list[dict[str, Any]] = []

    for row in heatmap.get("rows", []):
        tier = str(row.get("risk_tier", "low"))
        if tier == "critical":
            recommended = {
                "pressure_ratio_threshold": 0.55,
                "anomaly_delta_threshold": 0.08,
                "anomaly_min_pressure_ratio": 0.25,
                "throttle_mode_on_anomaly": "strict",
                "force_fallback_on_pressure": True,
                "preemptive_throttle_on_anomaly": True,
                "hard_stop_on_limit": True,
            }
        elif tier == "high":
            recommended = {
                "pressure_ratio_threshold": 0.65,
                "anomaly_delta_threshold": 0.1,
                "anomaly_min_pressure_ratio": 0.35,
                "throttle_mode_on_anomaly": "strict",
                "force_fallback_on_pressure": True,
                "preemptive_throttle_on_anomaly": True,
                "hard_stop_on_limit": False,
            }
        elif tier == "medium":
            recommended = {
                "pressure_ratio_threshold": 0.75,
                "anomaly_delta_threshold": 0.15,
                "anomaly_min_pressure_ratio": 0.45,
                "throttle_mode_on_anomaly": "conservative",
                "force_fallback_on_pressure": True,
                "preemptive_throttle_on_anomaly": True,
                "hard_stop_on_limit": False,
            }
        else:
            recommended = {
                "pressure_ratio_threshold": 0.85,
                "anomaly_delta_threshold": 0.2,
                "anomaly_min_pressure_ratio": 0.5,
                "throttle_mode_on_anomaly": "conservative",
                "force_fallback_on_pressure": True,
                "preemptive_throttle_on_anomaly": True,
                "hard_stop_on_limit": False,
            }

        rows.append(
            {
                "tenant_id": row.get("tenant_id", ""),
                "tenant_code": row.get("tenant_code", ""),
                "risk_tier": tier,
                "current_pressure_ratio": row.get("pressure_ratio", 0.0),
                "recommended_profile_patch": recommended,
            }
        )

    return {"count": len(rows), "rows": rows}


def apply_orchestration_cost_policy_tightening_matrix(
    db: Session,
    limit: int = 200,
    *,
    min_tier: str = "high",
    dry_run: bool = True,
) -> dict[str, Any]:
    tier_rank = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    minimum = tier_rank.get(str(min_tier).strip().lower(), 3)

    matrix = orchestration_cost_policy_tightening_matrix(db, limit=limit)
    rows: list[dict[str, Any]] = []

    for row in matrix.get("rows", []):
        tier = str(row.get("risk_tier", "low"))
        if tier_rank.get(tier, 1) < minimum:
            continue

        try:
            tenant_id = UUID(str(row.get("tenant_id", "")))
        except (TypeError, ValueError):
            rows.append({
                "tenant_id": str(row.get("tenant_id", "")),
                "tenant_code": str(row.get("tenant_code", "")),
                "risk_tier": tier,
                "status": "not_found",
            })
            continue

        patch = dict(row.get("recommended_profile_patch", {}))
        current = get_orchestration_cost_guardrail_profile(tenant_id).get("profile", {})
        merged = dict(current)
        merged.update(patch)

        if dry_run:
            rows.append(
                {
                    "tenant_id": str(tenant_id),
                    "tenant_code": str(row.get("tenant_code", "")),
                    "risk_tier": tier,
                    "status": "dry_run",
                    "profile_patch": patch,
                }
            )
            continue

        upserted = upsert_orchestration_cost_guardrail_profile(tenant_id, merged)
        rows.append(
            {
                "tenant_id": str(tenant_id),
                "tenant_code": str(row.get("tenant_code", "")),
                "risk_tier": tier,
                "status": "applied",
                "profile_patch": patch,
                "updated_profile": upserted.get("profile", {}),
            }
        )

    return {"count": len(rows), "dry_run": dry_run, "min_tier": min_tier, "rows": rows}
