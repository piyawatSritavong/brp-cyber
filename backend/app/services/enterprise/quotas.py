from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.core.config import settings
from app.services.redis_client import redis_client

TENANT_QUOTA_PREFIX = "tenant_quota"
TENANT_USAGE_PREFIX = "tenant_usage"


def _quota_key(tenant_id: UUID) -> str:
    return f"{TENANT_QUOTA_PREFIX}:{tenant_id}"


def _usage_key(tenant_id: UUID) -> str:
    return f"{TENANT_USAGE_PREFIX}:{tenant_id}"


def _period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def get_quota(tenant_id: UUID) -> dict[str, int]:
    raw = redis_client.hgetall(_quota_key(tenant_id))
    return {
        "events_per_month": int(raw.get("events_per_month", settings.tenant_default_events_per_month)),
        "actions_per_day": int(raw.get("actions_per_day", settings.tenant_default_actions_per_day)),
        "tokens_per_month": int(raw.get("tokens_per_month", settings.tenant_default_tokens_per_month)),
    }


def set_quota(tenant_id: UUID, events_per_month: int, actions_per_day: int, tokens_per_month: int) -> dict[str, int]:
    redis_client.hset(
        _quota_key(tenant_id),
        mapping={
            "events_per_month": str(events_per_month),
            "actions_per_day": str(actions_per_day),
            "tokens_per_month": str(tokens_per_month),
        },
    )
    return get_quota(tenant_id)


def get_usage(tenant_id: UUID) -> dict[str, int | str]:
    raw = redis_client.hgetall(_usage_key(tenant_id))
    return {
        "period": raw.get("period", _period()),
        "events": int(raw.get("events", "0")),
        "actions": int(raw.get("actions", "0")),
        "tokens": int(raw.get("tokens", "0")),
    }


def _ensure_period(tenant_id: UUID) -> None:
    usage = get_usage(tenant_id)
    if usage["period"] == _period():
        return
    redis_client.hset(_usage_key(tenant_id), mapping={"period": _period(), "events": "0", "actions": "0", "tokens": "0"})


def add_usage(tenant_id: UUID, events: int = 0, actions: int = 0, tokens: int = 0) -> dict[str, int | str]:
    _ensure_period(tenant_id)
    key = _usage_key(tenant_id)
    if events:
        redis_client.hincrby(key, "events", events)
    if actions:
        redis_client.hincrby(key, "actions", actions)
    if tokens:
        redis_client.hincrby(key, "tokens", tokens)
    redis_client.hset(key, mapping={"period": _period()})
    return get_usage(tenant_id)


def check_quota(tenant_id: UUID, events: int = 0, actions: int = 0, tokens: int = 0) -> dict[str, object]:
    quota = get_quota(tenant_id)
    usage = get_usage(tenant_id)

    events_ok = usage["events"] + events <= quota["events_per_month"]
    actions_ok = usage["actions"] + actions <= quota["actions_per_day"]
    tokens_ok = usage["tokens"] + tokens <= quota["tokens_per_month"]

    return {
        "allowed": events_ok and actions_ok and tokens_ok,
        "quota": quota,
        "usage": usage,
        "checks": {
            "events_ok": events_ok,
            "actions_ok": actions_ok,
            "tokens_ok": tokens_ok,
        },
    }
