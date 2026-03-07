from __future__ import annotations

import ast
import json
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.services.audit import CONTROL_PLANE_AUDIT_STREAM
from app.services.enterprise.cost_meter import get_cost
from app.services.enterprise.queueing import queue_partition_stats
from app.services.policy_store import is_approval_mode_enabled, list_pending_actions
from app.services.redis_client import redis_client

SECURITY_STREAM_KEY = "security_events"
ORCHESTRATOR_CYCLE_PREFIX = "orchestrator_cycles"
ORCHESTRATOR_KPI_TREND_PREFIX = "orchestrator_kpi_trend"
PURPLE_REPORT_PREFIX = "purple_reports"
OBJECTIVE_GATE_HISTORY_PREFIX = "objective_gate_history"
OBJECTIVE_GATE_GLOBAL_HISTORY_STREAM = "objective_gate_global_history"


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_latest_purple_report(tenant_id: UUID) -> dict[str, Any]:
    entries = redis_client.xrevrange(f"{PURPLE_REPORT_PREFIX}:{tenant_id}", count=1)
    if not entries:
        return {}

    payload = entries[0][1].get("payload", "")
    if not payload:
        return {}

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return {}


def _read_cycle_results(tenant_id: UUID, limit: int) -> list[dict[str, Any]]:
    entries = redis_client.xrevrange(f"{ORCHESTRATOR_CYCLE_PREFIX}:{tenant_id}", count=max(1, limit))
    rows: list[dict[str, Any]] = []

    for _, fields in entries:
        raw = fields.get("payload", "")
        if not raw:
            continue

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(raw)
            except (ValueError, SyntaxError):
                continue

        if isinstance(parsed, dict):
            rows.append(parsed)

    return rows


def _read_kpi_trend(tenant_id: UUID, limit: int) -> list[dict[str, str]]:
    entries = redis_client.xrevrange(f"{ORCHESTRATOR_KPI_TREND_PREFIX}:{tenant_id}", count=max(1, limit))
    return [fields for _, fields in entries]


def _security_event_counts(tenant_id: UUID, limit: int = 10000) -> dict[str, int]:
    entries = redis_client.xrevrange(SECURITY_STREAM_KEY, count=max(1, limit))
    counts = {"red": 0, "detection": 0, "response": 0}

    for _, fields in entries:
        payload = fields.get("payload", "")
        if not payload:
            continue

        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue

        metadata = event.get("metadata", {})
        if metadata.get("tenant_id") != str(tenant_id):
            continue

        event_type = event.get("event_type")
        if event_type == "red_event":
            counts["red"] += 1
        elif event_type == "detection_event":
            counts["detection"] += 1
        elif event_type == "response_event":
            counts["response"] += 1

    return counts


def _audit_count(tenant_id: UUID, limit: int = 5000) -> int:
    entries = redis_client.xrevrange(CONTROL_PLANE_AUDIT_STREAM, count=max(1, limit))
    tenant_ref = str(tenant_id)
    count = 0

    for _, fields in entries:
        target = fields.get("target", "")
        details = fields.get("details", "{}")
        if tenant_ref in target:
            count += 1
            continue
        if tenant_ref in details:
            count += 1

    return count


