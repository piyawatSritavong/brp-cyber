from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import ingest as ingest_api
from app.services import blue_detection, dead_letter, event_store
from app.services import firewall_client, notifier
from app.services import policy_store
from app.services.runtime_state import runtime_state
from app.main import app


class FakeRedis:
    def __init__(self) -> None:
        self.zsets: dict[str, dict[str, int]] = {}
        self.strings: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self._counter = 0

    def zadd(self, key: str, mapping: dict[str, int]) -> None:
        self.zsets.setdefault(key, {}).update(mapping)

    def zremrangebyscore(self, key: str, min_score: int, max_score: int) -> None:
        if key not in self.zsets:
            return
        to_remove = [member for member, score in self.zsets[key].items() if min_score <= score <= max_score]
        for member in to_remove:
            self.zsets[key].pop(member, None)

    def zcard(self, key: str) -> int:
        return len(self.zsets.get(key, {}))

    def expire(self, key: str, seconds: int) -> bool:
        return True

    def exists(self, key: str) -> int:
        return 1 if key in self.strings else 0

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.strings[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        bucket = self.hashes.setdefault(key, {})
        bucket.update(mapping)
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self._counter += 1
        event_id = f"{self._counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        entries = self.streams.get(key, [])
        return list(reversed(entries))[:count]


def _configure_fake_runtime(fake_redis: FakeRedis) -> None:
    blue_detection.redis_client = fake_redis
    policy_store.redis_client = fake_redis
    ingest_api.redis_client = fake_redis
    event_store.redis_client = fake_redis
    dead_letter.redis_client = fake_redis

    blue_detection.block_ip = lambda tenant, ip, reason: True
    blue_detection.send_telegram_message = lambda message: True

    firewall_client.write_dead_letter = dead_letter.write_dead_letter
    notifier.write_dead_letter = dead_letter.write_dead_letter

    runtime_state.set_kill_switch(False)


def test_ingest_auth_login_creates_incident_timeline() -> None:
    fake_redis = FakeRedis()
    _configure_fake_runtime(fake_redis)

    tenant_id = str(uuid4())

    with TestClient(app) as client:
        for _ in range(12):
            response = client.post(
                "/ingest/auth-login",
                json={
                    "tenant_id": tenant_id,
                    "source_ip": "198.51.100.77",
                    "username": "admin",
                    "success": False,
                    "auth_source": "system_auth",
                },
            )
            assert response.status_code == 200

        incidents = client.get(f"/ingest/incidents/{tenant_id}?limit=20")
        assert incidents.status_code == 200
        data = incidents.json()
        assert data["count"] >= 1
        assert data["incidents"][0]["signal"] == "brute_force_suspected"


def test_dead_letter_endpoint_returns_written_events() -> None:
    fake_redis = FakeRedis()
    _configure_fake_runtime(fake_redis)

    dead_letter.write_dead_letter(
        component="notifier",
        operation="send_telegram_message",
        payload={"message": "x"},
        error="simulated_failure",
    )

    with TestClient(app) as client:
        response = client.get("/ingest/dead-letters?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["dead_letters"][0]["component"] == "notifier"
