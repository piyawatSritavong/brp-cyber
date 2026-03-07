from __future__ import annotations

from datetime import datetime
from ipaddress import ip_address, ip_network
from uuid import UUID, uuid4

from app.core.config import settings
from app.services.event_store import persist_event
from app.services.firewall_client import block_ip
from app.services.notifier import send_telegram_message
from app.services import policy_store as _policy_store
from app.services.policy_store import get_blue_policy
from app.services.redis_client import redis_client
from schemas.events import DetectionEvent, EventMetadata, ResponseEvent
from schemas.ingest import AuthLoginEvent, SystemAuthEvent, WafHttpEvent


def _parse_csv(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _is_allowlisted_ip(source_ip: str) -> bool:
    allowlisted = _parse_csv(settings.allowlist_ips)
    return source_ip in allowlisted


def _is_allowlisted_cidr(source_ip: str) -> bool:
    try:
        ip_value = ip_address(source_ip)
    except ValueError:
        return False

    for cidr in _parse_csv(settings.allowlist_cidrs):
        try:
            if ip_value in ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def _is_allowlisted_username(username: str) -> bool:
    return username.lower() in {name.lower() for name in _parse_csv(settings.allowlist_usernames)}


def _is_allowlisted_asn(source_asn: int | None) -> bool:
    if source_asn is None:
        return False
    asns = {int(item) for item in _parse_csv(settings.allowlist_asns) if item.isdigit()}
    return source_asn in asns


def _failure_key(tenant_id: UUID, source_ip: str) -> str:
    return f"auth_failures:{tenant_id}:{source_ip}"


def _incident_stream_key(tenant_id: UUID) -> str:
    return f"incidents:{tenant_id}"


def _cooldown_key(tenant_id: UUID, source_ip: str) -> str:
    return f"incident_cooldown:{tenant_id}:{source_ip}"


def _is_login_related_path(path: str) -> bool:
    normalized = path.lower()
    return "/login" in normalized or "/admin" in normalized or "/auth" in normalized


def process_system_auth_event(event: SystemAuthEvent) -> dict[str, str]:
    normalized = AuthLoginEvent(
        tenant_id=event.tenant_id,
        timestamp=event.timestamp,
        source_ip=event.source_ip,
        source_asn=event.source_asn,
        username=event.username,
        success=event.event_type == "login_success",
        auth_source=event.auth_source,
    )
    return process_auth_login_event(normalized)


def process_waf_http_event(event: WafHttpEvent) -> dict[str, str]:
    is_failed_login_pattern = _is_login_related_path(event.path) and event.status_code in {401, 403, 429}
    if not is_failed_login_pattern:
        return {"status": "ignored", "reason": "non_login_or_non_failed_pattern"}

    normalized = AuthLoginEvent(
        tenant_id=event.tenant_id,
        timestamp=event.timestamp,
        source_ip=event.source_ip,
        source_asn=event.source_asn,
        username=event.username,
        success=False,
        auth_source=event.provider,
    )
    return process_auth_login_event(normalized)


def process_auth_login_event(event: AuthLoginEvent) -> dict[str, str]:
    _policy_store.redis_client = redis_client
    policy = get_blue_policy(event.tenant_id)
    threshold = policy["failed_login_threshold_per_minute"]
    window_seconds = policy["failure_window_seconds"]
    incident_cooldown_seconds = policy["incident_cooldown_seconds"]

    if event.success:
        return {"status": "ignored", "reason": "success_login"}

    now_ts = int(event.timestamp.timestamp())
    key = _failure_key(event.tenant_id, event.source_ip)
    redis_client.zadd(key, {str(uuid4()): now_ts})
    redis_client.zremrangebyscore(key, 0, now_ts - window_seconds)
    failure_count = redis_client.zcard(key)
    redis_client.expire(key, window_seconds * 3)

    if failure_count <= threshold:
        return {"status": "monitored", "reason": f"below_threshold:{failure_count}"}

    if _is_allowlisted_ip(event.source_ip):
        return {"status": "suppressed", "reason": "allowlisted_ip"}
    if _is_allowlisted_cidr(event.source_ip):
        return {"status": "suppressed", "reason": "allowlisted_cidr"}
    if _is_allowlisted_username(event.username):
        return {"status": "suppressed", "reason": "allowlisted_username"}
    if _is_allowlisted_asn(event.source_asn):
        return {"status": "suppressed", "reason": "allowlisted_asn"}

    cooldown_key = _cooldown_key(event.tenant_id, event.source_ip)
    if redis_client.exists(cooldown_key):
        return {"status": "suppressed", "reason": "incident_cooldown"}
    redis_client.set(cooldown_key, "1", ex=incident_cooldown_seconds)

    metadata = EventMetadata(
        tenant_id=event.tenant_id,
        correlation_id=uuid4(),
        trace_id=uuid4(),
        source="blue_detection_engine",
        timestamp=datetime.utcnow(),
    )

    detection = DetectionEvent(
        metadata=metadata,
        detector="failed_login_burst",
        severity="high",
        signal_name="brute_force_suspected",
        confidence=0.9,
        status="confirmed",
    )
    persist_event(detection)

    block_ok = block_ip(str(event.tenant_id), event.source_ip, reason="brute_force_suspected")
    response = ResponseEvent(
        metadata=metadata,
        action="block_ip",
        reason_code="brute_force_suspected",
        actor="blue_auto_response",
        target=event.source_ip,
        result="success" if block_ok else "failed",
    )
    persist_event(response)

    incident_payload = {
        "tenant_id": str(event.tenant_id),
        "timestamp": metadata.timestamp.isoformat(),
        "threat_actor": event.source_ip,
        "severity": detection.severity,
        "signal": detection.signal_name,
        "action_taken": response.action,
        "action_result": response.result,
        "username": event.username,
        "failed_attempts": str(failure_count),
    }
    redis_client.xadd(_incident_stream_key(event.tenant_id), incident_payload, maxlen=10000, approximate=True)

    alert_message = (
        f"[BRP-Cyber] Threat Detected\n"
        f"Tenant: {event.tenant_id}\n"
        f"Actor: {event.source_ip}\n"
        f"Severity: HIGH\n"
        f"Action: block_ip ({response.result})\n"
        f"Signal: brute_force_suspected"
    )
    send_telegram_message(alert_message)

    return {"status": "mitigated", "reason": "brute_force_suspected"}
