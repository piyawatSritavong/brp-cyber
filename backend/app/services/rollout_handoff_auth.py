from __future__ import annotations

import hashlib
import ipaddress
import secrets
import time
from typing import Any
from uuid import UUID

from app.services.redis_client import redis_client

ROLLOUT_HANDOFF_TOKEN_PREFIX = "rollout_handoff_token"
ROLLOUT_HANDOFF_RECEIPT_PREFIX = "rollout_handoff_receipt"
ROLLOUT_HANDOFF_POLICY_PREFIX = "rollout_handoff_policy"
ROLLOUT_HANDOFF_ANOMALY_PREFIX = "rollout_handoff_anomaly"
ROLLOUT_HANDOFF_TRUST_EVENT_PREFIX = "rollout_handoff_trust_event"
ROLLOUT_HANDOFF_CONTAINMENT_PREFIX = "rollout_handoff_containment"


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _token_key(token_id: str) -> str:
    return f"{ROLLOUT_HANDOFF_TOKEN_PREFIX}:{token_id}"


def _receipt_key(tenant_id: UUID) -> str:
    return f"{ROLLOUT_HANDOFF_RECEIPT_PREFIX}:{tenant_id}"


def _policy_key(tenant_id: UUID) -> str:
    return f"{ROLLOUT_HANDOFF_POLICY_PREFIX}:{tenant_id}"


def _anomaly_key(tenant_id: UUID) -> str:
    return f"{ROLLOUT_HANDOFF_ANOMALY_PREFIX}:{tenant_id}"


def _trust_event_key(tenant_id: UUID) -> str:
    return f"{ROLLOUT_HANDOFF_TRUST_EVENT_PREFIX}:{tenant_id}"


def _containment_key(tenant_id: UUID) -> str:
    return f"{ROLLOUT_HANDOFF_CONTAINMENT_PREFIX}:{tenant_id}"


def _normalize_policy(raw: dict[str, str] | None = None) -> dict[str, Any]:
    row = raw or {}
    high = max(1, min(100, int(row.get("containment_high_threshold", "60") or 60)))
    critical = max(high, min(100, int(row.get("containment_critical_threshold", "85") or 85)))
    action_high = str(row.get("containment_action_high", "harden_session") or "harden_session").strip()
    action_critical = str(row.get("containment_action_critical", "revoke_token") or "revoke_token").strip()
    if action_high not in {"log_only", "harden_session", "revoke_token"}:
        action_high = "harden_session"
    if action_critical not in {"log_only", "harden_session", "revoke_token"}:
        action_critical = "revoke_token"
    return {
        "anomaly_detection_enabled": str(row.get("anomaly_detection_enabled", "1")) in {"1", "true", "True"},
        "auto_revoke_on_ip_mismatch": str(row.get("auto_revoke_on_ip_mismatch", "1")) in {"1", "true", "True"},
        "max_denied_attempts_before_revoke": max(1, int(row.get("max_denied_attempts_before_revoke", "3") or 3)),
        "adaptive_hardening_enabled": str(row.get("adaptive_hardening_enabled", "1")) in {"1", "true", "True"},
        "risk_threshold_block": max(1, min(100, int(row.get("risk_threshold_block", "85") or 85))),
        "risk_threshold_harden": max(1, min(100, int(row.get("risk_threshold_harden", "60") or 60))),
        "harden_session_ttl_seconds": max(60, int(row.get("harden_session_ttl_seconds", "300") or 300)),
        "containment_playbook_enabled": str(row.get("containment_playbook_enabled", "1")) in {"1", "true", "True"},
        "containment_high_threshold": high,
        "containment_critical_threshold": critical,
        "containment_action_high": action_high,
        "containment_action_critical": action_critical,
    }


