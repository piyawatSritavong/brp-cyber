from __future__ import annotations

from uuid import uuid4

from app.services import orchestrator, policy_store
from schemas.orchestration import OrchestrationCycleRequest, OrchestrationMultiCycleRequest


class FakeRedis:
    def __init__(self) -> None:
        self.strings: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self._counter = 0

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.strings[key] = value
        return True

    def exists(self, key: str) -> int:
        return 1 if key in self.strings else 0

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(key, {}).update(mapping)
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def hincrby(self, key: str, field: str, amount: int) -> int:
        bucket = self.hashes.setdefault(key, {})
        current = int(bucket.get(field, "0"))
        updated = current + amount
        bucket[field] = str(updated)
        return updated

    def hincrbyfloat(self, key: str, field: str, amount: float) -> float:
        bucket = self.hashes.setdefault(key, {})
        current = float(bucket.get(field, "0"))
        updated = current + amount
        bucket[field] = str(updated)
        return updated

    def keys(self, pattern: str):
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self.hashes.keys() if k.startswith(prefix)]
        return [k for k in self.hashes.keys() if k == pattern]

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self._counter += 1
        event_id = f"{self._counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]

    def xrange(self, key: str, count: int = 100):
        return list(self.streams.get(key, []))[:count]


def _setup(fake_redis: FakeRedis) -> None:
    policy_store.redis_client = fake_redis
    orchestrator.redis_client = fake_redis
    orchestrator.send_telegram_message = lambda message: True
    orchestrator.evaluate_and_persist_objective_gate = lambda tenant_id: {
        "overall_pass": True,
        "gates": {"red": {"pass": True}, "blue": {"pass": True}, "purple": {"pass": True}},
    }

    orchestrator.run_simulation = lambda request: {
        "status": "completed",
        "scenario_name": request.scenario_name,
        "executed_events": request.events_count,
    }


def test_orchestration_cycle_with_feedback() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    report_counter = {"count": 0}

    def _fake_report(tenant_id, limit=5000):
        report_counter["count"] += 1
        return {
            "report_id": f"r-{report_counter['count']}",
            "summary": "Detection coverage=80%",
            "kpi": {
                "mttd_seconds": 20,
                "mttr_seconds": 150,
                "detection_coverage": 0.8,
                "blocked_before_impact_rate": 0.5,
                "mitigated_count": 4,
                "detected_count": 8,
                "attack_count": 10,
            },
        }

    orchestrator.generate_daily_report = _fake_report

    tenant_id = uuid4()
    payload = OrchestrationCycleRequest(
        tenant_id=tenant_id,
        target_asset="acb.example.com/admin-login",
        red_scenario_name="credential_stuffing_sim",
        red_events_count=30,
        strategy_profile="balanced",
    )

    result = orchestrator.run_orchestration_cycle(payload)

    assert result["red_result"]["status"] == "completed"
    assert result["purple_report"]["report_id"] == "r-1"
    assert result["feedback_result"]["status"] == "applied"

    state = orchestrator.get_tenant_orchestration_state(tenant_id)
    assert state["strategy_profile"] == "balanced"
    assert state["blue_policy"]["failed_login_threshold_per_minute"] == 9


