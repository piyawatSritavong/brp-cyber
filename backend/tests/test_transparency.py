from __future__ import annotations

from app.core.config import settings
from app.services import control_plane_transparency as tr


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.strings: dict[str, str] = {}
        self.counter = 0

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

    def set(self, key: str, value: str) -> bool:
        self.strings[key] = value
        return True

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self.counter += 1
        event_id = f"{self.counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]


def test_publish_transparency_entry_filesystem() -> None:
    fake = FakeRedis()
    tr.redis_client = fake
    tr.publication_status = lambda limit=1: {
        "count": 1,
        "rows": [
            {
                "publication_id": "pub-1",
                "pack_id": "audit-pack-1",
                "manifest_path": "m1.json",
                "archive_object": "a1.tar.gz",
                "metadata_object": "a1.meta.json",
                "mode": "filesystem",
                "published_at": "2026-01-01T00:00:00+00:00",
                "valid": True,
            }
        ],
    }

    orig_mode = settings.control_plane_transparency_mode
    orig_dir = settings.control_plane_transparency_filesystem_dir
    try:
        settings.control_plane_transparency_mode = "filesystem"
        settings.control_plane_transparency_filesystem_dir = "./tmp/compliance/test_transparency"

        dry = tr.publish_transparency_entry(dry_run=True)
        assert dry["status"] == "dry_run"

        result = tr.publish_transparency_entry(dry_run=False)
        assert result["status"] == "published"

        status = tr.transparency_status(limit=10)
        assert status["count"] == 1
    finally:
        settings.control_plane_transparency_mode = orig_mode
        settings.control_plane_transparency_filesystem_dir = orig_dir
