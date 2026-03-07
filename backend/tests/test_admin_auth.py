from __future__ import annotations

import time

from app.core.config import settings
from app.services import admin_auth


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


def test_issue_verify_rotate_revoke() -> None:
    fake = FakeRedis()
    admin_auth.redis_client = fake
    settings.control_plane_admin_token_ttl_seconds = 600

    issued = admin_auth.issue_admin_token(actor="bootstrap", scopes=["control_plane:read", "admin:token:write"])
    assert issued["token"].startswith("adm_")

    verified = admin_auth.verify_admin_token(issued["token"])
    assert verified["valid"] is True
    assert "control_plane:read" in verified["scopes"]

    rotated = admin_auth.rotate_admin_token(issued["token"])
    assert rotated["status"] == "rotated"
    assert "control_plane:read" in rotated["scopes"]

    old_check = admin_auth.verify_admin_token(issued["token"])
    assert old_check["valid"] is False

    new_check = admin_auth.verify_admin_token(rotated["new_token"])
    assert new_check["valid"] is True

    revoked = admin_auth.revoke_admin_token(rotated["new_token"])
    assert revoked["status"] == "revoked"

    revoked_check = admin_auth.verify_admin_token(rotated["new_token"])
    assert revoked_check["valid"] is False


def test_expired_token() -> None:
    fake = FakeRedis()
    admin_auth.redis_client = fake
    settings.control_plane_admin_token_ttl_seconds = 1

    issued = admin_auth.issue_admin_token(actor="bootstrap")
    token_id = issued["token_id"]
    key = f"control_plane_admin_token:{token_id}"
    fake.hashes[key]["expires_at"] = str(int(time.time()) - 5)

    verified = admin_auth.verify_admin_token(issued["token"])
    assert verified["valid"] is False
    assert verified["reason"] == "expired"


def test_scope_check() -> None:
    verified = {"scopes": ["control_plane:read"]}
    assert admin_auth.token_has_scope(verified, "control_plane:read") is True
    assert admin_auth.token_has_scope(verified, "control_plane:write") is False


def test_tenant_scope_check() -> None:
    scoped = {"tenant_scope": "acb"}
    assert admin_auth.token_allows_tenant(scoped, "acb") is True
    assert admin_auth.token_allows_tenant(scoped, "xyz") is False

    global_scope = {"tenant_scope": "*"}
    assert admin_auth.token_allows_tenant(global_scope, "acb") is True