def test_orchestration_cycle_applies_cost_throttle_override() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    orchestrator.generate_daily_report = lambda tenant_id, limit=5000: {
        "report_id": "r-throttle",
        "summary": "throttle test",
        "kpi": {
            "mttd_seconds": 20,
            "mttr_seconds": 120,
            "detection_coverage": 0.9,
            "blocked_before_impact_rate": 0.6,
            "mitigated_count": 5,
            "detected_count": 8,
            "attack_count": 10,
        },
    }

    orig_eval = orchestrator.evaluate_orchestration_cost_guardrail
    orig_get_mode = orchestrator.get_orchestration_cost_throttle_override_mode
    try:
        orchestrator.evaluate_orchestration_cost_guardrail = lambda tenant_id, tenant_code, apply_actions=True: {
            "status": "ok",
            "state": {"severity": "high", "throttle_override": "conservative"},
            "metrics": {"pressure_ratio": 1.2},
            "actions": [{"action": "set_throttle_override", "value": "conservative"}],
        }
        orchestrator.get_orchestration_cost_throttle_override_mode = lambda tenant_id: "conservative"

        tenant_id = uuid4()
        cycle = orchestrator.run_orchestration_cycle(
            OrchestrationCycleRequest(
                tenant_id=tenant_id,
                target_asset="acb.example.com/admin-login",
                red_events_count=40,
                strategy_profile="balanced",
            )
        )
        assert cycle["throttle"]["mode"] == "conservative"
        assert cycle["throttle"]["requested_red_events_count"] == 40
        assert cycle["throttle"]["effective_red_events_count"] == 20
        assert cycle["red_result"]["executed_events"] == 20
        assert cycle["model_routing"]["red"]["estimated_tokens"] == 400
    finally:
        orchestrator.evaluate_orchestration_cost_guardrail = orig_eval
        orchestrator.get_orchestration_cost_throttle_override_mode = orig_get_mode


def test_approval_mode_and_manual_approve() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    orchestrator.generate_daily_report = lambda tenant_id, limit=5000: {
        "report_id": "r-approval",
        "summary": "Need stricter threshold",
        "kpi": {
            "mttd_seconds": 30,
            "mttr_seconds": 180,
            "detection_coverage": 0.6,
            "blocked_before_impact_rate": 0.2,
            "mitigated_count": 2,
            "detected_count": 6,
            "attack_count": 10,
        },
    }

    tenant_id = uuid4()
    orchestrator.set_tenant_approval_mode(tenant_id, True)

    cycle = orchestrator.run_orchestration_cycle(
        OrchestrationCycleRequest(
            tenant_id=tenant_id,
            target_asset="acb.example.com/admin-login",
            strategy_profile="balanced",
        )
    )
    assert cycle["feedback_result"]["status"] == "pending_approval"
    action_id = cycle["feedback_result"]["action"]["action_id"]

    approved = orchestrator.approve_pending_action(tenant_id, action_id, True)
    assert approved["status"] == "applied"
    state = orchestrator.get_tenant_orchestration_state(tenant_id)
    assert state["blue_policy"]["failed_login_threshold_per_minute"] == 9


def test_multi_cycle_and_kpi_trend() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    kpis = [0.7, 0.75, 0.74, 0.8]

    def _fake_report(tenant_id, limit=5000):
        coverage = kpis.pop(0)
        return {
            "report_id": f"r-{coverage}",
            "summary": "trend",
            "kpi": {
                "mttd_seconds": 25,
                "mttr_seconds": 90,
                "detection_coverage": coverage,
                "blocked_before_impact_rate": 0.6,
                "mitigated_count": 5,
                "detected_count": 8,
                "attack_count": 10,
            },
        }

    orchestrator.generate_daily_report = _fake_report

    tenant_id = uuid4()
    result = orchestrator.run_multi_cycle(
        OrchestrationMultiCycleRequest(
            tenant_id=tenant_id,
            target_asset="acb.example.com/admin-login",
            strategy_profile="balanced",
            cycles=4,
            stop_on_no_improvement=True,
        )
    )

    assert result["executed_cycles"] == 3
    trend = orchestrator.get_kpi_trend(tenant_id, limit=10)
    assert len(trend) == 3


