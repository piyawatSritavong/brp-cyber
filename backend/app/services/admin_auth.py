from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any

from app.core.config import settings
from app.services.idp_auth import introspect_token
from app.services.redis_client import redis_client

ADMIN_TOKEN_PREFIX = "control_plane_admin_token"


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _token_key(token_id: str) -> str:
    return f"{ADMIN_TOKEN_PREFIX}:{token_id}"


def _normalize_scopes(scopes: list[str] | None) -> str:
    values = [s.strip() for s in (scopes or []) if s.strip()]
    if not values:
        values = ["*"]
    return ",".join(sorted(set(values)))


def issue_admin_token(
    actor: str = "bootstrap",
    scopes: list[str] | None = None,
    ttl_seconds: int | None = None,
    tenant_scope: str | None = None,
) -> dict[str, Any]:
    token_id = secrets.token_hex(8)
    secret = secrets.token_urlsafe(24)
    ttl = max(60, ttl_seconds or settings.control_plane_admin_token_ttl_seconds)
    expires_at = int(time.time()) + ttl

    scope_value = (tenant_scope or "*").strip()

    redis_client.hset(
        _token_key(token_id),
        mapping={
            "secret_hash": _hash_secret(secret),
            "expires_at": str(expires_at),
            "actor": actor,
            "revoked": "0",
            "scopes": _normalize_scopes(scopes),
            "tenant_scope": scope_value,
        },
    )
    redis_client.expire(_token_key(token_id), ttl)

    return {
        "token": f"adm_{token_id}.{secret}",
        "token_id": token_id,
        "expires_at": expires_at,
        "ttl_seconds": ttl,
        "scopes": (scopes or ["*"]),
        "tenant_scope": scope_value,
    }


def auth_posture() -> dict[str, Any]:
    provider = settings.control_plane_auth_provider.lower().strip()
    env = settings.environment.lower().strip()

    local_bootstrap_available = True
    reason = "enabled"

    if provider == "idp":
        local_bootstrap_available = False
        reason = "idp_provider_enabled"
    elif not settings.control_plane_allow_local_bootstrap:
        local_bootstrap_available = False
        reason = "local_bootstrap_disabled_by_policy"
    elif env in {"prod", "production"} and settings.control_plane_require_idp_in_production:
        local_bootstrap_available = False
        reason = "idp_required_in_production"

    return {
        "auth_provider": provider,
        "environment": env,
        "local_bootstrap_available": local_bootstrap_available,
        "reason": reason,
        "require_idp_in_production": settings.control_plane_require_idp_in_production,
    }


def verify_admin_token(token: str) -> dict[str, Any]:
    if settings.control_plane_auth_provider.lower().strip() == "idp":
        return introspect_token(token)

    if not token.startswith("adm_") or "." not in token:
        return {"valid": False, "reason": "invalid_format"}

    prefix, secret = token.split(".", 1)
    token_id = prefix.removeprefix("adm_")
    data = redis_client.hgetall(_token_key(token_id))
    if not data:
        return {"valid": False, "reason": "not_found"}

    if data.get("revoked") == "1":
        return {"valid": False, "reason": "revoked"}

    expires_at = int(data.get("expires_at", "0"))
    if int(time.time()) >= expires_at:
        return {"valid": False, "reason": "expired"}

    if _hash_secret(secret) != data.get("secret_hash"):
        return {"valid": False, "reason": "secret_mismatch"}

    scopes = [s for s in data.get("scopes", "*").split(",") if s]
    return {
        "valid": True,
        "token_id": token_id,
        "actor": data.get("actor", "unknown"),
        "expires_at": expires_at,
        "scopes": scopes,
        "tenant_scope": data.get("tenant_scope", "*"),
    }


def token_has_scope(verified: dict[str, Any], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def token_allows_tenant(verified: dict[str, Any], tenant_code: str) -> bool:
    scope = str(verified.get("tenant_scope", "*") or "*")
    return scope == "*" or scope == tenant_code


def revoke_admin_token(token: str) -> dict[str, Any]:
    verification = verify_admin_token(token)
    if not verification.get("valid"):
        return {"status": "not_revoked", "reason": verification.get("reason", "invalid")}

    token_id = str(verification["token_id"])
    redis_client.hset(_token_key(token_id), mapping={"revoked": "1"})
    return {"status": "revoked", "token_id": token_id}


def rotate_admin_token(token: str) -> dict[str, Any]:
    verification = verify_admin_token(token)
    if not verification.get("valid"):
        return {"status": "not_rotated", "reason": verification.get("reason", "invalid")}

    old_token_id = str(verification["token_id"])
    redis_client.hset(_token_key(old_token_id), mapping={"revoked": "1"})
    issued = issue_admin_token(
        actor=f"rotate:{old_token_id}",
        scopes=verification.get("scopes", ["*"]),
        tenant_scope=verification.get("tenant_scope", "*"),
    )
    return {
        "status": "rotated",
        "revoked_token_id": old_token_id,
        "new_token": issued["token"],
        "new_token_id": issued["token_id"],
        "expires_at": issued["expires_at"],
        "scopes": issued["scopes"],
        "tenant_scope": issued["tenant_scope"],
    }
