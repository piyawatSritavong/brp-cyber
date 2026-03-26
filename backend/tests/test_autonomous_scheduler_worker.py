from __future__ import annotations

from typing import Any

from app.services.autonomous_scheduler_worker import (
    AUTONOMOUS_WORKER_LEASE_KEY,
    AUTONOMOUS_WORKER_STATUS_KEY,
    DistributedAutonomousScheduler,
    autonomous_runtime_mode,
    distributed_worker_expected,
    embedded_api_runtime_enabled,
)


class FakeRedis:
    def __init__(self) -> None:
        self.strings: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

    def set(self, key: str, value: str, ex: int | None = None, nx: bool = False) -> bool:
        if nx and key in self.strings:
            return False
        self.strings[key] = value
        return True

    def delete(self, key: str) -> int:
        return 1 if self.strings.pop(key, None) is not None else 0


class FakeSettings:
    autonomous_orchestration_enabled = True
    autonomous_runtime_mode = "worker"
    autonomous_runtime_worker_id = ""
    autonomous_tick_interval_seconds = 5
    autonomous_runtime_lease_ttl_seconds = 90
    autonomous_runtime_status_ttl_seconds = 300
    autonomous_tick_limit = 200


class FakeRuntime:
    def __init__(self) -> None:
        self.calls = 0
        self.running = False

    def status(self) -> dict[str, Any]:
        return {"running": self.running, "iterations": self.calls}

    def start(self) -> dict[str, Any]:
        self.running = True
        return self.status()

    def stop(self) -> dict[str, Any]:
        self.running = False
        return self.status()

    def run_once(self) -> dict[str, Any]:
        self.calls += 1
        return {
            "running": False,
            "iterations": self.calls,
            "last_error": "",
            "last_result": {"tick": {"executed_count": 1}},
        }


def test_distributed_scheduler_runs_once_and_persists_status() -> None:
    fake_runtime = FakeRuntime()
    fake_redis = FakeRedis()
    scheduler = DistributedAutonomousScheduler(
        runtime=fake_runtime,
        redis_backend=fake_redis,
        settings_obj=FakeSettings(),
        worker_id="worker-a",
    )

    result = scheduler.run_worker_iteration()
    assert fake_runtime.calls == 1
    assert result["distributed"]["status"] == "leader"
    assert result["lease_owner"] == "worker-a"
    assert fake_redis.get(AUTONOMOUS_WORKER_LEASE_KEY) == "worker-a"
    assert "worker-a" in str(fake_redis.get(AUTONOMOUS_WORKER_STATUS_KEY))


def test_distributed_scheduler_enters_standby_when_other_worker_holds_lease() -> None:
    fake_runtime = FakeRuntime()
    fake_redis = FakeRedis()
    fake_redis.set(AUTONOMOUS_WORKER_LEASE_KEY, "worker-b")
    scheduler = DistributedAutonomousScheduler(
        runtime=fake_runtime,
        redis_backend=fake_redis,
        settings_obj=FakeSettings(),
        worker_id="worker-a",
    )

    result = scheduler.run_worker_iteration()
    assert fake_runtime.calls == 0
    assert result["distributed"]["status"] == "standby"
    assert result["distributed"]["lease_owner"] == "worker-b"


def test_distributed_scheduler_stop_request_targets_active_worker() -> None:
    fake_runtime = FakeRuntime()
    fake_redis = FakeRedis()
    scheduler = DistributedAutonomousScheduler(
        runtime=fake_runtime,
        redis_backend=fake_redis,
        settings_obj=FakeSettings(),
        worker_id="worker-a",
    )

    first = scheduler.run_worker_iteration()
    assert first["distributed"]["status"] == "leader"

    stop_requested = scheduler.request_stop(reason="test_stop")
    assert stop_requested["action"] == "stop_requested"
    assert stop_requested["stop_request"]["target_worker_id"] == "worker-a"

    stopped = scheduler.run_worker_iteration()
    assert stopped["distributed"]["status"] == "stopped"
    assert fake_redis.get(AUTONOMOUS_WORKER_LEASE_KEY) is None


def test_autonomous_runtime_mode_helpers() -> None:
    settings_obj = FakeSettings()
    assert autonomous_runtime_mode(settings_obj) == "worker"
    assert distributed_worker_expected(settings_obj) is True
    assert embedded_api_runtime_enabled(settings_obj) is False

    settings_obj.autonomous_runtime_mode = "api"
    assert autonomous_runtime_mode(settings_obj) == "api"
    assert distributed_worker_expected(settings_obj) is False
    assert embedded_api_runtime_enabled(settings_obj) is True

    settings_obj.autonomous_orchestration_enabled = False
    assert autonomous_runtime_mode(settings_obj) == "disabled"
