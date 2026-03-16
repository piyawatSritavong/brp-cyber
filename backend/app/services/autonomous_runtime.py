from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

from app.core.config import settings
from app.services.blue_log_refiner import process_blue_log_refiner_schedules
from app.services.connector_credential_hygiene import process_credential_hygiene_schedules
from app.services.connector_reliability import process_connector_replay_schedules
from app.services.coworker_delivery import process_coworker_delivery_escalation_schedules
from app.services.coworker_plugins import process_coworker_plugin_schedules
from app.services.detection_autotune import process_detection_autotune_schedules
from app.services.blue_managed_responder import process_managed_responder_schedules
from app.services.blue_threat_localizer import process_blue_threat_localizer_schedules
from app.services.orchestrator import run_activation_scheduler_tick
from app.services.red_exploit_autopilot import process_red_exploit_autopilot_schedules
from app.services.red_plugin_intelligence import process_red_plugin_sync_schedules
from app.services.red_shadow_pentest import process_red_shadow_pentest_schedules
from app.services.red_simulator import process_due_schedules
from app.services.threat_content_pipeline import process_threat_content_pipeline_schedules


class AutonomousRuntime:
    def __init__(
        self,
        *,
        tick_runner: Callable[[int], dict[str, Any]] = run_activation_scheduler_tick,
        red_schedule_runner: Callable[[int], dict[str, Any]] = process_due_schedules,
        hygiene_schedule_runner: Callable[[int], dict[str, Any]] = process_credential_hygiene_schedules,
        replay_schedule_runner: Callable[[int], dict[str, Any]] = process_connector_replay_schedules,
        detection_autotune_schedule_runner: Callable[[int], dict[str, Any]] = process_detection_autotune_schedules,
        blue_log_refiner_schedule_runner: Callable[[int], dict[str, Any]] = process_blue_log_refiner_schedules,
        blue_managed_responder_schedule_runner: Callable[[int], dict[str, Any]] = process_managed_responder_schedules,
        blue_threat_localizer_schedule_runner: Callable[[int], dict[str, Any]] = process_blue_threat_localizer_schedules,
        red_exploit_autopilot_schedule_runner: Callable[[int], dict[str, Any]] = process_red_exploit_autopilot_schedules,
        red_shadow_pentest_schedule_runner: Callable[[int], dict[str, Any]] = process_red_shadow_pentest_schedules,
        red_plugin_sync_schedule_runner: Callable[[int], dict[str, Any]] = process_red_plugin_sync_schedules,
        threat_content_pipeline_schedule_runner: Callable[[int], dict[str, Any]] = process_threat_content_pipeline_schedules,
        coworker_plugin_schedule_runner: Callable[[int], dict[str, Any]] = process_coworker_plugin_schedules,
        coworker_delivery_escalation_schedule_runner: Callable[[int], dict[str, Any]] = process_coworker_delivery_escalation_schedules,
    ) -> None:
        self._tick_runner = tick_runner
        self._red_schedule_runner = red_schedule_runner
        self._hygiene_schedule_runner = hygiene_schedule_runner
        self._replay_schedule_runner = replay_schedule_runner
        self._detection_autotune_schedule_runner = detection_autotune_schedule_runner
        self._blue_log_refiner_schedule_runner = blue_log_refiner_schedule_runner
        self._blue_managed_responder_schedule_runner = blue_managed_responder_schedule_runner
        self._blue_threat_localizer_schedule_runner = blue_threat_localizer_schedule_runner
        self._red_exploit_autopilot_schedule_runner = red_exploit_autopilot_schedule_runner
        self._red_shadow_pentest_schedule_runner = red_shadow_pentest_schedule_runner
        self._red_plugin_sync_schedule_runner = red_plugin_sync_schedule_runner
        self._threat_content_pipeline_schedule_runner = threat_content_pipeline_schedule_runner
        self._coworker_plugin_schedule_runner = coworker_plugin_schedule_runner
        self._coworker_delivery_escalation_schedule_runner = coworker_delivery_escalation_schedule_runner
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
            "hygiene_schedule_enabled": bool(getattr(settings, "autonomous_connector_hygiene_schedule_enabled", True)),
            "hygiene_schedule_limit": max(1, int(getattr(settings, "autonomous_connector_hygiene_schedule_limit", 100))),
            "replay_schedule_enabled": bool(getattr(settings, "autonomous_connector_replay_schedule_enabled", True)),
            "replay_schedule_limit": max(1, int(getattr(settings, "autonomous_connector_replay_schedule_limit", 100))),
            "detection_autotune_schedule_enabled": bool(
                getattr(settings, "autonomous_detection_autotune_schedule_enabled", True)
            ),
            "detection_autotune_schedule_limit": max(
                1, int(getattr(settings, "autonomous_detection_autotune_schedule_limit", 100))
            ),
            "blue_log_refiner_schedule_enabled": bool(
                getattr(settings, "autonomous_blue_log_refiner_schedule_enabled", True)
            ),
            "blue_log_refiner_schedule_limit": max(
                1, int(getattr(settings, "autonomous_blue_log_refiner_schedule_limit", 100))
            ),
            "blue_managed_responder_schedule_enabled": bool(
                getattr(settings, "autonomous_blue_managed_responder_schedule_enabled", True)
            ),
            "blue_managed_responder_schedule_limit": max(
                1, int(getattr(settings, "autonomous_blue_managed_responder_schedule_limit", 100))
            ),
            "blue_threat_localizer_schedule_enabled": bool(
                getattr(settings, "autonomous_blue_threat_localizer_schedule_enabled", True)
            ),
            "blue_threat_localizer_schedule_limit": max(
                1, int(getattr(settings, "autonomous_blue_threat_localizer_schedule_limit", 100))
            ),
            "red_exploit_autopilot_schedule_enabled": bool(
                getattr(settings, "autonomous_red_exploit_autopilot_schedule_enabled", True)
            ),
            "red_exploit_autopilot_schedule_limit": max(
                1, int(getattr(settings, "autonomous_red_exploit_autopilot_schedule_limit", 100))
            ),
            "red_shadow_pentest_schedule_enabled": bool(
                getattr(settings, "autonomous_red_shadow_pentest_schedule_enabled", True)
            ),
            "red_shadow_pentest_schedule_limit": max(
                1, int(getattr(settings, "autonomous_red_shadow_pentest_schedule_limit", 100))
            ),
            "red_plugin_sync_schedule_enabled": bool(
                getattr(settings, "autonomous_red_plugin_sync_schedule_enabled", True)
            ),
            "red_plugin_sync_schedule_limit": max(
                1, int(getattr(settings, "autonomous_red_plugin_sync_schedule_limit", 100))
            ),
            "threat_content_pipeline_schedule_enabled": bool(
                getattr(settings, "autonomous_threat_content_pipeline_schedule_enabled", True)
            ),
            "threat_content_pipeline_schedule_limit": max(
                1, int(getattr(settings, "autonomous_threat_content_pipeline_schedule_limit", 20))
            ),
            "coworker_plugin_schedule_enabled": bool(
                getattr(settings, "autonomous_coworker_plugin_schedule_enabled", True)
            ),
            "coworker_plugin_schedule_limit": max(
                1, int(getattr(settings, "autonomous_coworker_plugin_schedule_limit", 100))
            ),
            "coworker_delivery_escalation_schedule_enabled": bool(
                getattr(settings, "autonomous_coworker_delivery_escalation_schedule_enabled", True)
            ),
            "coworker_delivery_escalation_schedule_limit": max(
                1, int(getattr(settings, "autonomous_coworker_delivery_escalation_schedule_limit", 100))
            ),
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
        hygiene_limit = max(1, int(getattr(settings, "autonomous_connector_hygiene_schedule_limit", 100)))
        hygiene_enabled = bool(getattr(settings, "autonomous_connector_hygiene_schedule_enabled", True))
        replay_limit = max(1, int(getattr(settings, "autonomous_connector_replay_schedule_limit", 100)))
        replay_enabled = bool(getattr(settings, "autonomous_connector_replay_schedule_enabled", True))
        detection_autotune_limit = max(1, int(getattr(settings, "autonomous_detection_autotune_schedule_limit", 100)))
        detection_autotune_enabled = bool(getattr(settings, "autonomous_detection_autotune_schedule_enabled", True))
        blue_log_refiner_limit = max(1, int(getattr(settings, "autonomous_blue_log_refiner_schedule_limit", 100)))
        blue_log_refiner_enabled = bool(getattr(settings, "autonomous_blue_log_refiner_schedule_enabled", True))
        blue_managed_responder_limit = max(
            1, int(getattr(settings, "autonomous_blue_managed_responder_schedule_limit", 100))
        )
        blue_managed_responder_enabled = bool(
            getattr(settings, "autonomous_blue_managed_responder_schedule_enabled", True)
        )
        blue_threat_localizer_limit = max(
            1, int(getattr(settings, "autonomous_blue_threat_localizer_schedule_limit", 100))
        )
        blue_threat_localizer_enabled = bool(
            getattr(settings, "autonomous_blue_threat_localizer_schedule_enabled", True)
        )
        red_exploit_autopilot_limit = max(1, int(getattr(settings, "autonomous_red_exploit_autopilot_schedule_limit", 100)))
        red_exploit_autopilot_enabled = bool(getattr(settings, "autonomous_red_exploit_autopilot_schedule_enabled", True))
        red_shadow_pentest_limit = max(1, int(getattr(settings, "autonomous_red_shadow_pentest_schedule_limit", 100)))
        red_shadow_pentest_enabled = bool(getattr(settings, "autonomous_red_shadow_pentest_schedule_enabled", True))
        red_plugin_sync_limit = max(1, int(getattr(settings, "autonomous_red_plugin_sync_schedule_limit", 100)))
        red_plugin_sync_enabled = bool(getattr(settings, "autonomous_red_plugin_sync_schedule_enabled", True))
        threat_content_pipeline_limit = max(
            1, int(getattr(settings, "autonomous_threat_content_pipeline_schedule_limit", 20))
        )
        threat_content_pipeline_enabled = bool(
            getattr(settings, "autonomous_threat_content_pipeline_schedule_enabled", True)
        )
        coworker_plugin_limit = max(1, int(getattr(settings, "autonomous_coworker_plugin_schedule_limit", 100)))
        coworker_plugin_enabled = bool(getattr(settings, "autonomous_coworker_plugin_schedule_enabled", True))
        coworker_delivery_escalation_limit = max(
            1, int(getattr(settings, "autonomous_coworker_delivery_escalation_schedule_limit", 100))
        )
        coworker_delivery_escalation_enabled = bool(
            getattr(settings, "autonomous_coworker_delivery_escalation_schedule_enabled", True)
        )
        now_iso = datetime.now(timezone.utc).isoformat()
        result: dict[str, Any] = {
            "tick": {},
            "red_schedule": {"status": "disabled"},
            "hygiene_schedule": {"status": "disabled"},
            "replay_schedule": {"status": "disabled"},
            "detection_autotune_schedule": {"status": "disabled"},
            "blue_log_refiner_schedule": {"status": "disabled"},
            "blue_managed_responder_schedule": {"status": "disabled"},
            "blue_threat_localizer_schedule": {"status": "disabled"},
            "red_exploit_autopilot_schedule": {"status": "disabled"},
            "red_shadow_pentest_schedule": {"status": "disabled"},
            "red_plugin_sync_schedule": {"status": "disabled"},
            "threat_content_pipeline_schedule": {"status": "disabled"},
            "coworker_plugin_schedule": {"status": "disabled"},
            "coworker_delivery_escalation_schedule": {"status": "disabled"},
        }
        error_text = ""

        try:
            result["tick"] = self._tick_runner(tick_limit)
            if red_enabled:
                result["red_schedule"] = self._red_schedule_runner(red_limit)
            if hygiene_enabled:
                result["hygiene_schedule"] = self._hygiene_schedule_runner(hygiene_limit)
            if replay_enabled:
                result["replay_schedule"] = self._replay_schedule_runner(replay_limit)
            if detection_autotune_enabled:
                result["detection_autotune_schedule"] = self._detection_autotune_schedule_runner(detection_autotune_limit)
            if blue_log_refiner_enabled:
                result["blue_log_refiner_schedule"] = self._blue_log_refiner_schedule_runner(blue_log_refiner_limit)
            if blue_managed_responder_enabled:
                result["blue_managed_responder_schedule"] = self._blue_managed_responder_schedule_runner(
                    blue_managed_responder_limit
                )
            if blue_threat_localizer_enabled:
                result["blue_threat_localizer_schedule"] = self._blue_threat_localizer_schedule_runner(
                    blue_threat_localizer_limit
                )
            if red_exploit_autopilot_enabled:
                result["red_exploit_autopilot_schedule"] = self._red_exploit_autopilot_schedule_runner(red_exploit_autopilot_limit)
            if red_shadow_pentest_enabled:
                result["red_shadow_pentest_schedule"] = self._red_shadow_pentest_schedule_runner(red_shadow_pentest_limit)
            if red_plugin_sync_enabled:
                result["red_plugin_sync_schedule"] = self._red_plugin_sync_schedule_runner(red_plugin_sync_limit)
            if threat_content_pipeline_enabled:
                result["threat_content_pipeline_schedule"] = self._threat_content_pipeline_schedule_runner(
                    threat_content_pipeline_limit
                )
            if coworker_plugin_enabled:
                result["coworker_plugin_schedule"] = self._coworker_plugin_schedule_runner(coworker_plugin_limit)
            if coworker_delivery_escalation_enabled:
                result["coworker_delivery_escalation_schedule"] = self._coworker_delivery_escalation_schedule_runner(
                    coworker_delivery_escalation_limit
                )
        except Exception as exc:
            error_text = str(exc)
            result["error"] = error_text

        with self._lock:
            self._state["enabled"] = bool(getattr(settings, "autonomous_orchestration_enabled", True))
            self._state["interval_seconds"] = max(5, int(getattr(settings, "autonomous_tick_interval_seconds", 30)))
            self._state["tick_limit"] = tick_limit
            self._state["red_schedule_enabled"] = red_enabled
            self._state["red_schedule_limit"] = red_limit
            self._state["hygiene_schedule_enabled"] = hygiene_enabled
            self._state["hygiene_schedule_limit"] = hygiene_limit
            self._state["replay_schedule_enabled"] = replay_enabled
            self._state["replay_schedule_limit"] = replay_limit
            self._state["detection_autotune_schedule_enabled"] = detection_autotune_enabled
            self._state["detection_autotune_schedule_limit"] = detection_autotune_limit
            self._state["blue_log_refiner_schedule_enabled"] = blue_log_refiner_enabled
            self._state["blue_log_refiner_schedule_limit"] = blue_log_refiner_limit
            self._state["blue_managed_responder_schedule_enabled"] = blue_managed_responder_enabled
            self._state["blue_managed_responder_schedule_limit"] = blue_managed_responder_limit
            self._state["blue_threat_localizer_schedule_enabled"] = blue_threat_localizer_enabled
            self._state["blue_threat_localizer_schedule_limit"] = blue_threat_localizer_limit
            self._state["red_exploit_autopilot_schedule_enabled"] = red_exploit_autopilot_enabled
            self._state["red_exploit_autopilot_schedule_limit"] = red_exploit_autopilot_limit
            self._state["red_shadow_pentest_schedule_enabled"] = red_shadow_pentest_enabled
            self._state["red_shadow_pentest_schedule_limit"] = red_shadow_pentest_limit
            self._state["red_plugin_sync_schedule_enabled"] = red_plugin_sync_enabled
            self._state["red_plugin_sync_schedule_limit"] = red_plugin_sync_limit
            self._state["threat_content_pipeline_schedule_enabled"] = threat_content_pipeline_enabled
            self._state["threat_content_pipeline_schedule_limit"] = threat_content_pipeline_limit
            self._state["coworker_plugin_schedule_enabled"] = coworker_plugin_enabled
            self._state["coworker_plugin_schedule_limit"] = coworker_plugin_limit
            self._state["coworker_delivery_escalation_schedule_enabled"] = coworker_delivery_escalation_enabled
            self._state["coworker_delivery_escalation_schedule_limit"] = coworker_delivery_escalation_limit
            self._state["last_tick_at"] = now_iso
            self._state["last_result"] = result
            self._state["last_error"] = error_text
            self._state["iterations"] = int(self._state.get("iterations", 0) or 0) + 1
            self._state["running"] = bool(self._thread and self._thread.is_alive()) and not self._stop_event.is_set()
            return dict(self._state)


autonomous_runtime = AutonomousRuntime()