def test_one_click_activation_and_scheduler_tick() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    orchestrator.generate_daily_report = lambda tenant_id, limit=5000: {
        "report_id": "r-activation",
        "summary": "auto cycle",
        "kpi": {
            "mttd_seconds": 15,
            "mttr_seconds": 80,
            "detection_coverage": 0.92,
            "blocked_before_impact_rate": 0.7,
            "mitigated_count": 6,
            "detected_count": 8,
            "attack_count": 10,
        },
    }

    tenant_id = uuid4()
    activated = orchestrator.activate_tenant_orchestration(
        tenant_id=tenant_id,
        target_asset="acb.example.com/admin-login",
        red_scenario_name="credential_stuffing_sim",
        red_events_count=20,
        strategy_profile="balanced",
        cycle_interval_seconds=60,
        approval_mode=False,
    )
    assert activated["status"] == "active"

    tick = orchestrator.run_activation_scheduler_tick(limit=50)
    assert tick["executed_count"] == 1

    state = orchestrator.get_tenant_activation_state(tenant_id)
    assert state["run_count"] == 1
    assert state["last_cycle_index"] == 1
    assert state["last_status"] != ""

    paused = orchestrator.pause_tenant_orchestration(tenant_id)
    assert paused["status"] == "paused"

    tick_after_pause = orchestrator.run_activation_scheduler_tick(limit=50)
    assert tick_after_pause["executed_count"] == 0

    deactivated = orchestrator.deactivate_tenant_orchestration(tenant_id)
    assert deactivated["status"] == "inactive"


def test_pilot_activation_requires_objective_gate_unless_forced() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_id = uuid4()
    orchestrator.evaluate_and_persist_objective_gate = lambda tenant_id: {
        "overall_pass": False,
        "gates": {"blue": {"pass": False}},
    }

    blocked = orchestrator.activate_pilot_session(
        tenant_id=tenant_id,
        target_asset="acb.example.com/admin-login",
        require_objective_gate_pass=True,
        force=False,
    )
    assert blocked["status"] == "blocked_by_objective_gate"

    forced = orchestrator.activate_pilot_session(
        tenant_id=tenant_id,
        target_asset="acb.example.com/admin-login",
        require_objective_gate_pass=True,
        force=True,
    )
    assert forced["status"] == "pilot_running"
    assert forced["objective_gate"]["overall_pass"] is False


def test_pilot_status_and_deactivate() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    orchestrator.generate_daily_report = lambda tenant_id, limit=5000: {
        "report_id": "r-pilot",
        "summary": "pilot cycle",
        "kpi": {
            "mttd_seconds": 10,
            "mttr_seconds": 60,
            "detection_coverage": 0.95,
            "blocked_before_impact_rate": 0.75,
            "mitigated_count": 7,
            "detected_count": 8,
            "attack_count": 10,
        },
    }
    orchestrator.evaluate_and_persist_objective_gate = lambda tenant_id: {
        "overall_pass": True,
        "gates": {"red": {"pass": True}, "blue": {"pass": True}},
    }

    tenant_id = uuid4()
    started = orchestrator.activate_pilot_session(
        tenant_id=tenant_id,
        target_asset="acb.example.com/admin-login",
        require_objective_gate_pass=True,
    )
    assert started["status"] == "pilot_running"

    _ = orchestrator.run_activation_scheduler_tick(limit=50)
    status = orchestrator.get_pilot_session_status(tenant_id)
    assert status["pilot"]["status"] == "running"
    assert status["activation"]["status"] == "active"

    sessions = orchestrator.list_pilot_sessions(limit=20)
    assert sessions["count"] >= 1
    assert sessions["running"] >= 1

    stopped = orchestrator.deactivate_pilot_session(tenant_id, reason="uat_done")
    assert stopped["status"] == "pilot_stopped"

    status_after = orchestrator.get_pilot_session_status(tenant_id)
    assert status_after["pilot"]["status"] == "stopped"


