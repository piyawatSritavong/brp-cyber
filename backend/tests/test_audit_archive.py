from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.services import audit_archive


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

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self._counter += 1
        event_id = f"{self._counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrange(self, key: str, min: str = "-", max: str = "+", count: int | None = None):
        entries = self.streams.get(key, [])
        return entries[:count] if count is not None else entries

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]


def test_archive_chain_and_immutable_store(tmp_path: Path) -> None:
    fake = FakeRedis()
    audit_archive.redis_client = fake

    settings.control_plane_audit_archive_hmac_key = "test-key"
    settings.control_plane_audit_archive_dir = str(tmp_path / "audit_archive")
    settings.control_plane_immutable_store_dir = str(tmp_path / "immutable_store")

    payload = {"events": [{"id": "1-0"}], "source": "test"}

    r1 = audit_archive.archive_export_batch(payload, exported_count=1)
    r2 = audit_archive.archive_export_batch(payload, exported_count=1)

    assert r1["signature"] != ""
    assert r2["signature"] != ""

    status = audit_archive.archive_status(limit=10)
    assert status["count"] == 2

    verify = audit_archive.verify_archive_chain(limit=10)
    assert verify["valid"] is True
