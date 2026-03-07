from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any

from app.services.redis_client import redis_client

PILOT_OPERATOR_TOKEN_PREFIX = "pilot_operator_token"


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _token_key(token_id: str) -> str:
    return f"{PILOT_OPERATOR_TOKEN_PREFIX}:{token_id}"


def _normalize_scopes(scopes: list[str] | None) -> str:
    values = [s.strip() for s in (scopes or []) if s.strip()]
    allowed = {"pilot:read", "pilot:write"}
    filtered = sorted(set(v for v in values if v in allowed))
    if not filtered:
        filtered = ["pilot:read", "pilot:write"]
    return ",".join(filtered)


def issue_pilot_operator_token(
    actor: str,
    tenant_code: str,
    scopes: list[str] | None = None,
    ttl_seconds: int = 86400,
) -> dict[str, Any]:
    token_id = secrets.token_hex(8)
    secret = secrets.token_urlsafe(24)
    ttl = max(60, int(ttl_seconds))
    expires_at = int(time.time()) + ttl

    redis_client.hset(
        _token_key(token_id),
        mapping={
            "secret_hash": _hash_secret(secret),
            "expires_at": str(expires_at),
            "actor": actor,
            "revoked": "0",
            "tenant_scope": tenant_code.lower().strip(),
            "scopes": _normalize_scopes(scopes),
        },
    )
    redis_client.expire(_token_key(token_id), ttl)

    normalized_scopes = [s for s in _normalize_scopes(scopes).split(",") if s]
    return {
        "token": f"opt_{token_id}.{secret}",
        "token_id": token_id,
        "actor": actor,
        "tenant_scope": tenant_code.lower().strip(),
        "scopes": normalized_scopes,
        "expires_at": expires_at,
        "ttl_seconds": ttl,
    }


def verify_pilot_operator_token(token: str) -> dict[str, Any]:
    if not token.startswith("opt_") or "." not in token:
        return {"valid": False, "reason": "invalid_format"}

    prefix, secret = token.split(".", 1)
    token_id = prefix.removeprefix("opt_")
    data = redis_client.hgetall(_token_key(token_id))
    if not data:
        return {"valid": False, "reason": "not_found"}

    if data.get("revoked") == "1":
        return {"valid": False, "reason": "revoked"}

    expires_at = int(data.get("expires_at", "0") or 0)
    if int(time.time()) >= expires_at:
        return {"valid": False, "reason": "expired"}

    if _hash_secret(secret) != data.get("secret_hash", ""):
        return {"valid": False, "reason": "secret_mismatch"}

    scopes = [s for s in data.get("scopes", "").split(",") if s]
    return {
        "valid": True,
        "token_id": token_id,
        "actor": data.get("actor", "unknown"),
        "tenant_scope": data.get("tenant_scope", ""),
        "scopes": scopes,
        "expires_at": expires_at,
    }


def revoke_pilot_operator_token(token: str) -> dict[str, Any]:
    verified = verify_pilot_operator_token(token)
    if not verified.get("valid"):
        return {"status": "not_revoked", "reason": verified.get("reason", "invalid")}

    token_id = str(verified["token_id"])
    redis_client.hset(_token_key(token_id), mapping={"revoked": "1"})
    return {"status": "revoked", "token_id": token_id}


def operator_has_scope(verified: dict[str, Any], scope: str) -> bool:
    return scope in set(verified.get("scopes", []))


def operator_allows_tenant(verified: dict[str, Any], tenant_code: str) -> bool:
    return str(verified.get("tenant_scope", "")).lower().strip() == tenant_code.lower().strip()
