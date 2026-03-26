from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.main import app
from app.services import blue_detection, event_store, orchestrator, policy_store, red_simulator

TEST_REDIS_DB = 14


def _redis_test_url(redis_url: str, db: int = TEST_REDIS_DB) -> str:
    parts = urlsplit(redis_url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{db}", parts.query, parts.fragment))


@pytest.fixture()
def live_red_orchestrator_runtime() -> Redis:
    client = Redis.from_url(_redis_test_url(settings.redis_url), decode_responses=True)
    try:
        client.ping()
        client.flushdb()
    except RedisError as exc:
        with suppress(Exception):
            client.close()
        pytest.skip(f"live redis unavailable for red/orchestrator integration test: {exc}")

    orig_red_redis = red_simulator.redis_client
    orig_blue_redis = blue_detection.redis_client
    orig_event_redis = event_store.redis_client
    orig_policy_redis = policy_store.redis_client
    orig_orchestrator_redis = orchestrator.redis_client
    orig_red_allowed_targets = settings.red_allowed_targets
    orig_red_default_source_ips = settings.red_default_source_ips
    orig_red_default_usernames = settings.red_default_usernames
    orig_red_max_events = settings.red_max_events_per_run
    orig_red_delay = settings.red_min_delay_ms
    orig_block_ip = blue_detection.block_ip
    orig_blue_notify = blue_detection.send_telegram_message
    orig_orchestrator_notify = orchestrator.send_telegram_message

    red_simulator.redis_client = client
    blue_detection.redis_client = client
    event_store.redis_client = client
    policy_store.redis_client = client
    orchestrator.redis_client = client
    blue_detection.block_ip = lambda tenant_id, ip, reason: True
    blue_detection.send_telegram_message = lambda message: True
    orchestrator.send_telegram_message = lambda message: True
    settings.red_allowed_targets = "acb.example.com/admin-login"
    settings.red_default_source_ips = "203.0.113.20"
    settings.red_default_usernames = "admin"
    settings.red_max_events_per_run = 20
    settings.red_min_delay_ms = 0

    try:
        yield client
    finally:
        red_simulator.redis_client = orig_red_redis
        blue_detection.redis_client = orig_blue_redis
        event_store.redis_client = orig_event_redis
        policy_store.redis_client = orig_policy_redis
        orchestrator.redis_client = orig_orchestrator_redis
        blue_detection.block_ip = orig_block_ip
        blue_detection.send_telegram_message = orig_blue_notify
        orchestrator.send_telegram_message = orig_orchestrator_notify
        settings.red_allowed_targets = orig_red_allowed_targets
        settings.red_default_source_ips = orig_red_default_source_ips
        settings.red_default_usernames = orig_red_default_usernames
        settings.red_max_events_per_run = orig_red_max_events
        settings.red_min_delay_ms = orig_red_delay
        with suppress(RedisError):
            client.flushdb()
        with suppress(Exception):
            client.close()


def test_red_sim_live_redis_schedule_tick_api_roundtrip(live_red_orchestrator_runtime: Redis) -> None:
    live_redis = live_red_orchestrator_runtime
    tenant_id = uuid4()
    tenant_str = str(tenant_id)
    now = datetime.now(timezone.utc)

    with TestClient(app) as client:
        overdue = client.post(
            "/red-sim/schedule",
            json={
                "tenant_id": tenant_str,
                "scenario_name": "credential_stuffing_sim",
                "target_asset": "acb.example.com/admin-login",
                "events_count": 12,
                "run_at": (now - timedelta(seconds=2)).isoformat(),
                "source_ips": ["203.0.113.20"],
                "usernames": ["admin"],
            },
        )
        assert overdue.status_code == 200
        overdue_data = overdue.json()
        assert overdue_data["status"] == "scheduled"

        future = client.post(
            "/red-sim/schedule",
            json={
                "tenant_id": tenant_str,
                "scenario_name": "slow_bruteforce_sim",
                "target_asset": "acb.example.com/admin-login",
                "events_count": 5,
                "run_at": (now + timedelta(minutes=10)).isoformat(),
                "source_ips": ["203.0.113.21"],
                "usernames": ["ops"],
            },
        )
        assert future.status_code == 200

        tick = client.post("/red-sim/tick?limit=50")
        assert tick.status_code == 200
        tick_data = tick.json()
        assert tick_data["processed"] == 1
        assert tick_data["skipped"] >= 1

        replay = client.post("/red-sim/tick?limit=50")
        assert replay.status_code == 200
        assert replay.json()["processed"] == 0

    assert live_redis.get(f"red_sim_job_status:{overdue_data['job_id']}") == "done"

    security_rows = live_redis.xrevrange("security_events", count=200)
    tenant_event_types = [fields.get("event_type", "") for _, fields in security_rows if fields.get("tenant_id") == tenant_str]
    assert tenant_event_types.count("red_event") >= 2
    assert "detection_event" in tenant_event_types
    assert "response_event" in tenant_event_types


def test_orchestrator_live_redis_approval_workflow_api_roundtrip(live_red_orchestrator_runtime: Redis) -> None:
    orig_run = orchestrator.run_simulation
    orig_report = orchestrator.generate_daily_report
    orig_guardrail = orchestrator.evaluate_orchestration_cost_guardrail
    orig_get_throttle = orchestrator.get_orchestration_cost_throttle_override_mode

    orchestrator.run_simulation = lambda request: {
        "status": "completed",
        "scenario_name": request.scenario_name,
        "executed_events": request.events_count,
    }
    orchestrator.generate_daily_report = lambda tenant_id, limit=5000: {
        "report_id": "live-approval-report",
        "summary": "approval workflow live test",
        "kpi": {
            "mttd_seconds": 20,
            "mttr_seconds": 120,
            "detection_coverage": 0.8,
            "blocked_before_impact_rate": 0.4,
            "mitigated_count": 4,
            "detected_count": 8,
            "attack_count": 10,
        },
    }
    orchestrator.evaluate_orchestration_cost_guardrail = lambda tenant_id, tenant_code, apply_actions=True: {
        "status": "ok",
        "state": {"severity": "low"},
        "metrics": {},
        "actions": [],
    }
    orchestrator.get_orchestration_cost_throttle_override_mode = lambda tenant_id: ""

    try:
        tenant_id = uuid4()
        tenant_str = str(tenant_id)

        with TestClient(app) as client:
            activate = client.post(
                "/orchestrator/activate",
                json={
                    "tenant_id": tenant_str,
                    "target_asset": "acb.example.com/admin-login",
                    "red_scenario_name": "credential_stuffing_sim",
                    "red_events_count": 20,
                    "strategy_profile": "balanced",
                    "cycle_interval_seconds": 60,
                    "approval_mode": True,
                },
            )
            assert activate.status_code == 200
            assert activate.json()["status"] == "active"

            tick = client.post("/orchestrator/tick?limit=50")
            assert tick.status_code == 200
            tick_data = tick.json()
            assert tick_data["executed_count"] == 1
            assert tick_data["executed"][0]["result_status"] == "ok"

            activation = client.get(f"/orchestrator/activation/{tenant_str}")
            assert activation.status_code == 200
            activation_data = activation.json()
            assert activation_data["run_count"] == 1
            assert activation_data["last_cycle_index"] == 1

            state = client.get(f"/orchestrator/state/{tenant_str}")
            assert state.status_code == 200
            state_data = state.json()
            assert state_data["approval_mode"] is True
            assert state_data["blue_policy"]["failed_login_threshold_per_minute"] == 10
            assert len(state_data["pending_actions"]) == 1
            action_id = state_data["pending_actions"][0]["action_id"]
            assert state_data["pending_actions"][0]["status"] == "pending_approval"

            approve = client.post(
                "/orchestrator/approve",
                json={"tenant_id": tenant_str, "action_id": action_id, "approve": True},
            )
            assert approve.status_code == 200
            approve_data = approve.json()
            assert approve_data["status"] == "applied"
            assert approve_data["blue_policy"]["failed_login_threshold_per_minute"] == 9

            state_after = client.get(f"/orchestrator/state/{tenant_str}")
            assert state_after.status_code == 200
            state_after_data = state_after.json()
            assert state_after_data["blue_policy"]["failed_login_threshold_per_minute"] == 9
            assert state_after_data["pending_actions"][0]["status"] == "applied"
    finally:
        orchestrator.run_simulation = orig_run
        orchestrator.generate_daily_report = orig_report
        orchestrator.evaluate_orchestration_cost_guardrail = orig_guardrail
        orchestrator.get_orchestration_cost_throttle_override_mode = orig_get_throttle
