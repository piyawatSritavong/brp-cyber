from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Tenant
from app.services.enterprise.cost_meter import get_cost
from app.services.enterprise.quotas import get_quota, get_usage, set_quota
from app.services.notifier import send_telegram_message
from app.services.redis_client import redis_client

ORCH_COST_GUARDRAIL_PROFILE_PREFIX = "control_plane_orchestration_cost_guardrail_profile"
ORCH_COST_GUARDRAIL_EVENT_PREFIX = "control_plane_orchestration_cost_guardrail_events"
ORCH_COST_ROUTING_OVERRIDE_PREFIX = "control_plane_orchestration_cost_routing_override"
ORCH_COST_THROTTLE_OVERRIDE_PREFIX = "control_plane_orchestration_cost_throttle_override"
ORCH_COST_ANOMALY_STATE_PREFIX = "control_plane_orchestration_cost_anomaly_state"


def _profile_key(tenant_id: UUID) -> str:
    return f"{ORCH_COST_GUARDRAIL_PROFILE_PREFIX}:{tenant_id}"


def _event_key(tenant_id: UUID) -> str:
    return f"{ORCH_COST_GUARDRAIL_EVENT_PREFIX}:{tenant_id}"


def _routing_override_key(tenant_id: UUID) -> str:
    return f"{ORCH_COST_ROUTING_OVERRIDE_PREFIX}:{tenant_id}"


def _throttle_override_key(tenant_id: UUID) -> str:
    return f"{ORCH_COST_THROTTLE_OVERRIDE_PREFIX}:{tenant_id}"


def _anomaly_state_key(tenant_id: UUID) -> str:
    return f"{ORCH_COST_ANOMALY_STATE_PREFIX}:{tenant_id}"


def _list_tenants(db: Session, limit: int) -> list[Tenant]:
    return db.query(Tenant).limit(max(1, limit)).all()


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    if value is None:
        return default
    return bool(value)


