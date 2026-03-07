from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings
from app.services import control_plane_audit_pack_publication as pub


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.counter = 0

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self.counter += 1
        event_id = f"{self.counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]


def test_publish_latest_audit_pack_filesystem() -> None:
    fake = FakeRedis()
    pub.redis_client = fake

    base = Path("./tmp/compliance/test_pub")
    pack_dir = base / "audit-pack-1"
    pack_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = pack_dir / "manifest.json"
    evidence = pack_dir / "evidence.json"
    evidence.write_text(json.dumps({"ok": True}), encoding="utf-8")

    manifest = {
        "pack_id": "audit-pack-1",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "overall_pass": True,
        "artifacts": [{"name": evidence.name, "path": str(evidence), "sha256": pub._sha256_file(evidence), "size_bytes": evidence.stat().st_size}],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    pub.audit_pack_status = lambda limit=1: {
        "count": 1,
        "rows": [
            {
                "pack_id": "audit-pack-1",
                "generated_at": "2026-01-01T00:00:00+00:00",
                "pack_dir": str(pack_dir),
                "manifest_path": str(manifest_path),
                "manifest_sha256": pub._sha256_file(manifest_path),
                "overall_pass": True,
            }
        ],
    }

    pub.verify_external_audit_pack = lambda manifest_path: {"valid": True, "failure_count": 0}

    orig_mode = settings.control_plane_audit_pack_publication_mode
    orig_dir = settings.control_plane_audit_pack_publication_filesystem_dir
    orig_require = settings.control_plane_audit_pack_publication_require_valid_pack

    try:
        settings.control_plane_audit_pack_publication_mode = "filesystem"
        settings.control_plane_audit_pack_publication_filesystem_dir = "./tmp/compliance/test_published"
        settings.control_plane_audit_pack_publication_require_valid_pack = True

        dry = pub.publish_latest_audit_pack(dry_run=True)
        assert dry["status"] == "dry_run"

        result = pub.publish_latest_audit_pack(dry_run=False)
        assert result["status"] == "published"
        assert str(result["archive_object"]).endswith(".tar.gz")

        status = pub.publication_status(limit=10)
        assert status["count"] == 1
    finally:
        settings.control_plane_audit_pack_publication_mode = orig_mode
        settings.control_plane_audit_pack_publication_filesystem_dir = orig_dir
        settings.control_plane_audit_pack_publication_require_valid_pack = orig_require