def evaluate_objective_gate(
    tenant_id: UUID,
    lookback_cycles: int = 20,
    trend_limit: int = 20,
    min_detection_coverage: float = 0.9,
    min_blocked_before_impact_rate: float = 0.6,
    min_trend_improvement_ratio: float = 0.6,
    max_monthly_cost_usd: float = 50.0,
) -> dict[str, Any]:
    cycles = _read_cycle_results(tenant_id, lookback_cycles)
    latest_report = _read_latest_purple_report(tenant_id)
    trend = _read_kpi_trend(tenant_id, trend_limit)
    security_counts = _security_event_counts(tenant_id)
    audit_count = _audit_count(tenant_id)
    pending_actions = list_pending_actions(tenant_id, limit=200)
    approval_mode = is_approval_mode_enabled(tenant_id)

    # Red gate
    total_cycles = len(cycles)
    completed_cycles = 0
    allowlist_rejections = 0
    execution_ratios: list[float] = []

    for cycle in cycles:
        red = cycle.get("red_result", {})
        status = red.get("status")
        if status == "completed":
            completed_cycles += 1
        if red.get("reason") == "target_not_allowlisted":
            allowlist_rejections += 1

        requested = _as_int(red.get("requested_events"), 0)
        executed = _as_int(red.get("executed_events"), 0)
        if requested > 0:
            execution_ratios.append(executed / requested)

    completion_rate = (completed_cycles / total_cycles) if total_cycles else 0.0
    execution_ratio_avg = (sum(execution_ratios) / len(execution_ratios)) if execution_ratios else 0.0
    red_pass = (
        total_cycles > 0
        and completion_rate >= 0.9
        and execution_ratio_avg >= 0.95
        and allowlist_rejections == 0
    )

    # Blue gate
    kpi = latest_report.get("kpi", {})
    detection_coverage = _as_float(kpi.get("detection_coverage"), 0.0)
    blocked_before_impact = _as_float(kpi.get("blocked_before_impact_rate"), 0.0)
    detected_count = _as_int(kpi.get("detected_count"), 0)
    mitigated_count = _as_int(kpi.get("mitigated_count"), 0)

    blue_pass = (
        detection_coverage >= min_detection_coverage
        and blocked_before_impact >= min_blocked_before_impact_rate
        and (detected_count > 0 or security_counts["detection"] > 0)
        and (mitigated_count > 0 or security_counts["response"] > 0)
    )

    # Purple gate
    recommendation_rows = latest_report.get("table", [])
    tracked_feedback_count = len(pending_actions)
    purple_pass = bool(latest_report) and len(recommendation_rows) > 0 and tracked_feedback_count > 0

    # Closed-loop gate
    improved_flags = [1 for row in trend if str(row.get("improved", "0")) == "1"]
    improvement_ratio = (len(improved_flags) / len(trend)) if trend else 0.0
    closed_loop_pass = len(trend) >= 2 and improvement_ratio >= min_trend_improvement_ratio

    # Enterprise gate
    cost = get_cost(tenant_id)
    cost_usd = _as_float(cost.get("usd"), 0.0)
    try:
        queue_stats = queue_partition_stats()
    except Exception:
        queue_stats = {"total_lag": 0}
    total_lag = _as_int(queue_stats.get("total_lag"), 0)
    throughput_threshold = settings.autoscale_lag_per_worker_threshold * max(1, settings.queue_partitions)
    enterprise_pass = cost_usd <= max_monthly_cost_usd and total_lag <= throughput_threshold

    # Compliance gate
    compliance_pass = audit_count > 0 and allowlist_rejections == 0

    gates = {
        "red": {
            "pass": red_pass,
            "completion_rate": round(completion_rate, 4),
            "execution_ratio_avg": round(execution_ratio_avg, 4),
            "allowlist_rejections": allowlist_rejections,
            "sample_cycles": total_cycles,
        },
        "blue": {
            "pass": blue_pass,
            "detection_coverage": round(detection_coverage, 4),
            "blocked_before_impact_rate": round(blocked_before_impact, 4),
            "detected_count": detected_count,
            "mitigated_count": mitigated_count,
            "security_event_counts": security_counts,
        },
        "purple": {
            "pass": purple_pass,
            "has_report": bool(latest_report),
            "recommendation_count": len(recommendation_rows),
            "feedback_tracked_count": tracked_feedback_count,
        },
        "closed_loop": {
            "pass": closed_loop_pass,
            "trend_samples": len(trend),
            "improvement_ratio": round(improvement_ratio, 4),
        },
        "enterprise": {
            "pass": enterprise_pass,
            "monthly_cost_usd": round(cost_usd, 6),
            "max_monthly_cost_usd": max_monthly_cost_usd,
            "queue_total_lag": total_lag,
            "queue_lag_threshold": throughput_threshold,
        },
        "compliance": {
            "pass": compliance_pass,
            "audit_entries": audit_count,
            "approval_mode": approval_mode,
            "guardrail_violations": allowlist_rejections,
        },
    }

    overall_pass = all(section["pass"] for section in gates.values())

    return {
        "tenant_id": str(tenant_id),
        "overall_pass": overall_pass,
        "thresholds": {
            "min_detection_coverage": min_detection_coverage,
            "min_blocked_before_impact_rate": min_blocked_before_impact_rate,
            "min_trend_improvement_ratio": min_trend_improvement_ratio,
            "max_monthly_cost_usd": max_monthly_cost_usd,
            "lookback_cycles": lookback_cycles,
            "trend_limit": trend_limit,
        },
        "gates": gates,
    }


