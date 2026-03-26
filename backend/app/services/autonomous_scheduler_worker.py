from __future__ import annotations

import json
import os
import socket
import time
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.services.autonomous_runtime import autonomous_runtime
from app.services.redis_client import redis_client

AUTONOMOUS_WORKER_STATUS_KEY = "autonomous_scheduler_worker:status"
AUTONOMOUS_WORKER_LEASE_KEY = "autonomous_scheduler_worker:lease"
AUTONOMOUS_WORKER_STOP_KEY = "autonomous_scheduler_worker:stop"
VALID_AUTONOMOUS_RUNTIME_MODES = {"api", "worker", "disabled"}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def autonomous_runtime_mode(settings_obj: Any = settings) -> str:
    if not bool(getattr(settings_obj, "autonomous_orchestration_enabled", True)):
        return "disabled"
    value = str(getattr(settings_obj, "autonomous_runtime_mode", "worker") or "worker").strip().lower()
    if value not in VALID_AUTONOMOUS_RUNTIME_MODES:
        return "worker"
    return value


def embedded_api_runtime_enabled(settings_obj: Any = settings) -> bool:
    return autonomous_runtime_mode(settings_obj) == "api"


def distributed_worker_expected(settings_obj: Any = settings) -> bool:
    return autonomous_runtime_mode(settings_obj) == "worker"