def test_scheduler_auto_stop_after_consecutive_failures() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_id = uuid4()
    _ = orchestrator.activate_pilot_session(
        tenant_id=tenant_id,
        target_asset="acb.example.com/admin-login",
        require_objective_gate_pass=True,
    )
    _ = orchestrator.upsert_tenant_safety_policy(
        tenant_id=tenant_id,
        max_consecutive_failures=2,
        auto_stop_on_consecutive_failures=True,
        notify_on_auto_stop=True,
    )
    fake_redis.hashes[orchestrator._activation_key(tenant_id)]["next_run_epoch"] = "1"

    original_cycle = orchestrator.run_orchestration_cycle
    orchestrator.run_orchestration_cycle = lambda request, cycle_index=1: (_ for _ in ()).throw(RuntimeError("boom"))
    try:
        tick_1 = orchestrator.run_activation_scheduler_tick(limit=50, now_epoch=1)
        assert tick_1["executed_count"] == 1

        state_after_1 = orchestrator.get_tenant_activation_state(tenant_id)
        assert state_after_1["status"] == "active"
        assert state_after_1["consecutive_failures"] == 1

        state_key = orchestrator._activation_key(tenant_id)
        fake_redis.hashes[state_key]["next_run_epoch"] = "1"
        tick_2 = orchestrator.run_activation_scheduler_tick(limit=50, now_epoch=1)
        assert tick_2["executed_count"] == 1
        assert tick_2["executed"][0]["result_status"] == "auto_stopped"

        stopped = orchestrator.get_pilot_session_status(tenant_id)
        assert stopped["activation"]["status"] == "paused"
        assert stopped["pilot"]["status"] == "stopped"

        incidents = orchestrator.pilot_incidents(tenant_id, limit=20)
        assert incidents["count"] >= 2
        assert any(row.get("incident_type") == "pilot_auto_stop" for row in incidents["rows"])
    finally:
        orchestrator.run_orchestration_cycle = original_cycle


def test_objective_gate_tick_auto_stop_when_enabled() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_id = uuid4()
    _ = orchestrator.activate_pilot_session(
        tenant_id=tenant_id,
        target_asset="acb.example.com/admin-login",
        require_objective_gate_pass=False,
    )
    _ = orchestrator.upsert_tenant_safety_policy(
        tenant_id=tenant_id,
        objective_gate_check_each_tick=True,
        auto_stop_on_objective_gate_fail=True,
    )
    fake_redis.hashes[orchestrator._activation_key(tenant_id)]["next_run_epoch"] = "1"
    orchestrator.evaluate_and_persist_objective_gate = lambda tenant_id: {
        "overall_pass": False,
        "gates": {"blue": {"pass": False}},
    }

    tick = orchestrator.run_activation_scheduler_tick(limit=20, now_epoch=1)
    assert tick["executed_count"] == 1
    assert tick["executed"][0]["result_status"] == "auto_stopped"

    status = orchestrator.get_pilot_session_status(tenant_id)
    assert status["activation"]["status"] == "paused"
    assert status["pilot"]["status"] == "stopped"


def test_scheduler_global_execution_cap() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_ids = [uuid4(), uuid4(), uuid4()]
    for tenant_id in tenant_ids:
        _ = orchestrator.activate_tenant_orchestration(
            tenant_id=tenant_id,
            target_asset="acb.example.com/admin-login",
            red_events_count=10,
            cycle_interval_seconds=60,
        )
        fake_redis.hashes[orchestrator._activation_key(tenant_id)]["next_run_epoch"] = "1"

    original_cap = orchestrator.settings.orchestrator_scheduler_max_executions_per_tick
    orchestrator.settings.orchestrator_scheduler_max_executions_per_tick = 1
    try:
        tick = orchestrator.run_activation_scheduler_tick(limit=20, now_epoch=1)
        assert tick["executed_count"] == 1
        assert tick["max_executions_per_tick"] == 1
        assert len([row for row in tick["skipped"] if row["reason"] == "global_tick_execution_cap"]) >= 2
    finally:
        orchestrator.settings.orchestrator_scheduler_max_executions_per_tick = original_cap


