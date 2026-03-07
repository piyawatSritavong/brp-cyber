from __future__ import annotations

from uuid import UUID

from app.core.config import settings
from app.services.redis_client import redis_client

BLUE_POLICY_PREFIX = "blue_policy"
STRATEGY_PREFIX = "tenant_strategy"
APPROVAL_MODE_PREFIX = "tenant_approval_mode"
PENDING_ACTION_PREFIX = "tenant_pending_action"


def _blue_key(tenant_id: UUID) -> str:
    return f"{BLUE_POLICY_PREFIX}:{tenant_id}"


def _strategy_key(tenant_id: UUID) -> str:
    return f"{STRATEGY_PREFIX}:{tenant_id}"


def _approval_mode_key(tenant_id: UUID) -> str:
    return f"{APPROVAL_MODE_PREFIX}:{tenant_id}"


def _pending_action_key(tenant_id: UUID, action_id: str) -> str:
    return f"{PENDING_ACTION_PREFIX}:{tenant_id}:{action_id}"


def get_blue_policy(tenant_id: UUID) -> dict[str, int]:
    raw = redis_client.hgetall(_blue_key(tenant_id))
    return {
        "failed_login_threshold_per_minute": int(raw.get("failed_login_threshold_per_minute", settings.blue_failed_login_threshold_per_minute)),
        "failure_window_seconds": int(raw.get("failure_window_seconds", settings.blue_failure_window_seconds)),
        "incident_cooldown_seconds": int(raw.get("incident_cooldown_seconds", settings.blue_incident_cooldown_seconds)),
    }


def set_blue_policy(
    tenant_id: UUID,
    failed_login_threshold_per_minute: int,
    failure_window_seconds: int,
    incident_cooldown_seconds: int,
) -> dict[str, int]:
    key = _blue_key(tenant_id)
    redis_client.hset(
        key,
        mapping={
            "failed_login_threshold_per_minute": str(failed_login_threshold_per_minute),
            "failure_window_seconds": str(failure_window_seconds),
            "incident_cooldown_seconds": str(incident_cooldown_seconds),
        },
    )
    return get_blue_policy(tenant_id)


def get_strategy_profile(tenant_id: UUID) -> str:
    return redis_client.get(_strategy_key(tenant_id)) or "balanced"


def set_strategy_profile(tenant_id: UUID, strategy_profile: str) -> str:
    redis_client.set(_strategy_key(tenant_id), strategy_profile)
    return strategy_profile


def is_approval_mode_enabled(tenant_id: UUID) -> bool:
    value = redis_client.get(_approval_mode_key(tenant_id))
    return value == "1"


def set_approval_mode(tenant_id: UUID, enabled: bool) -> bool:
    redis_client.set(_approval_mode_key(tenant_id), "1" if enabled else "0")
    return enabled


def save_pending_action(tenant_id: UUID, action_id: str, payload: dict[str, str]) -> dict[str, str]:
    key = _pending_action_key(tenant_id, action_id)
    redis_client.hset(key, mapping=payload)
    return get_pending_action(tenant_id, action_id)


def get_pending_action(tenant_id: UUID, action_id: str) -> dict[str, str]:
    key = _pending_action_key(tenant_id, action_id)
    return redis_client.hgetall(key)


def list_pending_actions(tenant_id: UUID, limit: int = 100) -> list[dict[str, str]]:
    pattern = f"{PENDING_ACTION_PREFIX}:{tenant_id}:*"
    action_keys = redis_client.keys(pattern)[: max(1, limit)]
    actions: list[dict[str, str]] = []
    for key in action_keys:
        raw = redis_client.hgetall(key)
        if raw:
            actions.append(raw)
    return actions
