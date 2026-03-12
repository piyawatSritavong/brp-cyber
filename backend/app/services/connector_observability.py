from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import ConnectorDeliveryEvent, Site


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


def record_connector_event(
    db: Session,
    *,
    connector_source: str,
    event_type: str,
    status: str,
    tenant_id: UUID | None = None,
    site_id: UUID | None = None,
    latency_ms: int = 0,
    attempt: int = 1,
    payload: dict[str, object] | None = None,
    error_message: str = "",
) -> ConnectorDeliveryEvent:
    resolved_tenant_id = tenant_id
    if not resolved_tenant_id and site_id:
        site = db.get(Site, site_id)
        resolved_tenant_id = site.tenant_id if site else None
    row = ConnectorDeliveryEvent(
        tenant_id=resolved_tenant_id,
        site_id=site_id,
        connector_source=connector_source.strip().lower(),
        event_type=event_type,
        status=status,
        latency_ms=max(0, int(latency_ms)),
        attempt=max(1, int(attempt)),
        payload_json=_as_json(payload or {}),
        error_message=error_message[:4000],
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    return row


def ingest_connector_event(
    db: Session,
    *,
    connector_source: str,
    event_type: str,
    status: str,
    tenant_id: UUID | None = None,
    site_id: UUID | None = None,
    latency_ms: int = 0,
    attempt: int = 1,
    payload: dict[str, object] | None = None,
    error_message: str = "",
) -> dict[str, object]:
    row = record_connector_event(
        db,
        connector_source=connector_source,
        event_type=event_type,
        status=status,
        tenant_id=tenant_id,
        site_id=site_id,
        latency_ms=latency_ms,
        attempt=attempt,
        payload=payload,
        error_message=error_message,
    )
    db.commit()
    db.refresh(row)
    return {
        "status": "accepted",
        "event_id": str(row.id),
        "connector_source": row.connector_source,
        "event_type": row.event_type,
        "event_status": row.status,
    }


def list_connector_events(
    db: Session,
    *,
    connector_source: str = "",
    status: str = "",
    tenant_id: UUID | None = None,
    site_id: UUID | None = None,
    limit: int = 200,
) -> dict[str, object]:
    stmt = select(ConnectorDeliveryEvent).order_by(desc(ConnectorDeliveryEvent.created_at)).limit(max(1, min(limit, 2000)))
    if connector_source:
        stmt = stmt.where(ConnectorDeliveryEvent.connector_source == connector_source.strip().lower())
    if status:
        stmt = stmt.where(ConnectorDeliveryEvent.status == status)
    if tenant_id:
        stmt = stmt.where(ConnectorDeliveryEvent.tenant_id == tenant_id)
    if site_id:
        stmt = stmt.where(ConnectorDeliveryEvent.site_id == site_id)

    rows = db.scalars(stmt).all()
    return {
        "count": len(rows),
        "rows": [
            {
                "event_id": str(row.id),
                "site_id": str(row.site_id) if row.site_id else "",
                "tenant_id": str(row.tenant_id) if row.tenant_id else "",
                "connector_source": row.connector_source,
                "event_type": row.event_type,
                "status": row.status,
                "latency_ms": row.latency_ms,
                "attempt": row.attempt,
                "payload": _safe_json_load(row.payload_json),
                "error_message": row.error_message,
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ],
    }


def connector_health_snapshot(db: Session, *, limit: int = 2000) -> dict[str, object]:
    rows = db.scalars(
        select(ConnectorDeliveryEvent)
        .order_by(desc(ConnectorDeliveryEvent.created_at))
        .limit(max(1, min(limit, 5000)))
    ).all()

    if not rows:
        return {
            "total_events": 0,
            "success_count": 0,
            "retry_count": 0,
            "dead_letter_count": 0,
            "failed_count": 0,
            "success_rate": 0.0,
            "average_latency_ms": 0.0,
            "sources": [],
        }

    success_count = len([row for row in rows if row.status == "success"])
    retry_count = len([row for row in rows if row.event_type == "retry" or row.status == "retrying"])
    dead_letter_count = len([row for row in rows if row.event_type == "dead_letter"])
    failed_count = len([row for row in rows if row.status == "failed"])
    success_rate = round(success_count / len(rows), 4)
    average_latency_ms = round(sum(row.latency_ms for row in rows) / len(rows), 2)

    source_stats: dict[str, dict[str, float]] = defaultdict(lambda: {"events": 0.0, "success": 0.0, "dead_letter": 0.0})
    for row in rows:
        bucket = source_stats[row.connector_source]
        bucket["events"] += 1
        if row.status == "success":
            bucket["success"] += 1
        if row.event_type == "dead_letter":
            bucket["dead_letter"] += 1

    sources = []
    for source, stats in source_stats.items():
        events = int(stats["events"])
        success = int(stats["success"])
        dead = int(stats["dead_letter"])
        sources.append(
            {
                "source": source,
                "events": events,
                "success_rate": round((success / events), 4) if events else 0.0,
                "dead_letter_count": dead,
            }
        )
    sources.sort(key=lambda item: item["events"], reverse=True)

    return {
        "total_events": len(rows),
        "success_count": success_count,
        "retry_count": retry_count,
        "dead_letter_count": dead_letter_count,
        "failed_count": failed_count,
        "success_rate": success_rate,
        "average_latency_ms": average_latency_ms,
        "sources": sources[:20],
    }
