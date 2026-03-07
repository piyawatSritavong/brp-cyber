from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import settings
from app.services.enterprise.queueing import autoscaling_recommendation
from app.services.redis_client import redis_client

AUTOSCALER_TARGET_KEY = "autoscaler:target_workers"
AUTOSCALER_CURRENT_KEY = "autoscaler:current_workers"
AUTOSCALER_COOLDOWN_KEY = "autoscaler:cooldown"
AUTOSCALER_HISTORY_STREAM = "autoscaler:history"


def get_status() -> dict[str, int | str]:
    current_workers = int(redis_client.get(AUTOSCALER_CURRENT_KEY) or settings.autoscale_min_workers)
    target_workers = int(redis_client.get(AUTOSCALER_TARGET_KEY) or current_workers)
    recommendation = autoscaling_recommendation(current_workers=current_workers)
    cooldown_active = bool(redis_client.exists(AUTOSCALER_COOLDOWN_KEY))

    return {
        "current_workers": current_workers,
        "target_workers": target_workers,
        "cooldown_active": "1" if cooldown_active else "0",
        "desired_workers": int(recommendation["desired_workers"]),
        "scale_delta": int(recommendation["scale_delta"]),
        "total_lag": int(recommendation["total_lag"]),
    }


def reconcile(current_workers: int | None = None) -> dict[str, int | str]:
    if current_workers is None:
        current_workers = int(redis_client.get(AUTOSCALER_CURRENT_KEY) or settings.autoscale_min_workers)

    current_workers = max(settings.autoscale_min_workers, current_workers)
    redis_client.set(AUTOSCALER_CURRENT_KEY, str(current_workers))

    recommendation = autoscaling_recommendation(current_workers=current_workers)
    desired_workers = max(settings.autoscale_min_workers, int(recommendation["desired_workers"]))

    cooldown_active = bool(redis_client.exists(AUTOSCALER_COOLDOWN_KEY))
    action = "noop"

    if desired_workers != current_workers and not cooldown_active:
        redis_client.set(AUTOSCALER_TARGET_KEY, str(desired_workers))
        redis_client.set(AUTOSCALER_COOLDOWN_KEY, "1", ex=settings.autoscale_apply_cooldown_seconds)
        action = "scale_up" if desired_workers > current_workers else "scale_down"

    redis_client.xadd(
        AUTOSCALER_HISTORY_STREAM,
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_workers": str(current_workers),
            "desired_workers": str(desired_workers),
            "action": action,
            "total_lag": str(recommendation["total_lag"]),
        },
        maxlen=10000,
        approximate=True,
    )

    return {
        "current_workers": current_workers,
        "desired_workers": desired_workers,
        "action": action,
        "cooldown_active": "1" if cooldown_active else "0",
        "total_lag": int(recommendation["total_lag"]),
    }


def history(limit: int = 100) -> list[dict[str, str]]:
    entries = redis_client.xrevrange(AUTOSCALER_HISTORY_STREAM, count=max(1, limit))
    result: list[dict[str, str]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        result.append(row)
    return result