def _history_key(tenant_id: UUID) -> str:
    return f"{OBJECTIVE_GATE_HISTORY_PREFIX}:{tenant_id}"


def persist_objective_gate_snapshot(tenant_id: UUID, evaluation: dict[str, Any]) -> dict[str, Any]:
    snapshot = {
        "tenant_id": str(tenant_id),
        "overall_pass": "1" if evaluation.get("overall_pass") else "0",
        "gates": json.dumps(evaluation.get("gates", {})),
        "thresholds": json.dumps(evaluation.get("thresholds", {})),
    }
    event_id = redis_client.xadd(
        _history_key(tenant_id),
        snapshot,
        maxlen=50000,
        approximate=True,
    )
    redis_client.xadd(
        OBJECTIVE_GATE_GLOBAL_HISTORY_STREAM,
        snapshot,
        maxlen=500000,
        approximate=True,
    )
    return {"status": "stored", "event_id": event_id}


def evaluate_and_persist_objective_gate(
    tenant_id: UUID,
    lookback_cycles: int = 20,
    trend_limit: int = 20,
    min_detection_coverage: float = 0.9,
    min_blocked_before_impact_rate: float = 0.6,
    min_trend_improvement_ratio: float = 0.6,
    max_monthly_cost_usd: float = 50.0,
) -> dict[str, Any]:
    evaluation = evaluate_objective_gate(
        tenant_id=tenant_id,
        lookback_cycles=lookback_cycles,
        trend_limit=trend_limit,
        min_detection_coverage=min_detection_coverage,
        min_blocked_before_impact_rate=min_blocked_before_impact_rate,
        min_trend_improvement_ratio=min_trend_improvement_ratio,
        max_monthly_cost_usd=max_monthly_cost_usd,
    )
    persist_objective_gate_snapshot(tenant_id, evaluation)
    return evaluation


