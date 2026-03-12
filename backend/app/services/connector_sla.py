from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import ConnectorDeliveryEvent, ConnectorSlaBreachEvent, ConnectorSlaProfile, Tenant
from app.services.action_center import route_alert


def _as_json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _safe_json_load(value: str | None) -> dict[str, object]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _profile_row(row: ConnectorSlaProfile) -> dict[str, object]:
    return {
        "profile_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "connector_source": row.connector_source,
        "min_events": row.min_events,
        "min_success_rate": row.min_success_rate,
        "max_dead_letter_count": row.max_dead_letter_count,
        "max_average_latency_ms": row.max_average_latency_ms,
        "notify_on_breach": bool(row.notify_on_breach),
        "enabled": bool(row.enabled),
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    }


def _default_profile(tenant_id: str, connector_source: str) -> dict[str, object]:
    return {
        "profile_id": "",
        "tenant_id": tenant_id,
        "connector_source": connector_source,
        "min_events": 20,
        "min_success_rate": 95,
        "max_dead_letter_count": 5,
        "max_average_latency_ms": 5000,
        "notify_on_breach": True,
        "enabled": True,
        "created_at": "",
        "updated_at": "",
    }


def upsert_connector_sla_profile(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str,
    min_events: int,
    min_success_rate: int,
    max_dead_letter_count: int,
    max_average_latency_ms: int,
    notify_on_breach: bool,
    enabled: bool,
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}
    source = connector_source.strip().lower() or "*"
    row = db.scalar(
        select(ConnectorSlaProfile).where(ConnectorSlaProfile.tenant_id == tenant.id, ConnectorSlaProfile.connector_source == source)
    )
    now = datetime.now(timezone.utc)
    if row:
        row.min_events = min_events
        row.min_success_rate = min_success_rate
        row.max_dead_letter_count = max_dead_letter_count
        row.max_average_latency_ms = max_average_latency_ms
        row.notify_on_breach = notify_on_breach
        row.enabled = enabled
        row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"status": "updated", "profile": _profile_row(row)}

    created = ConnectorSlaProfile(
        tenant_id=tenant.id,
        connector_source=source,
        min_events=min_events,
        min_success_rate=min_success_rate,
        max_dead_letter_count=max_dead_letter_count,
        max_average_latency_ms=max_average_latency_ms,
        notify_on_breach=notify_on_breach,
        enabled=enabled,
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"status": "created", "profile": _profile_row(created)}


def get_connector_sla_profile(db: Session, tenant_code: str, connector_source: str = "*") -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}
    source = connector_source.strip().lower() or "*"
    row = db.scalar(
        select(ConnectorSlaProfile).where(ConnectorSlaProfile.tenant_id == tenant.id, ConnectorSlaProfile.connector_source == source)
    )
    if row:
        return {"status": "ok", "profile": _profile_row(row)}
    wildcard = db.scalar(
        select(ConnectorSlaProfile).where(ConnectorSlaProfile.tenant_id == tenant.id, ConnectorSlaProfile.connector_source == "*")
    )
    if wildcard:
        return {"status": "ok", "profile": _profile_row(wildcard)}
    return {"status": "default", "profile": _default_profile(str(tenant.id), source)}


def evaluate_connector_sla(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str,
    lookback_limit: int = 1000,
    route_alert_on_breach: bool = True,
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}

    profile = get_connector_sla_profile(db, tenant_code, connector_source).get("profile", {})
    if not profile:
        return {"status": "profile_not_found", "tenant_code": tenant_code}
    if not bool(profile.get("enabled", True)):
        return {"status": "disabled", "profile": profile}

    source = connector_source.strip().lower() or "*"
    stmt = (
        select(ConnectorDeliveryEvent)
        .where(ConnectorDeliveryEvent.tenant_id == tenant.id)
        .order_by(desc(ConnectorDeliveryEvent.created_at))
        .limit(max(1, min(lookback_limit, 5000)))
    )
    if source != "*":
        stmt = stmt.where(ConnectorDeliveryEvent.connector_source == source)
    rows = db.scalars(stmt).all()

    total_events = len(rows)
    success_count = len([row for row in rows if row.status == "success"])
    dead_letter_count = len([row for row in rows if row.event_type == "dead_letter"])
    average_latency_ms = round((sum(row.latency_ms for row in rows) / total_events), 2) if total_events else 0.0
    success_rate = round((success_count / total_events) * 100, 2) if total_events else 0.0

    breach_reasons: list[str] = []
    if total_events >= int(profile.get("min_events", 20)):
        if success_rate < float(profile.get("min_success_rate", 95)):
            breach_reasons.append(f"success_rate_below_threshold:{success_rate}")
        if dead_letter_count > int(profile.get("max_dead_letter_count", 5)):
            breach_reasons.append(f"dead_letter_above_threshold:{dead_letter_count}")
        if average_latency_ms > float(profile.get("max_average_latency_ms", 5000)):
            breach_reasons.append(f"latency_above_threshold:{average_latency_ms}")

    breach_detected = len(breach_reasons) > 0
    severity = "high"
    if success_rate < max(20.0, float(profile.get("min_success_rate", 95)) - 20.0) or dead_letter_count > int(
        profile.get("max_dead_letter_count", 5)
    ) * 2:
        severity = "critical"

    metrics = {
        "total_events": total_events,
        "success_count": success_count,
        "success_rate": success_rate,
        "dead_letter_count": dead_letter_count,
        "average_latency_ms": average_latency_ms,
        "connector_source": source,
    }

    routing = {"status": "skipped"}
    breach_id = ""
    if breach_detected:
        breach = ConnectorSlaBreachEvent(
            tenant_id=tenant.id,
            site_id=rows[0].site_id if rows else None,
            connector_source=source,
            severity=severity,
            breach_reason=";".join(breach_reasons),
            metrics_json=_as_json(metrics),
            routed=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(breach)
        db.flush()
        breach_id = str(breach.id)
        if route_alert_on_breach and bool(profile.get("notify_on_breach", True)):
            routing = route_alert(
                db,
                tenant_id=tenant.id,
                site_id=rows[0].site_id if rows else None,
                source="connector_sla",
                severity=severity,
                title=f"Connector SLA breach: {source}",
                message="; ".join(breach_reasons),
                payload=metrics,
            )
            breach.routed = True
        db.commit()

    return {
        "status": "evaluated",
        "tenant_code": tenant_code,
        "profile": profile,
        "metrics": metrics,
        "breach_detected": breach_detected,
        "breach_reasons": breach_reasons,
        "breach_severity": severity if breach_detected else "",
        "breach_id": breach_id,
        "routing": routing,
    }


def list_connector_sla_breaches(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str = "",
    limit: int = 200,
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"count": 0, "rows": []}
    stmt = (
        select(ConnectorSlaBreachEvent)
        .where(ConnectorSlaBreachEvent.tenant_id == tenant.id)
        .order_by(desc(ConnectorSlaBreachEvent.created_at))
        .limit(max(1, min(limit, 2000)))
    )
    if connector_source:
        stmt = stmt.where(ConnectorSlaBreachEvent.connector_source == connector_source.strip().lower())
    rows = db.scalars(stmt).all()
    return {
        "count": len(rows),
        "rows": [
            {
                "breach_id": str(row.id),
                "tenant_id": str(row.tenant_id),
                "site_id": str(row.site_id) if row.site_id else "",
                "connector_source": row.connector_source,
                "severity": row.severity,
                "breach_reason": row.breach_reason,
                "metrics": _safe_json_load(row.metrics_json),
                "routed": bool(row.routed),
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ],
    }

