from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_orchestration_assurance as oa
from app.services.enterprise import objective_gate


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.counter = 0

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self.counter += 1
        event_id = f"{self.counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]


def test_orchestration_objectives_status() -> None:
    fake = FakeRedis()
    objective_gate.redis_client = fake
    oa.redis_client = fake

    tenant_pass = uuid4()
    tenant_fail = uuid4()

    objective_gate.persist_objective_gate_snapshot(
        tenant_pass,
        {
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
        },
    )
    objective_gate.persist_objective_gate_snapshot(
        tenant_fail,
        {
            "overall_pass": False,
            "gates": {
                "red": {"pass": False},
                "blue": {"pass": True},
                "purple": {"pass": False},
                "closed_loop": {"pass": True},
                "enterprise": {"pass": True},
                "compliance": {"pass": True},
            },
            "thresholds": {},
        },
    )

    result = oa.orchestration_objectives_status(limit=10)
    assert result["status"] == "ok"
    assert result["sample_count"] == 2
    assert result["tenant_count"] == 2
    assert result["overall_pass_rate"] == 0.5
    assert result["gate_pass_rates"]["blue"] == 1.0
    assert result["gate_pass_rates"]["red"] == 0.5
    assert result["enterprise_readiness"]["ready"] is False
