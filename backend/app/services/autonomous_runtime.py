from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.config import settings
from app.services.orchestrator import run_activation_scheduler_tick
from app.services.red_simulator import process_due_schedules


class AutonomousRuntime:
    def __init__(
        self,
        *,
        tick_runner: Callable[[int], dict[str, Any]] = run_activation_scheduler_tick,
        red_schedule_runner: Callable[[int], dict[str, Any]] = process_due_schedules,
    ) -> None:
        self._tick_runner = tick_runner
        self._red_schedule_runner = red_schedule_runner
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {
            "enabled": bool(getattr(settings, "autonomous_orchestration_enabled", True)),
            "running": False,
            "interval_seconds": max(5, int(getattr(settings, "autonomous_tick_interval_seconds", 30))),
            "tick_limit": max(1, int(getattr(settings, "autonomous_tick_limit", 200))),
            "red_schedule_enabled": bool(getattr(settings, "autonomous_red_schedule_tick_enabled", True)),
            "red_schedule_limit": max(1, int(getattr(settings, "autonomous_red_schedule_limit", 100))),
            "started_at": "",
            "stopped_at": "",
            "last_tick_at": "",
            "last_error": "",
            "iterations": 0,
            "last_result": {},
        }

    def status(self) -> dict[str, Any]:
        with self._lock:
            snapshot = dict(self._state)
            snapshot["thread_alive"] = bool(self._thread and self._thread.is_alive())
            return snapshot

    def start(self) -> dict[str, Any]:
        with self._lock:
            if not self._state.get("enabled", True):
                self._state["running"] = False
                return dict(self._state)
            if self._thread and self._thread.is_alive():
                self._state["running"] = True
                return dict(self._state)
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name="brp-autonomous-runtime", daemon=True)
            self._thread.start()
            self._state["running"] = True
            self._state["started_at"] = datetime.now(timezone.utc).isoformat()
            self._state["stopped_at"] = ""
            return dict(self._state)

    def stop(self, timeout_seconds: float = 3.0) -> dict[str, Any]:
        thread: threading.Thread | None = None
        with self._lock:
            self._stop_event.set()
            thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=max(0.1, timeout_seconds))
        with self._lock:
            self._state["running"] = False
            self._state["stopped_at"] = datetime.now(timezone.utc).isoformat()
            return dict(self._state)

    def run_once(self) -> dict[str, Any]:
        return self._execute_once()

    def _run_loop(self) -> None:
        interval = max(5, int(getattr(settings, "autonomous_tick_interval_seconds", 30)))
        while not self._stop_event.is_set():
            self._execute_once()
            if self._stop_event.wait(interval):
                break

    def _execute_once(self) -> dict[str, Any]:
        tick_limit = max(1, int(getattr(settings, "autonomous_tick_limit", 200)))
        red_limit = max(1, int(getattr(settings, "autonomous_red_schedule_limit", 100)))
        red_enabled = bool(getattr(settings, "autonomous_red_schedule_tick_enabled", True))
        now_iso = datetime.now(timezone.utc).isoformat()
        result: dict[str, Any] = {"tick": {}, "red_schedule": {"status": "disabled"}}
        error_text = ""

        try:
            result["tick"] = self._tick_runner(tick_limit)
            if red_enabled:
                result["red_schedule"] = self._red_schedule_runner(red_limit)
        except Exception as exc:
            error_text = str(exc)
            result["error"] = error_text

        with self._lock:
            self._state["enabled"] = bool(getattr(settings, "autonomous_orchestration_enabled", True))
            self._state["interval_seconds"] = max(5, int(getattr(settings, "autonomous_tick_interval_seconds", 30)))
            self._state["tick_limit"] = tick_limit
            self._state["red_schedule_enabled"] = red_enabled
            self._state["red_schedule_limit"] = red_limit
            self._state["last_tick_at"] = now_iso
            self._state["last_result"] = result
            self._state["last_error"] = error_text
            self._state["iterations"] = int(self._state.get("iterations", 0) or 0) + 1
            self._state["running"] = bool(self._thread and self._thread.is_alive()) and not self._stop_event.is_set()
            return dict(self._state)


autonomous_runtime = AutonomousRuntime()

