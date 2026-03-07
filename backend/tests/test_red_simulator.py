from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.config import settings
from app.services import red_simulator
from schemas.red_sim import RedSimulationRunRequest, RedSimulationScheduleRequest


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.strings: dict[str, str] = {}
        self._counter = 0

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self._counter += 1
        event_id = f"{self._counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]

    def exists(self, key: str) -> int:
        return 1 if key in self.strings else 0

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.strings[key] = value
        return True


def test_red_run_with_guardrails_and_blue_feedback() -> None:
    fake_redis = FakeRedis()
    red_simulator.redis_client = fake_redis

    persisted = []
    red_simulator.persist_event = lambda event: persisted.append(event.event_type)

    blue_results = []
    red_simulator.process_auth_login_event = lambda event: blue_results.append(event.source_ip) or {
        "status": "monitored",
        "reason": "test",
    }

    settings.red_allowed_targets = "acb.example.com/admin-login"
    settings.red_default_source_ips = "203.0.113.10,203.0.113.11"
    settings.red_default_usernames = "admin,root"
    settings.red_max_events_per_run = 5
    settings.red_min_delay_ms = 0

    rejected = red_simulator.run_simulation(
        RedSimulationRunRequest(
            tenant_id=uuid4(),
            scenario_name="credential_stuffing_sim",
            target_asset="not-allowed.example.com/login",
            events_count=3,
        )
    )
    assert rejected["status"] == "rejected"

    result = red_simulator.run_simulation(
        RedSimulationRunRequest(
            tenant_id=uuid4(),
            scenario_name="credential_stuffing_sim",
            target_asset="acb.example.com/admin-login",
            events_count=7,
        )
    )

    assert result["status"] == "completed"
    assert result["executed_events"] == 5
    assert len(result["results"]) == 5
    assert len(blue_results) == 5
    assert persisted.count("red_event") >= 2


def test_red_schedule_and_tick() -> None:
    fake_redis = FakeRedis()
    red_simulator.redis_client = fake_redis

    settings.red_allowed_targets = "acb.example.com/admin-login"
    settings.red_max_events_per_run = 3
    settings.red_min_delay_ms = 0

    run_calls = []

    def _fake_run(request):
        run_calls.append(request)
        return {"status": "completed"}

    red_simulator.run_simulation = _fake_run

    payload_now = RedSimulationScheduleRequest(
        tenant_id=uuid4(),
        scenario_name="slow_bruteforce_sim",
        target_asset="acb.example.com/admin-login",
        events_count=2,
        run_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        source_ips=["203.0.113.20"],
        usernames=["admin"],
    )
    payload_future = RedSimulationScheduleRequest(
        tenant_id=uuid4(),
        scenario_name="admin_endpoint_probe_sim",
        target_asset="acb.example.com/admin-login",
        events_count=2,
        run_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        source_ips=["203.0.113.21"],
        usernames=["ops"],
    )

    scheduled_1 = red_simulator.schedule_simulation(payload_now)
    scheduled_2 = red_simulator.schedule_simulation(payload_future)

    assert scheduled_1["status"] == "scheduled"
    assert scheduled_2["status"] == "scheduled"

    result = red_simulator.process_due_schedules(limit=50)
    assert result["processed"] == 1
    assert result["skipped"] >= 1
    assert len(run_calls) == 1

    first_call = run_calls[0]
    assert first_call.scenario_name == "slow_bruteforce_sim"
    assert first_call.source_ips == ["203.0.113.20"]
    assert first_call.usernames == ["admin"]

    replay_result = red_simulator.process_due_schedules(limit=50)
    assert replay_result["processed"] == 0
