from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.services import audit_offload


class FakeRedis:
    def __init__(self) -> None:
        self.strings: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self._counter = 0

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.strings[key] = value
        return True

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(key, {}).update(mapping)
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def hincrby(self, key: str, field: str, amount: int) -> int:
        bucket = self.hashes.setdefault(key, {})
        current = int(bucket.get(field, "0"))
        bucket[field] = str(current + amount)
        return int(bucket[field])

    def xrange(self, key: str, min: str = "-", max: str = "+", count: int | None = None):
        entries = self.streams.get(key, [])
        if min.startswith("("):
            min_id = min[1:]
            filtered = [(eid, fields) for eid, fields in entries if eid > min_id]
        else:
            filtered = entries
        return filtered[:count] if count is not None else filtered

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self._counter += 1
        event_id = f"{self._counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id


def test_filesystem_offload(tmp_path: Path) -> None:
    fake = FakeRedis()
    audit_offload.redis_client = fake

    settings.control_plane_offload_mode = "filesystem"
    settings.control_plane_offload_filesystem_dir = str(tmp_path / "offload")

    fake.xadd("control_plane_audit_archive", {"signature": "abc123", "payload_hash": "h1", "generated_at": "t", "exported_count": "1", "prev_signature": ""})
    fake.xadd("control_plane_audit_archive", {"signature": "def456", "payload_hash": "h2", "generated_at": "t", "exported_count": "1", "prev_signature": "abc123"})

    result = audit_offload.offload_archive_batches(limit=100)
    assert result["status"] == "success"
    assert result["offloaded"] == 2

    status = audit_offload.offload_status()
    assert status["offloaded_records"] == 2