def issue_rollout_handoff_token(
    *,
    tenant_id: UUID,
    actor: str,
    auditor_name: str = "external_auditor",
    ttl_seconds: int = 86400,
    session_ttl_seconds: int = 3600,
    max_accesses: int = 100,
    allowed_ip_cidrs: str = "",
) -> dict[str, Any]:
    token_id = secrets.token_hex(8)
    secret = secrets.token_urlsafe(24)
    ttl = max(60, int(ttl_seconds))
    expires_at = int(time.time()) + ttl
    session_ttl = max(60, min(ttl, int(session_ttl_seconds)))
    session_expires_at = int(time.time()) + session_ttl
    max_reads = max(1, int(max_accesses))

    redis_client.hset(
        _token_key(token_id),
        mapping={
            "secret_hash": _hash_secret(secret),
            "expires_at": str(expires_at),
            "session_expires_at": str(session_expires_at),
            "max_accesses": str(max_reads),
            "access_count": "0",
            "allowed_ip_cidrs": allowed_ip_cidrs.strip(),
            "denied_attempts": "0",
            "last_denied_reason": "",
            "actor": actor,
            "auditor_name": auditor_name,
            "revoked": "0",
            "tenant_scope": str(tenant_id),
        },
    )
    redis_client.expire(_token_key(token_id), ttl)

    return {
        "token": f"rht_{token_id}.{secret}",
        "token_id": token_id,
        "actor": actor,
        "auditor_name": auditor_name,
        "tenant_scope": str(tenant_id),
        "expires_at": expires_at,
        "session_expires_at": session_expires_at,
        "max_accesses": max_reads,
        "allowed_ip_cidrs": allowed_ip_cidrs.strip(),
        "ttl_seconds": ttl,
    }


def upsert_rollout_handoff_policy(
    *,
    tenant_id: UUID,
    anomaly_detection_enabled: bool = True,
    auto_revoke_on_ip_mismatch: bool = True,
    max_denied_attempts_before_revoke: int = 3,
    adaptive_hardening_enabled: bool = True,
    risk_threshold_block: int = 85,
    risk_threshold_harden: int = 60,
    harden_session_ttl_seconds: int = 300,
    containment_playbook_enabled: bool = True,
    containment_high_threshold: int = 60,
    containment_critical_threshold: int = 85,
    containment_action_high: str = "harden_session",
    containment_action_critical: str = "revoke_token",
) -> dict[str, Any]:
    normalized = _normalize_policy(
        {
            "anomaly_detection_enabled": anomaly_detection_enabled,
            "auto_revoke_on_ip_mismatch": auto_revoke_on_ip_mismatch,
            "max_denied_attempts_before_revoke": max_denied_attempts_before_revoke,
            "adaptive_hardening_enabled": adaptive_hardening_enabled,
            "risk_threshold_block": risk_threshold_block,
            "risk_threshold_harden": risk_threshold_harden,
            "harden_session_ttl_seconds": harden_session_ttl_seconds,
            "containment_playbook_enabled": containment_playbook_enabled,
            "containment_high_threshold": containment_high_threshold,
            "containment_critical_threshold": containment_critical_threshold,
            "containment_action_high": containment_action_high,
            "containment_action_critical": containment_action_critical,
        }
    )
    redis_client.hset(
        _policy_key(tenant_id),
        mapping={
            "anomaly_detection_enabled": "1" if normalized["anomaly_detection_enabled"] else "0",
            "auto_revoke_on_ip_mismatch": "1" if normalized["auto_revoke_on_ip_mismatch"] else "0",
            "max_denied_attempts_before_revoke": str(normalized["max_denied_attempts_before_revoke"]),
            "adaptive_hardening_enabled": "1" if normalized["adaptive_hardening_enabled"] else "0",
            "risk_threshold_block": str(normalized["risk_threshold_block"]),
            "risk_threshold_harden": str(normalized["risk_threshold_harden"]),
            "harden_session_ttl_seconds": str(normalized["harden_session_ttl_seconds"]),
            "containment_playbook_enabled": "1" if normalized["containment_playbook_enabled"] else "0",
            "containment_high_threshold": str(normalized["containment_high_threshold"]),
            "containment_critical_threshold": str(normalized["containment_critical_threshold"]),
            "containment_action_high": str(normalized["containment_action_high"]),
            "containment_action_critical": str(normalized["containment_action_critical"]),
        },
    )
    return {"tenant_id": str(tenant_id), "policy": normalized}


