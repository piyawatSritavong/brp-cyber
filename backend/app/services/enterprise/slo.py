from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.services.redis_client import redis_client

SLO_PREFIX = "tenant_slo"


def _slo_key(tenant_id: UUID) -> str:
    period = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{SLO_PREFIX}:{tenant_id}:{period}"


def record_http_result(tenant_id: UUID, duration_seconds: float, success: bool) -> None:
    key = _slo_key(tenant_id)
    redis_client.hincrby(key, "requests_total", 1)
    redis_client.hincrbyfloat(key, "latency_total_seconds", duration_seconds)
    if success:
        redis_client.hincrby(key, "requests_success", 1)
    else:
        redis_client.hincrby(key, "requests_failed", 1)
    redis_client.hset(key, mapping={"updated_at": datetime.now(timezone.utc).isoformat()})


def get_slo_snapshot(tenant_id: UUID) -> dict[str, float | str]:
    key = _slo_key(tenant_id)
    raw = redis_client.hgetall(key)

    total = int(raw.get("requests_total", "0"))
    success = int(raw.get("requests_success", "0"))
    failed = int(raw.get("requests_failed", "0"))
    latency_total = float(raw.get("latency_total_seconds", "0"))

    availability = (success / total) if total else 1.0
    latency_avg = (latency_total / total) if total else 0.0

    return {
        "tenant_id": str(tenant_id),
        "requests_total": float(total),
        "requests_success": float(success),
        "requests_failed": float(failed),
        "availability": round(availability, 6),
        "latency_avg_seconds": round(latency_avg, 6),
        "updated_at": raw.get("updated_at", ""),
    }
