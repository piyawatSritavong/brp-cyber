from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from app.core.config import settings
from app.services import blue_detection
from app.services import policy_store
from schemas.ingest import AuthLoginEvent, SystemAuthEvent, WafHttpEvent


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
        stream = self.streams.setdefault(key, [])
        stream.append((event_id, fields))
        return event_id


def _failed_auth_event(tenant_id, source_ip: str = "203.0.113.10") -> AuthLoginEvent:
    return AuthLoginEvent(
        tenant_id=tenant_id,
        timestamp=datetime.utcnow(),
        source_ip=source_ip,
        username="admin",
        success=False,
        auth_source="system_auth",
    )


def test_threshold_trigger_and_cooldown() -> None:
    fake_redis = FakeRedis()
    tenant_id = uuid4()

    persisted = []
    blocked = []
    alerts = []

    blue_detection.redis_client = fake_redis
    policy_store.redis_client = fake_redis
    blue_detection.persist_event = lambda event: persisted.append(event.event_type)
    blue_detection.block_ip = lambda tenant, ip, reason: blocked.append((tenant, ip, reason)) or True
    blue_detection.send_telegram_message = lambda message: alerts.append(message) or True

    settings.blue_failed_login_threshold_per_minute = 2
    settings.blue_failure_window_seconds = 60
    settings.blue_incident_cooldown_seconds = 120
    settings.allowlist_ips = "127.0.0.1"

    r1 = blue_detection.process_auth_login_event(_failed_auth_event(tenant_id))
    r2 = blue_detection.process_auth_login_event(_failed_auth_event(tenant_id))
    r3 = blue_detection.process_auth_login_event(_failed_auth_event(tenant_id))
    r4 = blue_detection.process_auth_login_event(_failed_auth_event(tenant_id))

    assert r1["status"] == "monitored"
    assert r2["status"] == "monitored"
    assert r3["status"] == "mitigated"
    assert r4["status"] == "suppressed"
    assert r4["reason"] == "incident_cooldown"
    assert len(blocked) == 1
    assert len(alerts) == 1
    assert persisted.count("detection_event") == 1
    assert persisted.count("response_event") == 1


def test_allowlist_suppresses_detection() -> None:
    fake_redis = FakeRedis()
    tenant_id = uuid4()

    blue_detection.redis_client = fake_redis
    policy_store.redis_client = fake_redis
    blue_detection.persist_event = lambda event: None
    blue_detection.block_ip = lambda tenant, ip, reason: True
    blue_detection.send_telegram_message = lambda message: True

    settings.blue_failed_login_threshold_per_minute = 1
    settings.blue_failure_window_seconds = 60
    settings.allowlist_ips = "198.51.100.9"

    event = _failed_auth_event(tenant_id, source_ip="198.51.100.9")
    blue_detection.process_auth_login_event(event)
    result = blue_detection.process_auth_login_event(event)

    assert result["status"] == "suppressed"
    assert result["reason"] == "allowlisted_ip"


def test_cidr_username_asn_suppression() -> None:
    fake_redis = FakeRedis()
    tenant_id = uuid4()

    blue_detection.redis_client = fake_redis
    policy_store.redis_client = fake_redis
    blue_detection.persist_event = lambda event: None
    blue_detection.block_ip = lambda tenant, ip, reason: True
    blue_detection.send_telegram_message = lambda message: True

    settings.blue_failed_login_threshold_per_minute = 1
    settings.blue_failure_window_seconds = 60
    settings.allowlist_ips = ""
    settings.allowlist_cidrs = "203.0.113.0/24"
    settings.allowlist_usernames = "service-account"
    settings.allowlist_asns = "64500"

    ev_cidr = AuthLoginEvent(
        tenant_id=tenant_id,
        timestamp=datetime.utcnow(),
        source_ip="203.0.113.77",
        username="admin",
        success=False,
        auth_source="system_auth",
    )
    blue_detection.process_auth_login_event(ev_cidr)
    r1 = blue_detection.process_auth_login_event(ev_cidr)
    assert r1["status"] == "suppressed"
    assert r1["reason"] == "allowlisted_cidr"

    ev_user = AuthLoginEvent(
        tenant_id=tenant_id,
        timestamp=datetime.utcnow(),
        source_ip="198.51.100.77",
        username="service-account",
        success=False,
        auth_source="system_auth",
    )
    blue_detection.process_auth_login_event(ev_user)
    r2 = blue_detection.process_auth_login_event(ev_user)
    assert r2["status"] == "suppressed"
    assert r2["reason"] == "allowlisted_username"

    ev_asn = AuthLoginEvent(
        tenant_id=tenant_id,
        timestamp=datetime.utcnow(),
        source_ip="198.51.100.99",
        source_asn=64500,
        username="unknown-user",
        success=False,
        auth_source="system_auth",
    )
    blue_detection.process_auth_login_event(ev_asn)
    r3 = blue_detection.process_auth_login_event(ev_asn)
    assert r3["status"] == "suppressed"
    assert r3["reason"] == "allowlisted_asn"


def test_system_auth_and_waf_normalization() -> None:
    fake_redis = FakeRedis()
    tenant_id = uuid4()

    blue_detection.redis_client = fake_redis
    policy_store.redis_client = fake_redis
    blue_detection.persist_event = lambda event: None
    blue_detection.block_ip = lambda tenant, ip, reason: True
    blue_detection.send_telegram_message = lambda message: True

    settings.blue_failed_login_threshold_per_minute = 1
    settings.blue_failure_window_seconds = 60
    settings.blue_incident_cooldown_seconds = 1
    settings.allowlist_ips = "127.0.0.1"
    settings.allowlist_cidrs = ""
    settings.allowlist_usernames = ""
    settings.allowlist_asns = ""

    system_event = SystemAuthEvent(
        tenant_id=tenant_id,
        timestamp=datetime.utcnow(),
        source_ip="203.0.113.77",
        username="admin",
        event_type="login_failure",
        auth_source="system_auth",
    )
    r1 = blue_detection.process_system_auth_event(system_event)
    r2 = blue_detection.process_system_auth_event(system_event)

    assert r1["status"] == "monitored"
    assert r2["status"] == "mitigated"

    waf_ignore = WafHttpEvent(
        tenant_id=tenant_id,
        timestamp=datetime.utcnow(),
        source_ip="203.0.113.80",
        path="/products",
        method="GET",
        status_code=200,
        waf_action="allow",
    )
    assert blue_detection.process_waf_http_event(waf_ignore)["status"] == "ignored"

    # Move old attempts out of window to avoid cross-test signal accumulation in the same tenant/IP set.
    past_event = AuthLoginEvent(
        tenant_id=tenant_id,
        timestamp=datetime.utcnow() - timedelta(seconds=120),
        source_ip="203.0.113.81",
        username="ops",
        success=False,
        auth_source="system_auth",
    )
    blue_detection.process_auth_login_event(past_event)

    waf_fail = WafHttpEvent(
        tenant_id=tenant_id,
        timestamp=datetime.utcnow(),
        source_ip="203.0.113.88",
        path="/admin/login",
        method="POST",
        status_code=401,
        waf_action="challenge",
        username="admin",
    )
    r3 = blue_detection.process_waf_http_event(waf_fail)
    r4 = blue_detection.process_waf_http_event(waf_fail)
    assert r3["status"] == "monitored"
    assert r4["status"] == "mitigated"
