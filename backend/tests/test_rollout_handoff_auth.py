from __future__ import annotations

from uuid import uuid4

from app.services import rollout_handoff_auth as auth


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.expiry: dict[str, int] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self._counter = 0

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(key, {}).update(mapping)
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def expire(self, key: str, ttl: int) -> bool:
        self.expiry[key] = ttl
        return True

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self._counter += 1
        event_id = f"{self._counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]


def test_issue_verify_revoke_rollout_handoff_token() -> None:
    fake = FakeRedis()
    auth.redis_client = fake

    tenant_id = uuid4()
    issued = auth.issue_rollout_handoff_token(tenant_id=tenant_id, actor="admin", auditor_name="auditor-x", ttl_seconds=3600)
    assert issued["token"].startswith("rht_")

    verified = auth.verify_rollout_handoff_token(issued["token"])
    assert verified["valid"] is True
    assert auth.handoff_allows_tenant(verified, tenant_id) is True

    consumed = auth.verify_rollout_handoff_token(issued["token"], source_ip="203.0.113.10", consume=True)
    assert consumed["valid"] is True
    receipts = auth.rollout_handoff_receipts(tenant_id, limit=10)
    assert receipts["count"] == 1

    revoked = auth.revoke_rollout_handoff_token(issued["token"])
    assert revoked["status"] == "revoked"

    verified_after = auth.verify_rollout_handoff_token(issued["token"])
    assert verified_after["valid"] is False


def test_handoff_token_ip_and_access_limit_enforced() -> None:
    fake = FakeRedis()
    auth.redis_client = fake

    tenant_id = uuid4()
    issued = auth.issue_rollout_handoff_token(
        tenant_id=tenant_id,
        actor="admin",
        ttl_seconds=3600,
        session_ttl_seconds=1800,
        max_accesses=1,
        allowed_ip_cidrs="203.0.113.0/24",
    )

    denied_ip = auth.verify_rollout_handoff_token(issued["token"], source_ip="198.51.100.9", consume=True)
    assert denied_ip["valid"] is False
    assert denied_ip["reason"] == "source_ip_not_allowed"
    anomalies = auth.rollout_handoff_anomalies(tenant_id, limit=10)
    assert anomalies["count"] >= 1

    ok = auth.verify_rollout_handoff_token(issued["token"], source_ip="203.0.113.8", consume=True)
    assert ok["valid"] is False
    assert ok["reason"] == "revoked"


def test_handoff_policy_can_disable_auto_revoke_on_ip_mismatch() -> None:
    fake = FakeRedis()
    auth.redis_client = fake

    tenant_id = uuid4()
    _ = auth.upsert_rollout_handoff_policy(
        tenant_id=tenant_id,
        anomaly_detection_enabled=True,
        auto_revoke_on_ip_mismatch=False,
        max_denied_attempts_before_revoke=2,
    )
    issued = auth.issue_rollout_handoff_token(
        tenant_id=tenant_id,
        actor="admin",
        ttl_seconds=3600,
        max_accesses=5,
        allowed_ip_cidrs="203.0.113.0/24",
    )

    denied_1 = auth.verify_rollout_handoff_token(issued["token"], source_ip="198.51.100.1", consume=True)
    assert denied_1["valid"] is False
    denied_2 = auth.verify_rollout_handoff_token(issued["token"], source_ip="198.51.100.2", consume=True)
    assert denied_2["valid"] is False

    after = auth.verify_rollout_handoff_token(issued["token"], source_ip="203.0.113.20", consume=True)
    assert after["valid"] is False
    assert after["reason"] == "revoked"


def test_handoff_adaptive_hardening_reduces_session_ttl() -> None:
    fake = FakeRedis()
    auth.redis_client = fake

    tenant_id = uuid4()
    _ = auth.upsert_rollout_handoff_policy(
        tenant_id=tenant_id,
        anomaly_detection_enabled=True,
        auto_revoke_on_ip_mismatch=False,
        max_denied_attempts_before_revoke=10,
        adaptive_hardening_enabled=True,
        risk_threshold_block=95,
        risk_threshold_harden=10,
        harden_session_ttl_seconds=120,
    )
    issued = auth.issue_rollout_handoff_token(
        tenant_id=tenant_id,
        actor="admin",
        ttl_seconds=3600,
        session_ttl_seconds=1800,
        max_accesses=10,
        allowed_ip_cidrs="203.0.113.0/24",
    )
    token_id = issued["token"].split(".", 1)[0].removeprefix("rht_")
    before = int(fake.hashes[f"rollout_handoff_token:{token_id}"]["session_expires_at"])

    _ = auth.verify_rollout_handoff_token(issued["token"], source_ip="198.51.100.1", consume=True)
    allowed = auth.verify_rollout_handoff_token(issued["token"], source_ip="203.0.113.1", consume=True)
    assert allowed["valid"] is True
    after = int(fake.hashes[f"rollout_handoff_token:{token_id}"]["session_expires_at"])
    assert after <= before
    trust_events = auth.rollout_handoff_trust_events(tenant_id, limit=10)
    assert trust_events["count"] >= 2
    assert any(row.get("status") == "allowed" for row in trust_events["rows"])


