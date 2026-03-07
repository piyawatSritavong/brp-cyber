from __future__ import annotations

import ast
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.services.control_plane_assurance_contracts import evaluate_assurance_contract
from app.services.control_plane_assurance_policy_packs import get_assurance_policy_pack
from app.services.notifier import send_telegram_message
from app.services import policy_store as _policy_store
from app.services.policy_store import (
    get_pending_action,
    get_blue_policy,
    get_strategy_profile,
    is_approval_mode_enabled,
    save_pending_action,
    set_approval_mode,
    set_blue_policy,
    set_strategy_profile,
)
from app.services.redis_client import redis_client

ASSURANCE_REMEDIATION_STREAM_PREFIX = "control_plane_assurance_remediation"


def _stream_key(tenant_code: str) -> str:
    return f"{ASSURANCE_REMEDIATION_STREAM_PREFIX}:{tenant_code.lower().strip()}"


def _sync_policy_store_client() -> None:
    _policy_store.redis_client = redis_client


def _action(
    tenant_id: UUID,
    tenant_code: str,
    action_name: str,
    reason: str,
    priority: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "action_id": str(uuid4()),
        "tenant_id": str(tenant_id),
        "tenant_code": tenant_code,
        "action_name": action_name,
        "reason": reason,
        "priority": priority,
        "params": params or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def build_assurance_remediation_actions(
    tenant_id: UUID,
    tenant_code: str,
    evaluation: dict[str, Any],
) -> list[dict[str, Any]]:
    _sync_policy_store_client()
    unmet = evaluation.get("evaluation", {}).get("unmet_clauses", [])
    actions: list[dict[str, Any]] = []

    for clause in unmet:
        clause_name = str(clause.get("clause", ""))
        if clause_name == "min_overall_pass_rate":
            actions.append(
                _action(
                    tenant_id,
                    tenant_code,
                    action_name="set_strategy_profile",
                    reason="overall_pass_rate_below_contract",
                    priority="critical",
                    params={"strategy_profile": "conservative"},
                )
            )
        elif clause_name == "min_gate_pass_rate":
            gate = str(clause.get("gate", ""))
            if gate == "blue":
                policy = get_blue_policy(tenant_id)
                tightened = max(1, int(policy["failed_login_threshold_per_minute"]) - 2)
                actions.append(
                    _action(
                        tenant_id,
                        tenant_code,
                        action_name="tighten_blue_threshold",
                        reason="blue_gate_pass_rate_below_contract",
                        priority="critical",
                        params={
                            "failed_login_threshold_per_minute": tightened,
                            "failure_window_seconds": int(policy["failure_window_seconds"]),
                            "incident_cooldown_seconds": int(policy["incident_cooldown_seconds"]),
                        },
                    )
                )
            elif gate in {"red", "purple", "closed_loop"}:
                actions.append(
                    _action(
                        tenant_id,
                        tenant_code,
                        action_name="set_strategy_profile",
                        reason=f"{gate}_gate_pass_rate_below_contract",
                        priority="high",
                        params={"strategy_profile": "conservative"},
                    )
                )
        elif clause_name == "max_enterprise_monthly_cost_usd":
            actions.append(
                _action(
                    tenant_id,
                    tenant_code,
                    action_name="set_strategy_profile",
                    reason="enterprise_cost_above_contract",
                    priority="critical",
                    params={"strategy_profile": "conservative"},
                )
            )
            actions.append(
                _action(
                    tenant_id,
                    tenant_code,
                    action_name="enable_approval_mode",
                    reason="enterprise_cost_above_contract",
                    priority="high",
                    params={"enabled": True},
                )
            )
        elif clause_name == "required_frameworks":
            actions.append(
                _action(
                    tenant_id,
                    tenant_code,
                    action_name="enable_approval_mode",
                    reason="regulatory_framework_contract_not_met",
                    priority="high",
                    params={"enabled": True},
                )
            )

    dedup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in actions:
        dedup[(row["action_name"], row["reason"])] = row
    return list(dedup.values())


def _apply_action(tenant_id: UUID, action: dict[str, Any]) -> dict[str, Any]:
    _sync_policy_store_client()
    action_name = str(action.get("action_name", ""))
    params = action.get("params", {}) if isinstance(action.get("params"), dict) else {}

    if action_name == "set_strategy_profile":
        previous = get_strategy_profile(tenant_id)
        profile = str(params.get("strategy_profile", "conservative"))
        set_strategy_profile(tenant_id, profile)
        return {
            "status": "applied",
            "action_name": action_name,
            "strategy_profile": profile,
            "rollback_action": "set_strategy_profile",
            "rollback_params": {"strategy_profile": previous},
        }

    if action_name == "tighten_blue_threshold":
        previous_policy = get_blue_policy(tenant_id)
        applied = set_blue_policy(
            tenant_id,
            failed_login_threshold_per_minute=int(params.get("failed_login_threshold_per_minute", 5)),
            failure_window_seconds=int(params.get("failure_window_seconds", 60)),
            incident_cooldown_seconds=int(params.get("incident_cooldown_seconds", 180)),
        )
        return {
            "status": "applied",
            "action_name": action_name,
            "blue_policy": applied,
            "rollback_action": "tighten_blue_threshold",
            "rollback_params": previous_policy,
        }

    if action_name == "enable_approval_mode":
        previous_mode = is_approval_mode_enabled(tenant_id)
        enabled = bool(params.get("enabled", True))
        set_approval_mode(tenant_id, enabled)
        return {
            "status": "applied",
            "action_name": action_name,
            "approval_mode": enabled,
            "rollback_action": "enable_approval_mode",
            "rollback_params": {"enabled": previous_mode},
        }

    return {"status": "skipped", "action_name": action_name, "reason": "unknown_action"}


def _coerce_params(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                return loaded
        except json.JSONDecodeError:
            pass
        try:
            loaded = ast.literal_eval(raw)
            if isinstance(loaded, dict):
                return loaded
        except (ValueError, SyntaxError):
            return {}
    return {}


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _rollback_action(tenant_id: UUID, action: dict[str, Any]) -> dict[str, Any]:
    _sync_policy_store_client()
    rollback_action = str(action.get("rollback_action", ""))
    rollback_params = _coerce_params(action.get("rollback_params", {}))
    if not rollback_action:
        return {"status": "skipped", "reason": "no_rollback_action"}

    if rollback_action == "set_strategy_profile":
        profile = str(rollback_params.get("strategy_profile", "balanced"))
        set_strategy_profile(tenant_id, profile)
        return {"status": "rolled_back", "rollback_action": rollback_action, "strategy_profile": profile}

    if rollback_action == "tighten_blue_threshold":
        applied = set_blue_policy(
            tenant_id,
            failed_login_threshold_per_minute=int(rollback_params.get("failed_login_threshold_per_minute", 10)),
            failure_window_seconds=int(rollback_params.get("failure_window_seconds", 60)),
            incident_cooldown_seconds=int(rollback_params.get("incident_cooldown_seconds", 120)),
        )
        return {"status": "rolled_back", "rollback_action": rollback_action, "blue_policy": applied}

    if rollback_action == "enable_approval_mode":
        enabled = bool(rollback_params.get("enabled", False))
        set_approval_mode(tenant_id, enabled)
        return {"status": "rolled_back", "rollback_action": rollback_action, "approval_mode": enabled}

    return {"status": "skipped", "reason": "unknown_rollback_action"}


def remediate_assurance_breach(
    tenant_id: UUID,
    tenant_code: str,
    limit: int = 100,
    auto_apply: bool = False,
) -> dict[str, Any]:
    _sync_policy_store_client()
    evaluation = evaluate_assurance_contract(tenant_id, tenant_code, limit=limit)
    if evaluation.get("status") != "ok":
        return evaluation

    if evaluation.get("evaluation", {}).get("contract_pass", False):
        return {
            "status": "no_breach",
            "tenant_id": str(tenant_id),
            "tenant_code": tenant_code,
            "evaluation": evaluation.get("evaluation", {}),
            "actions": [],
        }

    actions = build_assurance_remediation_actions(tenant_id, tenant_code, evaluation)
    batch_id = str(uuid4())
    baseline_eval = evaluation.get("evaluation", {})
    baseline_overall_pass_rate = _as_float(baseline_eval.get("overall_pass_rate"), 0.0)
    baseline_unmet_count = len(baseline_eval.get("unmet_clauses", []))

    policy_pack_resp = get_assurance_policy_pack(tenant_code)
    policy_pack = policy_pack_resp.get("policy_pack", {})
    auto_apply_actions = set(policy_pack.get("auto_apply_actions", []))
    force_approval_actions = set(policy_pack.get("force_approval_actions", []))
    blocked_actions = set(policy_pack.get("blocked_actions", []))
    max_auto_apply = int(policy_pack.get("max_auto_apply_actions_per_run", 0) or 0)
    notify_only = bool(policy_pack.get("notify_only", False))
    rollback_on_worse = bool(policy_pack.get("rollback_on_worse_result", True))
    min_effectiveness_delta = _as_float(policy_pack.get("min_effectiveness_delta"), 0.0)

    results: list[dict[str, Any]] = []
    auto_applied_count = 0

    for action in actions:
        action_name = str(action.get("action_name", ""))
        if action_name in blocked_actions:
            record = {
                **action,
                "batch_id": batch_id,
                "status": "blocked_by_policy_pack",
                "resolved_at": datetime.now(timezone.utc).isoformat(),
                "baseline_overall_pass_rate": baseline_overall_pass_rate,
                "baseline_unmet_count": baseline_unmet_count,
            }
        else:
            should_auto_apply = auto_apply
            if not auto_apply and action_name in auto_apply_actions:
                should_auto_apply = True
            if action_name in force_approval_actions:
                should_auto_apply = False
            if notify_only:
                should_auto_apply = False
            if should_auto_apply and auto_applied_count >= max_auto_apply:
                should_auto_apply = False

            if should_auto_apply:
                applied = _apply_action(tenant_id, action)
                record = {
                    **action,
                    **applied,
                    "batch_id": batch_id,
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "baseline_overall_pass_rate": baseline_overall_pass_rate,
                    "baseline_unmet_count": baseline_unmet_count,
                }
                auto_applied_count += 1
            else:
                pending = {
                    **action,
                    "batch_id": batch_id,
                    "status": "pending_approval",
                    "current_strategy_profile": get_strategy_profile(tenant_id),
                    "current_approval_mode": is_approval_mode_enabled(tenant_id),
                    "baseline_overall_pass_rate": baseline_overall_pass_rate,
                    "baseline_unmet_count": baseline_unmet_count,
                }
                save_pending_action(tenant_id, action["action_id"], {k: str(v) for k, v in pending.items()})
                record = pending

        redis_client.xadd(
            _stream_key(tenant_code),
            {k: str(v) for k, v in record.items()},
            maxlen=100000,
            approximate=True,
        )
        results.append(record)

    post_evaluation_resp = evaluate_assurance_contract(tenant_id, tenant_code, limit=limit)
    post_eval = post_evaluation_resp.get("evaluation", {}) if post_evaluation_resp.get("status") == "ok" else {}
    post_overall_pass_rate = _as_float(post_eval.get("overall_pass_rate"), baseline_overall_pass_rate)
    post_unmet_count = len(post_eval.get("unmet_clauses", [])) if isinstance(post_eval.get("unmet_clauses", []), list) else baseline_unmet_count
    effectiveness_delta = round(post_overall_pass_rate - baseline_overall_pass_rate, 4)
    rollback_triggered = False
    rolled_back_count = 0

    should_rollback = (
        auto_applied_count > 0
        and rollback_on_worse
        and effectiveness_delta < min_effectiveness_delta
    )

    if should_rollback:
        rollback_triggered = True
        for row in results:
            if str(row.get("status", "")) != "applied":
                continue
            rollback_result = _rollback_action(tenant_id, row)
            if rollback_result.get("status") == "rolled_back":
                rolled_back_count += 1
            rollback_row = {
                "batch_id": batch_id,
                "action_id": str(row.get("action_id", "")),
                "action_name": str(row.get("action_name", "")),
                "kind": "rollback",
                "status": rollback_result.get("status", "unknown"),
                "reason": "effectiveness_below_threshold",
                "effectiveness_delta": effectiveness_delta,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            redis_client.xadd(
                _stream_key(tenant_code),
                {k: str(v) for k, v in rollback_row.items()},
                maxlen=100000,
                approximate=True,
            )

    summary_row = {
        "kind": "batch_summary",
        "batch_id": batch_id,
        "baseline_overall_pass_rate": baseline_overall_pass_rate,
        "post_overall_pass_rate": post_overall_pass_rate,
        "baseline_unmet_count": baseline_unmet_count,
        "post_unmet_count": post_unmet_count,
        "effectiveness_delta": effectiveness_delta,
        "auto_applied_count": auto_applied_count,
        "rollback_triggered": "1" if rollback_triggered else "0",
        "rolled_back_count": rolled_back_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    redis_client.xadd(
        _stream_key(tenant_code),
        {k: str(v) for k, v in summary_row.items()},
        maxlen=100000,
        approximate=True,
    )

    send_telegram_message(
        f"[ASSURANCE BREACH] tenant={tenant_code} actions={len(results)} auto_applied={auto_applied_count} effectiveness_delta={effectiveness_delta} rollback={rollback_triggered}"
    )

    return {
        "status": "remediation_planned" if auto_applied_count == 0 else "remediation_applied_or_planned",
        "tenant_id": str(tenant_id),
        "tenant_code": tenant_code,
        "evaluation": evaluation.get("evaluation", {}),
        "policy_pack": policy_pack,
        "effectiveness": summary_row,
        "actions": results,
    }


def approve_assurance_remediation_action(
    tenant_id: UUID,
    tenant_code: str,
    action_id: str,
    approve: bool,
) -> dict[str, Any]:
    _sync_policy_store_client()
    action = get_pending_action(tenant_id, action_id)
    if not action:
        return {"status": "not_found", "action_id": action_id}
    if action.get("status") != "pending_approval":
        return {"status": "invalid_state", "action_id": action_id, "current_status": action.get("status")}

    normalized = dict(action)
    normalized["params"] = _coerce_params(action.get("params", {}))

    if not approve:
        normalized["status"] = "rejected"
        normalized["resolved_at"] = datetime.now(timezone.utc).isoformat()
        save_pending_action(tenant_id, action_id, {k: str(v) for k, v in normalized.items()})
        redis_client.xadd(
            _stream_key(tenant_code),
            {k: str(v) for k, v in normalized.items()},
            maxlen=100000,
            approximate=True,
        )
        return {"status": "rejected", "action": normalized}

    applied = _apply_action(tenant_id, normalized)
    normalized.update(applied)
    normalized["status"] = "applied" if applied.get("status") == "applied" else str(applied.get("status", "unknown"))
    normalized["resolved_at"] = datetime.now(timezone.utc).isoformat()
    save_pending_action(tenant_id, action_id, {k: str(v) for k, v in normalized.items()})
    redis_client.xadd(
        _stream_key(tenant_code),
        {k: str(v) for k, v in normalized.items()},
        maxlen=100000,
        approximate=True,
    )
    return {"status": normalized["status"], "action": normalized}


def assurance_remediation_status(tenant_code: str, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_stream_key(tenant_code), count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"tenant_code": tenant_code, "count": len(rows), "rows": rows}


def assurance_remediation_effectiveness(tenant_code: str, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_stream_key(tenant_code), count=max(1, limit))
    summaries: list[dict[str, Any]] = []

    for event_id, fields in entries:
        if str(fields.get("kind", "")) != "batch_summary":
            continue
        delta = _as_float(fields.get("effectiveness_delta"), 0.0)
        summaries.append(
            {
                "id": event_id,
                "batch_id": fields.get("batch_id", ""),
                "effectiveness_delta": round(delta, 4),
                "baseline_overall_pass_rate": round(_as_float(fields.get("baseline_overall_pass_rate"), 0.0), 4),
                "post_overall_pass_rate": round(_as_float(fields.get("post_overall_pass_rate"), 0.0), 4),
                "rollback_triggered": str(fields.get("rollback_triggered", "0")) == "1",
                "rolled_back_count": int(_as_float(fields.get("rolled_back_count"), 0.0)),
                "timestamp": fields.get("timestamp", ""),
            }
        )

    count = len(summaries)
    improved = len([s for s in summaries if s["effectiveness_delta"] > 0])
    rollback_count = len([s for s in summaries if s["rollback_triggered"]])
    avg_delta = round((sum(s["effectiveness_delta"] for s in summaries) / count) if count else 0.0, 4)

    return {
        "tenant_code": tenant_code,
        "count": count,
        "improved_batches": improved,
        "rollback_batches": rollback_count,
        "average_effectiveness_delta": avg_delta,
        "rows": summaries,
    }
