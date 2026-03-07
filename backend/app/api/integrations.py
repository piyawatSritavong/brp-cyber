from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.integration_layer import (
    ingest_integration_event,
    list_integration_events,
    list_supported_adapters,
    verify_webhook_signature,
)
from schemas.integrations import IntegrationEventIngestRequest, IntegrationWebhookIngestRequest

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/adapters")
def integration_adapters() -> dict[str, object]:
    return list_supported_adapters()


@router.post("/events")
def ingest_event(payload: IntegrationEventIngestRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    return ingest_integration_event(
        db,
        source=payload.source,
        event_kind=payload.event_kind,
        payload=payload.payload,
        site_id=payload.site_id,
        tenant_code=payload.tenant_code,
        site_code=payload.site_code,
        webhook_event_id=payload.webhook_event_id,
    )


@router.post("/webhooks/{source}")
async def ingest_webhook(
    source: str,
    request: Request,
    body: IntegrationWebhookIngestRequest,
    db: Session = Depends(get_db),
    x_brp_signature: str = Header(default=""),
) -> dict[str, object]:
    raw_body = await request.body()
    if not verify_webhook_signature(raw_body, x_brp_signature):
        raise HTTPException(status_code=403, detail="invalid_webhook_signature")
    webhook_payload = body.payload
    if not webhook_payload:
        raw_json = await request.json()
        if isinstance(raw_json, dict):
            webhook_payload = {
                key: value
                for key, value in raw_json.items()
                if key not in {"event_kind", "site_id", "tenant_code", "site_code", "payload", "webhook_event_id"}
            }
    return ingest_integration_event(
        db,
        source=source,
        event_kind=body.event_kind,
        payload=webhook_payload,
        site_id=body.site_id,
        tenant_code=body.tenant_code,
        site_code=body.site_code,
        webhook_event_id=body.webhook_event_id,
    )


@router.get("/events")
def integration_events(
    source: str = "",
    site_id: UUID | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return list_integration_events(db, source=source, site_id=site_id, limit=limit)