def list_objective_gate_history(tenant_id: UUID, limit: int = 100) -> list[dict[str, Any]]:
    entries = redis_client.xrevrange(_history_key(tenant_id), count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row: dict[str, Any] = {
            "id": event_id,
            "tenant_id": fields.get("tenant_id", str(tenant_id)),
            "overall_pass": fields.get("overall_pass", "0") == "1",
        }
        gates_raw = fields.get("gates", "{}")
        thresholds_raw = fields.get("thresholds", "{}")
        try:
            row["gates"] = json.loads(gates_raw)
        except json.JSONDecodeError:
            row["gates"] = {}
        try:
            row["thresholds"] = json.loads(thresholds_raw)
        except json.JSONDecodeError:
            row["thresholds"] = {}
        rows.append(row)
    return rows


def objective_gate_remediation_plan(evaluation: dict[str, Any]) -> dict[str, Any]:
    gates = evaluation.get("gates", {})
    actions: list[dict[str, str]] = []

    if not gates.get("red", {}).get("pass", False):
        actions.append(
            {
                "gate": "red",
                "priority": "high",
                "action": "Validate allowlist targets and scenario profile coverage, then rerun at least 3 cycles.",
            }
        )
    if not gates.get("blue", {}).get("pass", False):
        actions.append(
            {
                "gate": "blue",
                "priority": "critical",
                "action": "Tighten failed-login threshold and verify firewall auto-block + notifier delivery on replayed auth burst.",
            }
        )
    if not gates.get("purple", {}).get("pass", False):
        actions.append(
            {
                "gate": "purple",
                "priority": "high",
                "action": "Ensure daily report generation and recommendation tracking state are both present for the tenant.",
            }
        )
    if not gates.get("closed_loop", {}).get("pass", False):
        actions.append(
            {
                "gate": "closed_loop",
                "priority": "high",
                "action": "Run additional orchestrator multi-cycle and confirm KPI trend improved ratio reaches threshold.",
            }
        )
    if not gates.get("enterprise", {}).get("pass", False):
        actions.append(
            {
                "gate": "enterprise",
                "priority": "critical",
                "action": "Reduce queue lag via autoscaler reconcile and lower model spend using SLM-first routing policy.",
            }
        )
    if not gates.get("compliance", {}).get("pass", False):
        actions.append(
            {
                "gate": "compliance",
                "priority": "critical",
                "action": "Enable control-plane audit trail coverage for all admin actions and re-run gate snapshot.",
            }
        )

    return {
        "overall_pass": bool(evaluation.get("overall_pass", False)),
        "failed_gate_count": len(actions),
        "actions": actions,
    }


def objective_gate_blockers(evaluation: dict[str, Any]) -> dict[str, Any]:
    gates = evaluation.get("gates", {})
    blockers: list[dict[str, str]] = []

    for gate_name, gate_state in gates.items():
        if gate_state.get("pass", False):
            continue

        reason = "threshold_not_met"
        if gate_name == "red":
            reason = "simulation_coverage_or_safety_failed"
        elif gate_name == "blue":
            reason = "detect_or_mitigate_below_threshold"
        elif gate_name == "purple":
            reason = "report_or_feedback_tracking_missing"
        elif gate_name == "closed_loop":
            reason = "kpi_improvement_ratio_insufficient"
        elif gate_name == "enterprise":
            reason = "queue_lag_or_cost_exceeds_policy"
        elif gate_name == "compliance":
            reason = "auditability_or_guardrail_check_failed"

        blockers.append({"gate": gate_name, "reason": reason})

    return {
        "overall_pass": bool(evaluation.get("overall_pass", False)),
        "blocker_count": len(blockers),
        "blockers": blockers,
    }


def objective_gate_dashboard(limit: int = 100) -> dict[str, Any]:
    keys = redis_client.keys(f"{OBJECTIVE_GATE_HISTORY_PREFIX}:*")
    rows: list[dict[str, Any]] = []

    for key in keys[: max(1, limit)]:
        tenant_id = key.split(":", 1)[-1]
        try:
            entries = redis_client.xrevrange(key, count=1)
        except Exception:
            continue
        if not entries:
            continue

        latest = entries[0][1]
        gates_raw = latest.get("gates", "{}")
        try:
            gates = json.loads(gates_raw)
        except json.JSONDecodeError:
            gates = {}

        pass_value = latest.get("overall_pass", "0") == "1"
        blockers = objective_gate_blockers({"overall_pass": pass_value, "gates": gates})
        rows.append(
            {
                "tenant_id": tenant_id,
                "overall_pass": pass_value,
                "failed_gate_count": blockers["blocker_count"],
                "blockers": blockers["blockers"],
            }
        )

    if not rows:
        global_entries = redis_client.xrevrange(OBJECTIVE_GATE_GLOBAL_HISTORY_STREAM, count=max(1, limit * 20))
        latest_by_tenant: dict[str, dict[str, Any]] = {}
        for _, fields in global_entries:
            tenant_id = str(fields.get("tenant_id", ""))
            if not tenant_id or tenant_id in latest_by_tenant:
                continue
            latest_by_tenant[tenant_id] = fields
            if len(latest_by_tenant) >= max(1, limit):
                break

        for tenant_id, latest in latest_by_tenant.items():
            gates_raw = latest.get("gates", "{}")
            try:
                gates = json.loads(gates_raw)
            except json.JSONDecodeError:
                gates = {}

            pass_value = latest.get("overall_pass", "0") == "1"
            blockers = objective_gate_blockers({"overall_pass": pass_value, "gates": gates})
            rows.append(
                {
                    "tenant_id": tenant_id,
                    "overall_pass": pass_value,
                    "failed_gate_count": blockers["blocker_count"],
                    "blockers": blockers["blockers"],
                }
            )

    rows.sort(key=lambda item: (item["overall_pass"], item["failed_gate_count"]))
    passing = len([r for r in rows if r["overall_pass"]])

    return {
        "total_tenants": len(rows),
        "passing_tenants": passing,
        "failing_tenants": len(rows) - passing,
        "rows": rows,
    }