class DistributedAutonomousScheduler:
    def __init__(
        self,
        *,
        runtime: Any = autonomous_runtime,
        redis_backend: Any = redis_client,
        settings_obj: Any = settings,
        worker_id: str = "",
    ) -> None:
        self._runtime = runtime
        self._redis = redis_backend
        self._settings = settings_obj
        configured_worker_id = str(worker_id or getattr(settings_obj, "autonomous_runtime_worker_id", "") or "").strip()
        self._worker_id = configured_worker_id or f"autonomous-worker-{socket.gethostname()}-{os.getpid()}"

    @property
    def worker_id(self) -> str:
        return self._worker_id

    def mode(self) -> str:
        return autonomous_runtime_mode(self._settings)

    def embedded_api_enabled(self) -> bool:
        return embedded_api_runtime_enabled(self._settings)

    def worker_expected(self) -> bool:
        return distributed_worker_expected(self._settings)

    def status(self) -> dict[str, Any]:
        distributed = self._load_json(AUTONOMOUS_WORKER_STATUS_KEY) or {}
        stop_request = self._load_json(AUTONOMOUS_WORKER_STOP_KEY) or {}
        lease_owner = str(self._safe_get(AUTONOMOUS_WORKER_LEASE_KEY) or "")
        snapshot: dict[str, Any] = {
            "enabled": bool(getattr(self._settings, "autonomous_orchestration_enabled", True)),
            "mode": self.mode(),
            "embedded_api_enabled": self.embedded_api_enabled(),
            "distributed_worker_expected": self.worker_expected(),
            "worker_id": self._worker_id,
            "lease_owner": lease_owner,
            "stop_requested": bool(stop_request),
            "stop_request": stop_request,
            "distributed": distributed,
        }
        with suppress(Exception):
            snapshot["local"] = self._runtime.status()
        return snapshot

    def start_control(self) -> dict[str, Any]:
        if self.mode() == "disabled":
            result = self.status()
            result["action"] = "disabled"
            return result
        if self.embedded_api_enabled():
            local_state = self._runtime.start()
            result = self.status()
            result["action"] = "started_embedded_runtime"
            result["local"] = local_state
            return result

        cleared = self.clear_stop_request()
        result = self.status()
        result["action"] = "external_worker_required"
        result["cleared_stop_request"] = bool(cleared.get("deleted_stop_request"))
        result["command"] = "python backend/scripts/run_autonomous_scheduler_worker.py"
        return result

    def stop_control(self, reason: str = "api_stop_request") -> dict[str, Any]:
        if self.embedded_api_enabled():
            local_state = self._runtime.stop()
            result = self.status()
            result["action"] = "stopped_embedded_runtime"
            result["local"] = local_state
            return result
        if not self.worker_expected():
            result = self.status()
            result["action"] = "disabled"
            return result
        return self.request_stop(reason=reason)

    def run_once_control(self) -> dict[str, Any]:
        if self.embedded_api_enabled():
            local_state = self._runtime.run_once()
            result = self.status()
            result["action"] = "ran_embedded_runtime_once"
            result["local"] = local_state
            return result
        result = self.status()
        result["action"] = "external_worker_required"
        result["command"] = "python backend/scripts/run_autonomous_scheduler_worker.py --once"
        return result

    def request_stop(self, reason: str = "api_stop_request") -> dict[str, Any]:
        lease_owner = str(self._safe_get(AUTONOMOUS_WORKER_LEASE_KEY) or "")
        if not lease_owner:
            result = self.status()
            result["action"] = "no_worker_running"
            return result
        payload = {
            "requested_at": _utcnow_iso(),
            "reason": str(reason or "api_stop_request"),
            "target_worker_id": lease_owner,
        }
        self._safe_set(
            AUTONOMOUS_WORKER_STOP_KEY,
            json.dumps(payload, ensure_ascii=True, sort_keys=True),
            ex=max(30, self._lease_ttl_seconds() * 2),
        )
        result = self.status()
        result["action"] = "stop_requested"
        result["stop_request"] = payload
        result["stop_requested"] = True
        return result

    def clear_stop_request(self) -> dict[str, Any]:
        deleted = self._safe_delete(AUTONOMOUS_WORKER_STOP_KEY)
        result = self.status()
        result["action"] = "cleared_stop_request"
        result["deleted_stop_request"] = bool(deleted)
        return result

    def run_worker_iteration(self) -> dict[str, Any]:
        now_iso = _utcnow_iso()
        mode = self.mode()

        if mode != "worker":
            distributed = self._persist_distributed_status(
                {
                    "worker_id": self._worker_id,
                    "hostname": socket.gethostname(),
                    "pid": os.getpid(),
                    "status": "mode_mismatch" if mode == "api" else "disabled",
                    "mode": mode,
                    "lease_owner": str(self._safe_get(AUTONOMOUS_WORKER_LEASE_KEY) or ""),
                    "last_heartbeat_at": now_iso,
                    "last_run_at": "",
                    "error": "",
                    "interval_seconds": self._interval_seconds(),
                    "last_result": {},
                }
            )
            result = self.status()
            result["distributed"] = distributed
            return result

        stop_request = self._load_json(AUTONOMOUS_WORKER_STOP_KEY) or {}
        target_worker_id = str(stop_request.get("target_worker_id", "") or "")
        if stop_request and target_worker_id == self._worker_id:
            self._release_lease_if_owned()
            self._safe_delete(AUTONOMOUS_WORKER_STOP_KEY)
            distributed = self._persist_distributed_status(
                {
                    "worker_id": self._worker_id,
                    "hostname": socket.gethostname(),
                    "pid": os.getpid(),
                    "status": "stopped",
                    "mode": mode,
                    "lease_owner": "",
                    "last_heartbeat_at": now_iso,
                    "last_run_at": "",
                    "error": "",
                    "stop_reason": str(stop_request.get("reason", "stop_requested")),
                    "interval_seconds": self._interval_seconds(),
                }
            )
            result = self.status()
            result["distributed"] = distributed
            return result

        acquired = self._acquire_or_renew_lease()
        if not acquired:
            lease_owner = str(self._safe_get(AUTONOMOUS_WORKER_LEASE_KEY) or "")
            distributed = self._persist_distributed_status(
                {
                    "worker_id": self._worker_id,
                    "hostname": socket.gethostname(),
                    "pid": os.getpid(),
                    "status": "standby",
                    "mode": mode,
                    "lease_owner": lease_owner,
                    "last_heartbeat_at": now_iso,
                    "error": "",
                    "interval_seconds": self._interval_seconds(),
                }
            )
            result = self.status()
            result["distributed"] = distributed
            return result

        runtime_state = self._runtime.run_once()
        distributed = self._persist_distributed_status(
            {
                "worker_id": self._worker_id,
                "hostname": socket.gethostname(),
                "pid": os.getpid(),
                "status": "leader",
                "mode": mode,
                "lease_owner": self._worker_id,
                "last_heartbeat_at": now_iso,
                "last_run_at": now_iso,
                "error": str(runtime_state.get("last_error", "") or ""),
                "iterations": int(runtime_state.get("iterations", 0) or 0),
                "interval_seconds": self._interval_seconds(),
                "tick_limit": max(1, int(getattr(self._settings, "autonomous_tick_limit", 200))),
                "last_result": runtime_state.get("last_result", {}),
            }
        )
        result = self.status()
        result["distributed"] = distributed
        return result

    def run_forever(self, max_iterations: int | None = None) -> dict[str, Any]:
        completed = 0
        snapshot = self.status()
        try:
            while True:
                snapshot = self.run_worker_iteration()
                completed += 1
                status_name = str(snapshot.get("distributed", {}).get("status", "") or "")
                if max_iterations is not None and completed >= max(1, int(max_iterations)):
                    break
                if status_name in {"disabled", "mode_mismatch", "stopped"}:
                    break
                time.sleep(self._interval_seconds())
        finally:
            self._release_lease_if_owned()
            distributed = self._persist_distributed_status(
                {
                    "worker_id": self._worker_id,
                    "hostname": socket.gethostname(),
                    "pid": os.getpid(),
                    "status": "stopped" if self.worker_expected() else self.mode(),
                    "mode": self.mode(),
                    "lease_owner": str(self._safe_get(AUTONOMOUS_WORKER_LEASE_KEY) or ""),
                    "last_heartbeat_at": _utcnow_iso(),
                }
            )
            snapshot = self.status()
            snapshot["distributed"] = distributed
        return snapshot

    def _interval_seconds(self) -> int:
        return max(5, int(getattr(self._settings, "autonomous_tick_interval_seconds", 30)))

    def _lease_ttl_seconds(self) -> int:
        return max(10, int(getattr(self._settings, "autonomous_runtime_lease_ttl_seconds", 90)))

    def _status_ttl_seconds(self) -> int:
        return max(30, int(getattr(self._settings, "autonomous_runtime_status_ttl_seconds", 300)))

    def _safe_get(self, key: str) -> str | None:
        with suppress(Exception):
            return self._redis.get(key)
        return None

    def _safe_set(self, key: str, value: str, *, ex: int | None = None, nx: bool = False) -> bool:
        try:
            return bool(self._redis.set(key, value, ex=ex, nx=nx))
        except TypeError:
            return bool(self._redis.set(key, value, ex=ex))
        except Exception:
            return False

    def _safe_delete(self, key: str) -> int:
        with suppress(Exception):
            return int(self._redis.delete(key) or 0)
        return 0

    def _load_json(self, key: str) -> dict[str, Any]:
        raw = self._safe_get(key)
        if not raw:
            return {}
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def _persist_distributed_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        status_row = self._load_json(AUTONOMOUS_WORKER_STATUS_KEY)
        status_row.update(payload)
        self._safe_set(
            AUTONOMOUS_WORKER_STATUS_KEY,
            json.dumps(status_row, ensure_ascii=True, sort_keys=True, default=str),
            ex=self._status_ttl_seconds(),
        )
        return status_row

    def _acquire_or_renew_lease(self) -> bool:
        lease_owner = str(self._safe_get(AUTONOMOUS_WORKER_LEASE_KEY) or "")
        if lease_owner == self._worker_id:
            self._safe_set(AUTONOMOUS_WORKER_LEASE_KEY, self._worker_id, ex=self._lease_ttl_seconds())
            return True
        return self._safe_set(
            AUTONOMOUS_WORKER_LEASE_KEY,
            self._worker_id,
            ex=self._lease_ttl_seconds(),
            nx=True,
        )

    def _release_lease_if_owned(self) -> None:
        if str(self._safe_get(AUTONOMOUS_WORKER_LEASE_KEY) or "") != self._worker_id:
            return
        self._safe_delete(AUTONOMOUS_WORKER_LEASE_KEY)


distributed_autonomous_scheduler = DistributedAutonomousScheduler()