def get_rollout_handoff_policy(tenant_id: UUID) -> dict[str, Any]:
    raw = redis_client.hgetall(_policy_key(tenant_id))
    return {"tenant_id": str(tenant_id), "policy": _normalize_policy(raw if raw else None)}


def _normalize_source_ip(source_ip: str) -> str:
    value = source_ip.strip()
    if not value:
        return ""
    return value.split(",", 1)[0].strip()


def _ip_allowed(source_ip: str, allowed_ip_cidrs: str) -> bool:
    if not allowed_ip_cidrs.strip():
        return True
    if not source_ip:
        return False
    try:
        ip = ipaddress.ip_address(source_ip)
    except ValueError:
        return False
    for part in [p.strip() for p in allowed_ip_cidrs.split(",") if p.strip()]:
        try:
            network = ipaddress.ip_network(part, strict=False)
        except ValueError:
            continue
        if ip in network:
            return True
    return False


def _append_access_receipt(
    *,
    tenant_id: UUID,
    token_id: str,
    auditor_name: str,
    source_ip: str,
    status: str,
    reason: str,
    access_count: int,
) -> None:
    redis_client.xadd(
        _receipt_key(tenant_id),
        {
            "tenant_id": str(tenant_id),
            "token_id": token_id,
            "auditor_name": auditor_name,
            "source_ip": source_ip,
            "status": status,
            "reason": reason,
            "access_count": str(access_count),
            "timestamp": str(int(time.time())),
        },
        maxlen=5000,
        approximate=True,
    )


def _append_anomaly(
    *,
    tenant_id: UUID,
    token_id: str,
    reason: str,
    source_ip: str,
    denied_attempts: int,
    auto_revoked: bool,
) -> None:
    redis_client.xadd(
        _anomaly_key(tenant_id),
        {
            "tenant_id": str(tenant_id),
            "token_id": token_id,
            "reason": reason,
            "source_ip": source_ip,
            "denied_attempts": str(denied_attempts),
            "auto_revoked": "1" if auto_revoked else "0",
            "timestamp": str(int(time.time())),
        },
        maxlen=5000,
        approximate=True,
    )


def _append_trust_event(
    *,
    tenant_id: UUID,
    token_id: str,
    status: str,
    reason: str,
    source_ip: str,
    risk_score: int,
    action_taken: str,
) -> None:
    redis_client.xadd(
        _trust_event_key(tenant_id),
        {
            "tenant_id": str(tenant_id),
            "token_id": token_id,
            "status": status,
            "reason": reason,
            "source_ip": source_ip,
            "risk_score": str(risk_score),
            "action_taken": action_taken,
            "timestamp": str(int(time.time())),
        },
        maxlen=5000,
        approximate=True,
    )


def _append_containment_event(
    *,
    tenant_id: UUID,
    token_id: str,
    source_ip: str,
    risk_score: int,
    risk_tier: str,
    action_taken: str,
    trigger_reason: str,
) -> None:
    redis_client.xadd(
        _containment_key(tenant_id),
        {
            "tenant_id": str(tenant_id),
            "token_id": token_id,
            "source_ip": source_ip,
            "risk_score": str(risk_score),
            "risk_tier": risk_tier,
            "action_taken": action_taken,
            "trigger_reason": trigger_reason,
            "timestamp": str(int(time.time())),
        },
        maxlen=5000,
        approximate=True,
    )


def _containment_tier(policy: dict[str, Any], risk_score: int) -> str:
    critical = int(policy.get("containment_critical_threshold", 85))
    high = int(policy.get("containment_high_threshold", 60))
    if risk_score >= critical:
        return "critical"
    if risk_score >= high:
        return "high"
    return "normal"


