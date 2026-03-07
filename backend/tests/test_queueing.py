from __future__ import annotations

from uuid import uuid4

from app.core.config import settings
from app.services.enterprise import queueing


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.groups: dict[str, list[dict[str, object]]] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self._counter = 0

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self._counter += 1
        event_id = f"{self._counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        if key in self.groups:
            for g in self.groups[key]:
                g["lag"] = int(g.get("lag", 0)) + 1
        return event_id

    def xgroup_create(self, key: str, groupname: str, id: str = "0", mkstream: bool = False):
        if mkstream and key not in self.streams:
            self.streams[key] = []
        groups = self.groups.setdefault(key, [])
        for g in groups:
            if g["name"] == groupname:
                raise RuntimeError("BUSYGROUP")
        groups.append({"name": groupname, "lag": 0})

    def xinfo_stream(self, key: str) -> dict[str, int]:
        return {"length": len(self.streams.get(key, []))}

    def xinfo_groups(self, key: str):
        return self.groups.get(key, [])

    def hincrby(self, key: str, field: str, amount: int) -> int:
        bucket = self.hashes.setdefault(key, {})
        current = int(bucket.get(field, "0"))
        bucket[field] = str(current + amount)
        return int(bucket[field])

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(key, {}).update(mapping)
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))


def test_queue_partition_enqueue_and_autoscale() -> None:
    fake = FakeRedis()
    queueing.redis_client = fake

    settings.queue_partitions = 4
    settings.queue_stream_prefix = "scan_tasks"
    settings.queue_worker_group = "scan-workers"
    settings.autoscale_lag_per_worker_threshold = 2
    settings.autoscale_max_workers = 10

    groups = queueing.ensure_worker_groups()
    assert len(groups) == 4

    tenant_id = uuid4()
    for _ in range(5):
        queueing.enqueue_scan_task(tenant_id, "scan", {"target": "acb.example.com"})

    stats = queueing.queue_partition_stats()
    assert stats["total_length"] == 5
    assert stats["total_lag"] >= 5

    rec = queueing.autoscaling_recommendation(current_workers=1)
    assert rec["desired_workers"] >= 3


def test_worker_progress_metrics() -> None:
    fake = FakeRedis()
    queueing.redis_client = fake

    result = queueing.record_worker_progress("worker-1", processed=10, errors=1)
    assert result["processed"] == "10"
    assert result["errors"] == "1"
