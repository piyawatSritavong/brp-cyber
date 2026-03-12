from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import ActionCenterDispatchEvent, ActionCenterRoutingPolicy, Site, Tenant
from app.services.notifier import send_line_message, send_telegram_message

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _as_json(value: dict[str, object] | list[object]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _safe_json_load(value: str | None) -> list[object]:
    if not value:
        return []
    try:
        payload = json.loads(value)
        if isinstance(payload, list):
            return payload
    except Exception:
        pass
    return []


def _policy_row(row: ActionCenterRoutingPolicy) -> dict[str, object]:
    return {
        "policy_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "policy_version": row.policy_version,
        "owner": row.owner,
        "telegram_enabled": bool(row.telegram_enabled),
        "line_enabled": bool(row.line_enabled),
        "min_severity": row.min_severity,
        "routing_tags": _safe_json_load(row.routing_tags_json),
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    }


def _default_policy(tenant_id: UUID) -> dict[str, object]:
    return {
        "policy_id": "",
        "tenant_id": str(tenant_id),
        "policy_version": "default",
        "owner": "system",
        "telegram_enabled": True,
        "line_enabled": False,
        "min_severity": "high",
        "routing_tags": [],
        "created_at": "",
        "updated_at": "",
    }


def _get_policy_for_tenant(db: Session, tenant_id: UUID) -> dict[str, object]:
    row = db.scalar(select(ActionCenterRoutingPolicy).where(ActionCenterRoutingPolicy.tenant_id == tenant_id))
    if row:
        return _policy_row(row)
    return _default_policy(tenant_id)


def upsert_action_center_policy(
    db: Session,
    *,
    tenant_code: str,
    policy_version: str,
    owner: str,
    telegram_enabled: bool,
    line_enabled: bool,
    min_severity: str,
    routing_tags: list[str],
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}
    row = db.scalar(select(ActionCenterRoutingPolicy).where(ActionCenterRoutingPolicy.tenant_id == tenant.id))
    now = datetime.now(timezone.utc)
    if row:
        row.policy_version = policy_version
        row.owner = owner
        row.telegram_enabled = telegram_enabled
        row.line_enabled = line_enabled
        row.min_severity = min_severity
        row.routing_tags_json = _as_json(routing_tags)
        row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"status": "updated", "policy": _policy_row(row)}

    created = ActionCenterRoutingPolicy(
        tenant_id=tenant.id,
        policy_version=policy_version,
        owner=owner,
        telegram_enabled=telegram_enabled,
        line_enabled=line_enabled,
        min_severity=min_severity,
        routing_tags_json=_as_json(routing_tags),
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"status": "created", "policy": _policy_row(created)}


def get_action_center_policy(db: Session, tenant_code: str) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}
    return {"status": "ok", "policy": _get_policy_for_tenant(db, tenant.id)}


def _severity_allowed(policy_min: str, severity: str) -> bool:
    min_rank = SEVERITY_ORDER.get(policy_min, 2)
    sev_rank = SEVERITY_ORDER.get(severity, 1)
    return sev_rank >= min_rank


def route_alert(
    db: Session,
    *,
    tenant_id: UUID,
    site_id: UUID | None,
    source: str,
    severity: str,
    title: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, object]:
    policy = _get_policy_for_tenant(db, tenant_id)
    allowed = _severity_allowed(str(policy.get("min_severity", "high")), severity)

    telegram_status = "skipped_threshold"
    line_status = "skipped_threshold"
    if allowed:
        text = f"[BRP-Cyber][{severity.upper()}] {title}\n{message}"
        if bool(policy.get("telegram_enabled", True)):
            telegram_status = "sent" if send_telegram_message(text) else "failed"
        else:
            telegram_status = "disabled"
        if bool(policy.get("line_enabled", False)):
            line_status = "sent" if send_line_message(text) else "failed"
        else:
            line_status = "disabled"

    event = ActionCenterDispatchEvent(
        tenant_id=tenant_id,
        site_id=site_id,
        source=source,
        severity=severity,
        title=title[:255],
        message=message[:4000],
        telegram_status=telegram_status,
        line_status=line_status,
        payload_json=_as_json(payload or {}),
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {
        "status": "dispatched",
        "event_id": str(event.id),
        "policy_min_severity": policy.get("min_severity", "high"),
        "telegram_status": telegram_status,
        "line_status": line_status,
    }


def dispatch_manual_alert(
    db: Session,
    *,
    tenant_code: str,
    site_code: str,
    source: str,
    severity: str,
    title: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}
    site = None
    if site_code:
        site = db.scalar(select(Site).where(Site.tenant_id == tenant.id, Site.site_code == site_code))
    routed = route_alert(
        db,
        tenant_id=tenant.id,
        site_id=site.id if site else None,
        source=source,
        severity=severity,
        title=title,
        message=message,
        payload=payload or {},
    )
    return {"status": "ok", "routing": routed}


def list_action_center_events(
    db: Session,
    *,
    tenant_code: str = "",
    severity: str = "",
    limit: int = 200,
) -> dict[str, object]:
    stmt = select(ActionCenterDispatchEvent).order_by(desc(ActionCenterDispatchEvent.created_at)).limit(max(1, min(limit, 2000)))
    if tenant_code:
        tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
        if not tenant:
            return {"count": 0, "rows": []}
        stmt = stmt.where(ActionCenterDispatchEvent.tenant_id == tenant.id)
    if severity:
        stmt = stmt.where(ActionCenterDispatchEvent.severity == severity)
    rows = db.scalars(stmt).all()
    return {
        "count": len(rows),
        "rows": [
            {
                "event_id": str(row.id),
                "tenant_id": str(row.tenant_id),
                "site_id": str(row.site_id) if row.site_id else "",
                "source": row.source,
                "severity": row.severity,
                "title": row.title,
                "message": row.message,
                "telegram_status": row.telegram_status,
                "line_status": row.line_status,
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ],
    }
