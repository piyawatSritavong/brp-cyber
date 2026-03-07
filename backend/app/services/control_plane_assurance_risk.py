from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Tenant
from app.services.control_plane_assurance_contracts import evaluate_assurance_contract
from app.services.control_plane_assurance_policy_packs import get_assurance_policy_pack, upsert_assurance_policy_pack
from app.services.control_plane_assurance_remediation import assurance_remediation_effectiveness
from app.services.enterprise.objective_gate import objective_gate_dashboard

RISK_TIERS = ("low", "medium", "high", "critical")
RISK_TIER_SCORE = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _list_tenants(db: Session, limit: int) -> list[Tenant]:
    return db.query(Tenant).limit(max(1, limit)).all()


def _risk_tier(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def _recommended_pack_for_tier(tier: str) -> dict[str, Any]:
    if tier == "critical":
        return {
            "auto_apply_actions": ["tighten_blue_threshold"],
            "force_approval_actions": ["enable_approval_mode", "set_strategy_profile"],
            "blocked_actions": [],
            "max_auto_apply_actions_per_run": 1,
            "notify_only": False,
            "rollback_on_worse_result": True,
            "min_effectiveness_delta": 0.02,
        }
    if tier == "high":
        return {
            "auto_apply_actions": ["tighten_blue_threshold"],
            "force_approval_actions": ["enable_approval_mode"],
            "blocked_actions": [],
            "max_auto_apply_actions_per_run": 1,
            "notify_only": False,
            "rollback_on_worse_result": True,
            "min_effectiveness_delta": 0.01,
        }
    if tier == "medium":
        return {
            "auto_apply_actions": ["tighten_blue_threshold"],
            "force_approval_actions": [],
            "blocked_actions": [],
            "max_auto_apply_actions_per_run": 1,
            "notify_only": False,
            "rollback_on_worse_result": True,
            "min_effectiveness_delta": 0.0,
        }
    return {
        "auto_apply_actions": [],
        "force_approval_actions": [],
        "blocked_actions": [],
        "max_auto_apply_actions_per_run": 1,
        "notify_only": False,
        "rollback_on_worse_result": True,
        "min_effectiveness_delta": 0.0,
    }


def assurance_risk_heatmap(db: Session, limit: int = 200) -> dict[str, Any]:
    tenants = _list_tenants(db, limit)
    objective_rows = objective_gate_dashboard(limit=max(1, limit)).get("rows", [])
    objective_map = {str(row.get("tenant_id", "")): row for row in objective_rows}

    rows: list[dict[str, Any]] = []
    tier_counts = {tier: 0 for tier in RISK_TIERS}

    for tenant in tenants:
        tenant_id = str(tenant.id)
        objective = objective_map.get(tenant_id, {})
        failed_gate_count = int(objective.get("failed_gate_count", 0) or 0)
        overall_objective_pass = bool(objective.get("overall_pass", False))

        contract = evaluate_assurance_contract(tenant.id, tenant.tenant_code, limit=200)
        contract_eval = contract.get("evaluation", {}) if contract.get("status") == "ok" else {}
        contract_pass = bool(contract_eval.get("contract_pass", False))

        effectiveness = assurance_remediation_effectiveness(tenant.tenant_code, limit=200)
        avg_delta = float(effectiveness.get("average_effectiveness_delta", 0.0) or 0.0)
        rollback_batches = int(effectiveness.get("rollback_batches", 0) or 0)

        risk_score = 0
        if not overall_objective_pass:
            risk_score += 30
        if not contract_pass:
            risk_score += 35
        risk_score += min(20, failed_gate_count * 3)
        if avg_delta < 0:
            risk_score += 10
        if rollback_batches > 0:
            risk_score += 5
        risk_score = max(0, min(100, risk_score))

        tier = _risk_tier(risk_score)
        tier_counts[tier] += 1

        rows.append(
            {
                "tenant_id": tenant_id,
                "tenant_code": tenant.tenant_code,
                "risk_score": risk_score,
                "risk_tier": tier,
                "objective_gate_pass": overall_objective_pass,
                "failed_gate_count": failed_gate_count,
                "contract_pass": contract_pass,
                "average_effectiveness_delta": round(avg_delta, 4),
                "rollback_batches": rollback_batches,
            }
        )

    rows.sort(key=lambda row: (-int(row["risk_score"]), row["tenant_code"]))
    return {"count": len(rows), "tier_counts": tier_counts, "rows": rows}


def assurance_risk_recommendations(db: Session, limit: int = 200) -> dict[str, Any]:
    heatmap = assurance_risk_heatmap(db, limit=limit)
    recommendations: list[dict[str, Any]] = []

    for row in heatmap.get("rows", []):
        tier = str(row.get("risk_tier", "low"))
        if tier == "low":
            continue
        recommendations.append(
            {
                "tenant_id": row.get("tenant_id", ""),
                "tenant_code": row.get("tenant_code", ""),
                "risk_score": row.get("risk_score", 0),
                "risk_tier": tier,
                "recommended_policy_pack": _recommended_pack_for_tier(tier),
            }
        )

    return {"count": len(recommendations), "rows": recommendations}


def apply_assurance_risk_recommendations(
    db: Session,
    limit: int = 200,
    max_tier: str = "critical",
    dry_run: bool = True,
) -> dict[str, Any]:
    max_tier_value = RISK_TIER_SCORE.get(max_tier, RISK_TIER_SCORE["critical"])
    recommendations = assurance_risk_recommendations(db, limit=limit).get("rows", [])
    applied_rows: list[dict[str, Any]] = []

    for rec in recommendations:
        tier = str(rec.get("risk_tier", "low"))
        if RISK_TIER_SCORE.get(tier, 0) < max_tier_value:
            continue

        tenant_code = str(rec.get("tenant_code", ""))
        existing_pack = get_assurance_policy_pack(tenant_code).get("policy_pack", {})
        merged = {
            **existing_pack,
            **dict(rec.get("recommended_policy_pack", {})),
            "owner": "adaptive-risk-loop",
            "pack_version": "2.0",
        }

        result = (
            {"status": "dry_run", "tenant_code": tenant_code, "policy_pack": merged}
            if dry_run
            else upsert_assurance_policy_pack(tenant_code, merged)
        )
        applied_rows.append(
            {
                "tenant_code": tenant_code,
                "risk_tier": tier,
                "risk_score": rec.get("risk_score", 0),
                "status": result.get("status", "unknown"),
            }
        )

    return {"count": len(applied_rows), "dry_run": dry_run, "rows": applied_rows}
