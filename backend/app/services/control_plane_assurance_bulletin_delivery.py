from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from app.services.control_plane_assurance_digest_signing import signed_tenant_risk_bulletin_status
from app.services.redis_client import redis_client
from app.services.retry import run_with_retry

ASSURANCE_BULLETIN_DISTRIBUTION_PREFIX = "control_plane_assurance_bulletin_distribution"
ASSURANCE_BULLETIN_RECEIPT_STREAM_PREFIX = "control_plane_assurance_bulletin_receipts"


def _policy_key(tenant_code: str) -> str:
    return f"{ASSURANCE_BULLETIN_DISTRIBUTION_PREFIX}:{tenant_code.lower().strip()}"


def _receipt_stream_key(tenant_code: str) -> str:
    return f"{ASSURANCE_BULLETIN_RECEIPT_STREAM_PREFIX}:{tenant_code.lower().strip()}"


def _normalize_policy(payload: dict[str, Any]) -> dict[str, Any]:
    retry_attempts = int(payload.get("retry_attempts", 3) or 3)
    retry_attempts = min(10, max(1, retry_attempts))
    retry_backoff = float(payload.get("retry_backoff_seconds", 0.5) or 0.5)
    retry_backoff = min(30.0, max(0.1, retry_backoff))
    return {
        "policy_version": str(payload.get("policy_version", "1.0")),
        "owner": str(payload.get("owner", "security")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "enabled": bool(payload.get("enabled", True)),
        "signed_only": bool(payload.get("signed_only", True)),
        "webhook_url": str(payload.get("webhook_url", "")).strip(),
        "auth_header": str(payload.get("auth_header", "")).strip(),
        "timeout_seconds": float(payload.get("timeout_seconds", 5.0) or 5.0),
        "retry_attempts": retry_attempts,
        "retry_backoff_seconds": retry_backoff,
    }


def upsert_bulletin_distribution_policy(tenant_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    policy = _normalize_policy(payload)
    redis_client.set(_policy_key(tenant_code), json.dumps(policy, ensure_ascii=True, sort_keys=True))
    return {"status": "upserted", "tenant_code": tenant_code, "policy": policy}


def get_bulletin_distribution_policy(tenant_code: str) -> dict[str, Any]:
    raw = redis_client.get(_policy_key(tenant_code))
    if not raw:
        return {"status": "default", "tenant_code": tenant_code, "policy": _normalize_policy({})}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "corrupted", "tenant_code": tenant_code}
    return {"status": "ok", "tenant_code": tenant_code, "policy": _normalize_policy(loaded)}


def _send_webhook(webhook_url: str, payload: dict[str, Any], auth_header: str, timeout_seconds: float) -> tuple[int, str]:
    headers = {"content-type": "application/json"}
    if auth_header:
        headers["authorization"] = auth_header

    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.post(webhook_url, json=payload, headers=headers)
        return resp.status_code, resp.text[:1000]


def _send_webhook_with_retry(
    webhook_url: str,
    payload: dict[str, Any],
    auth_header: str,
    timeout_seconds: float,
    retry_attempts: int,
    retry_backoff_seconds: float,
) -> tuple[int, str]:
    def _call() -> tuple[int, str]:
        status, body = _send_webhook(
            webhook_url=webhook_url,
            payload=payload,
            auth_header=auth_header,
            timeout_seconds=timeout_seconds,
        )
        if status >= 500:
            raise RuntimeError(f"upstream_5xx:{status}")
        return status, body

    return run_with_retry(_call, attempts=retry_attempts, backoff_seconds=retry_backoff_seconds)


def deliver_signed_tenant_bulletin(tenant_code: str, limit: int = 1) -> dict[str, Any]:
    policy_resp = get_bulletin_distribution_policy(tenant_code)
    if policy_resp.get("status") == "corrupted":
        return policy_resp
    policy = policy_resp.get("policy", {})

    if not bool(policy.get("enabled", True)):
        return {"status": "disabled", "tenant_code": tenant_code}

    bulletin = signed_tenant_risk_bulletin_status(tenant_code=tenant_code, limit=max(1, limit))
    rows = bulletin.get("rows", [])
    if not rows:
        return {"status": "no_bulletin", "tenant_code": tenant_code}

    latest = rows[0]
    if bool(policy.get("signed_only", True)) and not latest.get("signature", ""):
        return {"status": "rejected_unsigned", "tenant_code": tenant_code}

    webhook_url = str(policy.get("webhook_url", "")).strip()
    if not webhook_url:
        return {"status": "not_configured", "tenant_code": tenant_code}

    delivery_payload = {
        "tenant_code": tenant_code,
        "snapshot_id": latest.get("id", ""),
        "generated_at": latest.get("generated_at", ""),
        "payload_hash": latest.get("payload_hash", ""),
        "signature": latest.get("signature", ""),
        "scope": latest.get("scope", ""),
    }

    try:
        http_status, response_excerpt = _send_webhook_with_retry(
            webhook_url=webhook_url,
            payload=delivery_payload,
            auth_header=str(policy.get("auth_header", "")),
            timeout_seconds=float(policy.get("timeout_seconds", 5.0) or 5.0),
            retry_attempts=int(policy.get("retry_attempts", 3) or 3),
            retry_backoff_seconds=float(policy.get("retry_backoff_seconds", 0.5) or 0.5),
        )
        status = "delivered" if 200 <= http_status < 300 else "delivery_failed"
        error = "" if status == "delivered" else f"http_status_{http_status}"
    except Exception as exc:
        http_status = 0
        response_excerpt = ""
        status = "delivery_error"
        error = str(exc)

    receipt = {
        "tenant_code": tenant_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "webhook_url": webhook_url,
        "snapshot_id": str(latest.get("id", "")),
        "http_status": str(http_status),
        "error": error,
        "response_excerpt": response_excerpt,
    }
    receipt_id = redis_client.xadd(_receipt_stream_key(tenant_code), receipt, maxlen=100000, approximate=True)

    return {
        "status": status,
        "tenant_code": tenant_code,
        "receipt_id": receipt_id,
        "snapshot_id": latest.get("id", ""),
        "http_status": http_status,
        "error": error,
    }


def bulletin_delivery_receipts(tenant_code: str, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_receipt_stream_key(tenant_code), count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"tenant_code": tenant_code, "count": len(rows), "rows": rows}