def test_rate_budget_auto_pause_and_usage_tracking() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_id = uuid4()
    _ = orchestrator.activate_pilot_session(
        tenant_id=tenant_id,
        target_asset="acb.example.com/admin-login",
        red_events_count=40,
        require_objective_gate_pass=False,
    )
    _ = orchestrator.upsert_tenant_rate_budget(
        tenant_id=tenant_id,
        max_cycles_per_hour=5,
        max_red_events_per_hour=30,
        enforce_rate_budget=True,
        auto_pause_on_budget_exceeded=True,
        notify_on_budget_exceeded=True,
    )
    fake_redis.hashes[orchestrator._activation_key(tenant_id)]["next_run_epoch"] = "1"

    tick = orchestrator.run_activation_scheduler_tick(limit=20, now_epoch=1)
    assert tick["executed_count"] == 1
    assert tick["executed"][0]["result_status"] == "auto_stopped"

    status = orchestrator.get_pilot_session_status(tenant_id)
    assert status["activation"]["status"] == "paused"
    assert status["pilot"]["status"] == "stopped"

    incidents = orchestrator.pilot_incidents(tenant_id, limit=10)
    assert any(row.get("incident_type") == "rate_budget_exceeded" for row in incidents["rows"])
    usage = orchestrator.get_tenant_rate_budget_usage(tenant_id, hour_epoch=1)
    assert usage["cycles_used"] == 0
    assert usage["red_events_used"] == 0


def test_rate_budget_usage_increments_when_within_limit() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_id = uuid4()
    _ = orchestrator.activate_tenant_orchestration(
        tenant_id=tenant_id,
        target_asset="acb.example.com/admin-login",
        red_events_count=10,
        cycle_interval_seconds=60,
    )
    _ = orchestrator.upsert_tenant_rate_budget(
        tenant_id=tenant_id,
        max_cycles_per_hour=2,
        max_red_events_per_hour=25,
        enforce_rate_budget=True,
        auto_pause_on_budget_exceeded=False,
    )
    fake_redis.hashes[orchestrator._activation_key(tenant_id)]["next_run_epoch"] = "1"

    tick_1 = orchestrator.run_activation_scheduler_tick(limit=20, now_epoch=1)
    assert tick_1["executed_count"] == 1

    fake_redis.hashes[orchestrator._activation_key(tenant_id)]["next_run_epoch"] = "1"
    tick_2 = orchestrator.run_activation_scheduler_tick(limit=20, now_epoch=1)
    assert tick_2["executed_count"] == 1

    usage = orchestrator.get_tenant_rate_budget_usage(tenant_id, hour_epoch=1)
    assert usage["cycles_used"] == 2
    assert usage["red_events_used"] == 20


def test_scheduler_priority_tier_preferred_under_execution_cap() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    critical_tenant = uuid4()
    low_tenant = uuid4()
    for tenant_id in [critical_tenant, low_tenant]:
        _ = orchestrator.activate_tenant_orchestration(
            tenant_id=tenant_id,
            target_asset="acb.example.com/admin-login",
            red_events_count=10,
            cycle_interval_seconds=60,
        )
        fake_redis.hashes[orchestrator._activation_key(tenant_id)]["next_run_epoch"] = "1"

    _ = orchestrator.upsert_tenant_scheduler_profile(critical_tenant, priority_tier="critical")
    _ = orchestrator.upsert_tenant_scheduler_profile(low_tenant, priority_tier="low")

    original_cap = orchestrator.settings.orchestrator_scheduler_max_executions_per_tick
    orchestrator.settings.orchestrator_scheduler_max_executions_per_tick = 1
    try:
        tick = orchestrator.run_activation_scheduler_tick(limit=20, now_epoch=1)
        assert tick["executed_count"] == 1
        assert tick["executed"][0]["tenant_id"] == str(critical_tenant)
        low_state = orchestrator.get_tenant_activation_state(low_tenant)
        assert low_state["scheduler_skip_streak"] == 1
    finally:
        orchestrator.settings.orchestrator_scheduler_max_executions_per_tick = original_cap


