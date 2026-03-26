from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import orchestrator as orchestrator_api
from app.main import app


class StubScheduler:
    def status(self) -> dict[str, object]:
        return {"mode": "worker", "distributed_worker_expected": True}

    def start_control(self) -> dict[str, object]:
        return {"action": "external_worker_required", "command": "python backend/scripts/run_autonomous_scheduler_worker.py"}

    def stop_control(self, reason: str = "api_stop_request") -> dict[str, object]:
        return {"action": "stop_requested", "reason": reason}

    def run_once_control(self) -> dict[str, object]:
        return {"action": "external_worker_required", "command": "python backend/scripts/run_autonomous_scheduler_worker.py --once"}


def test_autonomous_api_uses_distributed_scheduler_control_surface() -> None:
    original = orchestrator_api.distributed_autonomous_scheduler
    orchestrator_api.distributed_autonomous_scheduler = StubScheduler()
    try:
        with TestClient(app) as client:
            status = client.get("/orchestrator/autonomous/status")
            assert status.status_code == 200
            assert status.json()["mode"] == "worker"

            start = client.post("/orchestrator/autonomous/start")
            assert start.status_code == 200
            assert start.json()["action"] == "external_worker_required"

            stop = client.post("/orchestrator/autonomous/stop")
            assert stop.status_code == 200
            assert stop.json()["action"] == "stop_requested"

            run_once = client.post("/orchestrator/autonomous/run-once")
            assert run_once.status_code == 200
            assert run_once.json()["action"] == "external_worker_required"
    finally:
        orchestrator_api.distributed_autonomous_scheduler = original