def test_handoff_risk_threshold_block_revokes_token() -> None:
    fake = FakeRedis()
    auth.redis_client = fake

    tenant_id = uuid4()
    _ = auth.upsert_rollout_handoff_policy(
        tenant_id=tenant_id,
        anomaly_detection_enabled=True,
        auto_revoke_on_ip_mismatch=False,
        max_denied_attempts_before_revoke=20,
        adaptive_hardening_enabled=True,
        risk_threshold_block=10,
        risk_threshold_harden=5,
        harden_session_ttl_seconds=120,
    )
    issued = auth.issue_rollout_handoff_token(
        tenant_id=tenant_id,
        actor="admin",
        ttl_seconds=3600,
        session_ttl_seconds=1800,
        max_accesses=10,
        allowed_ip_cidrs="203.0.113.0/24",
    )
    _ = auth.verify_rollout_handoff_token(issued["token"], source_ip="198.51.100.1", consume=True)
    blocked = auth.verify_rollout_handoff_token(issued["token"], source_ip="203.0.113.2", consume=True)
    assert blocked["valid"] is False
    assert blocked["reason"] == "risk_threshold_block"

    anomalies = auth.rollout_handoff_anomalies(tenant_id, limit=20)
    assert any(row.get("reason") == "risk_threshold_block" for row in anomalies["rows"])
    trust_events = auth.rollout_handoff_trust_events(tenant_id, limit=20)
    assert any(row.get("reason") == "risk_threshold_block" and row.get("action_taken") == "revoked" for row in trust_events["rows"])
    snapshot = auth.rollout_handoff_risk_snapshot(tenant_id, limit=20)
    assert snapshot["max_risk_score"] >= 10
    assert snapshot["blocked_count"] >= 1


def test_handoff_containment_playbook_and_governance_snapshot() -> None:
    fake = FakeRedis()
    auth.redis_client = fake

    tenant_id = uuid4()
    _ = auth.upsert_rollout_handoff_policy(
        tenant_id=tenant_id,
        anomaly_detection_enabled=True,
        auto_revoke_on_ip_mismatch=False,
        max_denied_attempts_before_revoke=10,
        adaptive_hardening_enabled=True,
        risk_threshold_block=99,
        risk_threshold_harden=80,
        harden_session_ttl_seconds=120,
        containment_playbook_enabled=True,
        containment_high_threshold=10,
        containment_critical_threshold=95,
        containment_action_high="harden_session",
        containment_action_critical="revoke_token",
    )
    issued = auth.issue_rollout_handoff_token(
        tenant_id=tenant_id,
        actor="admin",
        ttl_seconds=3600,
        session_ttl_seconds=1800,
        max_accesses=10,
        allowed_ip_cidrs="203.0.113.0/24",
    )
    token_id = issued["token"].split(".", 1)[0].removeprefix("rht_")
    before = int(fake.hashes[f"rollout_handoff_token:{token_id}"]["session_expires_at"])

    _ = auth.verify_rollout_handoff_token(issued["token"], source_ip="198.51.100.22", consume=True)
    after = int(fake.hashes[f"rollout_handoff_token:{token_id}"]["session_expires_at"])
    assert after <= before

    containment = auth.rollout_handoff_containment_events(tenant_id, limit=20)
    assert containment["count"] >= 1
    assert any(row.get("action_taken") == "harden_session" for row in containment["rows"])

    governance = auth.rollout_handoff_governance_snapshot(tenant_id, limit=20)
    assert governance["risk_snapshot"]["count"] >= 1
    assert governance["containment_event_count"] >= 1
    assert governance["containment_action_counts"].get("harden_session", 0) >= 1
