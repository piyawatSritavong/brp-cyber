from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from itertools import cycle
from typing import Any
from uuid import UUID, uuid4

from app.core.config import settings
from app.services.blue_detection import process_auth_login_event
from app.services.event_store import persist_event
from app.services.redis_client import redis_client
from schemas.events import EventMetadata, RedEvent
from schemas.ingest import AuthLoginEvent
from schemas.red_sim import RedSimulationRunRequest, RedSimulationScheduleRequest

RED_SCENARIO_LIBRARY: dict[str, dict[str, str]] = {
    "credential_stuffing_sim": {
        "tactic": "auth_burst_sim",
        "description": "Simulated repeated login failures from distributed IPs",
    },
    "slow_bruteforce_sim": {
        "tactic": "auth_slow_burst_sim",
        "description": "Low-rate repeated login attempts to test slow-burst detection",
    },
    "admin_endpoint_probe_sim": {
        "tactic": "admin_login_probe_sim",
        "description": "Simulated probing on admin/login assets with failed auth outcomes",
    },
}

RED_SCHEDULE_STREAM_KEY = "red_sim_schedule"


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _target_is_allowed(target_asset: str) -> bool:
    allowlist = _parse_csv(settings.red_allowed_targets)
    if not allowlist:
        return False
    normalized = target_asset.strip().lower()
    return any(normalized == allowed.lower() for allowed in allowlist)


def _run_source_ips(request: RedSimulationRunRequest) -> list[str]:
    if request.source_ips:
        return request.source_ips
    default_ips = _parse_csv(settings.red_default_source_ips)
    return default_ips or ["203.0.113.10"]


def _run_usernames(request: RedSimulationRunRequest) -> list[str]:
    if request.usernames:
        return request.usernames
    default_users = _parse_csv(settings.red_default_usernames)
    return default_users or ["admin"]


def _scenario_tactic(scenario_name: str) -> str:
    scenario = RED_SCENARIO_LIBRARY.get(scenario_name)
    return scenario["tactic"] if scenario else "custom_sim_tactic"


def list_scenarios() -> dict[str, Any]:
    return {"count": len(RED_SCENARIO_LIBRARY), "scenarios": RED_SCENARIO_LIBRARY}


def run_simulation(request: RedSimulationRunRequest) -> dict[str, Any]:
    if not _target_is_allowed(request.target_asset):
        return {
            "status": "rejected",
            "reason": "target_not_allowlisted",
            "target_asset": request.target_asset,
        }

    capped_events = min(request.events_count, settings.red_max_events_per_run)
    source_ips = _run_source_ips(request)
    usernames = _run_usernames(request)
    src_cycle = cycle(source_ips)
    user_cycle = cycle(usernames)

    run_correlation_id = uuid4()

    started_event = RedEvent(
        metadata=EventMetadata(
            tenant_id=request.tenant_id,
            correlation_id=run_correlation_id,
            trace_id=uuid4(),
            source="red_simulator",
            timestamp=datetime.now(timezone.utc),
        ),
        scenario_name=request.scenario_name,
        target_asset=request.target_asset,
        tactic=_scenario_tactic(request.scenario_name),
        outcome="started",
        safety_boundary_ok=True,
    )
    persist_event(started_event)

    simulation_results: list[dict[str, str]] = []
    delay_seconds = max(settings.red_min_delay_ms, 0) / 1000.0

    for _ in range(capped_events):
        source_ip = next(src_cycle)
        username = next(user_cycle)

        red_tick_event = RedEvent(
            metadata=EventMetadata(
                tenant_id=request.tenant_id,
                correlation_id=run_correlation_id,
                trace_id=uuid4(),
                source="red_simulator",
                timestamp=datetime.now(timezone.utc),
            ),
            scenario_name=request.scenario_name,
            target_asset=request.target_asset,
            tactic=_scenario_tactic(request.scenario_name),
            outcome="partial",
            safety_boundary_ok=True,
        )
        persist_event(red_tick_event)

        blue_result = process_auth_login_event(
            AuthLoginEvent(
                tenant_id=request.tenant_id,
                timestamp=datetime.now(timezone.utc),
                source_ip=source_ip,
                username=username,
                success=False,
                auth_source="red_simulation",
            )
        )
        simulation_results.append(
            {
                "source_ip": source_ip,
                "username": username,
                "blue_status": blue_result["status"],
                "blue_reason": blue_result["reason"],
            }
        )

        if delay_seconds > 0:
            time.sleep(delay_seconds)

    completed_event = RedEvent(
        metadata=EventMetadata(
            tenant_id=request.tenant_id,
            correlation_id=run_correlation_id,
            trace_id=uuid4(),
            source="red_simulator",
            timestamp=datetime.now(timezone.utc),
        ),
        scenario_name=request.scenario_name,
        target_asset=request.target_asset,
        tactic=_scenario_tactic(request.scenario_name),
        outcome="completed",
        safety_boundary_ok=True,
    )
    persist_event(completed_event)

    return {
        "status": "completed",
        "scenario_name": request.scenario_name,
        "target_asset": request.target_asset,
        "requested_events": request.events_count,
        "executed_events": capped_events,
        "correlation_id": str(run_correlation_id),
        "results": simulation_results,
    }


def schedule_simulation(request: RedSimulationScheduleRequest) -> dict[str, str]:
    payload = {
        "tenant_id": str(request.tenant_id),
        "scenario_name": request.scenario_name,
        "target_asset": request.target_asset,
        "events_count": str(request.events_count),
        "run_at": request.run_at.astimezone(timezone.utc).isoformat(),
        "source_ips": json.dumps(request.source_ips or []),
        "usernames": json.dumps(request.usernames or []),
    }
    job_id = redis_client.xadd(RED_SCHEDULE_STREAM_KEY, payload, maxlen=50000, approximate=True)
    return {"status": "scheduled", "job_id": job_id}


def process_due_schedules(limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(RED_SCHEDULE_STREAM_KEY, count=max(1, limit))
    now = datetime.now(timezone.utc)

    processed = 0
    skipped = 0
    for job_id, fields in reversed(entries):
        job_status_key = f"red_sim_job_status:{job_id}"
        if redis_client.exists(job_status_key):
            skipped += 1
            continue

        run_at_raw = fields.get("run_at")
        if not run_at_raw:
            skipped += 1
            continue

        run_at = datetime.fromisoformat(run_at_raw.replace("Z", "+00:00")).astimezone(timezone.utc)
        if run_at > now:
            skipped += 1
            continue

        request = RedSimulationRunRequest(
            tenant_id=UUID(fields["tenant_id"]),
            scenario_name=fields["scenario_name"],
            target_asset=fields["target_asset"],
            events_count=int(fields.get("events_count", "20")),
            source_ips=json.loads(fields.get("source_ips", "[]")) or None,
            usernames=json.loads(fields.get("usernames", "[]")) or None,
        )
        run_simulation(request)
        redis_client.set(job_status_key, "done", ex=60 * 60 * 24 * 30)
        processed += 1

    return {"processed": processed, "skipped": skipped}
