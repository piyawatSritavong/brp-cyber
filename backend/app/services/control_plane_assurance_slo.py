from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Tenant
from app.services.control_plane_assurance_contracts import evaluate_assurance_contract
from app.services.control_plane_assurance_remediation import assurance_remediation_effectiveness
from app.services.control_plane_assurance_risk import assurance_risk_heatmap
from app.services.enterprise.slo import get_slo_snapshot
from app.services.redis_client import redis_client

ASSURANCE_SLO_PROFILE_PREFIX = "control_plane_assurance_slo_profile"
ASSURANCE_SLO_BUDGET_PREFIX = "control_plane_assurance_slo_budget"
ASSURANCE_SLO_BREACH_STREAM_PREFIX = "control_plane_assurance_slo_breaches"


def _profile_key(tenant_code: str) -> str:
    return f"{ASSURANCE_SLO_PROFILE_PREFIX}:{tenant_code.lower().strip()}"


def _budget_key(tenant_code: str) -> str:
    period = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{ASSURANCE_SLO_BUDGET_PREFIX}:{tenant_code.lower().strip()}:{period}"


def _breach_stream_key(tenant_code: str) -> str:
    return f"{ASSURANCE_SLO_BREACH_STREAM_PREFIX}:{tenant_code.lower().strip()}"


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_profile(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "profile_version": str(payload.get("profile_version", "1.0")),
        "owner": str(payload.get("owner", "security")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "max_breaches_per_day": max(1, _as_int(payload.get("max_breaches_per_day"), 5)),
        "min_contract_pass_rate": min(1.0, max(0.0, _as_float(payload.get("min_contract_pass_rate"), 0.95))),
        "min_effectiveness_delta": _as_float(payload.get("min_effectiveness_delta"), 0.0),
        "max_rollback_batches": max(0, _as_int(payload.get("max_rollback_batches"), 0)),
        "min_availability": min(1.0, max(0.0, _as_float(payload.get("min_availability"), 0.995))),
        "max_error_rate": min(1.0, max(0.0, _as_float(payload.get("max_error_rate"), 0.01))),
    }


def upsert_assurance_slo_profile(tenant_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    profile = _normalize_profile(payload)
    redis_client.set(_profile_key(tenant_code), json.dumps(profile, ensure_ascii=True, sort_keys=True))
    return {"status": "upserted", "tenant_code": tenant_code, "profile": profile}


def get_assurance_slo_profile(tenant_code: str) -> dict[str, Any]:
    raw = redis_client.get(_profile_key(tenant_code))
    if not raw:
        return {"status": "default", "tenant_code": tenant_code, "profile": _normalize_profile({})}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "corrupted", "tenant_code": tenant_code}
    return {"status": "ok", "tenant_code": tenant_code, "profile": _normalize_profile(loaded)}


def evaluate_assurance_slo(tenant_id: UUID, tenant_code: str, limit: int = 200) -> dict[str, Any]:
    profile_resp = get_assurance_slo_profile(tenant_code)
    if profile_resp.get("status") == "corrupted":
        return profile_resp
    profile = profile_resp.get("profile", _normalize_profile({}))

    contract = evaluate_assurance_contract(tenant_id, tenant_code, limit=limit)
    contract_eval = contract.get("evaluation", {}) if contract.get("status") == "ok" else {}
    overall_pass_rate = _as_float(contract_eval.get("overall_pass_rate"), 0.0)

    effectiveness = assurance_remediation_effectiveness(tenant_code, limit=limit)
    avg_delta = _as_float(effectiveness.get("average_effectiveness_delta"), 0.0)
    rollback_batches = _as_int(effectiveness.get("rollback_batches"), 0)

    tenant_slo = get_slo_snapshot(tenant_id)
    availability = _as_float(tenant_slo.get("availability"), 1.0)
    requests_total = max(0, _as_int(tenant_slo.get("requests_total"), 0))
    requests_failed = max(0, _as_int(tenant_slo.get("requests_failed"), 0))
    error_rate = (requests_failed / requests_total) if requests_total else 0.0

    breaches: list[dict[str, Any]] = []
    if overall_pass_rate < _as_float(profile.get("min_contract_pass_rate"), 0.95):
        breaches.append(
            {
                "clause": "min_contract_pass_rate",
                "required": _as_float(profile.get("min_contract_pass_rate"), 0.95),
                "actual": round(overall_pass_rate, 4),
            }
        )
    if avg_delta < _as_float(profile.get("min_effectiveness_delta"), 0.0):
        breaches.append(
            {
                "clause": "min_effectiveness_delta",
                "required": _as_float(profile.get("min_effectiveness_delta"), 0.0),
                "actual": round(avg_delta, 4),
            }
        )
    if rollback_batches > _as_int(profile.get("max_rollback_batches"), 0):
        breaches.append(
            {
                "clause": "max_rollback_batches",
                "required": _as_int(profile.get("max_rollback_batches"), 0),
                "actual": rollback_batches,
            }
        )
    if availability < _as_float(profile.get("min_availability"), 0.995):
        breaches.append(
            {
                "clause": "min_availability",
                "required": _as_float(profile.get("min_availability"), 0.995),
                "actual": round(availability, 6),
            }
        )
    if error_rate > _as_float(profile.get("max_error_rate"), 0.01):
        breaches.append(
            {
                "clause": "max_error_rate",
                "required": _as_float(profile.get("max_error_rate"), 0.01),
                "actual": round(error_rate, 6),
            }
        )

    budget_key = _budget_key(tenant_code)
    consumed = _as_int(redis_client.get(budget_key), 0)
    breach = len(breaches) > 0
    if breach:
        consumed += 1
        redis_client.set(budget_key, str(consumed))

        redis_client.xadd(
            _breach_stream_key(tenant_code),
            {
                "tenant_id": str(tenant_id),
                "tenant_code": tenant_code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "breach_count": str(len(breaches)),
                "breaches": json.dumps(breaches, ensure_ascii=True),
                "overall_pass_rate": str(round(overall_pass_rate, 4)),
                "average_effectiveness_delta": str(round(avg_delta, 4)),
                "availability": str(round(availability, 6)),
                "error_rate": str(round(error_rate, 6)),
            },
            maxlen=100000,
            approximate=True,
        )

    budget_total = _as_int(profile.get("max_breaches_per_day"), 5)
    remaining = max(0, budget_total - consumed)

    return {
        "status": "ok",
        "tenant_id": str(tenant_id),
        "tenant_code": tenant_code,
        "profile": profile,
        "metrics": {
            "overall_pass_rate": round(overall_pass_rate, 4),
            "average_effectiveness_delta": round(avg_delta, 4),
            "rollback_batches": rollback_batches,
            "availability": round(availability, 6),
            "error_rate": round(error_rate, 6),
            "requests_total": requests_total,
            "requests_failed": requests_failed,
        },
        "breach": breach,
        "breaches": breaches,
        "breach_budget": {
            "period": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "total": budget_total,
            "consumed": consumed,
            "remaining": remaining,
            "exhausted": consumed >= budget_total,
        },
    }


def assurance_slo_breach_history(tenant_code: str, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_breach_stream_key(tenant_code), count=max(1, limit))
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


def assurance_executive_risk_digest(db: Session, limit: int = 200) -> dict[str, Any]:
    heatmap = assurance_risk_heatmap(db, limit=limit)
    tenants = db.query(Tenant).limit(max(1, limit)).all()
    rows: list[dict[str, Any]] = []

    heatmap_by_code = {str(row.get("tenant_code", "")): row for row in heatmap.get("rows", [])}

    for tenant in tenants:
        tenant_code = tenant.tenant_code
        slo_eval = evaluate_assurance_slo(tenant.id, tenant_code, limit=limit)
        budget = slo_eval.get("breach_budget", {})
        heat = heatmap_by_code.get(tenant_code, {})

        rows.append(
            {
                "tenant_id": str(tenant.id),
                "tenant_code": tenant_code,
                "risk_tier": heat.get("risk_tier", "unknown"),
                "risk_score": heat.get("risk_score", 0),
                "slo_breach": bool(slo_eval.get("breach", False)),
                "breach_budget_remaining": int(budget.get("remaining", 0) or 0),
                "breach_budget_exhausted": bool(budget.get("exhausted", False)),
            }
        )

    rows.sort(key=lambda r: (not r["breach_budget_exhausted"], -int(r["risk_score"])))
    exhausted = len([r for r in rows if r["breach_budget_exhausted"]])

    return {
        "count": len(rows),
        "breach_budget_exhausted_count": exhausted,
        "rows": rows,
    }