def test_scheduler_backpressure_boost_reduces_starvation() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    critical_tenant = uuid4()
    low_tenant = uuid4()
    for tenant_id in [critical_tenant, low_tenant]:
        _ = orchestrator.activate_tenant_orchestration(
            tenant_id=tenant_id,
            target_asset="acb.example.com/admin-login",
            red_events_count=10,
            cycle_interval_seconds=60,
        )
    _ = orchestrator.upsert_tenant_scheduler_profile(critical_tenant, priority_tier="critical")
    _ = orchestrator.upsert_tenant_scheduler_profile(low_tenant, priority_tier="low", starvation_incident_threshold=2)

    original_cap = orchestrator.settings.orchestrator_scheduler_max_executions_per_tick
    orchestrator.settings.orchestrator_scheduler_max_executions_per_tick = 1
    try:
        executed_low = False
        for _ in range(6):
            fake_redis.hashes[orchestrator._activation_key(critical_tenant)]["next_run_epoch"] = "1"
            fake_redis.hashes[orchestrator._activation_key(low_tenant)]["next_run_epoch"] = "1"
            tick = orchestrator.run_activation_scheduler_tick(limit=20, now_epoch=1)
            if tick["executed_count"] == 1 and tick["executed"][0]["tenant_id"] == str(low_tenant):
                executed_low = True
                break
        assert executed_low is True

        incidents = orchestrator.pilot_incidents(low_tenant, limit=20)
        assert any(row.get("incident_type") == "scheduler_backpressure" for row in incidents["rows"])
    finally:
        orchestrator.settings.orchestrator_scheduler_max_executions_per_tick = original_cap


def test_rollout_hold_defers_execution() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_id = uuid4()
    _ = orchestrator.activate_tenant_orchestration(
        tenant_id=tenant_id,
        target_asset="acb.example.com/admin-login",
        red_events_count=10,
        cycle_interval_seconds=60,
    )
    _ = orchestrator.upsert_tenant_rollout_profile(tenant_id, rollout_stage="beta", hold=True)
    fake_redis.hashes[orchestrator._activation_key(tenant_id)]["next_run_epoch"] = "1"

    tick = orchestrator.run_activation_scheduler_tick(limit=20, now_epoch=1)
    assert tick["executed_count"] == 0
    assert any(row["reason"] == "rollout_hold" for row in tick["skipped"])

    incidents = orchestrator.pilot_incidents(tenant_id, limit=10)
    assert any(row.get("incident_type") == "rollout_hold" for row in incidents["rows"])


def test_rollout_canary_deferred_then_runs() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_id = uuid4()
    _ = orchestrator.activate_tenant_orchestration(
        tenant_id=tenant_id,
        target_asset="acb.example.com/admin-login",
        red_events_count=10,
        cycle_interval_seconds=60,
    )
    _ = orchestrator.upsert_tenant_rollout_profile(tenant_id, rollout_stage="beta", canary_percent=10, hold=False)

    original_slot = orchestrator._rollout_slot
    try:
        orchestrator._rollout_slot = lambda tenant_id, current_epoch, cycle_index: 99
        fake_redis.hashes[orchestrator._activation_key(tenant_id)]["next_run_epoch"] = "1"
        tick_deferred = orchestrator.run_activation_scheduler_tick(limit=20, now_epoch=1)
        assert tick_deferred["executed_count"] == 0
        assert any(row["reason"] == "rollout_canary_deferred" for row in tick_deferred["skipped"])

        orchestrator._rollout_slot = lambda tenant_id, current_epoch, cycle_index: 1
        fake_redis.hashes[orchestrator._activation_key(tenant_id)]["next_run_epoch"] = "1"
        tick_run = orchestrator.run_activation_scheduler_tick(limit=20, now_epoch=1)
        assert tick_run["executed_count"] == 1
    finally:
        orchestrator._rollout_slot = original_slot


