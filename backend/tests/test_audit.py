from __future__ import annotations

from app.services import audit


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self._counter = 0

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self._counter += 1
        event_id = f"{self._counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]


def test_control_plane_audit_stream() -> None:
    fake = FakeRedis()
    audit.redis_client = fake

    event_id = audit.write_control_plane_audit(
        actor="admin",
        action="tenant_onboard",
        status="created",
        target="acb",
        details={"tenant_id": "t-1"},
    )
    assert event_id == "1-0"

    rows = audit.list_control_plane_audit(limit=10)
    assert len(rows) == 1
    assert rows[0]["action"] == "tenant_onboard"
