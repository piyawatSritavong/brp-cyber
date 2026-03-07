from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.services.control_plane_regulatory_profiles import regulatory_scorecard
from app.services.enterprise.objective_gate import list_objective_gate_history
from app.services.redis_client import redis_client

ASSURANCE_CONTRACT_KEY_PREFIX = "control_plane_assurance_contract"

DEFAULT_REQUIRED_GATES = ("red", "blue", "purple", "closed_loop", "enterprise", "compliance")


def _key(tenant_code: str) -> str:
    return f"{ASSURANCE_CONTRACT_KEY_PREFIX}:{tenant_code.lower().strip()}"


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip().lower() for v in value if str(v).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v).strip().lower() for v in parsed if str(v).strip()]
        except json.JSONDecodeError:
            return fallback
    return fallback


def _normalize_contract(payload: dict[str, Any]) -> dict[str, Any]:
    required_gates = _safe_list(payload.get("required_gates"), list(DEFAULT_REQUIRED_GATES))
    if not required_gates:
        required_gates = list(DEFAULT_REQUIRED_GATES)

    required_frameworks = _safe_list(payload.get("required_frameworks"), [])

    return {
        "contract_version": str(payload.get("contract_version", "1.0")),
        "owner": str(payload.get("owner", "security")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "min_samples": max(1, _to_int(payload.get("min_samples"), 20)),
        "min_overall_pass_rate": min(1.0, max(0.0, _to_float(payload.get("min_overall_pass_rate"), 0.95))),
        "min_gate_pass_rate": min(1.0, max(0.0, _to_float(payload.get("min_gate_pass_rate"), 0.95))),
        "max_enterprise_monthly_cost_usd": max(0.0, _to_float(payload.get("max_enterprise_monthly_cost_usd"), 50.0)),
        "required_gates": required_gates,
        "required_frameworks": required_frameworks,
        "min_framework_readiness_score": min(
            100.0, max(0.0, _to_float(payload.get("min_framework_readiness_score"), 90.0))
        ),
    }


def upsert_assurance_contract(tenant_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_contract(payload)
    redis_client.set(_key(tenant_code), json.dumps(normalized, ensure_ascii=True, sort_keys=True))
    return {"status": "upserted", "tenant_code": tenant_code, "contract": normalized}


def get_assurance_contract(tenant_code: str) -> dict[str, Any]:
    raw = redis_client.get(_key(tenant_code))
    if not raw:
        return {"status": "not_found", "tenant_code": tenant_code}

    try:
        contract = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "corrupted", "tenant_code": tenant_code}

    return {"status": "ok", "tenant_code": tenant_code, "contract": contract}


def evaluate_assurance_contract(tenant_id: UUID, tenant_code: str, limit: int = 100) -> dict[str, Any]:
    contract_resp = get_assurance_contract(tenant_code)
    if contract_resp.get("status") != "ok":
        return contract_resp

    contract = contract_resp["contract"]
    history = list_objective_gate_history(tenant_id, limit=max(1, limit))
    sample_count = len(history)

    overall_pass_count = 0
    gate_pass_counts = {gate: 0 for gate in contract.get("required_gates", [])}
    max_enterprise_cost = 0.0

    for row in history:
        if row.get("overall_pass", False):
            overall_pass_count += 1

        gates = row.get("gates", {})
        for gate in gate_pass_counts:
            if bool(gates.get(gate, {}).get("pass", False)):
                gate_pass_counts[gate] += 1

        enterprise_cost = _to_float(gates.get("enterprise", {}).get("monthly_cost_usd"), 0.0)
        if enterprise_cost > max_enterprise_cost:
            max_enterprise_cost = enterprise_cost

    overall_pass_rate = (overall_pass_count / sample_count) if sample_count else 0.0
    gate_pass_rates = {
        gate: ((count / sample_count) if sample_count else 0.0) for gate, count in gate_pass_counts.items()
    }

    frameworks = {}
    for framework in contract.get("required_frameworks", []):
        frameworks[framework] = regulatory_scorecard(framework)

    min_framework_score = _to_float(contract.get("min_framework_readiness_score"), 90.0)
    framework_failures = []
    for framework, score in frameworks.items():
        if score.get("status") != "ok":
            framework_failures.append({"framework": framework, "reason": "not_supported"})
            continue
        if _to_float(score.get("readiness_score"), 0.0) < min_framework_score:
            framework_failures.append(
                {
                    "framework": framework,
                    "reason": "readiness_below_threshold",
                    "readiness_score": _to_float(score.get("readiness_score"), 0.0),
                }
            )

    unmet: list[dict[str, Any]] = []
    if sample_count < _to_int(contract.get("min_samples"), 20):
        unmet.append(
            {
                "clause": "min_samples",
                "required": _to_int(contract.get("min_samples"), 20),
                "actual": sample_count,
            }
        )
    if overall_pass_rate < _to_float(contract.get("min_overall_pass_rate"), 0.95):
        unmet.append(
            {
                "clause": "min_overall_pass_rate",
                "required": _to_float(contract.get("min_overall_pass_rate"), 0.95),
                "actual": round(overall_pass_rate, 4),
            }
        )

    min_gate_pass_rate = _to_float(contract.get("min_gate_pass_rate"), 0.95)
    for gate, rate in gate_pass_rates.items():
        if rate < min_gate_pass_rate:
            unmet.append(
                {"clause": "min_gate_pass_rate", "gate": gate, "required": min_gate_pass_rate, "actual": round(rate, 4)}
            )

    max_cost = _to_float(contract.get("max_enterprise_monthly_cost_usd"), 50.0)
    if max_enterprise_cost > max_cost:
        unmet.append(
            {
                "clause": "max_enterprise_monthly_cost_usd",
                "required": max_cost,
                "actual": round(max_enterprise_cost, 6),
            }
        )

    for failure in framework_failures:
        unmet.append({"clause": "required_frameworks", **failure})

    return {
        "status": "ok",
        "tenant_id": str(tenant_id),
        "tenant_code": tenant_code,
        "contract": contract,
        "evaluation": {
            "sample_count": sample_count,
            "overall_pass_rate": round(overall_pass_rate, 4),
            "gate_pass_rates": {k: round(v, 4) for k, v in gate_pass_rates.items()},
            "max_enterprise_monthly_cost_usd_observed": round(max_enterprise_cost, 6),
            "required_frameworks": frameworks,
            "contract_pass": len(unmet) == 0,
            "unmet_clauses": unmet,
        },
    }