def test_rollout_posture_auto_promotes_when_kpi_is_stable() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_id = uuid4()
    _ = orchestrator.upsert_tenant_rollout_profile(tenant_id, rollout_stage="alpha", canary_percent=40, hold=True)
    orchestrator._record_kpi_trend(tenant_id, 1, {"detection_coverage": 0.97, "mttd_seconds": 10, "mttr_seconds": 20}, True)
    orchestrator._record_kpi_trend(tenant_id, 2, {"detection_coverage": 0.98, "mttd_seconds": 10, "mttr_seconds": 20}, True)
    orchestrator._record_kpi_trend(tenant_id, 3, {"detection_coverage": 0.96, "mttd_seconds": 10, "mttr_seconds": 20}, True)

    decision_1 = orchestrator.evaluate_tenant_rollout_posture(tenant_id, apply=True)
    assert decision_1["action"] == "pending_promote"
    assert decision_1["applied"] is False

    decision_2 = orchestrator.evaluate_tenant_rollout_posture(tenant_id, apply=True)
    assert decision_2["action"] == "promote"
    assert decision_2["applied"] is True

    profile = orchestrator.get_tenant_rollout_profile(tenant_id)["profile"]
    assert profile["rollout_stage"] == "beta"
    assert profile["canary_percent"] == 60
    assert profile["hold"] is False


def test_rollout_posture_demotes_when_high_incident_exists() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_id = uuid4()
    _ = orchestrator.upsert_tenant_rollout_profile(tenant_id, rollout_stage="ga", canary_percent=90, hold=False)
    orchestrator._record_kpi_trend(tenant_id, 1, {"detection_coverage": 0.99, "mttd_seconds": 10, "mttr_seconds": 20}, True)
    _ = orchestrator._emit_pilot_incident(
        tenant_id,
        incident_type="pilot_auto_stop",
        severity="high",
        reason="safety_guardrail_triggered",
    )

    decision = orchestrator.evaluate_tenant_rollout_posture(tenant_id, apply=True)
    assert decision["action"] == "pending_approval"
    assert decision["applied"] is False

    pending_id = decision["pending_decision_id"]
    assert pending_id != ""
    approved = orchestrator.approve_pending_rollout_decision(tenant_id, pending_id, approve=True, reviewer="tester")
    assert approved["status"] == "approved_applied"

    profile = orchestrator.get_tenant_rollout_profile(tenant_id)["profile"]
    assert profile["rollout_stage"] == "beta"
    assert profile["hold"] is True

    history = orchestrator.rollout_decision_history(tenant_id, limit=10)
    assert history["count"] >= 1


def test_rollout_posture_cooldown_blocks_immediate_reversal() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_id = uuid4()
    _ = orchestrator.upsert_tenant_rollout_profile(tenant_id, rollout_stage="alpha", canary_percent=50, hold=False)
    orchestrator._record_kpi_trend(tenant_id, 1, {"detection_coverage": 0.97, "mttd_seconds": 10, "mttr_seconds": 20}, True)
    orchestrator._record_kpi_trend(tenant_id, 2, {"detection_coverage": 0.98, "mttd_seconds": 10, "mttr_seconds": 20}, True)
    orchestrator._record_kpi_trend(tenant_id, 3, {"detection_coverage": 0.99, "mttd_seconds": 10, "mttr_seconds": 20}, True)

    _ = orchestrator.evaluate_tenant_rollout_posture(tenant_id, apply=True)
    promoted = orchestrator.evaluate_tenant_rollout_posture(tenant_id, apply=True)
    assert promoted["action"] == "promote"
    assert promoted["applied"] is True

    _ = orchestrator._emit_pilot_incident(
        tenant_id,
        incident_type="pilot_auto_stop",
        severity="high",
        reason="post_promote_issue",
    )
    blocked = orchestrator.evaluate_tenant_rollout_posture(tenant_id, apply=True)
    assert blocked["action"] == "cooldown_blocked"
    assert blocked["applied"] is False
    assert blocked["cooldown_active"] is True


