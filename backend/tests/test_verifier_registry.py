from __future__ import annotations

from app.services import control_plane_verifier_registry as vr


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(key, {}).update(mapping)
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def expire(self, key: str, ttl: int) -> bool:
        return True


def test_issue_verify_and_revoke_verifier_token() -> None:
    fake = FakeRedis()
    vr.redis_client = fake

    issued = vr.issue_verifier_token(tenant_code="acb", verifier_name="auditor_x", ttl_seconds=3600)
    assert issued["token"].startswith("ver_")

    verified = vr.verify_verifier_token(token=issued["token"], tenant_code="acb")
    assert verified["valid"] is True
    assert verified["verifier_name"] == "auditor_x"

    wrong_tenant = vr.verify_verifier_token(token=issued["token"], tenant_code="xyz")
    assert wrong_tenant["valid"] is False

    revoked = vr.revoke_verifier_token(issued["token"])
    assert revoked["status"] == "revoked"

    verify_after = vr.verify_verifier_token(token=issued["token"], tenant_code="acb")
    assert verify_after["valid"] is False
    assert verify_after["reason"] == "revoked"