def _apply_containment_playbook(
    *,
    tenant_id: UUID,
    token_id: str,
    data: dict[str, str],
    source_ip: str,
    risk_score: int,
    trigger_reason: str,
    policy: dict[str, Any],
) -> str:
    if not policy.get("containment_playbook_enabled", True):
        return "disabled"

    tier = _containment_tier(policy, risk_score)
    action = "log_only"
    if tier == "critical":
        action = str(policy.get("containment_action_critical", "revoke_token"))
    elif tier == "high":
        action = str(policy.get("containment_action_high", "harden_session"))

    if action == "harden_session":
        now = int(time.time())
        hardened_until = now + int(policy.get("harden_session_ttl_seconds", 300))
        current_session_until = int(data.get("session_expires_at", "0") or 0)
        if current_session_until == 0 or hardened_until < current_session_until:
            redis_client.hset(_token_key(token_id), mapping={"session_expires_at": str(hardened_until)})
    elif action == "revoke_token":
        redis_client.hset(_token_key(token_id), mapping={"revoked": "1", "last_denied_reason": "containment_revoke"})

    _append_containment_event(
        tenant_id=tenant_id,
        token_id=token_id,
        source_ip=source_ip,
        risk_score=risk_score,
        risk_tier=tier,
        action_taken=action,
        trigger_reason=trigger_reason,
    )
    return action


def _compute_risk_score(*, data: dict[str, str], reason: str, source_ip: str) -> int:
    score = 0
    denied_attempts = int(data.get("denied_attempts", "0") or 0)
    access_count = int(data.get("access_count", "0") or 0)
    max_accesses = max(1, int(data.get("max_accesses", "100") or 100))

    if reason == "source_ip_not_allowed":
        score += 70
    elif reason == "access_limit_reached":
        score += 80
    elif reason == "risk_threshold_block":
        score += 90
    elif reason == "ok":
        score += 5

    score += min(30, denied_attempts * 10)
    ratio = access_count / max_accesses
    if ratio >= 0.9:
        score += 20
    elif ratio >= 0.75:
        score += 10

    if source_ip:
        score += 0
    return min(100, max(0, score))


def _apply_anomaly_policy(
    *,
    token_id: str,
    data: dict[str, str],
    reason: str,
    source_ip: str,
) -> None:
    tenant_scope = data.get("tenant_scope", "")
    if not tenant_scope:
        return
    try:
        tenant_id = UUID(tenant_scope)
    except ValueError:
        return
    policy = get_rollout_handoff_policy(tenant_id).get("policy", _normalize_policy())
    if not policy.get("anomaly_detection_enabled", True):
        return

    denied_attempts = int(data.get("denied_attempts", "0") or 0) + 1
    auto_revoke = False
    if reason == "source_ip_not_allowed" and bool(policy.get("auto_revoke_on_ip_mismatch", True)):
        auto_revoke = True
    if denied_attempts >= int(policy.get("max_denied_attempts_before_revoke", 3)):
        auto_revoke = True

    redis_client.hset(
        _token_key(token_id),
        mapping={
            "denied_attempts": str(denied_attempts),
            "last_denied_reason": reason,
            "revoked": "1" if auto_revoke else str(data.get("revoked", "0")),
        },
    )
    risk_score = _compute_risk_score(data={**data, "denied_attempts": str(denied_attempts)}, reason=reason, source_ip=source_ip)
    _append_access_receipt(
        tenant_id=tenant_id,
        token_id=token_id,
        auditor_name=str(data.get("auditor_name", "external_auditor")),
        source_ip=source_ip,
        status="denied",
        reason=reason,
        access_count=int(data.get("access_count", "0") or 0),
    )
    _append_anomaly(
        tenant_id=tenant_id,
        token_id=token_id,
        reason=reason,
        source_ip=source_ip,
        denied_attempts=denied_attempts,
        auto_revoked=auto_revoke,
    )
    _append_trust_event(
        tenant_id=tenant_id,
        token_id=token_id,
        status="denied",
        reason=reason,
        source_ip=source_ip,
        risk_score=risk_score,
        action_taken="revoked" if auto_revoke else "logged",
    )
    _apply_containment_playbook(
        tenant_id=tenant_id,
        token_id=token_id,
        data={**data, "denied_attempts": str(denied_attempts)},
        source_ip=source_ip,
        risk_score=risk_score,
        trigger_reason=reason,
        policy=policy,
    )


