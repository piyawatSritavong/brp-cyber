from __future__ import annotations

from app.core.config import settings
from app.services.enterprise import autoscaler


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

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]


def test_autoscaler_reconcile_and_history() -> None:
    fake = FakeRedis()
    autoscaler.redis_client = fake

    settings.autoscale_min_workers = 1
    settings.autoscale_apply_cooldown_seconds = 30

    autoscaler.autoscaling_recommendation = lambda current_workers: {
        "current_workers": current_workers,
        "desired_workers": 5,
        "scale_delta": 4,
        "total_lag": 4000,
        "lag_per_worker_threshold": 1000,
    }

    first = autoscaler.reconcile(current_workers=1)
    assert first["action"] == "scale_up"
    assert first["desired_workers"] == 5

    second = autoscaler.reconcile(current_workers=1)
    assert second["action"] == "noop"

    hist = autoscaler.history(limit=10)
    assert len(hist) == 2

    status = autoscaler.get_status()
    assert int(status["target_workers"]) == 5
