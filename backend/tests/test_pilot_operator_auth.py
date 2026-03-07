from __future__ import annotations

from app.services import pilot_operator_auth as po


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(key, {}).update(mapping)
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def expire(self, key: str, seconds: int) -> bool:
        return True


def test_issue_verify_revoke_operator_token() -> None:
    fake = FakeRedis()
    po.redis_client = fake

    issued = po.issue_pilot_operator_token(
        actor="pilot_admin",
        tenant_code="acb",
        scopes=["pilot:read", "pilot:write"],
        ttl_seconds=3600,
    )
    assert issued["token"].startswith("opt_")

    verified = po.verify_pilot_operator_token(issued["token"])
    assert verified["valid"] is True
    assert po.operator_has_scope(verified, "pilot:write") is True
    assert po.operator_allows_tenant(verified, "acb") is True
    assert po.operator_allows_tenant(verified, "xyz") is False

    revoked = po.revoke_pilot_operator_token(issued["token"])
    assert revoked["status"] == "revoked"

    check_after = po.verify_pilot_operator_token(issued["token"])
    assert check_after["valid"] is False
