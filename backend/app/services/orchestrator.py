from __future__ import annotations

import hmac
import json
from hashlib import sha256
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.core.config import settings
from app.services.enterprise import cost_meter as _cost_meter
from app.services.enterprise import quotas as _quotas
from app.services.control_plane_orchestration_cost_guardrail import (
    evaluate_orchestration_cost_guardrail,
    get_orchestration_cost_throttle_override_mode,
)
from app.services.enterprise.cost_meter import record_cost
from app.services.enterprise.model_router import route_model
from app.services.enterprise.objective_gate import evaluate_and_persist_objective_gate
from app.services.enterprise.quotas import add_usage, check_quota
from app.services.control_plane_notarization import notarize_payload
from app.services.notifier import send_telegram_message
from app.services.policy_store import (
    get_blue_policy,
    get_pending_action,
    get_strategy_profile,
    is_approval_mode_enabled,
    list_pending_actions,
    save_pending_action,
    set_approval_mode,
    set_blue_policy,
    set_strategy_profile,
)
from app.services.purple_core import generate_daily_report
from app.services.red_simulator import run_simulation
from app.services.redis_client import redis_client
from schemas.orchestration import OrchestrationCycleRequest, OrchestrationMultiCycleRequest
from schemas.red_sim import RedSimulationRunRequest

STRATEGY_PRESETS = {
    "conservative": {
        "priority": 1,
        "blue": {"failed_login_threshold_per_minute": 5, "failure_window_seconds": 60, "incident_cooldown_seconds": 180},
        "red_events_count": 20,
    },
    "balanced": {
        "priority": 2,
        "blue": {"failed_login_threshold_per_minute": 10, "failure_window_seconds": 60, "incident_cooldown_seconds": 120},
        "red_events_count": 30,
    },
    "aggressive": {
        "priority": 3,
        "blue": {"failed_login_threshold_per_minute": 15, "failure_window_seconds": 45, "incident_cooldown_seconds": 60},
        "red_events_count": 50,
    },
}

ORCHESTRATION_ACTIVATION_PREFIX = "orchestration_activation"
ORCHESTRATION_PILOT_SESSION_PREFIX = "orchestration_pilot_session"
ORCHESTRATION_SAFETY_POLICY_PREFIX = "orchestration_safety_policy"
ORCHESTRATION_INCIDENT_STREAM_PREFIX = "orchestration_incidents"
ORCHESTRATION_RATE_BUDGET_PREFIX = "orchestration_rate_budget"
ORCHESTRATION_RATE_USAGE_PREFIX = "orchestration_rate_usage"
ORCHESTRATION_SCHEDULER_PROFILE_PREFIX = "orchestration_scheduler_profile"
ORCHESTRATION_ROLLOUT_PROFILE_PREFIX = "orchestration_rollout_profile"
ORCHESTRATION_ROLLOUT_DECISION_STREAM_PREFIX = "orchestration_rollout_decisions"
ORCHESTRATION_ROLLOUT_GUARD_PREFIX = "orchestration_rollout_guard"
ORCHESTRATION_ROLLOUT_POLICY_PREFIX = "orchestration_rollout_policy"
ORCHESTRATION_ROLLOUT_PENDING_PREFIX = "orchestration_rollout_pending"
ORCHESTRATION_ROLLOUT_EVIDENCE_STREAM_PREFIX = "orchestration_rollout_evidence"
ORCHESTRATION_ROLLOUT_EVIDENCE_STATE_PREFIX = "orchestration_rollout_evidence:last_signature"
ORCHESTRATION_ROLLOUT_EVIDENCE_BUNDLE_PREFIX = "orchestration_rollout_evidence_bundle"

PRIORITY_TIERS = {"low": 1, "normal": 2, "high": 3, "critical": 4}
ROLLOUT_STAGES = {"alpha", "beta", "ga"}

def _preset(name: str) -> dict[str, Any]:
    return STRATEGY_PRESETS.get(name, STRATEGY_PRESETS["balanced"])


def _priority(strategy_profile: str) -> int:
    return int(_preset(strategy_profile).get("priority", 2))


def _kpi_trend_stream_key(tenant_id: UUID) -> str:
    return f"orchestrator_kpi_trend:{tenant_id}"


def _cycle_stream_key(tenant_id: UUID) -> str:
    return f"orchestrator_cycles:{tenant_id}"


def _cooldown_key(tenant_id: UUID, action_name: str) -> str:
    return f"orchestrator_cooldown:{tenant_id}:{action_name}"


def _activation_key(tenant_id: UUID) -> str:
    return f"{ORCHESTRATION_ACTIVATION_PREFIX}:{tenant_id}"


def _pilot_key(tenant_id: UUID) -> str:
    return f"{ORCHESTRATION_PILOT_SESSION_PREFIX}:{tenant_id}"


def _safety_policy_key(tenant_id: UUID) -> str:
    return f"{ORCHESTRATION_SAFETY_POLICY_PREFIX}:{tenant_id}"


def _incident_stream_key(tenant_id: UUID) -> str:
    return f"{ORCHESTRATION_INCIDENT_STREAM_PREFIX}:{tenant_id}"


def _rate_budget_key(tenant_id: UUID) -> str:
    return f"{ORCHESTRATION_RATE_BUDGET_PREFIX}:{tenant_id}"


def _rate_usage_key(tenant_id: UUID, hour_bucket_epoch: int) -> str:
    return f"{ORCHESTRATION_RATE_USAGE_PREFIX}:{tenant_id}:{hour_bucket_epoch}"


def _scheduler_profile_key(tenant_id: UUID) -> str:
    return f"{ORCHESTRATION_SCHEDULER_PROFILE_PREFIX}:{tenant_id}"


def _rollout_profile_key(tenant_id: UUID) -> str:
    return f"{ORCHESTRATION_ROLLOUT_PROFILE_PREFIX}:{tenant_id}"


def _rollout_decision_stream_key(tenant_id: UUID) -> str:
    return f"{ORCHESTRATION_ROLLOUT_DECISION_STREAM_PREFIX}:{tenant_id}"


def _rollout_guard_key(tenant_id: UUID) -> str:
    return f"{ORCHESTRATION_ROLLOUT_GUARD_PREFIX}:{tenant_id}"


def _rollout_policy_key(tenant_id: UUID) -> str:
    return f"{ORCHESTRATION_ROLLOUT_POLICY_PREFIX}:{tenant_id}"


def _rollout_pending_key(tenant_id: UUID, decision_id: str) -> str:
    return f"{ORCHESTRATION_ROLLOUT_PENDING_PREFIX}:{tenant_id}:{decision_id}"


def _rollout_evidence_stream_key(tenant_id: UUID) -> str:
    return f"{ORCHESTRATION_ROLLOUT_EVIDENCE_STREAM_PREFIX}:{tenant_id}"


def _rollout_evidence_state_key(tenant_id: UUID) -> str:
    return f"{ORCHESTRATION_ROLLOUT_EVIDENCE_STATE_PREFIX}:{tenant_id}"


def _rollout_evidence_bundle_stream_key(tenant_id: UUID) -> str:
    return f"{ORCHESTRATION_ROLLOUT_EVIDENCE_BUNDLE_PREFIX}:{tenant_id}"


