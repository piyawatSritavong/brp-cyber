from __future__ import annotations

from app.services import audit_export


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

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self._counter += 1
        event_id = f"{self._counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrange(self, key: str, min: str = "-", max: str = "+", count: int | None = None):
        entries = self.streams.get(key, [])
        if min.startswith("("):
            min_id = min[1:]
            filtered = [(eid, fields) for eid, fields in entries if eid > min_id]
        else:
            filtered = entries
        if count is not None:
            return filtered[:count]
        return filtered


def test_audit_export_success_and_status() -> None:
    fake = FakeRedis()
    audit_export.redis_client = fake

    fake.xadd("control_plane_audit", {"timestamp": "t1", "actor": "admin", "action": "x", "status": "ok", "target": "a", "details": "{}"})
    fake.xadd("control_plane_audit", {"timestamp": "t2", "actor": "admin", "action": "y", "status": "ok", "target": "b", "details": "{}"})

    sent = {}

    def _sender(payload):
        sent["count"] = len(payload["events"])
        return 200

    result = audit_export.export_control_plane_audit_to_siem(batch_size=100, sender=_sender)
    assert result["status"] == "success"
    assert result["exported"] == 2
    assert sent["count"] == 2

    status = audit_export.get_export_status()
    assert status["exported_events"] == 2
    assert status["successful_batches"] == 1


def test_audit_export_no_new_events() -> None:
    fake = FakeRedis()
    audit_export.redis_client = fake

    result = audit_export.export_control_plane_audit_to_siem(batch_size=50, sender=lambda payload: 200)
    assert result["status"] == "no_new_events"
