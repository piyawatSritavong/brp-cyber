from __future__ import annotations

import time

from app.core.config import settings
from app.services.autonomous_runtime import AutonomousRuntime


def test_autonomous_runtime_run_once_executes_tick_and_schedule() -> None:
    calls: dict[str, int] = {
        "tick": 0,
        "schedule": 0,
        "hygiene": 0,
        "replay": 0,
        "autotune": 0,
        "red_autopilot": 0,
        "threat_pipeline": 0,
    }

    def _tick(limit: int) -> dict[str, object]:
        calls["tick"] += 1
        return {"limit": limit, "executed_count": 1}

    def _schedule(limit: int) -> dict[str, object]:
        calls["schedule"] += 1
        return {"limit": limit, "processed": 2}

    def _hygiene(limit: int) -> dict[str, object]:
        calls["hygiene"] += 1
        return {"limit": limit, "executed_count": 3}

    def _replay(limit: int) -> dict[str, object]:
        calls["replay"] += 1
        return {"limit": limit, "executed_count": 2}

    def _autotune(limit: int) -> dict[str, object]:
        calls["autotune"] += 1
        return {"limit": limit, "executed_count": 4}

    def _red_autopilot(limit: int) -> dict[str, object]:
        calls["red_autopilot"] += 1
        return {"limit": limit, "executed_count": 5}

    def _threat_pipeline(limit: int) -> dict[str, object]:
        calls["threat_pipeline"] += 1
        return {"limit": limit, "executed_count": 1}

    runtime = AutonomousRuntime(
        tick_runner=_tick,
        red_schedule_runner=_schedule,
        hygiene_schedule_runner=_hygiene,
        replay_schedule_runner=_replay,
        detection_autotune_schedule_runner=_autotune,
        red_exploit_autopilot_schedule_runner=_red_autopilot,
        threat_content_pipeline_schedule_runner=_threat_pipeline,
    )
    state = runtime.run_once()
    assert calls["tick"] == 1
    assert calls["schedule"] == 1
    assert calls["hygiene"] == 1
    assert calls["replay"] == 1
    assert calls["autotune"] == 1
    assert calls["red_autopilot"] == 1
    assert calls["threat_pipeline"] == 1
    assert state["iterations"] == 1
    assert state["last_result"]["tick"]["executed_count"] == 1
    assert state["last_result"]["red_schedule"]["processed"] == 2
    assert state["last_result"]["hygiene_schedule"]["executed_count"] == 3
    assert state["last_result"]["replay_schedule"]["executed_count"] == 2
    assert state["last_result"]["detection_autotune_schedule"]["executed_count"] == 4
    assert state["last_result"]["red_exploit_autopilot_schedule"]["executed_count"] == 5
    assert state["last_result"]["threat_content_pipeline_schedule"]["executed_count"] == 1


def test_autonomous_runtime_start_and_stop() -> None:
    original_enabled = settings.autonomous_orchestration_enabled
    original_interval = settings.autonomous_tick_interval_seconds
    try:
        settings.autonomous_orchestration_enabled = True
        settings.autonomous_tick_interval_seconds = 1

        runtime = AutonomousRuntime(
            tick_runner=lambda limit: {"executed_count": 0, "limit": limit},
            red_schedule_runner=lambda limit: {"processed": 0, "limit": limit},
            hygiene_schedule_runner=lambda limit: {"executed_count": 0, "limit": limit},
            replay_schedule_runner=lambda limit: {"executed_count": 0, "limit": limit},
            detection_autotune_schedule_runner=lambda limit: {"executed_count": 0, "limit": limit},
            red_exploit_autopilot_schedule_runner=lambda limit: {"executed_count": 0, "limit": limit},
            threat_content_pipeline_schedule_runner=lambda limit: {"executed_count": 0, "limit": limit},
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