def _now_epoch() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _hour_bucket(epoch: int) -> int:
    return int(epoch // 3600) * 3600


def _normalize_safety_policy(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    row = raw or {}
    max_failures = int(row.get("max_consecutive_failures", 3) or 3)
    return {
        "max_consecutive_failures": max(1, min(20, max_failures)),
        "auto_stop_on_consecutive_failures": str(row.get("auto_stop_on_consecutive_failures", "1")) in {"1", "true", "True"},
        "objective_gate_check_each_tick": str(row.get("objective_gate_check_each_tick", "0")) in {"1", "true", "True"},
        "auto_stop_on_objective_gate_fail": str(row.get("auto_stop_on_objective_gate_fail", "0")) in {"1", "true", "True"},
        "notify_on_auto_stop": str(row.get("notify_on_auto_stop", "1")) in {"1", "true", "True"},
    }


def _normalize_rate_budget(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    row = raw or {}
    return {
        "max_cycles_per_hour": max(1, min(5000, int(row.get("max_cycles_per_hour", 120) or 120))),
        "max_red_events_per_hour": max(1, min(500000, int(row.get("max_red_events_per_hour", 10000) or 10000))),
        "enforce_rate_budget": str(row.get("enforce_rate_budget", "1")) in {"1", "true", "True"},
        "auto_pause_on_budget_exceeded": str(row.get("auto_pause_on_budget_exceeded", "1")) in {"1", "true", "True"},
        "notify_on_budget_exceeded": str(row.get("notify_on_budget_exceeded", "1")) in {"1", "true", "True"},
    }


def _normalize_scheduler_profile(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    row = raw or {}
    tier = str(row.get("priority_tier", "normal")).strip().lower()
    if tier not in PRIORITY_TIERS:
        tier = "normal"
    threshold = int(row.get("starvation_incident_threshold", 3) or 3)
    return {
        "priority_tier": tier,
        "starvation_incident_threshold": max(1, min(20, threshold)),
        "notify_on_starvation": str(row.get("notify_on_starvation", "0")) in {"1", "true", "True"},
    }


def _normalize_rollout_profile(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    row = raw or {}
    stage = str(row.get("rollout_stage", "ga")).strip().lower()
    if stage not in ROLLOUT_STAGES:
        stage = "ga"
    percent = int(row.get("canary_percent", 100) or 100)
    return {
        "rollout_stage": stage,
        "canary_percent": max(1, min(100, percent)),
        "hold": str(row.get("hold", "0")) in {"1", "true", "True"},
        "notify_on_hold": str(row.get("notify_on_hold", "0")) in {"1", "true", "True"},
    }


def _normalize_rollout_policy(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    row = raw or {}
    return {
        "auto_promote_enabled": str(row.get("auto_promote_enabled", "1")) in {"1", "true", "True"},
        "auto_demote_enabled": str(row.get("auto_demote_enabled", "1")) in {"1", "true", "True"},
        "require_approval_for_promote": str(row.get("require_approval_for_promote", "0")) in {"1", "true", "True"},
        "require_approval_for_demote": str(row.get("require_approval_for_demote", "1")) in {"1", "true", "True"},
        "require_dual_control_for_promote": str(row.get("require_dual_control_for_promote", "0")) in {"1", "true", "True"},
        "require_dual_control_for_demote": str(row.get("require_dual_control_for_demote", "0")) in {"1", "true", "True"},
    }


def _build_activation_row(tenant_id: UUID, raw: dict[str, str]) -> dict[str, Any]:
    return {
        "tenant_id": str(tenant_id),
        "status": raw.get("status", "inactive"),
        "target_asset": raw.get("target_asset", ""),
        "red_scenario_name": raw.get("red_scenario_name", "credential_stuffing_sim"),
        "red_events_count": int(raw.get("red_events_count", "30") or 30),
        "strategy_profile": raw.get("strategy_profile", "balanced"),
        "cycle_interval_seconds": int(raw.get("cycle_interval_seconds", "300") or 300),
        "run_count": int(raw.get("run_count", "0") or 0),
        "last_cycle_index": int(raw.get("last_cycle_index", "0") or 0),
        "consecutive_failures": int(raw.get("consecutive_failures", "0") or 0),
        "scheduler_skip_streak": int(raw.get("scheduler_skip_streak", "0") or 0),
        "last_run_at": raw.get("last_run_at", ""),
        "next_run_at": raw.get("next_run_at", ""),
        "next_run_epoch": int(raw.get("next_run_epoch", "0") or 0),
        "last_status": raw.get("last_status", ""),
        "last_error": raw.get("last_error", ""),
        "updated_at": raw.get("updated_at", ""),
    }


def _sync_enterprise_clients() -> None:
    _quotas.redis_client = redis_client
    _cost_meter.redis_client = redis_client


def _store_cycle_result(tenant_id: UUID, payload: dict[str, Any]) -> None:
    redis_client.xadd(
        _cycle_stream_key(tenant_id),
        {"payload": str(payload)},
        maxlen=10000,
        approximate=True,
    )


def _record_kpi_trend(tenant_id: UUID, cycle_index: int, kpi: dict[str, Any], improved: bool) -> None:
    redis_client.xadd(
        _kpi_trend_stream_key(tenant_id),
        {
            "cycle_index": str(cycle_index),
            "detection_coverage": str(kpi.get("detection_coverage", 0.0)),
            "mttd_seconds": str(kpi.get("mttd_seconds", 0.0)),
            "mttr_seconds": str(kpi.get("mttr_seconds", 0.0)),
            "improved": "1" if improved else "0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        maxlen=20000,
        approximate=True,
    )


def get_kpi_trend(tenant_id: UUID, limit: int = 100) -> list[dict[str, str]]:
    entries = redis_client.xrevrange(_kpi_trend_stream_key(tenant_id), count=max(1, limit))
    trends: list[dict[str, str]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        trends.append(row)
    return trends


def apply_strategy_profile(tenant_id: UUID, strategy_profile: str) -> dict[str, Any]:
    preset = _preset(strategy_profile)
    set_strategy_profile(tenant_id, strategy_profile)
    blue = preset["blue"]
    policy = set_blue_policy(
        tenant_id,
        failed_login_threshold_per_minute=blue["failed_login_threshold_per_minute"],
        failure_window_seconds=blue["failure_window_seconds"],
        incident_cooldown_seconds=blue["incident_cooldown_seconds"],
    )
    return {"tenant_id": str(tenant_id), "strategy_profile": strategy_profile, "blue_policy": policy}


def set_tenant_approval_mode(tenant_id: UUID, enabled: bool) -> dict[str, Any]:
    set_approval_mode(tenant_id, enabled)
    return {"tenant_id": str(tenant_id), "approval_mode": enabled}


def get_tenant_orchestration_state(tenant_id: UUID) -> dict[str, Any]:
    return {
        "tenant_id": str(tenant_id),
        "strategy_profile": get_strategy_profile(tenant_id),
        "blue_policy": get_blue_policy(tenant_id),
        "approval_mode": is_approval_mode_enabled(tenant_id),
        "pending_actions": list_pending_actions(tenant_id, limit=50),
    }


def _build_blue_policy_change(tenant_id: UUID, report: dict[str, Any], strategy_profile: str) -> dict[str, Any]:
    current_policy = get_blue_policy(tenant_id)
    kpi = report["kpi"]
    threshold = current_policy["failed_login_threshold_per_minute"]

    if kpi["detection_coverage"] < 0.9:
        threshold = max(1, threshold - 1)
    elif kpi["detection_coverage"] >= 0.99 and kpi["mttr_seconds"] <= 60:
        threshold = min(1000, threshold + 1)

    action_id = str(uuid4())
    return {
        "action_id": action_id,
        "action_name": "blue_policy_threshold_adjust",
        "priority": _priority(strategy_profile),
        "tenant_id": str(tenant_id),
        "status": "proposed",
        "proposed_threshold": str(threshold),
        "current_threshold": str(current_policy["failed_login_threshold_per_minute"]),
        "failure_window_seconds": str(current_policy["failure_window_seconds"]),
        "incident_cooldown_seconds": str(current_policy["incident_cooldown_seconds"]),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _resolve_conflict_and_apply(tenant_id: UUID, proposed_change: dict[str, Any]) -> dict[str, Any]:
    cooldown_key = _cooldown_key(tenant_id, proposed_change["action_name"])
    if redis_client.exists(cooldown_key):
        return {"status": "suppressed", "reason": "cooldown", "action": proposed_change}

    pending = list_pending_actions(tenant_id, limit=100)
    proposed_priority = int(proposed_change["priority"])
    for action in pending:
        if action.get("status") != "pending_approval":
            continue
        if action.get("action_name") != proposed_change["action_name"]:
            continue
        pending_priority = int(action.get("priority", "0"))
        if pending_priority > proposed_priority:
            return {
                "status": "suppressed",
                "reason": "lower_priority_than_pending",
                "pending_action_id": action.get("action_id"),
                "action": proposed_change,
            }

    if is_approval_mode_enabled(tenant_id):
        proposed_change["status"] = "pending_approval"
        save_pending_action(tenant_id, proposed_change["action_id"], {k: str(v) for k, v in proposed_change.items()})
        return {"status": "pending_approval", "action": proposed_change}

    applied_policy = set_blue_policy(
        tenant_id,
        failed_login_threshold_per_minute=int(proposed_change["proposed_threshold"]),
        failure_window_seconds=int(proposed_change["failure_window_seconds"]),
        incident_cooldown_seconds=int(proposed_change["incident_cooldown_seconds"]),
    )
    redis_client.set(cooldown_key, "1", ex=settings.orchestrator_conflict_cooldown_seconds)
    proposed_change["status"] = "applied"
    save_pending_action(tenant_id, proposed_change["action_id"], {k: str(v) for k, v in proposed_change.items()})
    return {"status": "applied", "action": proposed_change, "blue_policy": applied_policy}


def approve_pending_action(tenant_id: UUID, action_id: str, approve: bool) -> dict[str, Any]:
    action = get_pending_action(tenant_id, action_id)
    if not action:
        return {"status": "not_found", "action_id": action_id}

    if action.get("status") != "pending_approval":
        return {"status": "invalid_state", "action_id": action_id, "current_status": action.get("status")}

    if not approve:
        action["status"] = "rejected"
        action["resolved_at"] = datetime.now(timezone.utc).isoformat()
        save_pending_action(tenant_id, action_id, action)
        return {"status": "rejected", "action": action}

    applied_policy = set_blue_policy(
        tenant_id,
        failed_login_threshold_per_minute=int(action["proposed_threshold"]),
        failure_window_seconds=int(action["failure_window_seconds"]),
        incident_cooldown_seconds=int(action["incident_cooldown_seconds"]),
    )
    action["status"] = "applied"
    action["resolved_at"] = datetime.now(timezone.utc).isoformat()
    save_pending_action(tenant_id, action_id, action)
    redis_client.set(
        _cooldown_key(tenant_id, action["action_name"]),
        "1",
        ex=settings.orchestrator_conflict_cooldown_seconds,
    )
    return {"status": "applied", "action": action, "blue_policy": applied_policy}


def run_orchestration_cycle(request: OrchestrationCycleRequest, cycle_index: int = 1) -> dict[str, Any]:
    _sync_enterprise_clients()
    apply_strategy_profile(request.tenant_id, request.strategy_profile)
    try:
        cost_guardrail_eval = evaluate_orchestration_cost_guardrail(
            request.tenant_id,
            tenant_code=str(request.tenant_id),
            apply_actions=True,
        )
    except Exception as exc:
        cost_guardrail_eval = {
            "status": "evaluation_error",
            "state": {"severity": "unknown"},
            "metrics": {},
            "actions": [],
            "error": str(exc),
        }
    try:
        throttle_mode = get_orchestration_cost_throttle_override_mode(request.tenant_id)
    except Exception:
        throttle_mode = ""

    effective_red_events_count = max(1, int(request.red_events_count))
    if throttle_mode == "strict":
        effective_red_events_count = max(1, effective_red_events_count // 4)
    elif throttle_mode == "conservative":
        effective_red_events_count = max(1, effective_red_events_count // 2)

    quota_state = check_quota(
        request.tenant_id,
        events=effective_red_events_count,
        actions=1,
        tokens=effective_red_events_count * 40,
    )
    if not quota_state["allowed"]:
        return {
            "tenant_id": str(request.tenant_id),
            "cycle_index": cycle_index,
            "status": "blocked_by_quota",
            "quota_state": quota_state,
            "throttle": {
                "mode": throttle_mode,
                "requested_red_events_count": request.red_events_count,
                "effective_red_events_count": effective_red_events_count,
            },
            "cost_guardrail": {
                "state": cost_guardrail_eval.get("state", {}),
                "metrics": cost_guardrail_eval.get("metrics", {}),
                "actions": cost_guardrail_eval.get("actions", []),
            },
        }

    red_model = route_model(
        request.tenant_id,
        task_type="red_simulation",
        complexity="medium",
        estimated_tokens=effective_red_events_count * 20,
    )
    red_request = RedSimulationRunRequest(
        tenant_id=request.tenant_id,
        scenario_name=request.red_scenario_name,
        target_asset=request.target_asset,
        events_count=effective_red_events_count,
    )
    red_result = run_simulation(red_request)
    red_cost = record_cost(request.tenant_id, red_model.estimated_tokens, red_model.selected_model)

    purple_model = route_model(
        request.tenant_id,
        task_type="purple_report",
        complexity="high",
        estimated_tokens=1800,
    )
    report = generate_daily_report(request.tenant_id, limit=5000)
    purple_cost = record_cost(request.tenant_id, purple_model.estimated_tokens, purple_model.selected_model)
    proposed_change = _build_blue_policy_change(request.tenant_id, report, request.strategy_profile)
    feedback_result = _resolve_conflict_and_apply(request.tenant_id, proposed_change)
    usage_after = add_usage(
        request.tenant_id,
        events=effective_red_events_count,
        actions=1,
        tokens=red_model.estimated_tokens + purple_model.estimated_tokens,
    )

    result = {
        "tenant_id": str(request.tenant_id),
        "cycle_index": cycle_index,
        "strategy_profile": request.strategy_profile,
        "throttle": {
            "mode": throttle_mode,
            "requested_red_events_count": request.red_events_count,
            "effective_red_events_count": effective_red_events_count,
        },
        "red_result": red_result,
        "purple_report": {
            "report_id": report["report_id"],
            "summary": report["summary"],
            "kpi": report["kpi"],
        },
        "model_routing": {
            "red": red_model.as_dict(),
            "purple": purple_model.as_dict(),
        },
        "cost_snapshot": {
            "red_cost": red_cost,
            "purple_cost": purple_cost,
        },
        "cost_guardrail": {
            "state": cost_guardrail_eval.get("state", {}),
            "metrics": cost_guardrail_eval.get("metrics", {}),
            "actions": cost_guardrail_eval.get("actions", []),
        },
        "usage_after_cycle": usage_after,
        "feedback_result": feedback_result,
    }
    _store_cycle_result(request.tenant_id, result)
    return result


def run_multi_cycle(request: OrchestrationMultiCycleRequest) -> dict[str, Any]:
    previous_coverage: float | None = None
    cycles_output: list[dict[str, Any]] = []
    improvement_streak = 0

    for cycle_index in range(1, request.cycles + 1):
        cycle_req = OrchestrationCycleRequest(
            tenant_id=request.tenant_id,
            target_asset=request.target_asset,
            red_scenario_name=request.red_scenario_name,
            red_events_count=request.red_events_count,
            strategy_profile=request.strategy_profile,
        )
        result = run_orchestration_cycle(cycle_req, cycle_index=cycle_index)
        coverage = float(result["purple_report"]["kpi"].get("detection_coverage", 0.0))

        improved = previous_coverage is None or coverage >= previous_coverage
        _record_kpi_trend(request.tenant_id, cycle_index, result["purple_report"]["kpi"], improved)
        cycles_output.append(result)

        if improved:
            improvement_streak += 1
        else:
            improvement_streak = 0
            if request.stop_on_no_improvement:
                break

        previous_coverage = coverage

    return {
        "tenant_id": str(request.tenant_id),
        "requested_cycles": request.cycles,
        "executed_cycles": len(cycles_output),
        "improvement_streak": improvement_streak,
        "cycles": cycles_output,
    }


def activate_tenant_orchestration(
    tenant_id: UUID,
    target_asset: str,
    red_scenario_name: str = "credential_stuffing_sim",
    red_events_count: int = 30,
    strategy_profile: str = "balanced",
    cycle_interval_seconds: int = 300,
    approval_mode: bool = False,
) -> dict[str, Any]:
    interval = max(30, int(cycle_interval_seconds))
    now_epoch = _now_epoch()
    now_iso = datetime.now(timezone.utc).isoformat()
    set_tenant_approval_mode(tenant_id, approval_mode)
    apply_strategy_profile(tenant_id, strategy_profile)

    redis_client.hset(
        _activation_key(tenant_id),
        mapping={
            "status": "active",
            "target_asset": target_asset,
            "red_scenario_name": red_scenario_name,
            "red_events_count": str(max(1, red_events_count)),
            "strategy_profile": strategy_profile,
            "cycle_interval_seconds": str(interval),
            "run_count": "0",
            "last_cycle_index": "0",
            "consecutive_failures": "0",
            "scheduler_skip_streak": "0",
            "last_run_at": "",
            "next_run_at": now_iso,
            "next_run_epoch": str(now_epoch),
            "last_status": "activated",
            "last_error": "",
            "updated_at": now_iso,
        },
    )
    return get_tenant_activation_state(tenant_id)


def pause_tenant_orchestration(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.hgetall(_activation_key(tenant_id))
    if not raw:
        return {"tenant_id": str(tenant_id), "status": "not_found"}
    now_iso = datetime.now(timezone.utc).isoformat()
    redis_client.hset(
        _activation_key(tenant_id),
        mapping={"status": "paused", "updated_at": now_iso, "last_status": "paused"},
    )
    return get_tenant_activation_state(tenant_id)


def deactivate_tenant_orchestration(tenant_id: UUID) -> dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    redis_client.hset(
        _activation_key(tenant_id),
        mapping={
            "status": "inactive",
            "next_run_epoch": "0",
            "next_run_at": "",
            "updated_at": now_iso,
            "last_status": "deactivated",
        },
    )
    return get_tenant_activation_state(tenant_id)


def get_tenant_activation_state(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.hgetall(_activation_key(tenant_id))
    if not raw:
        return {"tenant_id": str(tenant_id), "status": "inactive"}
    return _build_activation_row(tenant_id, raw)


def list_activation_states(limit: int = 200) -> dict[str, Any]:
    keys = redis_client.keys(f"{ORCHESTRATION_ACTIVATION_PREFIX}:*")
    rows: list[dict[str, Any]] = []
    for key in keys[: max(1, limit)]:
        tenant_text = key.split(":", 1)[-1]
        try:
            tenant_id = UUID(tenant_text)
        except ValueError:
            continue
        rows.append(get_tenant_activation_state(tenant_id))
    active = len([row for row in rows if row.get("status") == "active"])
    return {"count": len(rows), "active": active, "inactive_or_paused": len(rows) - active, "rows": rows}


def upsert_tenant_safety_policy(
    tenant_id: UUID,
    *,
    max_consecutive_failures: int = 3,
    auto_stop_on_consecutive_failures: bool = True,
    objective_gate_check_each_tick: bool = False,
    auto_stop_on_objective_gate_fail: bool = False,
    notify_on_auto_stop: bool = True,
) -> dict[str, Any]:
    normalized = _normalize_safety_policy(
        {
            "max_consecutive_failures": max_consecutive_failures,
            "auto_stop_on_consecutive_failures": auto_stop_on_consecutive_failures,
            "objective_gate_check_each_tick": objective_gate_check_each_tick,
            "auto_stop_on_objective_gate_fail": auto_stop_on_objective_gate_fail,
            "notify_on_auto_stop": notify_on_auto_stop,
        }
    )
    redis_client.hset(
        _safety_policy_key(tenant_id),
        mapping={
            "max_consecutive_failures": str(normalized["max_consecutive_failures"]),
            "auto_stop_on_consecutive_failures": "1" if normalized["auto_stop_on_consecutive_failures"] else "0",
            "objective_gate_check_each_tick": "1" if normalized["objective_gate_check_each_tick"] else "0",
            "auto_stop_on_objective_gate_fail": "1" if normalized["auto_stop_on_objective_gate_fail"] else "0",
            "notify_on_auto_stop": "1" if normalized["notify_on_auto_stop"] else "0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"tenant_id": str(tenant_id), "policy": normalized}


def get_tenant_safety_policy(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.hgetall(_safety_policy_key(tenant_id))
    return {"tenant_id": str(tenant_id), "policy": _normalize_safety_policy(raw if raw else None)}


def upsert_tenant_rate_budget(
    tenant_id: UUID,
    *,
    max_cycles_per_hour: int = 120,
    max_red_events_per_hour: int = 10000,
    enforce_rate_budget: bool = True,
    auto_pause_on_budget_exceeded: bool = True,
    notify_on_budget_exceeded: bool = True,
) -> dict[str, Any]:
    normalized = _normalize_rate_budget(
        {
            "max_cycles_per_hour": max_cycles_per_hour,
            "max_red_events_per_hour": max_red_events_per_hour,
            "enforce_rate_budget": enforce_rate_budget,
            "auto_pause_on_budget_exceeded": auto_pause_on_budget_exceeded,
            "notify_on_budget_exceeded": notify_on_budget_exceeded,
        }
    )
    redis_client.hset(
        _rate_budget_key(tenant_id),
        mapping={
            "max_cycles_per_hour": str(normalized["max_cycles_per_hour"]),
            "max_red_events_per_hour": str(normalized["max_red_events_per_hour"]),
            "enforce_rate_budget": "1" if normalized["enforce_rate_budget"] else "0",
            "auto_pause_on_budget_exceeded": "1" if normalized["auto_pause_on_budget_exceeded"] else "0",
            "notify_on_budget_exceeded": "1" if normalized["notify_on_budget_exceeded"] else "0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"tenant_id": str(tenant_id), "budget": normalized}


def get_tenant_rate_budget(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.hgetall(_rate_budget_key(tenant_id))
    return {"tenant_id": str(tenant_id), "budget": _normalize_rate_budget(raw if raw else None)}


def get_tenant_rate_budget_usage(tenant_id: UUID, hour_epoch: int | None = None) -> dict[str, Any]:
    current = _hour_bucket(hour_epoch if hour_epoch is not None else _now_epoch())
    raw = redis_client.hgetall(_rate_usage_key(tenant_id, current))
    return {
        "tenant_id": str(tenant_id),
        "hour_bucket_epoch": current,
        "cycles_used": int(raw.get("cycles_used", "0") or 0),
        "red_events_used": int(raw.get("red_events_used", "0") or 0),
        "updated_at": raw.get("updated_at", ""),
    }


def upsert_tenant_scheduler_profile(
    tenant_id: UUID,
    *,
    priority_tier: str = "normal",
    starvation_incident_threshold: int = 3,
    notify_on_starvation: bool = False,
) -> dict[str, Any]:
    normalized = _normalize_scheduler_profile(
        {
            "priority_tier": priority_tier,
            "starvation_incident_threshold": starvation_incident_threshold,
            "notify_on_starvation": notify_on_starvation,
        }
    )
    redis_client.hset(
        _scheduler_profile_key(tenant_id),
        mapping={
            "priority_tier": normalized["priority_tier"],
            "starvation_incident_threshold": str(normalized["starvation_incident_threshold"]),
            "notify_on_starvation": "1" if normalized["notify_on_starvation"] else "0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"tenant_id": str(tenant_id), "profile": normalized}


def get_tenant_scheduler_profile(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.hgetall(_scheduler_profile_key(tenant_id))
    return {"tenant_id": str(tenant_id), "profile": _normalize_scheduler_profile(raw if raw else None)}


def upsert_tenant_rollout_profile(
    tenant_id: UUID,
    *,
    rollout_stage: str = "ga",
    canary_percent: int = 100,
    hold: bool = False,
    notify_on_hold: bool = False,
) -> dict[str, Any]:
    normalized = _normalize_rollout_profile(
        {
            "rollout_stage": rollout_stage,
            "canary_percent": canary_percent,
            "hold": hold,
            "notify_on_hold": notify_on_hold,
        }
    )
    redis_client.hset(
        _rollout_profile_key(tenant_id),
        mapping={
            "rollout_stage": normalized["rollout_stage"],
            "canary_percent": str(normalized["canary_percent"]),
            "hold": "1" if normalized["hold"] else "0",
            "notify_on_hold": "1" if normalized["notify_on_hold"] else "0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"tenant_id": str(tenant_id), "profile": normalized}


def get_tenant_rollout_profile(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.hgetall(_rollout_profile_key(tenant_id))
    return {"tenant_id": str(tenant_id), "profile": _normalize_rollout_profile(raw if raw else None)}


def upsert_tenant_rollout_policy(
    tenant_id: UUID,
    *,
    auto_promote_enabled: bool = True,
    auto_demote_enabled: bool = True,
    require_approval_for_promote: bool = False,
    require_approval_for_demote: bool = True,
    require_dual_control_for_promote: bool = False,
    require_dual_control_for_demote: bool = False,
) -> dict[str, Any]:
    normalized = _normalize_rollout_policy(
        {
            "auto_promote_enabled": auto_promote_enabled,
            "auto_demote_enabled": auto_demote_enabled,
            "require_approval_for_promote": require_approval_for_promote,
            "require_approval_for_demote": require_approval_for_demote,
            "require_dual_control_for_promote": require_dual_control_for_promote,
            "require_dual_control_for_demote": require_dual_control_for_demote,
        }
    )
    redis_client.hset(
        _rollout_policy_key(tenant_id),
        mapping={
            "auto_promote_enabled": "1" if normalized["auto_promote_enabled"] else "0",
            "auto_demote_enabled": "1" if normalized["auto_demote_enabled"] else "0",
            "require_approval_for_promote": "1" if normalized["require_approval_for_promote"] else "0",
            "require_approval_for_demote": "1" if normalized["require_approval_for_demote"] else "0",
            "require_dual_control_for_promote": "1" if normalized["require_dual_control_for_promote"] else "0",
            "require_dual_control_for_demote": "1" if normalized["require_dual_control_for_demote"] else "0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return {"tenant_id": str(tenant_id), "policy": normalized}


def get_tenant_rollout_policy(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.hgetall(_rollout_policy_key(tenant_id))
    return {"tenant_id": str(tenant_id), "policy": _normalize_rollout_policy(raw if raw else None)}


def list_pending_rollout_decisions(tenant_id: UUID, limit: int = 100) -> dict[str, Any]:
    keys = redis_client.keys(f"{ORCHESTRATION_ROLLOUT_PENDING_PREFIX}:{tenant_id}:*")
    rows: list[dict[str, str]] = []
    for key in keys[: max(1, limit)]:
        row = redis_client.hgetall(key)
        if not row:
            continue
        row["decision_id"] = key.split(":")[-1]
        rows.append(row)
    rows = sorted(rows, key=lambda item: item.get("created_at", ""), reverse=True)
    return {"tenant_id": str(tenant_id), "count": len(rows), "rows": rows}


def _find_pending_rollout_decision(tenant_id: UUID, action: str) -> dict[str, str] | None:
    pending = list_pending_rollout_decisions(tenant_id, limit=200).get("rows", [])
    for row in pending:
        if row.get("status") == "pending_approval" and row.get("action") == action:
            return row
    return None


def _create_pending_rollout_decision(tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    decision_id = str(uuid4())
    mapping = {k: str(v) for k, v in payload.items()}
    mapping["approvals_required"] = str(int(mapping.get("approvals_required", "1") or 1))
    mapping["approvals_received"] = "0"
    mapping["approvers"] = ""
    mapping["status"] = "pending_approval"
    mapping["created_at"] = datetime.now(timezone.utc).isoformat()
    redis_client.hset(_rollout_pending_key(tenant_id, decision_id), mapping=mapping)
    output = dict(mapping)
    output["decision_id"] = decision_id
    return output


def _sign_rollout_evidence(payload: dict[str, Any]) -> str:
    key = str(getattr(settings, "orchestrator_rollout_evidence_hmac_key", "change-me-rollout-evidence-hmac-key")).encode("utf-8")
    normalized = {str(k): str(v) for k, v in payload.items()}
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hmac.new(key, canonical, "sha256").hexdigest()


def _append_rollout_evidence(tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    signed = dict(payload)
    signed["tenant_id"] = str(tenant_id)
    signed["timestamp"] = datetime.now(timezone.utc).isoformat()
    signed["prev_signature"] = redis_client.get(_rollout_evidence_state_key(tenant_id)) or ""
    signed["signature"] = _sign_rollout_evidence(signed)
    event_id = redis_client.xadd(
        _rollout_evidence_stream_key(tenant_id),
        {k: str(v) for k, v in signed.items()},
        maxlen=5000,
        approximate=True,
    )
    redis_client.set(_rollout_evidence_state_key(tenant_id), signed["signature"])
    signed["id"] = event_id
    return signed


def rollout_evidence_history(tenant_id: UUID, limit: int = 100) -> dict[str, Any]:
    events = redis_client.xrevrange(_rollout_evidence_stream_key(tenant_id), count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in events:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"tenant_id": str(tenant_id), "count": len(rows), "rows": rows}


def verify_rollout_evidence_chain(tenant_id: UUID, limit: int = 1000) -> dict[str, Any]:
    entries = redis_client.xrange(_rollout_evidence_stream_key(tenant_id), count=max(1, limit))
    prev_signature = ""
    checked = 0
    for idx, (_, fields) in enumerate(entries):
        row = dict(fields)
        sig = str(row.pop("signature", ""))
        if not sig:
            return {"tenant_id": str(tenant_id), "valid": False, "index": idx, "reason": "missing_signature"}
        if str(row.get("tenant_id", "")) != str(tenant_id):
            return {"tenant_id": str(tenant_id), "valid": False, "index": idx, "reason": "tenant_mismatch"}
        if str(row.get("prev_signature", "")) != prev_signature:
            return {"tenant_id": str(tenant_id), "valid": False, "index": idx, "reason": "prev_signature_mismatch"}
        expected = _sign_rollout_evidence(row)
        if not hmac.compare_digest(sig, expected):
            return {"tenant_id": str(tenant_id), "valid": False, "index": idx, "reason": "signature_mismatch"}
        prev_signature = sig
        checked += 1
    return {"tenant_id": str(tenant_id), "valid": True, "checked": checked, "last_signature": prev_signature}


def export_rollout_evidence_bundle(
    tenant_id: UUID,
    destination_dir: str = "./tmp/compliance/rollout_evidence",
    limit: int = 1000,
    notarize: bool = True,
) -> dict[str, Any]:
    verify = verify_rollout_evidence_chain(tenant_id, limit=limit)
    history = rollout_evidence_history(tenant_id, limit=limit)
    bundle = {
        "tenant_id": str(tenant_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verify": verify,
        "evidence": history,
    }
    notarization = {"status": "skipped"}
    if notarize:
        notarization = notarize_payload(bundle)
    bundle["notarization"] = notarization

    root = Path(destination_dir)
    root.mkdir(parents=True, exist_ok=True)
    file_name = f"rollout_evidence_bundle_{tenant_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
    target = root / file_name
    target.write_text(json.dumps(bundle, ensure_ascii=True, indent=2), encoding="utf-8")

    redis_client.xadd(
        _rollout_evidence_bundle_stream_key(tenant_id),
        {
            "tenant_id": str(tenant_id),
            "generated_at": bundle["generated_at"],
            "path": str(target),
            "verify_valid": "1" if bool(verify.get("valid", False)) else "0",
            "notarized": "1" if str(notarization.get("status", "")) == "notarized" else "0",
            "receipt_id": str(notarization.get("receipt_id", "")),
        },
        maxlen=5000,
        approximate=True,
    )

    return {
        "status": "exported",
        "tenant_id": str(tenant_id),
        "path": str(target),
        "verify": verify,
        "notarization": notarization,
    }


def rollout_evidence_bundle_status(tenant_id: UUID, limit: int = 100) -> dict[str, Any]:
    events = redis_client.xrevrange(_rollout_evidence_bundle_stream_key(tenant_id), count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in events:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"tenant_id": str(tenant_id), "count": len(rows), "rows": rows}


def public_rollout_verifier_bundle(tenant_id: UUID, limit: int = 1000) -> dict[str, Any]:
    verify = verify_rollout_evidence_chain(tenant_id=tenant_id, limit=limit)
    evidence = rollout_evidence_history(tenant_id=tenant_id, limit=limit)
    decisions = rollout_decision_history(tenant_id=tenant_id, limit=min(limit, 200))
    exports = rollout_evidence_bundle_status(tenant_id=tenant_id, limit=1)
    latest_export = exports.get("rows", [{}])[0] if exports.get("rows") else {}
    return {
        "tenant_id": str(tenant_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verify": verify,
        "evidence_count": evidence.get("count", 0),
        "evidence": evidence.get("rows", []),
        "decision_count": decisions.get("count", 0),
        "decisions": decisions.get("rows", []),
        "latest_notarization": {
            "notarized": str(latest_export.get("notarized", "0")) == "1",
            "receipt_id": str(latest_export.get("receipt_id", "")),
            "generated_at": str(latest_export.get("generated_at", "")),
        },
    }


def approve_pending_rollout_decision(
    tenant_id: UUID,
    decision_id: str,
    approve: bool,
    reviewer: str = "operator",
) -> dict[str, Any]:
    key = _rollout_pending_key(tenant_id, decision_id)
    row = redis_client.hgetall(key)
    if not row:
        return {"status": "not_found", "tenant_id": str(tenant_id), "decision_id": decision_id}
    if row.get("status") not in {"pending_approval", "pending_secondary_approval"}:
        return {"status": "invalid_state", "tenant_id": str(tenant_id), "decision_id": decision_id, "current_status": row.get("status")}

    now_iso = datetime.now(timezone.utc).isoformat()
    reviewer_name = reviewer.strip() or "operator"
    if not approve:
        redis_client.hset(
            key,
            mapping={"status": "rejected", "resolved_at": now_iso, "reviewer": reviewer_name},
        )
        _append_rollout_evidence(
            tenant_id,
            {
                "decision_id": decision_id,
                "event_type": "rollout_decision_rejected",
                "reviewer": reviewer_name,
                "action": row.get("action", ""),
                "target_stage": row.get("target_stage", ""),
            },
        )
        return {"status": "rejected", "tenant_id": str(tenant_id), "decision_id": decision_id}

    required = max(1, int(row.get("approvals_required", "1") or 1))
    approver_tokens = [part.strip() for part in str(row.get("approvers", "")).split(",") if part.strip()]
    if reviewer_name in approver_tokens:
        return {"status": "duplicate_reviewer", "tenant_id": str(tenant_id), "decision_id": decision_id, "reviewer": reviewer_name}
    approver_tokens.append(reviewer_name)
    received = len(approver_tokens)

    if received < required:
        redis_client.hset(
            key,
            mapping={
                "status": "pending_secondary_approval",
                "approvals_received": str(received),
                "approvers": ",".join(approver_tokens),
                "last_reviewer": reviewer_name,
                "updated_at": now_iso,
            },
        )
        _append_rollout_evidence(
            tenant_id,
            {
                "decision_id": decision_id,
                "event_type": "rollout_decision_partial_approval",
                "reviewer": reviewer_name,
                "approvals_received": received,
                "approvals_required": required,
                "action": row.get("action", ""),
            },
        )
        return {
            "status": "pending_secondary_approval",
            "tenant_id": str(tenant_id),
            "decision_id": decision_id,
            "approvals_received": received,
            "approvals_required": required,
        }

    _ = upsert_tenant_rollout_profile(
        tenant_id,
        rollout_stage=row.get("target_stage", "ga"),
        canary_percent=int(row.get("target_canary_percent", "100") or 100),
        hold=str(row.get("target_hold", "False")).lower() in {"1", "true"},
        notify_on_hold=str(row.get("notify_on_hold", "False")).lower() in {"1", "true"},
    )
    redis_client.hset(
        key,
        mapping={
            "status": "approved_applied",
            "resolved_at": now_iso,
            "reviewer": reviewer_name,
            "approvals_received": str(received),
            "approvers": ",".join(approver_tokens),
        },
    )
    _append_rollout_evidence(
        tenant_id,
        {
            "decision_id": decision_id,
            "event_type": "rollout_decision_approved_applied",
            "reviewer": reviewer_name,
            "approvals_received": received,
            "approvals_required": required,
            "action": row.get("action", ""),
            "target_stage": row.get("target_stage", ""),
        },
    )
    return {
        "status": "approved_applied",
        "tenant_id": str(tenant_id),
        "decision_id": decision_id,
        "target_stage": row.get("target_stage", "ga"),
        "approvals_received": received,
        "approvals_required": required,
    }


def _effective_priority(profile: dict[str, Any], skip_streak: int) -> int:
    base = PRIORITY_TIERS.get(str(profile.get("priority_tier", "normal")), PRIORITY_TIERS["normal"])
    return base + min(max(0, int(skip_streak)), 4)


def _allowed_rollout_stages() -> set[str]:
    raw = str(getattr(settings, "orchestrator_rollout_allowed_stages", "alpha,beta,ga"))
    values = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return values or {"alpha", "beta", "ga"}


def _rollout_slot(tenant_id: UUID, current_epoch: int, cycle_index: int) -> int:
    bucket = _hour_bucket(current_epoch)
    token = f"{tenant_id}:{bucket}:{cycle_index}".encode("utf-8")
    digest = sha256(token).hexdigest()
    return (int(digest[:8], 16) % 100) + 1


def _rollout_stage_rank(stage: str) -> int:
    order = {"alpha": 1, "beta": 2, "ga": 3}
    return order.get(stage, 3)


def _next_rollout_stage(stage: str) -> str:
    if stage == "alpha":
        return "beta"
    if stage == "beta":
        return "ga"
    return "ga"


def _prev_rollout_stage(stage: str) -> str:
    if stage == "ga":
        return "beta"
    if stage == "beta":
        return "alpha"
    return "alpha"


def _check_and_reserve_rate_budget(tenant_id: UUID, *, red_events_count: int, current_epoch: int) -> dict[str, Any]:
    budget = get_tenant_rate_budget(tenant_id).get("budget", _normalize_rate_budget())
    usage = get_tenant_rate_budget_usage(tenant_id, hour_epoch=current_epoch)
    if not budget.get("enforce_rate_budget", True):
        return {"allowed": True, "budget": budget, "usage": usage}

    next_cycles = int(usage.get("cycles_used", 0)) + 1
    next_events = int(usage.get("red_events_used", 0)) + max(1, int(red_events_count))
    if next_cycles > int(budget.get("max_cycles_per_hour", 120)) or next_events > int(budget.get("max_red_events_per_hour", 10000)):
        return {
            "allowed": False,
            "budget": budget,
            "usage": usage,
            "next_cycles": next_cycles,
            "next_events": next_events,
        }

    redis_client.hset(
        _rate_usage_key(tenant_id, int(usage.get("hour_bucket_epoch", current_epoch))),
        mapping={
            "cycles_used": str(next_cycles),
            "red_events_used": str(next_events),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    usage["cycles_used"] = next_cycles
    usage["red_events_used"] = next_events
    return {"allowed": True, "budget": budget, "usage": usage}


def _emit_pilot_incident(
    tenant_id: UUID,
    *,
    incident_type: str,
    severity: str,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "tenant_id": str(tenant_id),
        "incident_type": incident_type,
        "severity": severity,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if metadata:
        for key, value in metadata.items():
            event[f"meta_{key}"] = str(value)
    event_id = redis_client.xadd(
        _incident_stream_key(tenant_id),
        {k: str(v) for k, v in event.items()},
        maxlen=5000,
        approximate=True,
    )
    event["id"] = event_id
    return event


def pilot_incidents(tenant_id: UUID, limit: int = 100) -> dict[str, Any]:
    events = redis_client.xrevrange(_incident_stream_key(tenant_id), count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in events:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"tenant_id": str(tenant_id), "count": len(rows), "rows": rows}


def rollout_decision_history(tenant_id: UUID, limit: int = 100) -> dict[str, Any]:
    events = redis_client.xrevrange(_rollout_decision_stream_key(tenant_id), count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in events:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"tenant_id": str(tenant_id), "count": len(rows), "rows": rows}


def get_rollout_guard_state(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.hgetall(_rollout_guard_key(tenant_id))
    now_epoch = _now_epoch()
    cooldown_until = int(raw.get("cooldown_until_epoch", "0") or 0)
    return {
        "tenant_id": str(tenant_id),
        "promote_streak": int(raw.get("promote_streak", "0") or 0),
        "demote_streak": int(raw.get("demote_streak", "0") or 0),
        "last_action": raw.get("last_action", "none"),
        "last_adjusted_epoch": int(raw.get("last_adjusted_epoch", "0") or 0),
        "cooldown_until_epoch": cooldown_until,
        "cooldown_active": cooldown_until > now_epoch,
        "updated_at": raw.get("updated_at", ""),
    }


def _persist_rollout_guard_state(tenant_id: UUID, state: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "promote_streak": str(int(state.get("promote_streak", 0) or 0)),
        "demote_streak": str(int(state.get("demote_streak", 0) or 0)),
        "last_action": str(state.get("last_action", "none")),
        "last_adjusted_epoch": str(int(state.get("last_adjusted_epoch", 0) or 0)),
        "cooldown_until_epoch": str(int(state.get("cooldown_until_epoch", 0) or 0)),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    redis_client.hset(_rollout_guard_key(tenant_id), mapping=mapping)
    return get_rollout_guard_state(tenant_id)


def evaluate_tenant_rollout_posture(
    tenant_id: UUID,
    *,
    kpi_limit: int = 5,
    incident_limit: int = 30,
    apply: bool = True,
) -> dict[str, Any]:
    profile = get_tenant_rollout_profile(tenant_id).get("profile", _normalize_rollout_profile())
    policy = get_tenant_rollout_policy(tenant_id).get("policy", _normalize_rollout_policy())
    guard = get_rollout_guard_state(tenant_id)
    now_epoch = _now_epoch()
    trend = get_kpi_trend(tenant_id, limit=max(1, kpi_limit))
    incidents = pilot_incidents(tenant_id, limit=max(1, incident_limit)).get("rows", [])

    coverage: list[float] = []
    for row in trend:
        try:
            coverage.append(float(row.get("detection_coverage", "0") or 0.0))
        except (TypeError, ValueError):
            coverage.append(0.0)

    promote_samples = max(1, int(getattr(settings, "orchestrator_rollout_auto_promote_kpi_samples", 3)))
    promote_min = float(getattr(settings, "orchestrator_rollout_auto_promote_min_coverage", 0.95))
    promote_streak_required = max(1, int(getattr(settings, "orchestrator_rollout_promote_streak_required", 2)))
    demote_streak_required = max(1, int(getattr(settings, "orchestrator_rollout_demote_streak_required", 1)))
    cooldown_seconds = max(0, int(getattr(settings, "orchestrator_rollout_decision_cooldown_seconds", 900)))
    recent_cov = coverage[:promote_samples]

    high_incidents = len([row for row in incidents if str(row.get("severity", "")).lower() in {"high", "critical"}])
    medium_incidents = len([row for row in incidents if str(row.get("severity", "")).lower() == "medium"])
    has_auto_stop = any(str(row.get("incident_type", "")) == "pilot_auto_stop" for row in incidents)

    current_stage = str(profile.get("rollout_stage", "ga"))
    current_canary = int(profile.get("canary_percent", 100))
    target_stage = current_stage
    target_canary = current_canary
    target_hold = bool(profile.get("hold", False))
    action = "no_change"
    reason = "stable"
    signal = "none"
    promote_streak = int(guard.get("promote_streak", 0))
    demote_streak = int(guard.get("demote_streak", 0))
    cooldown_until_epoch = int(guard.get("cooldown_until_epoch", 0))
    cooldown_active = cooldown_until_epoch > now_epoch

    if has_auto_stop or high_incidents >= 1:
        signal = "demote"
        demote_streak += 1
        promote_streak = 0
    elif len(recent_cov) == promote_samples and min(recent_cov) >= promote_min and medium_incidents == 0:
        signal = "promote"
        promote_streak += 1
        demote_streak = 0
    else:
        promote_streak = 0
        demote_streak = 0

    if signal == "demote" and demote_streak >= demote_streak_required:
        target_stage = _prev_rollout_stage(current_stage)
        target_canary = max(10, current_canary - 30)
        target_hold = True
        action = "demote"
        reason = "high_risk_incident_detected"
    elif signal == "promote" and promote_streak >= promote_streak_required:
        target_stage = _next_rollout_stage(current_stage)
        target_canary = min(100, current_canary + 20)
        target_hold = False
        action = "promote"
        reason = "kpi_consistently_good"
    elif signal == "promote":
        action = "pending_promote"
        reason = "hysteresis_waiting_for_streak"
    elif signal == "demote":
        action = "pending_demote"
        reason = "hysteresis_waiting_for_streak"

    changed = (
        target_stage != current_stage
        or target_canary != current_canary
        or target_hold != bool(profile.get("hold", False))
    )
    if changed and cooldown_active:
        action = "cooldown_blocked"
        reason = "decision_cooldown_active"
        target_stage = current_stage
        target_canary = current_canary
        target_hold = bool(profile.get("hold", False))
        changed = False

    pending_decision_id = ""
    if changed and action == "promote" and not bool(policy.get("auto_promote_enabled", True)):
        action = "blocked_by_policy"
        reason = "auto_promote_disabled"
        changed = False
    if changed and action == "demote" and not bool(policy.get("auto_demote_enabled", True)):
        action = "blocked_by_policy"
        reason = "auto_demote_disabled"
        changed = False

    if changed and action in {"promote", "demote"}:
        requires_approval = (action == "promote" and bool(policy.get("require_approval_for_promote", False))) or (
            action == "demote" and bool(policy.get("require_approval_for_demote", True))
        )
        if requires_approval:
            approvals_required = 1
            if action == "promote" and bool(policy.get("require_dual_control_for_promote", False)):
                approvals_required = 2
            if action == "demote" and bool(policy.get("require_dual_control_for_demote", False)):
                approvals_required = 2
            existing = _find_pending_rollout_decision(tenant_id, action)
            if existing:
                pending_decision_id = str(existing.get("decision_id", ""))
            else:
                pending = _create_pending_rollout_decision(
                    tenant_id,
                    {
                        "action": action,
                        "reason": reason,
                        "current_stage": current_stage,
                        "target_stage": target_stage,
                        "current_canary_percent": current_canary,
                        "target_canary_percent": target_canary,
                        "current_hold": bool(profile.get("hold", False)),
                        "target_hold": target_hold,
                        "notify_on_hold": bool(profile.get("notify_on_hold", False)),
                        "approvals_required": approvals_required,
                    },
                )
                pending_decision_id = str(pending.get("decision_id", ""))
                _append_rollout_evidence(
                    tenant_id,
                    {
                        "decision_id": pending_decision_id,
                        "event_type": "rollout_decision_pending_approval",
                        "action": action,
                        "current_stage": current_stage,
                        "target_stage": target_stage,
                        "approvals_required": approvals_required,
                    },
                )
            action = "pending_approval"
            reason = "policy_requires_approval"
            changed = False

    applied = False
    if apply and changed:
        _ = upsert_tenant_rollout_profile(
            tenant_id,
            rollout_stage=target_stage,
            canary_percent=target_canary,
            hold=target_hold,
            notify_on_hold=bool(profile.get("notify_on_hold", False)),
        )
        applied = True
        cooldown_until_epoch = now_epoch + cooldown_seconds
        if action == "promote":
            promote_streak = 0
            demote_streak = 0
        if action == "demote":
            promote_streak = 0
            demote_streak = 0
        if action == "demote":
            _emit_pilot_incident(
                tenant_id,
                incident_type="rollout_demotion",
                severity="medium",
                reason=reason,
                metadata={"from_stage": current_stage, "to_stage": target_stage},
            )
        elif action == "promote":
            _emit_pilot_incident(
                tenant_id,
                incident_type="rollout_promotion",
                severity="low",
                reason=reason,
                metadata={"from_stage": current_stage, "to_stage": target_stage},
            )
        _append_rollout_evidence(
            tenant_id,
            {
                "decision_id": str(uuid4()),
                "event_type": "rollout_decision_auto_applied",
                "action": action,
                "reason": reason,
                "current_stage": current_stage,
                "target_stage": target_stage,
            },
        )

    guard_after = _persist_rollout_guard_state(
        tenant_id,
        {
            "promote_streak": promote_streak,
            "demote_streak": demote_streak,
            "last_action": action if applied else str(guard.get("last_action", "none")),
            "last_adjusted_epoch": now_epoch if applied else int(guard.get("last_adjusted_epoch", 0)),
            "cooldown_until_epoch": cooldown_until_epoch,
        },
    )

    decision = {
        "tenant_id": str(tenant_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "reason": reason,
        "applied": applied,
        "changed": changed,
        "current_stage": current_stage,
        "target_stage": target_stage,
        "current_canary_percent": current_canary,
        "target_canary_percent": target_canary,
        "current_hold": bool(profile.get("hold", False)),
        "target_hold": target_hold,
        "high_incidents": high_incidents,
        "medium_incidents": medium_incidents,
        "has_auto_stop": has_auto_stop,
        "kpi_samples_used": len(recent_cov),
        "kpi_min_coverage": min(recent_cov) if recent_cov else 0.0,
        "rollout_policy": policy,
        "pending_decision_id": pending_decision_id,
        "signal": signal,
        "promote_streak": guard_after.get("promote_streak", 0),
        "demote_streak": guard_after.get("demote_streak", 0),
        "promote_streak_required": promote_streak_required,
        "demote_streak_required": demote_streak_required,
        "cooldown_until_epoch": guard_after.get("cooldown_until_epoch", 0),
        "cooldown_active": guard_after.get("cooldown_active", False),
        "stage_rank_before": _rollout_stage_rank(current_stage),
        "stage_rank_after": _rollout_stage_rank(target_stage),
    }
    redis_client.xadd(
        _rollout_decision_stream_key(tenant_id),
        {k: str(v) for k, v in decision.items()},
        maxlen=5000,
        approximate=True,
    )
    return decision


def _auto_stop_for_safety(tenant_id: UUID, *, reason: str, source: str, notify: bool) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    redis_client.hset(
        _activation_key(tenant_id),
        mapping={
            "status": "paused",
            "last_status": "auto_stopped",
            "last_error": reason,
            "next_run_epoch": "0",
            "next_run_at": "",
            "updated_at": now_iso,
        },
    )
    pilot_raw = redis_client.hgetall(_pilot_key(tenant_id))
    if pilot_raw and pilot_raw.get("status", "inactive") == "running":
        redis_client.hset(
            _pilot_key(tenant_id),
            mapping={
                "status": "stopped",
                "ended_at": now_iso,
                "reason": reason,
                "updated_at": now_iso,
            },
        )

    _emit_pilot_incident(
        tenant_id,
        incident_type="pilot_auto_stop",
        severity="high",
        reason=reason,
        metadata={"source": source},
    )
    if notify:
        send_telegram_message(f"[BRP-Cyber] Pilot auto-stopped tenant={tenant_id} source={source} reason={reason}")


def run_activation_scheduler_tick(limit: int = 200, now_epoch: int | None = None) -> dict[str, Any]:
    current_epoch = now_epoch if now_epoch is not None else _now_epoch()
    states = list_activation_states(limit=limit).get("rows", [])
    max_executions = max(1, int(getattr(settings, "orchestrator_scheduler_max_executions_per_tick", 50)))
    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    scheduler_profiles: dict[str, dict[str, Any]] = {}
    rollout_profiles: dict[str, dict[str, Any]] = {}
    for state in states:
        tenant_text = str(state.get("tenant_id", ""))
        if not tenant_text:
            continue
        try:
            tenant_id = UUID(tenant_text)
        except ValueError:
            continue
        scheduler_profiles[tenant_text] = get_tenant_scheduler_profile(tenant_id).get("profile", _normalize_scheduler_profile())
        rollout_profiles[tenant_text] = get_tenant_rollout_profile(tenant_id).get("profile", _normalize_rollout_profile())

    allowed_stages = _allowed_rollout_stages()

    def _sort_key(state: dict[str, Any]) -> tuple[int, int, int, int]:
        tenant_text = str(state.get("tenant_id", ""))
        due = state.get("status") == "active" and int(state.get("next_run_epoch", 0) or 0) <= current_epoch
        skip_streak = int(state.get("scheduler_skip_streak", 0) or 0)
        profile = scheduler_profiles.get(tenant_text, _normalize_scheduler_profile())
        priority = _effective_priority(profile, skip_streak)
        next_run_epoch = int(state.get("next_run_epoch", 0) or 0)
        return (0 if due else 1, -priority, -skip_streak, next_run_epoch)

    states = sorted(states, key=_sort_key)

    for state in states:
        tenant_text = str(state.get("tenant_id", ""))
        if state.get("status") != "active":
            skipped.append({"tenant_id": tenant_text, "reason": "not_active"})
            continue

        due = int(state.get("next_run_epoch", 0) or 0) <= current_epoch
        if not due:
            skipped.append({"tenant_id": tenant_text, "reason": "not_due"})
            continue

        tenant_id = UUID(tenant_text)
        scheduler_profile = scheduler_profiles.get(tenant_text, _normalize_scheduler_profile())
        rollout_profile = rollout_profiles.get(tenant_text, _normalize_rollout_profile())
        if len(executed) >= max_executions:
            skip_streak = int(state.get("scheduler_skip_streak", 0) or 0) + 1
            redis_client.hset(
                _activation_key(tenant_id),
                mapping={"scheduler_skip_streak": str(skip_streak), "updated_at": datetime.now(timezone.utc).isoformat()},
            )
            skipped.append({"tenant_id": tenant_text, "reason": "global_tick_execution_cap"})
            threshold = int(scheduler_profile.get("starvation_incident_threshold", 3))
            if skip_streak == threshold:
                _emit_pilot_incident(
                    tenant_id,
                    incident_type="scheduler_backpressure",
                    severity="medium",
                    reason=f"skip_streak_threshold_reached:{skip_streak}",
                    metadata={"priority_tier": scheduler_profile.get("priority_tier", "normal")},
                )
                if bool(scheduler_profile.get("notify_on_starvation", False)):
                    send_telegram_message(
                        f"[BRP-Cyber] Scheduler backpressure tenant={tenant_id} "
                        f"skip_streak={skip_streak} priority={scheduler_profile.get('priority_tier', 'normal')}"
                    )
            continue

        if rollout_profile.get("rollout_stage", "ga") not in allowed_stages:
            skip_streak = int(state.get("scheduler_skip_streak", 0) or 0) + 1
            redis_client.hset(
                _activation_key(tenant_id),
                mapping={"scheduler_skip_streak": str(skip_streak), "updated_at": datetime.now(timezone.utc).isoformat()},
            )
            skipped.append({"tenant_id": tenant_text, "reason": "rollout_stage_blocked"})
            continue

        if bool(rollout_profile.get("hold", False)):
            skip_streak = int(state.get("scheduler_skip_streak", 0) or 0) + 1
            redis_client.hset(
                _activation_key(tenant_id),
                mapping={"scheduler_skip_streak": str(skip_streak), "updated_at": datetime.now(timezone.utc).isoformat()},
            )
            skipped.append({"tenant_id": tenant_text, "reason": "rollout_hold"})
            _emit_pilot_incident(
                tenant_id,
                incident_type="rollout_hold",
                severity="low",
                reason="tenant_rollout_hold_enabled",
                metadata={"rollout_stage": rollout_profile.get("rollout_stage", "ga")},
            )
            if bool(rollout_profile.get("notify_on_hold", False)):
                send_telegram_message(f"[BRP-Cyber] Rollout hold tenant={tenant_id} stage={rollout_profile.get('rollout_stage', 'ga')}")
            continue

        cycle_index = int(state.get("last_cycle_index", 0) or 0) + 1
        canary_slot = _rollout_slot(tenant_id, current_epoch, cycle_index)
        if canary_slot > int(rollout_profile.get("canary_percent", 100)):
            skip_streak = int(state.get("scheduler_skip_streak", 0) or 0) + 1
            redis_client.hset(
                _activation_key(tenant_id),
                mapping={"scheduler_skip_streak": str(skip_streak), "updated_at": datetime.now(timezone.utc).isoformat()},
            )
            skipped.append({"tenant_id": tenant_text, "reason": "rollout_canary_deferred"})
            continue

        safety_policy = get_tenant_safety_policy(tenant_id).get("policy", _normalize_safety_policy())
        budget_result = _check_and_reserve_rate_budget(
            tenant_id,
            red_events_count=int(state.get("red_events_count", 30) or 30),
            current_epoch=current_epoch,
        )
        redis_client.hset(_activation_key(tenant_id), mapping={"scheduler_skip_streak": "0"})
        if not budget_result.get("allowed", False):
            reason = (
                f"rate_budget_exceeded cycles={budget_result.get('next_cycles', 0)}/"
                f"{budget_result.get('budget', {}).get('max_cycles_per_hour', 0)} "
                f"events={budget_result.get('next_events', 0)}/"
                f"{budget_result.get('budget', {}).get('max_red_events_per_hour', 0)}"
            )
            _emit_pilot_incident(
                tenant_id,
                incident_type="rate_budget_exceeded",
                severity="medium",
                reason=reason,
                metadata={"hour_bucket_epoch": budget_result.get("usage", {}).get("hour_bucket_epoch", _hour_bucket(current_epoch))},
            )
            budget = budget_result.get("budget", {})
            if bool(budget.get("auto_pause_on_budget_exceeded", True)):
                _auto_stop_for_safety(
                    tenant_id,
                    reason=reason,
                    source="rate_budget",
                    notify=bool(budget.get("notify_on_budget_exceeded", True)),
                )
                executed.append({"tenant_id": tenant_text, "cycle_index": 0, "result_status": "auto_stopped"})
            else:
                skipped.append({"tenant_id": tenant_text, "reason": "rate_budget_exceeded"})
            continue

        if safety_policy.get("objective_gate_check_each_tick", False):
            gate = evaluate_and_persist_objective_gate(tenant_id=tenant_id)
            if not bool(gate.get("overall_pass", False)):
                reason = "objective_gate_fail_on_tick"
                if safety_policy.get("auto_stop_on_objective_gate_fail", False):
                    _auto_stop_for_safety(
                        tenant_id,
                        reason=reason,
                        source="objective_gate",
                        notify=bool(safety_policy.get("notify_on_auto_stop", True)),
                    )
                    executed.append({"tenant_id": tenant_text, "cycle_index": 0, "result_status": "auto_stopped"})
                    continue
                _emit_pilot_incident(
                    tenant_id,
                    incident_type="objective_gate_warning",
                    severity="medium",
                    reason=reason,
                    metadata={"failed_gates": [name for name, row in gate.get("gates", {}).items() if not row.get("pass", False)]},
                )

        req = OrchestrationCycleRequest(
            tenant_id=tenant_id,
            target_asset=str(state.get("target_asset", "")),
            red_scenario_name=str(state.get("red_scenario_name", "credential_stuffing_sim")),
            red_events_count=int(state.get("red_events_count", 30) or 30),
            strategy_profile=str(state.get("strategy_profile", "balanced")),
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        interval = max(30, int(state.get("cycle_interval_seconds", 300) or 300))
        next_epoch = current_epoch + interval
        next_iso = datetime.fromtimestamp(next_epoch, tz=timezone.utc).isoformat()

        try:
            result = run_orchestration_cycle(req, cycle_index=cycle_index)
            redis_client.hset(
                _activation_key(tenant_id),
                mapping={
                    "run_count": str(int(state.get("run_count", 0) or 0) + 1),
                    "last_cycle_index": str(cycle_index),
                    "consecutive_failures": "0",
                    "last_run_at": now_iso,
                    "next_run_at": next_iso,
                    "next_run_epoch": str(next_epoch),
                    "last_status": str(result.get("status", "ok")),
                    "last_error": "",
                    "updated_at": now_iso,
                },
            )
            executed.append(
                {
                    "tenant_id": tenant_text,
                    "cycle_index": cycle_index,
                    "result_status": str(result.get("status", "ok")),
                }
            )
            if bool(getattr(settings, "orchestrator_rollout_auto_adjust_enabled", True)):
                _ = evaluate_tenant_rollout_posture(tenant_id, apply=True)
        except Exception as exc:
            failures = int(state.get("consecutive_failures", 0) or 0) + 1
            redis_client.hset(
                _activation_key(tenant_id),
                mapping={
                    "last_run_at": now_iso,
                    "next_run_at": next_iso,
                    "next_run_epoch": str(next_epoch),
                    "consecutive_failures": str(failures),
                    "last_status": "error",
                    "last_error": str(exc),
                    "updated_at": now_iso,
                },
            )
            _emit_pilot_incident(
                tenant_id,
                incident_type="scheduler_cycle_error",
                severity="medium",
                reason=str(exc),
                metadata={"cycle_index": cycle_index, "consecutive_failures": failures},
            )
            if safety_policy.get("auto_stop_on_consecutive_failures", True) and failures >= int(
                safety_policy.get("max_consecutive_failures", 3)
            ):
                _auto_stop_for_safety(
                    tenant_id,
                    reason=f"consecutive_scheduler_failures:{failures}",
                    source="scheduler",
                    notify=bool(safety_policy.get("notify_on_auto_stop", True)),
                )
                executed.append({"tenant_id": tenant_text, "cycle_index": cycle_index, "result_status": "auto_stopped"})
                continue
            executed.append({"tenant_id": tenant_text, "cycle_index": cycle_index, "result_status": "error"})

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "max_executions_per_tick": max_executions,
        "executed_count": len(executed),
        "skipped_count": len(skipped),
        "executed": executed,
        "skipped": skipped,
    }


def _build_pilot_row(tenant_id: UUID, raw: dict[str, str]) -> dict[str, Any]:
    return {
        "tenant_id": str(tenant_id),
        "status": raw.get("status", "inactive"),
        "started_at": raw.get("started_at", ""),
        "ended_at": raw.get("ended_at", ""),
        "reason": raw.get("reason", ""),
        "objective_gate_pass": raw.get("objective_gate_pass", "0") == "1",
        "objective_gate_checked_at": raw.get("objective_gate_checked_at", ""),
        "objective_gate_summary": raw.get("objective_gate_summary", "{}"),
        "updated_at": raw.get("updated_at", ""),
    }


def activate_pilot_session(
    tenant_id: UUID,
    target_asset: str,
    red_scenario_name: str = "credential_stuffing_sim",
    red_events_count: int = 30,
    strategy_profile: str = "balanced",
    cycle_interval_seconds: int = 300,
    approval_mode: bool = False,
    require_objective_gate_pass: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    _sync_enterprise_clients()
    gate = evaluate_and_persist_objective_gate(tenant_id=tenant_id)
    gate_pass = bool(gate.get("overall_pass", False))
    if require_objective_gate_pass and not gate_pass and not force:
        return {
            "status": "blocked_by_objective_gate",
            "tenant_id": str(tenant_id),
            "objective_gate": gate,
        }

    activation = activate_tenant_orchestration(
        tenant_id=tenant_id,
        target_asset=target_asset,
        red_scenario_name=red_scenario_name,
        red_events_count=red_events_count,
        strategy_profile=strategy_profile,
        cycle_interval_seconds=cycle_interval_seconds,
        approval_mode=approval_mode,
    )
    now_iso = datetime.now(timezone.utc).isoformat()
    redis_client.hset(
        _pilot_key(tenant_id),
        mapping={
            "status": "running",
            "started_at": now_iso,
            "ended_at": "",
            "reason": "",
            "objective_gate_pass": "1" if gate_pass else "0",
            "objective_gate_checked_at": now_iso,
            "objective_gate_summary": str(
                {
                    "overall_pass": gate.get("overall_pass", False),
                    "failed_gates": [name for name, row in gate.get("gates", {}).items() if not row.get("pass", False)],
                }
            ),
            "updated_at": now_iso,
        },
    )
    return {
        "status": "pilot_running",
        "tenant_id": str(tenant_id),
        "activation": activation,
        "objective_gate": {
            "overall_pass": gate.get("overall_pass", False),
            "failed_gates": [name for name, row in gate.get("gates", {}).items() if not row.get("pass", False)],
        },
    }


def deactivate_pilot_session(tenant_id: UUID, reason: str = "manual_stop") -> dict[str, Any]:
    activation = deactivate_tenant_orchestration(tenant_id)
    now_iso = datetime.now(timezone.utc).isoformat()
    redis_client.hset(
        _pilot_key(tenant_id),
        mapping={
            "status": "stopped",
            "ended_at": now_iso,
            "reason": reason,
            "updated_at": now_iso,
        },
    )
    return {
        "status": "pilot_stopped",
        "tenant_id": str(tenant_id),
        "reason": reason,
        "activation": activation,
    }


def get_pilot_session_status(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.hgetall(_pilot_key(tenant_id))
    pilot = _build_pilot_row(tenant_id, raw) if raw else {"tenant_id": str(tenant_id), "status": "inactive"}
    activation = get_tenant_activation_state(tenant_id)
    trend = get_kpi_trend(tenant_id, limit=5)
    incidents = pilot_incidents(tenant_id, limit=5)
    rate_budget = get_tenant_rate_budget(tenant_id)
    rate_usage = get_tenant_rate_budget_usage(tenant_id)
    scheduler_profile = get_tenant_scheduler_profile(tenant_id)
    rollout_profile = get_tenant_rollout_profile(tenant_id)
    rollout_policy = get_tenant_rollout_policy(tenant_id)
    rollout_guard = get_rollout_guard_state(tenant_id)
    rollout_decisions = rollout_decision_history(tenant_id, limit=5)
    rollout_pending = list_pending_rollout_decisions(tenant_id, limit=5)
    rollout_evidence = rollout_evidence_history(tenant_id, limit=5)
    return {
        "tenant_id": str(tenant_id),
        "pilot": pilot,
        "activation": activation,
        "kpi_trend_count": len(trend),
        "kpi_trend": trend,
        "rate_budget": rate_budget.get("budget", {}),
        "rate_budget_usage": rate_usage,
        "scheduler_profile": scheduler_profile.get("profile", {}),
        "rollout_profile": rollout_profile.get("profile", {}),
        "rollout_policy": rollout_policy.get("policy", {}),
        "rollout_guard_state": rollout_guard,
        "recent_rollout_decisions_count": rollout_decisions.get("count", 0),
        "recent_rollout_decisions": rollout_decisions.get("rows", []),
        "pending_rollout_decisions_count": rollout_pending.get("count", 0),
        "pending_rollout_decisions": rollout_pending.get("rows", []),
        "recent_rollout_evidence_count": rollout_evidence.get("count", 0),
        "recent_rollout_evidence": rollout_evidence.get("rows", []),
        "recent_incidents_count": incidents.get("count", 0),
        "recent_incidents": incidents.get("rows", []),
    }


def list_pilot_sessions(limit: int = 200) -> dict[str, Any]:
    keys = redis_client.keys(f"{ORCHESTRATION_PILOT_SESSION_PREFIX}:*")
    rows: list[dict[str, Any]] = []
    for key in keys[: max(1, limit)]:
        tenant_text = key.split(":", 1)[-1]
        try:
            tenant_id = UUID(tenant_text)
        except ValueError:
            continue
        raw = redis_client.hgetall(_pilot_key(tenant_id))
        row = _build_pilot_row(tenant_id, raw)
        row["activation_status"] = get_tenant_activation_state(tenant_id).get("status", "inactive")
        rows.append(row)

    running = len([row for row in rows if row.get("status") == "running"])
    return {
        "count": len(rows),
        "running": running,
        "stopped_or_inactive": len(rows) - running,
        "rows": rows,
    }
