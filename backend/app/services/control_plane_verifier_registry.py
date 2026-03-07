from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any

from app.services.redis_client import redis_client

VERIFIER_TOKEN_PREFIX = "control_plane_external_verifier_token"


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _token_key(token_id: str) -> str:
    return f"{VERIFIER_TOKEN_PREFIX}:{token_id}"


def issue_verifier_token(
    tenant_code: str,
    verifier_name: str,
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
            "revoked": "0",
            "tenant_code": tenant_code.lower().strip(),
            "verifier_name": verifier_name,
        },
    )
    redis_client.expire(_token_key(token_id), ttl)

    return {
        "token": f"ver_{token_id}.{secret}",
        "token_id": token_id,
        "tenant_code": tenant_code,
        "verifier_name": verifier_name,
        "expires_at": expires_at,
        "ttl_seconds": ttl,
    }


def verify_verifier_token(token: str, tenant_code: str) -> dict[str, Any]:
    if not token.startswith("ver_") or "." not in token:
        return {"valid": False, "reason": "invalid_format"}

    prefix, secret = token.split(".", 1)
    token_id = prefix.removeprefix("ver_")
    data = redis_client.hgetall(_token_key(token_id))
    if not data:
        return {"valid": False, "reason": "not_found"}
    if data.get("revoked") == "1":
        return {"valid": False, "reason": "revoked"}

    expires_at = int(data.get("expires_at", "0") or 0)
    if int(time.time()) >= expires_at:
        return {"valid": False, "reason": "expired"}

    if _hash_secret(secret) != data.get("secret_hash"):
        return {"valid": False, "reason": "secret_mismatch"}

    expected_tenant = str(data.get("tenant_code", "")).lower().strip()
    if expected_tenant != tenant_code.lower().strip():
        return {"valid": False, "reason": "tenant_scope_mismatch"}

    return {
        "valid": True,
        "token_id": token_id,
        "tenant_code": expected_tenant,
        "verifier_name": data.get("verifier_name", "unknown"),
        "expires_at": expires_at,
    }


def revoke_verifier_token(token: str) -> dict[str, Any]:
    if not token.startswith("ver_") or "." not in token:
        return {"status": "not_revoked", "reason": "invalid_format"}
    token_id = token.split(".", 1)[0].removeprefix("ver_")
    data = redis_client.hgetall(_token_key(token_id))
    if not data:
        return {"status": "not_revoked", "reason": "not_found"}

    redis_client.hset(_token_key(token_id), mapping={"revoked": "1"})
    return {"status": "revoked", "token_id": token_id}