def test_rollout_policy_can_block_auto_promote() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_id = uuid4()
    _ = orchestrator.upsert_tenant_rollout_profile(tenant_id, rollout_stage="alpha", canary_percent=30, hold=False)
    _ = orchestrator.upsert_tenant_rollout_policy(
        tenant_id,
        auto_promote_enabled=False,
        auto_demote_enabled=True,
        require_approval_for_promote=False,
        require_approval_for_demote=True,
    )
    orchestrator._record_kpi_trend(tenant_id, 1, {"detection_coverage": 0.98, "mttd_seconds": 10, "mttr_seconds": 20}, True)
    orchestrator._record_kpi_trend(tenant_id, 2, {"detection_coverage": 0.99, "mttd_seconds": 10, "mttr_seconds": 20}, True)
    orchestrator._record_kpi_trend(tenant_id, 3, {"detection_coverage": 0.97, "mttd_seconds": 10, "mttr_seconds": 20}, True)

    _ = orchestrator.evaluate_tenant_rollout_posture(tenant_id, apply=True)
    decision = orchestrator.evaluate_tenant_rollout_posture(tenant_id, apply=True)
    assert decision["action"] == "blocked_by_policy"
    assert decision["reason"] == "auto_promote_disabled"

    profile = orchestrator.get_tenant_rollout_profile(tenant_id)["profile"]
    assert profile["rollout_stage"] == "alpha"


def test_rollout_dual_control_requires_two_reviewers() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_id = uuid4()
    _ = orchestrator.upsert_tenant_rollout_profile(tenant_id, rollout_stage="ga", canary_percent=80, hold=False)
    _ = orchestrator.upsert_tenant_rollout_policy(
        tenant_id,
        auto_promote_enabled=True,
        auto_demote_enabled=True,
        require_approval_for_demote=True,
        require_dual_control_for_demote=True,
    )
    _ = orchestrator._emit_pilot_incident(
        tenant_id,
        incident_type="pilot_auto_stop",
        severity="high",
        reason="trigger_demote",
    )

    decision = orchestrator.evaluate_tenant_rollout_posture(tenant_id, apply=True)
    assert decision["action"] == "pending_approval"
    pending_id = decision["pending_decision_id"]
    assert pending_id != ""

    first = orchestrator.approve_pending_rollout_decision(tenant_id, pending_id, approve=True, reviewer="alice")
    assert first["status"] == "pending_secondary_approval"
    assert first["approvals_required"] == 2

    dup = orchestrator.approve_pending_rollout_decision(tenant_id, pending_id, approve=True, reviewer="alice")
    assert dup["status"] == "duplicate_reviewer"

    second = orchestrator.approve_pending_rollout_decision(tenant_id, pending_id, approve=True, reviewer="bob")
    assert second["status"] == "approved_applied"
    assert second["approvals_required"] == 2
    assert second["approvals_received"] == 2

    profile = orchestrator.get_tenant_rollout_profile(tenant_id)["profile"]
    assert profile["rollout_stage"] == "beta"
    evidence = orchestrator.rollout_evidence_history(tenant_id, limit=20)
    assert evidence["count"] >= 2
    assert all("signature" in row for row in evidence["rows"])
    verify = orchestrator.verify_rollout_evidence_chain(tenant_id, limit=100)
    assert verify["valid"] is True


def test_export_rollout_evidence_bundle_with_notarization() -> None:
    fake_redis = FakeRedis()
    _setup(fake_redis)

    tenant_id = uuid4()
    _ = orchestrator._append_rollout_evidence(
        tenant_id,
        {
            "decision_id": "d1",
            "event_type": "rollout_decision_auto_applied",
            "action": "promote",
        },
    )
    original_notarize = orchestrator.notarize_payload
    orchestrator.notarize_payload = lambda payload: {
        "status": "notarized",
        "provider": "local_digest",
        "receipt_id": "receipt-1",
    }
    try:
        exported = orchestrator.export_rollout_evidence_bundle(
            tenant_id=tenant_id,
            destination_dir="./tmp/test_rollout_evidence_bundle",
            limit=50,
            notarize=True,
        )
        assert exported["status"] == "exported"
        assert exported["verify"]["valid"] is True
        assert exported["notarization"]["status"] == "notarized"

        status = orchestrator.rollout_evidence_bundle_status(tenant_id, limit=10)
        assert status["count"] >= 1
        assert status["rows"][0]["notarized"] == "1"
    finally:
        orchestrator.notarize_payload = original_notarize
