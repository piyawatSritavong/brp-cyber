from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import BlueEventLog, IntegrationEvent, Site, Tenant
from app.services.connector_observability import record_connector_event

SUPPORTED_ADAPTERS: dict[str, dict[str, object]] = {
    "generic": {"name": "Generic JSON Adapter", "ocsf_class": "security_finding"},
    "cloudflare": {"name": "Cloudflare Logpush Adapter", "ocsf_class": "web_activity"},
    "wazuh": {"name": "Wazuh Alert Adapter", "ocsf_class": "security_finding"},
    "splunk": {"name": "Splunk Event Adapter", "ocsf_class": "security_finding"},
    "crowdstrike": {"name": "CrowdStrike Detection Adapter", "ocsf_class": "endpoint_activity"},
}


def _as_json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _safe_json_load(value: str | None) -> dict[str, object]:
    if not value:
        return {}
    try:
        data = json.loads(value)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _get_nested(payload: dict[str, Any], key_path: str) -> Any:
    current: Any = payload
    for key in key_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _pick(payload: dict[str, Any], candidates: list[str], default: Any = "") -> Any:
    for candidate in candidates:
        value = _get_nested(payload, candidate) if "." in candidate else payload.get(candidate)
        if value not in (None, ""):
            return value
    return default


def _severity_to_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"critical", "high", "h", "severe"}:
        return "high"
    if text in {"medium", "med", "m", "warning"}:
        return "medium"
    if text in {"low", "l", "info", "informational"}:
        return "low"
    try:
        level = int(value)
    except Exception:
        return "low"
    if level >= 9:
        return "high"
    if level >= 5:
        return "medium"
    return "low"


def _to_iso_timestamp(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value
    return datetime.now(timezone.utc).isoformat()


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    secret = settings.integration_webhook_hmac_secret.strip()
    if not secret:
        return True
    if not signature:
        return False
    computed = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature.strip().lower())


def normalize_to_ocsf(source: str, event_kind: str, payload: dict[str, Any]) -> dict[str, object]:
    src = source.strip().lower() or "generic"
    adapter = src if src in SUPPORTED_ADAPTERS else "generic"
    event_class = str(SUPPORTED_ADAPTERS.get(adapter, {}).get("ocsf_class", "security_finding"))

    if adapter == "cloudflare":
        source_ip = str(_pick(payload, ["ClientIP", "client_ip", "source_ip"], "unknown"))
        target = str(_pick(payload, ["ClientRequestURI", "request.uri", "url", "path"], ""))
        status_code = int(_pick(payload, ["EdgeResponseStatus", "status", "status_code"], 0) or 0)
        severity = "high" if status_code >= 500 or status_code in {401, 403, 429} else "low"
        message = str(_pick(payload, ["message", "WAFAction", "action"], "cloudflare_event"))
    elif adapter == "wazuh":
        source_ip = str(_pick(payload, ["agent.ip", "data.srcip", "srcip", "source_ip"], "unknown"))
        target = str(_pick(payload, ["agent.name", "rule.id", "target"], ""))
        severity = _severity_to_label(_pick(payload, ["rule.level", "level", "severity"], "low"))
        message = str(_pick(payload, ["rule.description", "description", "message"], "wazuh_alert"))
    elif adapter == "splunk":
        source_ip = str(_pick(payload, ["src", "source_ip", "clientip"], "unknown"))
        target = str(_pick(payload, ["dest", "host", "target"], ""))
        severity = _severity_to_label(_pick(payload, ["severity", "risk_level", "priority"], "low"))
        message = str(_pick(payload, ["signature", "message", "event_name"], "splunk_event"))
    elif adapter == "crowdstrike":
        source_ip = str(_pick(payload, ["device.local_ip", "local_ip", "source_ip"], "unknown"))
        target = str(_pick(payload, ["device.hostname", "hostname", "device_id"], ""))
        severity = _severity_to_label(_pick(payload, ["severity", "behavior.severity", "confidence"], "medium"))
        message = str(_pick(payload, ["description", "behavior.description", "name"], "crowdstrike_detection"))
    else:
        source_ip = str(_pick(payload, ["source_ip", "client_ip", "ip", "src"], "unknown"))
        target = str(_pick(payload, ["target", "url", "path", "resource"], ""))
        severity = _severity_to_label(_pick(payload, ["severity", "level", "priority"], "low"))
        message = str(_pick(payload, ["message", "title", "event"], "security_event"))

    recommendation = "monitor_only"
    if severity == "high":
        recommendation = "immediate_containment"
    elif severity == "medium":
        recommendation = "triage_and_limit"

    return {
        "schema": "ocsf-1.1-compatible",
        "adapter": adapter,
        "source": src,
        "event_kind": event_kind or settings.integration_default_event_kind,
        "class_name": event_class,
        "severity": severity,
        "time": _to_iso_timestamp(_pick(payload, ["timestamp", "time", "@timestamp", "event_time"], "")),
        "actor": {"ip": source_ip},
        "target": {"resource": target},
        "message": message,
        "recommendation": recommendation,
        "raw_fields": payload,
    }


