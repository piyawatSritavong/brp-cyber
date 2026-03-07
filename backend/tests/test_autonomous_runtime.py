from __future__ import annotations

import time

from app.core.config import settings
from app.services.autonomous_runtime import AutonomousRuntime


def test_autonomous_runtime_run_once_executes_tick_and_schedule() -> None:
    calls: dict[str, int] = {"tick": 0, "schedule": 0}

    def _tick(limit: int) -> dict[str, object]:
        calls["tick"] += 1
        return {"limit": limit, "executed_count": 1}

    def _schedule(limit: int) -> dict[str, object]:
        calls["schedule"] += 1
        return {"limit": limit, "processed": 2}

    runtime = AutonomousRuntime(tick_runner=_tick, red_schedule_runner=_schedule)
    state = runtime.run_once()
    assert calls["tick"] == 1
    assert calls["schedule"] == 1
    assert state["iterations"] == 1
    assert state["last_result"]["tick"]["executed_count"] == 1
    assert state["last_result"]["red_schedule"]["processed"] == 2


def test_autonomous_runtime_start_and_stop() -> None:
    original_enabled = settings.autonomous_orchestration_enabled
    original_interval = settings.autonomous_tick_interval_seconds
    try:
        settings.autonomous_orchestration_enabled = True
        settings.autonomous_tick_interval_seconds = 1

        runtime = AutonomousRuntime(
            tick_runner=lambda limit: {"executed_count": 0, "limit": limit},
            red_schedule_runner=lambda limit: {"processed": 0, "limit": limit},
        )
        started = runtime.start()
        assert started["running"] is True

        time.sleep(1.2)
        stopped = runtime.stop()
        assert stopped["running"] is False
        assert stopped["iterations"] >= 1
    finally:
        settings.autonomous_orchestration_enabled = original_enabled
        settings.autonomous_tick_interval_seconds = original_interval

