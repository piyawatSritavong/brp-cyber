from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.core.config import settings
from app.services.redis_client import redis_client

COST_PREFIX = "tenant_cost"


def _cost_key(tenant_id: UUID) -> str:
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"{COST_PREFIX}:{tenant_id}:{period}"


def record_cost(tenant_id: UUID, tokens: int, model_name: str) -> dict[str, float | str]:
    # simplified meter: estimated USD per 1k tokens by class
    if model_name == settings.model_reasoning:
        unit_per_1k = settings.cost_reasoning_per_1k_tokens
    elif model_name == settings.model_processing:
        unit_per_1k = settings.cost_processing_per_1k_tokens
    else:
        unit_per_1k = settings.cost_fallback_per_1k_tokens

    increment = (tokens / 1000.0) * unit_per_1k
    key = _cost_key(tenant_id)
    redis_client.hincrbyfloat(key, "usd", increment)
    redis_client.hincrby(key, "tokens", tokens)
    redis_client.hset(key, mapping={"updated_at": datetime.now(timezone.utc).isoformat()})

    raw = redis_client.hgetall(key)
    return {
        "tenant_id": str(tenant_id),
        "period": key.split(":")[-1],
        "usd": round(float(raw.get("usd", "0")), 6),
        "tokens": float(raw.get("tokens", "0")),
    }


def get_cost(tenant_id: UUID) -> dict[str, float | str]:
    key = _cost_key(tenant_id)
    raw = redis_client.hgetall(key)
    return {
        "tenant_id": str(tenant_id),
        "period": key.split(":")[-1],
        "usd": round(float(raw.get("usd", "0")), 6),
        "tokens": float(raw.get("tokens", "0")),
        "updated_at": raw.get("updated_at", ""),
    }
