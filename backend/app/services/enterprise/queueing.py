from __future__ import annotations

import json
import zlib
from datetime import datetime, timezone
from uuid import UUID

from app.core.config import settings
from app.services.redis_client import redis_client

WORKER_METRIC_PREFIX = "worker_metrics"


def partition_for_tenant(tenant_id: UUID) -> int:
    hashed = zlib.crc32(str(tenant_id).encode("utf-8"))
    partitions = max(1, settings.queue_partitions)
    return hashed % partitions


def stream_name(partition: int) -> str:
    return f"{settings.queue_stream_prefix}:p{partition}"


def stream_names() -> list[str]:
    return [stream_name(i) for i in range(max(1, settings.queue_partitions))]


def enqueue_scan_task(tenant_id: UUID, task_type: str, payload: dict[str, object]) -> dict[str, str | int]:
    partition = partition_for_tenant(tenant_id)
    stream = stream_name(partition)
    body = {
        "tenant_id": str(tenant_id),
        "task_type": task_type,
        "payload": json.dumps(payload),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    event_id = redis_client.xadd(stream, body, maxlen=1_000_000, approximate=True)
    return {"stream": stream, "partition": partition, "event_id": event_id}


def ensure_worker_groups() -> dict[str, str]:
    result: dict[str, str] = {}
    for stream in stream_names():
        try:
            redis_client.xgroup_create(stream, settings.queue_worker_group, id="0", mkstream=True)
            result[stream] = "created"
        except Exception:
            result[stream] = "exists_or_failed"
    return result


def queue_partition_stats() -> dict[str, object]:
    partitions: list[dict[str, object]] = []
    total_lag = 0
    total_length = 0

    for idx, stream in enumerate(stream_names()):
        info = redis_client.xinfo_stream(stream)
        length = int(info.get("length", 0))
        groups = redis_client.xinfo_groups(stream)
        group_lag = 0
        for group in groups:
            if group.get("name") == settings.queue_worker_group:
                group_lag = int(group.get("lag", 0) or 0)
                break

        partitions.append(
            {
                "partition": idx,
                "stream": stream,
                "length": length,
                "lag": group_lag,
            }
        )
        total_lag += group_lag
        total_length += length

    return {
        "partitions": partitions,
        "total_lag": total_lag,
        "total_length": total_length,
    }


def autoscaling_recommendation(current_workers: int) -> dict[str, int | float]:
    stats = queue_partition_stats()
    total_lag = int(stats["total_lag"])

    threshold = max(1, settings.autoscale_lag_per_worker_threshold)
    desired = max(1, (total_lag // threshold) + (1 if total_lag % threshold else 0))
    desired = min(desired, settings.autoscale_max_workers)

    scale_delta = desired - current_workers

    return {
        "current_workers": current_workers,
        "desired_workers": desired,
        "scale_delta": scale_delta,
        "total_lag": total_lag,
        "lag_per_worker_threshold": threshold,
    }


def record_worker_progress(worker_id: str, processed: int, errors: int) -> dict[str, str]:
    key = f"{WORKER_METRIC_PREFIX}:{worker_id}"
    redis_client.hincrby(key, "processed", processed)
    redis_client.hincrby(key, "errors", errors)
    redis_client.hset(key, mapping={"updated_at": datetime.now(timezone.utc).isoformat()})
    return redis_client.hgetall(key)
