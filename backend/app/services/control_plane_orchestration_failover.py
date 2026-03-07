from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Tenant
from app.services.notifier import send_telegram_message
from app.services.orchestrator import get_tenant_activation_state, pilot_incidents
from app.services.redis_client import redis_client

ORCH_FAILOVER_PROFILE_PREFIX = "control_plane_orchestration_failover_profile"
ORCH_FAILOVER_STATE_PREFIX = "control_plane_orchestration_failover_state"
ORCH_FAILOVER_EVENT_PREFIX = "control_plane_orchestration_failover_events"


def _profile_key(tenant_id: UUID) -> str:
    return f"{ORCH_FAILOVER_PROFILE_PREFIX}:{tenant_id}"


def _state_key(tenant_id: UUID) -> str:
    return f"{ORCH_FAILOVER_STATE_PREFIX}:{tenant_id}"


def _event_key(tenant_id: UUID) -> str:
    return f"{ORCH_FAILOVER_EVENT_PREFIX}:{tenant_id}"


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    if value is None:
        return default
    return bool(value)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _list_tenants(db: Session, limit: int) -> list[Tenant]:
    return db.query(Tenant).limit(max(1, limit)).all()


def _normalize_profile(payload: dict[str, Any]) -> dict[str, Any]:
    primary_region = str(payload.get("primary_region", "ap-southeast-1")).strip() or "ap-southeast-1"
    secondary_region = str(payload.get("secondary_region", "ap-southeast-2")).strip() or "ap-southeast-2"
    if secondary_region == primary_region:
        secondary_region = "ap-southeast-2" if primary_region != "ap-southeast-2" else "ap-southeast-1"
    return {
        "profile_version": str(payload.get("profile_version", "1.0")),
        "owner": str(payload.get("owner", "sre")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "primary_region": primary_region,
        "secondary_region": secondary_region,
        "auto_failover_enabled": _as_bool(payload.get("auto_failover_enabled"), False),
        "health_score_failover_threshold": max(1, min(100, _as_int(payload.get("health_score_failover_threshold"), 60))),
        "max_high_incidents_before_failover": max(1, _as_int(payload.get("max_high_incidents_before_failover"), 2)),
        "notify_on_failover": _as_bool(payload.get("notify_on_failover"), True),
    }


def upsert_orchestration_failover_profile(tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    profile = _normalize_profile(payload)
    redis_client.set(_profile_key(tenant_id), json.dumps(profile, ensure_ascii=True, sort_keys=True))

    state_raw = redis_client.hgetall(_state_key(tenant_id))
    if not state_raw:
        redis_client.hset(
            _state_key(tenant_id),
            mapping={
                "active_region": profile["primary_region"],
                "failover_count": "0",
                "last_failover_at": "",
                "last_reason": "",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    return {"tenant_id": str(tenant_id), "status": "upserted", "profile": profile}


def get_orchestration_failover_profile(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.get(_profile_key(tenant_id))
    if not raw:
        return {"tenant_id": str(tenant_id), "status": "default", "profile": _normalize_profile({})}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {"tenant_id": str(tenant_id), "status": "corrupted"}
    return {"tenant_id": str(tenant_id), "status": "ok", "profile": _normalize_profile(loaded)}


def get_orchestration_failover_state(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.hgetall(_state_key(tenant_id))
    profile = get_orchestration_failover_profile(tenant_id).get("profile", _normalize_profile({}))
    if not raw:
        return {
            "tenant_id": str(tenant_id),
            "active_region": profile["primary_region"],
            "failover_count": 0,
            "last_failover_at": "",
            "last_reason": "",
        }
    return {
        "tenant_id": str(tenant_id),
        "active_region": str(raw.get("active_region", profile["primary_region"])),
        "failover_count": _as_int(raw.get("failover_count"), 0),
        "last_failover_at": str(raw.get("last_failover_at", "")),
        "last_reason": str(raw.get("last_reason", "")),
    }


def _emit_failover_event(tenant_id: UUID, tenant_code: str, event_type: str, details: dict[str, Any]) -> None:
    redis_client.xadd(
        _event_key(tenant_id),
        {
            "tenant_id": str(tenant_id),
            "tenant_code": tenant_code,
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": json.dumps(details, ensure_ascii=True),
        },
        maxlen=100000,
        approximate=True,
    )


def _compute_health_signal(tenant_id: UUID, tenant_code: str) -> dict[str, Any]:
    activation = get_tenant_activation_state(tenant_id)
    incidents = pilot_incidents(tenant_id, limit=30)
    rows = list(incidents.get("rows", []))
    high_incidents = len([r for r in rows if str(r.get("severity", "")).lower() in {"high", "critical"}])
    consecutive_failures = _as_int(activation.get("consecutive_failures"), 0)
    score = 100

    status = str(activation.get("status", "inactive"))
    if status == "inactive":
        score -= 30
    elif status == "paused":
        score -= 20

    score -= min(30, consecutive_failures * 10)
    score -= min(40, high_incidents * 15)
    score = max(0, min(100, score))

    return {
        "tenant_id": str(tenant_id),
        "tenant_code": tenant_code,
        "activation_status": status,
        "consecutive_failures": consecutive_failures,
        "high_incidents": high_incidents,
        "health_score": score,
    }


def trigger_orchestration_failover_drill(
    tenant_id: UUID,
    tenant_code: str,
    *,
    reason: str = "manual_drill",
    dry_run: bool = True,
) -> dict[str, Any]:
    profile = get_orchestration_failover_profile(tenant_id).get("profile", _normalize_profile({}))
    state = get_orchestration_failover_state(tenant_id)
    from_region = str(state.get("active_region", profile["primary_region"]))
    to_region = profile["secondary_region"] if from_region == profile["primary_region"] else profile["primary_region"]

    event_details = {
        "reason": reason,
        "from_region": from_region,
        "to_region": to_region,
        "dry_run": dry_run,
    }
    if dry_run:
        _emit_failover_event(tenant_id, tenant_code, "failover_drill_dry_run", event_details)
        return {"tenant_id": str(tenant_id), "tenant_code": tenant_code, "status": "dry_run", **event_details}

    now_iso = datetime.now(timezone.utc).isoformat()
    next_count = int(state.get("failover_count", 0) or 0) + 1
    redis_client.hset(
        _state_key(tenant_id),
        mapping={
            "active_region": to_region,
            "failover_count": str(next_count),
            "last_failover_at": now_iso,
            "last_reason": reason,
            "updated_at": now_iso,
        },
    )
    _emit_failover_event(tenant_id, tenant_code, "failover_triggered", event_details)
    if bool(profile.get("notify_on_failover", True)):
        send_telegram_message(
            f"[BRP-Cyber] Orchestration failover tenant={tenant_code} from={from_region} to={to_region} reason={reason}"
        )
    return {
        "tenant_id": str(tenant_id),
        "tenant_code": tenant_code,
        "status": "failed_over",
        "from_region": from_region,
        "to_region": to_region,
        "failover_count": next_count,
    }


def evaluate_orchestration_failover_health(
    tenant_id: UUID,
    tenant_code: str,
    *,
    allow_auto_failover: bool = False,
) -> dict[str, Any]:
    profile = get_orchestration_failover_profile(tenant_id).get("profile", _normalize_profile({}))
    signal = _compute_health_signal(tenant_id, tenant_code)
    threshold = int(profile.get("health_score_failover_threshold", 60))
    max_incidents = int(profile.get("max_high_incidents_before_failover", 2))
    recommend = int(signal["health_score"]) <= threshold or int(signal["high_incidents"]) >= max_incidents

    result = {
        "status": "ok",
        "tenant_id": str(tenant_id),
        "tenant_code": tenant_code,
        "health": signal,
        "failover_recommended": recommend,
        "profile": profile,
        "auto_failover_executed": False,
    }
    _emit_failover_event(
        tenant_id,
        tenant_code,
        "health_evaluated",
        {
            "health_score": signal["health_score"],
            "high_incidents": signal["high_incidents"],
            "failover_recommended": recommend,
        },
    )

    if recommend and allow_auto_failover and bool(profile.get("auto_failover_enabled", False)):
        drill = trigger_orchestration_failover_drill(
            tenant_id,
            tenant_code,
            reason="auto_health_threshold",
            dry_run=False,
        )
        result["auto_failover_executed"] = drill.get("status") == "failed_over"
        result["auto_failover"] = drill
    return result


def orchestration_failover_events(tenant_id: UUID, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_event_key(tenant_id), count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row: dict[str, Any] = {"id": event_id}
        row.update(fields)
        try:
            row["details"] = json.loads(str(fields.get("details", "{}")))
        except json.JSONDecodeError:
            row["details"] = {}
        rows.append(row)
    return {"tenant_id": str(tenant_id), "count": len(rows), "rows": rows}


def orchestration_failover_enterprise_snapshot(db: Session, limit: int = 200) -> dict[str, Any]:
    tenants = _list_tenants(db, limit=max(1, limit))
    rows: list[dict[str, Any]] = []
    auto_candidates = 0
    unhealthy = 0
    for tenant in tenants:
        health = evaluate_orchestration_failover_health(tenant.id, tenant.tenant_code, allow_auto_failover=False)
        state = get_orchestration_failover_state(tenant.id)
        row = {
            "tenant_id": str(tenant.id),
            "tenant_code": tenant.tenant_code,
            "active_region": state.get("active_region", "unknown"),
            "failover_count": int(state.get("failover_count", 0) or 0),
            "health_score": int(health.get("health", {}).get("health_score", 0) or 0),
            "high_incidents": int(health.get("health", {}).get("high_incidents", 0) or 0),
            "failover_recommended": bool(health.get("failover_recommended", False)),
        }
        if row["failover_recommended"]:
            auto_candidates += 1
        if row["health_score"] <= 60:
            unhealthy += 1
        rows.append(row)
    rows.sort(key=lambda r: (not bool(r["failover_recommended"]), int(r["health_score"])))
    return {"count": len(rows), "failover_candidates": auto_candidates, "unhealthy_count": unhealthy, "rows": rows}
