from __future__ import annotations

from app.services import audit_recovery


class FakeRedis:
    def __init__(self) -> None:
        self.strings: dict[str, str] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self._counter = 0

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.strings[key] = value
        return True

    def exists(self, key: str) -> int:
        return 1 if key in self.strings else 0

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


def test_replay_failed_batches() -> None:
    fake = FakeRedis()
    audit_recovery.redis_client = fake

    audit_recovery.write_failed_batch({"events": [{"id": "1-0"}]}, "failed")
    audit_recovery.write_failed_batch({"events": [{"id": "2-0"}]}, "failed")

    sent = {"count": 0}

    def _sender(payload):
        sent["count"] += 1
        return 200

    first = audit_recovery.replay_failed_batches(limit=10, sender=_sender)
    assert first["replayed"] == 2
    assert sent["count"] == 2

    second = audit_recovery.replay_failed_batches(limit=10, sender=_sender)
    assert second["replayed"] == 0
    assert second["skipped"] >= 2

    # Acknowledge one batch and verify reconciliation view.
    ack = audit_recovery.acknowledge_failed_batch("1-0", "ack-123")
    assert ack["status"] == "acked"

    recon = audit_recovery.reconcile_failed_batches(limit=10)
    assert recon["total_failed_batches"] >= 2
    assert recon["acked_count"] >= 1