def _resolve_site(
    db: Session,
    *,
    site_id: UUID | None,
    tenant_code: str,
    site_code: str,
) -> Site | None:
    if site_id:
        return db.get(Site, site_id)
    if site_code:
        row = db.scalar(select(Site).where(Site.site_code == site_code))
        if row:
            return row
    if tenant_code and site_code:
        tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
        if tenant:
            return db.scalar(select(Site).where(Site.tenant_id == tenant.id, Site.site_code == site_code))
    return None


def _route_to_blue_event(db: Session, site: Site | None, normalized: dict[str, object]) -> str:
    if not site:
        return ""
    severity = str(normalized.get("severity", "low"))
    recommendation = str(normalized.get("recommendation", "monitor_only"))
    event = BlueEventLog(
        site_id=site.id,
        event_type=str(normalized.get("event_kind", "external_event")),
        source_ip=str(normalized.get("actor", {}).get("ip", "unknown")),
        payload_json=_as_json(normalized),
        ai_severity=severity,
        ai_recommendation=recommendation,
        status="open",
        action_taken="",
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.flush()
    return str(event.id)


def ingest_integration_event(
    db: Session,
    *,
    source: str,
    event_kind: str,
    payload: dict[str, Any],
    site_id: UUID | None,
    tenant_code: str,
    site_code: str,
    webhook_event_id: str = "",
) -> dict[str, object]:
    site = _resolve_site(db, site_id=site_id, tenant_code=tenant_code, site_code=site_code)
    normalized = normalize_to_ocsf(source=source, event_kind=event_kind, payload=payload)
    if webhook_event_id:
        normalized["webhook_event_id"] = webhook_event_id

    row = IntegrationEvent(
        site_id=site.id if site else None,
        source=source.strip().lower() or "generic",
        event_kind=event_kind or settings.integration_default_event_kind,
        raw_payload_json=_as_json(payload),
        normalized_payload_json=_as_json(normalized),
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    blue_event_id = _route_to_blue_event(db, site, normalized)
    record_connector_event(
        db,
        connector_source=source.strip().lower() or "generic",
        event_type="delivery_attempt",
        status="success",
        site_id=site.id if site else None,
        latency_ms=0,
        attempt=1,
        payload={"event_kind": event_kind or settings.integration_default_event_kind, "blue_event_id": blue_event_id},
    )
    db.commit()
    db.refresh(row)
    return {
        "status": "accepted",
        "integration_event_id": str(row.id),
        "site_id": str(site.id) if site else "",
        "blue_event_id": blue_event_id,
        "normalized": normalized,
    }


def list_integration_events(
    db: Session,
    *,
    source: str = "",
    site_id: UUID | None = None,
    limit: int = 100,
) -> dict[str, object]:
    stmt = select(IntegrationEvent).order_by(desc(IntegrationEvent.created_at)).limit(max(1, min(limit, 1000)))
    if source:
        stmt = stmt.where(IntegrationEvent.source == source.strip().lower())
    if site_id:
        stmt = stmt.where(IntegrationEvent.site_id == site_id)
    rows = db.scalars(stmt).all()
    return {
        "count": len(rows),
        "rows": [
            {
                "integration_event_id": str(row.id),
                "site_id": str(row.site_id) if row.site_id else "",
                "source": row.source,
                "event_kind": row.event_kind,
                "normalized": _safe_json_load(row.normalized_payload_json),
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ],
    }


def list_supported_adapters() -> dict[str, object]:
    return {
        "count": len(SUPPORTED_ADAPTERS),
        "adapters": SUPPORTED_ADAPTERS,
    }