def verify_rollout_handoff_token(token: str, *, source_ip: str = "", consume: bool = False) -> dict[str, Any]:
    if not token.startswith("rht_") or "." not in token:
        return {"valid": False, "reason": "invalid_format"}

    prefix, secret = token.split(".", 1)
    token_id = prefix.removeprefix("rht_")
    data = redis_client.hgetall(_token_key(token_id))
    if not data:
        return {"valid": False, "reason": "not_found"}
    if data.get("revoked") == "1":
        return {"valid": False, "reason": "revoked"}

    now = int(time.time())
    expires_at = int(data.get("expires_at", "0") or 0)
    if now >= expires_at:
        return {"valid": False, "reason": "expired"}
    session_expires_at = int(data.get("session_expires_at", "0") or 0)
    if session_expires_at and now >= session_expires_at:
        return {"valid": False, "reason": "session_expired"}
    if _hash_secret(secret) != data.get("secret_hash", ""):
        return {"valid": False, "reason": "secret_mismatch"}

    src_ip = _normalize_source_ip(source_ip)
    if not _ip_allowed(src_ip, str(data.get("allowed_ip_cidrs", ""))):
        if consume:
            _apply_anomaly_policy(token_id=token_id, data=data, reason="source_ip_not_allowed", source_ip=src_ip)
        return {"valid": False, "reason": "source_ip_not_allowed"}

    token_id_value = token_id
    access_count = int(data.get("access_count", "0") or 0)
    max_accesses = int(data.get("max_accesses", "100") or 100)
    if access_count >= max_accesses:
        if consume:
            _apply_anomaly_policy(token_id=token_id, data=data, reason="access_limit_reached", source_ip=src_ip)
        return {"valid": False, "reason": "access_limit_reached"}

    if consume:
        policy = get_rollout_handoff_policy(UUID(data.get("tenant_scope", ""))).get("policy", _normalize_policy())
        tenant_id = UUID(data.get("tenant_scope", ""))
        risk_score = _compute_risk_score(data=data, reason="ok", source_ip=src_ip)
        if policy.get("adaptive_hardening_enabled", True) and risk_score >= int(policy.get("risk_threshold_block", 85)):
            redis_client.hset(_token_key(token_id), mapping={"revoked": "1", "last_denied_reason": "risk_threshold_block"})
            _append_access_receipt(
                tenant_id=tenant_id,
                token_id=token_id_value,
                auditor_name=str(data.get("auditor_name", "external_auditor")),
                source_ip=src_ip,
                status="denied",
                reason="risk_threshold_block",
                access_count=access_count,
            )
            _append_anomaly(
                tenant_id=tenant_id,
                token_id=token_id_value,
                reason="risk_threshold_block",
                source_ip=src_ip,
                denied_attempts=int(data.get("denied_attempts", "0") or 0),
                auto_revoked=True,
            )
            _append_trust_event(
                tenant_id=tenant_id,
                token_id=token_id_value,
                status="denied",
                reason="risk_threshold_block",
                source_ip=src_ip,
                risk_score=risk_score,
                action_taken="revoked",
            )
            _append_containment_event(
                tenant_id=tenant_id,
                token_id=token_id_value,
                source_ip=src_ip,
                risk_score=risk_score,
                risk_tier="critical",
                action_taken="revoke_token",
                trigger_reason="risk_threshold_block",
            )
            return {"valid": False, "reason": "risk_threshold_block"}

        if policy.get("adaptive_hardening_enabled", True) and risk_score >= int(policy.get("risk_threshold_harden", 60)):
            now = int(time.time())
            hardened_until = now + int(policy.get("harden_session_ttl_seconds", 300))
            current_session_until = int(data.get("session_expires_at", "0") or 0)
            if current_session_until == 0 or hardened_until < current_session_until:
                redis_client.hset(_token_key(token_id), mapping={"session_expires_at": str(hardened_until)})
                session_expires_at = hardened_until

        access_count += 1
        redis_client.hset(_token_key(token_id), mapping={"access_count": str(access_count)})
        _append_access_receipt(
            tenant_id=tenant_id,
            token_id=token_id_value,
            auditor_name=str(data.get("auditor_name", "external_auditor")),
            source_ip=src_ip,
            status="allowed",
            reason="ok",
            access_count=access_count,
        )
        _append_trust_event(
            tenant_id=tenant_id,
            token_id=token_id_value,
            status="allowed",
            reason="ok",
            source_ip=src_ip,
            risk_score=risk_score,
            action_taken="allowed",
        )
        _apply_containment_playbook(
            tenant_id=tenant_id,
            token_id=token_id_value,
            data={**data, "access_count": str(access_count)},
            source_ip=src_ip,
            risk_score=risk_score,
            trigger_reason="ok",
            policy=policy,
        )

    return {
        "valid": True,
        "token_id": token_id_value,
        "actor": data.get("actor", "unknown"),
        "auditor_name": data.get("auditor_name", "external_auditor"),
        "tenant_scope": data.get("tenant_scope", ""),
        "expires_at": expires_at,
        "session_expires_at": session_expires_at,
        "max_accesses": max_accesses,
        "access_count": access_count,
    }


