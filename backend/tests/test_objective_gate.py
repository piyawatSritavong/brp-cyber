from __future__ import annotations

import json
from uuid import uuid4

from app.services import audit, policy_store
from app.services.enterprise import cost_meter, objective_gate, queueing


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.strings: dict[str, str] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self._counter = 0

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(key, {}).update(mapping)
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def hincrby(self, key: str, field: str, amount: int) -> int:
        bucket = self.hashes.setdefault(key, {})
        value = int(bucket.get(field, "0")) + amount
        bucket[field] = str(value)
        return value

    def hincrbyfloat(self, key: str, field: str, amount: float) -> float:
        bucket = self.hashes.setdefault(key, {})
        value = float(bucket.get(field, "0")) + amount
        bucket[field] = str(value)
        return value

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.strings[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

    def keys(self, pattern: str):
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self.hashes if k.startswith(prefix)]
        return [k for k in self.hashes if k == pattern]

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self._counter += 1
        event_id = f"{self._counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]

    def xinfo_stream(self, key: str) -> dict[str, int]:
        return {"length": len(self.streams.get(key, []))}

    def xinfo_groups(self, key: str):
        return [{"name": "scan-workers", "lag": 0}]


def _setup(fake: FakeRedis) -> None:
    objective_gate.redis_client = fake
    cost_meter.redis_client = fake
    policy_store.redis_client = fake
    queueing.redis_client = fake
    audit.redis_client = fake


def test_objective_gate_pass() -> None:
    fake = FakeRedis()
    _setup(fake)

    tenant_id = uuid4()

    # Red/Orchestration evidence
    cycle_payload = {
        "red_result": {
            "status": "completed",
            "requested_events": 20,
            "executed_events": 20,
        }
    }
    for _ in range(3):
        fake.xadd(f"orchestrator_cycles:{tenant_id}", {"payload": str(cycle_payload)})

    # Purple report evidence
    fake.xadd(
        f"purple_reports:{tenant_id}",
        {
            "report_id": "r-1",
            "payload": json.dumps(
                {
                    "kpi": {
                        "detection_coverage": 0.96,
                        "blocked_before_impact_rate": 0.8,
                        "detected_count": 10,
                        "mitigated_count": 8,
                    },
                    "table": [{"attack_type": "credential_stuffing_sim", "recommendation": "keep"}],
                }
            ),
        },
    )

    # KPI trend evidence
    fake.xadd(f"orchestrator_kpi_trend:{tenant_id}", {"improved": "1"})
    fake.xadd(f"orchestrator_kpi_trend:{tenant_id}", {"improved": "1"})
    fake.xadd(f"orchestrator_kpi_trend:{tenant_id}", {"improved": "0"})

    # Security stream evidence for blue detections/responses
    fake.xadd(
        "security_events",
        {
            "payload": json.dumps(
                {
                    "event_type": "detection_event",
                    "metadata": {"tenant_id": str(tenant_id)},
                }
            )
        },
    )
    fake.xadd(
        "security_events",
        {
            "payload": json.dumps(
                {
                    "event_type": "response_event",
                    "metadata": {"tenant_id": str(tenant_id)},
                }
            )
        },
    )

    # Cost within budget
    cost_meter.record_cost(tenant_id, tokens=1000, model_name="llama3.1-8b-instruct")

    # Feedback tracking evidence
    policy_store.save_pending_action(
        tenant_id,
        "action-1",
        {
            "action_id": "action-1",
            "status": "applied",
            "action_name": "blue_policy_threshold_adjust",
        },
    )

    # Compliance audit evidence
    audit.write_control_plane_audit(
        actor="admin",
        action="tenant.status",
        status="success",
        target=f"tenant:{tenant_id}",
        details={"tenant_id": str(tenant_id)},
    )

    result = objective_gate.evaluate_objective_gate(tenant_id)

    assert result["overall_pass"] is True
    assert result["gates"]["red"]["pass"] is True
    assert result["gates"]["blue"]["pass"] is True
    assert result["gates"]["purple"]["pass"] is True
    assert result["gates"]["closed_loop"]["pass"] is True
    assert result["gates"]["enterprise"]["pass"] is True
    assert result["gates"]["compliance"]["pass"] is True


def test_objective_gate_fail_when_no_evidence() -> None:
    fake = FakeRedis()
    _setup(fake)

    tenant_id = uuid4()
    result = objective_gate.evaluate_objective_gate(tenant_id)

    assert result["overall_pass"] is False
    assert result["gates"]["red"]["pass"] is False
    assert result["gates"]["blue"]["pass"] is False
    assert result["gates"]["purple"]["pass"] is False
    assert result["gates"]["closed_loop"]["pass"] is False
    assert result["gates"]["compliance"]["pass"] is False


def test_objective_gate_history_and_remediation() -> None:
    fake = FakeRedis()
    _setup(fake)

    tenant_id = uuid4()
    result = objective_gate.evaluate_and_persist_objective_gate(tenant_id)
    history = objective_gate.list_objective_gate_history(tenant_id, limit=10)

    assert result["overall_pass"] is False
    assert len(history) == 1
    assert history[0]["overall_pass"] is False
    assert "gates" in history[0]
    assert len(fake.streams.get(objective_gate.OBJECTIVE_GATE_GLOBAL_HISTORY_STREAM, [])) == 1

    remediation = objective_gate.objective_gate_remediation_plan(result)
    assert remediation["failed_gate_count"] > 0
    assert len(remediation["actions"]) > 0

    blockers = objective_gate.objective_gate_blockers(result)
    assert blockers["blocker_count"] > 0
    assert len(blockers["blockers"]) > 0


def test_objective_gate_dashboard_summary() -> None:
    fake = FakeRedis()
    _setup(fake)

    tenant_pass = uuid4()
    tenant_fail = uuid4()

    pass_eval = {
        "overall_pass": True,
        "gates": {
            "red": {"pass": True},
            "blue": {"pass": True},
            "purple": {"pass": True},
            "closed_loop": {"pass": True},
            "enterprise": {"pass": True},
            "compliance": {"pass": True},
        },
        "thresholds": {},
    }
    fail_eval = {
        "overall_pass": False,
        "gates": {
            "red": {"pass": True},
            "blue": {"pass": False},
            "purple": {"pass": False},
            "closed_loop": {"pass": True},
            "enterprise": {"pass": True},
            "compliance": {"pass": True},
        },
        "thresholds": {},
    }

    objective_gate.persist_objective_gate_snapshot(tenant_pass, pass_eval)
    objective_gate.persist_objective_gate_snapshot(tenant_fail, fail_eval)

    dashboard = objective_gate.objective_gate_dashboard(limit=10)
    assert dashboard["total_tenants"] == 2
    assert dashboard["passing_tenants"] == 1
    assert dashboard["failing_tenants"] == 1
    assert dashboard["rows"][0]["overall_pass"] is False
