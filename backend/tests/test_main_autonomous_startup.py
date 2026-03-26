from __future__ import annotations

import asyncio

from app import main
from app.core.config import settings


def test_startup_event_only_starts_embedded_runtime_in_api_mode(monkeypatch) -> None:
    original_enabled = settings.autonomous_orchestration_enabled
    original_mode = settings.autonomous_runtime_mode
    original_auto_init = settings.auto_init_db_on_startup

    start_calls: list[str] = []
    stop_calls: list[str] = []

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(main.Base.metadata, "create_all", lambda bind: None)
    monkeypatch.setattr(main.autonomous_runtime, "start", lambda: start_calls.append("start") or {"running": True})
    monkeypatch.setattr(main.autonomous_runtime, "stop", lambda: stop_calls.append("stop") or {"running": False})

    try:
        settings.autonomous_orchestration_enabled = True
        settings.auto_init_db_on_startup = False

        settings.autonomous_runtime_mode = "worker"
        asyncio.run(main.startup_event())
        asyncio.run(main.shutdown_event())
        assert start_calls == []
        assert stop_calls == []

        settings.autonomous_runtime_mode = "api"
        asyncio.run(main.startup_event())
        asyncio.run(main.shutdown_event())
        assert start_calls == ["start"]
        assert stop_calls == ["stop"]
    finally:
        settings.autonomous_orchestration_enabled = original_enabled
        settings.autonomous_runtime_mode = original_mode
        settings.auto_init_db_on_startup = original_auto_init