def _normalize_profile(payload: dict[str, Any]) -> dict[str, Any]:
    throttle_mode = str(payload.get("throttle_mode_on_anomaly", "conservative")).strip().lower()
    if throttle_mode not in {"conservative", "strict"}:
        throttle_mode = "conservative"
    return {
        "profile_version": str(payload.get("profile_version", "1.0")),
        "owner": str(payload.get("owner", "finops")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "monthly_cost_limit_usd": max(0.1, _as_float(payload.get("monthly_cost_limit_usd"), 50.0)),
        "monthly_token_limit": max(1000, _as_int(payload.get("monthly_token_limit"), 2_000_000)),
        "pressure_ratio_threshold": min(1.0, max(0.1, _as_float(payload.get("pressure_ratio_threshold"), 0.85))),
        "hard_stop_on_limit": _as_bool(payload.get("hard_stop_on_limit"), False),
        "force_fallback_on_pressure": _as_bool(payload.get("force_fallback_on_pressure"), True),
        "preemptive_throttle_on_anomaly": _as_bool(payload.get("preemptive_throttle_on_anomaly"), True),
        "anomaly_delta_threshold": min(3.0, max(0.01, _as_float(payload.get("anomaly_delta_threshold"), 0.2))),
        "anomaly_min_pressure_ratio": min(3.0, max(0.05, _as_float(payload.get("anomaly_min_pressure_ratio"), 0.5))),
        "anomaly_ema_alpha": min(1.0, max(0.05, _as_float(payload.get("anomaly_ema_alpha"), 0.4))),
        "throttle_mode_on_anomaly": throttle_mode,
        "notify_on_breach": _as_bool(payload.get("notify_on_breach"), True),
    }


def upsert_orchestration_cost_guardrail_profile(tenant_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    profile = _normalize_profile(payload)
    redis_client.set(_profile_key(tenant_id), json.dumps(profile, ensure_ascii=True, sort_keys=True))
    return {"tenant_id": str(tenant_id), "status": "upserted", "profile": profile}


def get_orchestration_cost_guardrail_profile(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.get(_profile_key(tenant_id))
    if not raw:
        return {"tenant_id": str(tenant_id), "status": "default", "profile": _normalize_profile({})}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {"tenant_id": str(tenant_id), "status": "corrupted"}
    return {"tenant_id": str(tenant_id), "status": "ok", "profile": _normalize_profile(loaded)}


def get_orchestration_cost_routing_override(tenant_id: UUID) -> dict[str, Any]:
    mode = get_orchestration_cost_routing_override_mode(tenant_id)
    return {"tenant_id": str(tenant_id), "routing_override": mode}


def get_orchestration_cost_routing_override_mode(tenant_id: UUID) -> str:
    return str(redis_client.get(_routing_override_key(tenant_id)) or "").strip().lower()


def get_orchestration_cost_throttle_override(tenant_id: UUID) -> dict[str, Any]:
    mode = get_orchestration_cost_throttle_override_mode(tenant_id)
    return {"tenant_id": str(tenant_id), "throttle_override": mode}


def get_orchestration_cost_throttle_override_mode(tenant_id: UUID) -> str:
    return str(redis_client.get(_throttle_override_key(tenant_id)) or "").strip().lower()


def get_orchestration_cost_anomaly_state(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.get(_anomaly_state_key(tenant_id))
    if not raw:
        return {"tenant_id": str(tenant_id), "status": "default", "state": {}}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {"tenant_id": str(tenant_id), "status": "corrupted", "state": {}}
    return {"tenant_id": str(tenant_id), "status": "ok", "state": loaded}


def _persist_anomaly_state(tenant_id: UUID, state: dict[str, Any]) -> None:
    redis_client.set(_anomaly_state_key(tenant_id), json.dumps(state, ensure_ascii=True, sort_keys=True))


def _emit_event(tenant_id: UUID, tenant_code: str, event_type: str, details: dict[str, Any]) -> None:
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


def evaluate_orchestration_cost_guardrail(
    tenant_id: UUID,
    tenant_code: str,
    *,
    apply_actions: bool = False,
) -> dict[str, Any]:
    profile = get_orchestration_cost_guardrail_profile(tenant_id).get("profile", _normalize_profile({}))
    cost = get_cost(tenant_id)
    usage = get_usage(tenant_id)
    quota = get_quota(tenant_id)

    monthly_cost = _as_float(cost.get("usd"), 0.0)
    monthly_tokens = _as_int(usage.get("tokens"), 0)
    cost_limit = _as_float(profile.get("monthly_cost_limit_usd"), 50.0)
    token_limit = _as_int(profile.get("monthly_token_limit"), 2_000_000)

    cost_ratio = (monthly_cost / cost_limit) if cost_limit > 0 else 1.0
    token_ratio = (monthly_tokens / token_limit) if token_limit > 0 else 1.0
    pressure_ratio = max(cost_ratio, token_ratio)

    breached = cost_ratio >= 1.0 or token_ratio >= 1.0
    pressure = pressure_ratio >= _as_float(profile.get("pressure_ratio_threshold"), 0.85)
    anomaly_state = get_orchestration_cost_anomaly_state(tenant_id).get("state", {})
    prev_ema = _as_float(anomaly_state.get("ema_pressure_ratio"), pressure_ratio)
    alpha = _as_float(profile.get("anomaly_ema_alpha"), 0.4)
    ema_pressure_ratio = (alpha * pressure_ratio) + ((1.0 - alpha) * prev_ema)
    anomaly_delta = pressure_ratio - prev_ema
    anomaly = (
        pressure_ratio >= _as_float(profile.get("anomaly_min_pressure_ratio"), 0.5)
        and anomaly_delta >= _as_float(profile.get("anomaly_delta_threshold"), 0.2)
    )
    consecutive_anomaly_count = _as_int(anomaly_state.get("consecutive_anomaly_count"), 0)
    if anomaly:
        consecutive_anomaly_count += 1
    else:
        consecutive_anomaly_count = 0
    _persist_anomaly_state(
        tenant_id,
        {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "prev_ema_pressure_ratio": round(prev_ema, 6),
            "ema_pressure_ratio": round(ema_pressure_ratio, 6),
            "last_pressure_ratio": round(pressure_ratio, 6),
            "anomaly_delta": round(anomaly_delta, 6),
            "anomaly": anomaly,
            "consecutive_anomaly_count": consecutive_anomaly_count,
        },
    )

    severity = "normal"
    if breached:
        severity = "critical"
    elif anomaly:
        severity = "high"
    elif pressure:
        severity = "high"

    actions: list[dict[str, Any]] = []
    if apply_actions:
        if pressure and _as_bool(profile.get("force_fallback_on_pressure"), True):
            redis_client.set(_routing_override_key(tenant_id), "fallback_only")
            actions.append({"action": "set_routing_override", "value": "fallback_only"})
        elif not pressure:
            redis_client.set(_routing_override_key(tenant_id), "")
            actions.append({"action": "clear_routing_override"})
        if anomaly and _as_bool(profile.get("preemptive_throttle_on_anomaly"), True):
            throttle_mode = str(profile.get("throttle_mode_on_anomaly", "conservative")).strip().lower()
            redis_client.set(_throttle_override_key(tenant_id), throttle_mode)
            actions.append({"action": "set_throttle_override", "value": throttle_mode})
        elif not anomaly:
            redis_client.set(_throttle_override_key(tenant_id), "")
            actions.append({"action": "clear_throttle_override"})
        if breached and _as_bool(profile.get("hard_stop_on_limit"), False):
            # clamp token quota to current usage to stop additional heavy token use this month
            new_tokens_quota = max(1000, monthly_tokens)
            set_quota(
                tenant_id,
                events_per_month=_as_int(quota.get("events_per_month"), 100000),
                actions_per_day=_as_int(quota.get("actions_per_day"), 500),
                tokens_per_month=new_tokens_quota,
            )
            actions.append({"action": "clamp_token_quota", "tokens_per_month": new_tokens_quota})

    result = {
        "status": "ok",
        "tenant_id": str(tenant_id),
        "tenant_code": tenant_code,
        "profile": profile,
        "metrics": {
            "monthly_cost_usd": round(monthly_cost, 6),
            "monthly_tokens": monthly_tokens,
            "cost_ratio": round(cost_ratio, 4),
            "token_ratio": round(token_ratio, 4),
            "pressure_ratio": round(pressure_ratio, 4),
            "anomaly_delta": round(anomaly_delta, 4),
        },
        "state": {
            "pressure": pressure,
            "breached": breached,
            "anomaly": anomaly,
            "consecutive_anomaly_count": consecutive_anomaly_count,
            "severity": severity,
            "routing_override": redis_client.get(_routing_override_key(tenant_id)) or "",
            "throttle_override": redis_client.get(_throttle_override_key(tenant_id)) or "",
        },
        "actions": actions,
    }
    _emit_event(tenant_id, tenant_code, "cost_guardrail_evaluated", result["state"] | result["metrics"])

    if breached and _as_bool(profile.get("notify_on_breach"), True):
        send_telegram_message(
            f"[BRP-Cyber] Cost guardrail breached tenant={tenant_code} "
            f"cost_usd={monthly_cost:.4f}/{cost_limit:.4f} tokens={monthly_tokens}/{token_limit}"
        )

    return result


def orchestration_cost_guardrail_events(tenant_id: UUID, limit: int = 100) -> dict[str, Any]:
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


def orchestration_cost_guardrail_enterprise_snapshot(
    db: Session,
    limit: int = 200,
    *,
    apply_actions: bool = False,
) -> dict[str, Any]:
    tenants = _list_tenants(db, limit=max(1, limit))
    rows: list[dict[str, Any]] = []
    breached_count = 0
    pressure_count = 0
    for tenant in tenants:
        eval_result = evaluate_orchestration_cost_guardrail(
            tenant.id,
            tenant.tenant_code,
            apply_actions=apply_actions,
        )
        state = eval_result.get("state", {})
        metrics = eval_result.get("metrics", {})
        row = {
            "tenant_id": str(tenant.id),
            "tenant_code": tenant.tenant_code,
            "severity": state.get("severity", "normal"),
            "breached": bool(state.get("breached", False)),
            "pressure": bool(state.get("pressure", False)),
            "anomaly": bool(state.get("anomaly", False)),
            "monthly_cost_usd": metrics.get("monthly_cost_usd", 0.0),
            "monthly_tokens": metrics.get("monthly_tokens", 0),
            "pressure_ratio": metrics.get("pressure_ratio", 0.0),
            "routing_override": state.get("routing_override", ""),
            "throttle_override": state.get("throttle_override", ""),
        }
        if row["breached"]:
            breached_count += 1
        if row["pressure"]:
            pressure_count += 1
        rows.append(row)
    rows.sort(key=lambda r: (not bool(r["breached"]), not bool(r["pressure"]), -float(r["pressure_ratio"])))
    return {
        "count": len(rows),
        "breached_count": breached_count,
        "pressure_count": pressure_count,
        "anomaly_count": sum(1 for row in rows if bool(row.get("anomaly", False))),
        "rows": rows,
    }