def revoke_rollout_handoff_token(token: str) -> dict[str, Any]:
    verified = verify_rollout_handoff_token(token)
    if not verified.get("valid"):
        return {"status": "not_revoked", "reason": verified.get("reason", "invalid")}

    token_id = str(verified["token_id"])
    redis_client.hset(_token_key(token_id), mapping={"revoked": "1"})
    return {"status": "revoked", "token_id": token_id}


def handoff_allows_tenant(verified: dict[str, Any], tenant_id: UUID) -> bool:
    return str(verified.get("tenant_scope", "")).strip() == str(tenant_id)


def rollout_handoff_receipts(tenant_id: UUID, limit: int = 100) -> dict[str, Any]:
    events = redis_client.xrevrange(_receipt_key(tenant_id), count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in events:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"tenant_id": str(tenant_id), "count": len(rows), "rows": rows}


def rollout_handoff_anomalies(tenant_id: UUID, limit: int = 100) -> dict[str, Any]:
    events = redis_client.xrevrange(_anomaly_key(tenant_id), count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in events:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"tenant_id": str(tenant_id), "count": len(rows), "rows": rows}


def rollout_handoff_trust_events(tenant_id: UUID, limit: int = 100) -> dict[str, Any]:
    events = redis_client.xrevrange(_trust_event_key(tenant_id), count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in events:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"tenant_id": str(tenant_id), "count": len(rows), "rows": rows}


def rollout_handoff_risk_snapshot(tenant_id: UUID, limit: int = 200) -> dict[str, Any]:
    events = rollout_handoff_trust_events(tenant_id, limit=max(1, limit)).get("rows", [])
    if not events:
        return {"tenant_id": str(tenant_id), "count": 0, "avg_risk_score": 0.0, "max_risk_score": 0, "blocked_count": 0}
    scores: list[int] = []
    blocked = 0
    for row in events:
        score = int(row.get("risk_score", "0") or 0)
        scores.append(score)
        if row.get("action_taken") == "revoked":
            blocked += 1
    avg = sum(scores) / len(scores)
    return {
        "tenant_id": str(tenant_id),
        "count": len(scores),
        "avg_risk_score": round(avg, 2),
        "max_risk_score": max(scores),
        "blocked_count": blocked,
    }


def rollout_handoff_containment_events(tenant_id: UUID, limit: int = 100) -> dict[str, Any]:
    events = redis_client.xrevrange(_containment_key(tenant_id), count=max(1, limit))
    rows: list[dict[str, str]] = []
    for event_id, fields in events:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"tenant_id": str(tenant_id), "count": len(rows), "rows": rows}


def rollout_handoff_governance_snapshot(tenant_id: UUID, limit: int = 200) -> dict[str, Any]:
    risk = rollout_handoff_risk_snapshot(tenant_id, limit=max(1, limit))
    events = rollout_handoff_containment_events(tenant_id, limit=max(1, limit)).get("rows", [])
    action_counts: dict[str, int] = {}
    tier_counts: dict[str, int] = {}
    for row in events:
        action = str(row.get("action_taken", "unknown"))
        tier = str(row.get("risk_tier", "unknown"))
        action_counts[action] = action_counts.get(action, 0) + 1
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    return {
        "tenant_id": str(tenant_id),
        "risk_snapshot": risk,
        "containment_event_count": len(events),
        "containment_action_counts": action_counts,
        "containment_tier_counts": tier_counts,
    }
