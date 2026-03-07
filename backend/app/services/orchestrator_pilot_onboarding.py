from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.services.enterprise.objective_gate import evaluate_and_persist_objective_gate
from app.services.redis_client import redis_client

PILOT_ONBOARDING_PREFIX = "orchestrator_pilot_onboarding"


def _key(tenant_id: UUID) -> str:
    return f"{PILOT_ONBOARDING_PREFIX}:{tenant_id}"


def upsert_pilot_onboarding_profile(
    tenant_id: UUID,
    tenant_code: str,
    target_asset: str,
    strategy_profile: str = "balanced",
    red_scenario_name: str = "credential_stuffing_sim",
    cycle_interval_seconds: int = 300,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    redis_client.hset(
        _key(tenant_id),
        mapping={
            "tenant_id": str(tenant_id),
            "tenant_code": tenant_code.lower().strip(),
            "target_asset": target_asset,
            "strategy_profile": strategy_profile,
            "red_scenario_name": red_scenario_name,
            "cycle_interval_seconds": str(max(30, int(cycle_interval_seconds))),
            "updated_at": now,
        },
    )
    return get_pilot_onboarding_profile(tenant_id)


def get_pilot_onboarding_profile(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.hgetall(_key(tenant_id))
    if not raw:
        return {"status": "not_found", "tenant_id": str(tenant_id)}
    return {
        "status": "ok",
        "tenant_id": str(tenant_id),
        "tenant_code": raw.get("tenant_code", ""),
        "target_asset": raw.get("target_asset", ""),
        "strategy_profile": raw.get("strategy_profile", "balanced"),
        "red_scenario_name": raw.get("red_scenario_name", "credential_stuffing_sim"),
        "cycle_interval_seconds": int(raw.get("cycle_interval_seconds", "300") or 300),
        "updated_at": raw.get("updated_at", ""),
    }


def pilot_onboarding_checklist(tenant_id: UUID) -> dict[str, Any]:
    profile = get_pilot_onboarding_profile(tenant_id)
    gate = evaluate_and_persist_objective_gate(tenant_id=tenant_id)

    profile_ready = profile.get("status") == "ok" and bool(profile.get("target_asset", ""))
    gate_ready = bool(gate.get("overall_pass", False))
    failed_gates = [name for name, row in gate.get("gates", {}).items() if not row.get("pass", False)]

    checks = [
        {"name": "pilot_profile_configured", "pass": profile_ready},
        {"name": "objective_gate_pass", "pass": gate_ready},
    ]

    ready = all(row["pass"] for row in checks)
    return {
        "tenant_id": str(tenant_id),
        "ready": ready,
        "checks": checks,
        "failed_gates": failed_gates,
        "profile": profile,
    }
