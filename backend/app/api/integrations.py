from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Site
from app.db.session import get_db
from app.services.blue_log_refiner import ingest_blue_log_refiner_callback
from app.services.integration_layer import (
    ingest_integration_event,
    list_integration_events,
    list_supported_adapters,
    verify_webhook_signature,
)
from app.services.soar_playbook_hub import ingest_playbook_connector_result
from app.services.embedded_workflows import invoke_site_embedded_workflow
from app.services.integration_adapter_templates import list_adapter_invoke_templates
from schemas.integrations import (
    BlueLogRefinerCallbackWebhookRequest,
    EmbeddedWorkflowInvokeRequest,
    IntegrationEventIngestRequest,
    IntegrationWebhookIngestRequest,
)
from schemas.soar import SoarConnectorResultCallbackRequest

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _embedded_guardrail_status(reason: str) -> int:
    mapping = {
        "actor_not_allowed": 403,
        "rate_limit_exceeded": 429,
        "replay_detected": 409,
        "missing_webhook_event_id": 400,
        "payload_key_limit_exceeded": 422,
        "payload_size_limit_exceeded": 422,
        "playbook_code_required": 422,
        "playbook_not_allowed": 403,
        "playbook_blocked_by_endpoint_policy": 403,
        "required_payload_fields_missing": 422,
    }
    return mapping.get(reason, 409)


def _lookup_site_by_code(db: Session, site_code: str) -> Site | None:
    return db.scalar(select(Site).where(Site.site_code == site_code))


@router.get("/adapters")
def integration_adapters() -> dict[str, object]:
    return list_supported_adapters()


@router.get("/adapters/templates")
def integration_adapter_templates(source: str = "") -> dict[str, object]:
    return list_adapter_invoke_templates(source=source)


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


@router.post("/embedded/sites/{site_code}/{endpoint_code}/invoke")
def invoke_embedded_workflow(
    site_code: str,
    endpoint_code: str,
    payload: EmbeddedWorkflowInvokeRequest,
    db: Session = Depends(get_db),
    x_brp_embed_token: str = Header(default=""),
) -> dict[str, Any]:
    result = invoke_site_embedded_workflow(
        db,
        site_code=site_code,
        endpoint_code=endpoint_code,
        token=x_brp_embed_token,
        source=payload.source,
        event_kind=payload.event_kind,
        payload=payload.payload,
        config=payload.config,
        dry_run=payload.dry_run,
        actor=payload.actor,
        webhook_event_id=payload.webhook_event_id,
    )
    if result.get("status") in {"forbidden"}:
        raise HTTPException(status_code=403, detail=result.get("reason", "forbidden"))
    if result.get("status") in {"site_not_found", "endpoint_not_found"}:
        raise HTTPException(status_code=404, detail=result.get("status"))
    if result.get("status") == "endpoint_disabled":
        raise HTTPException(status_code=409, detail="endpoint_disabled")
    if result.get("status") == "playbook_not_found":
        raise HTTPException(status_code=404, detail="playbook_not_found")
    if result.get("status") == "blocked_by_policy":
        raise HTTPException(status_code=403, detail=result.get("reason", "blocked_by_policy"))
    if result.get("status") == "guardrail_blocked":
        reason = str(result.get("reason", "guardrail_blocked"))
        raise HTTPException(status_code=_embedded_guardrail_status(reason), detail=reason)
    return result


@router.post("/blue/log-refiner/sites/{site_code}/callback")
async def ingest_blue_log_refiner_source_callback(
    site_code: str,
    request: Request,
    payload: BlueLogRefinerCallbackWebhookRequest,
    db: Session = Depends(get_db),
    x_brp_signature: str = Header(default=""),
) -> dict[str, Any]:
    raw_body = await request.body()
    if not verify_webhook_signature(raw_body, x_brp_signature):
        raise HTTPException(status_code=403, detail="invalid_webhook_signature")
    result = ingest_blue_log_refiner_callback(
        db,
        site_code=site_code,
        connector_source=payload.connector_source,
        callback_type=payload.callback_type,
        source_system=payload.source_system,
        external_run_ref=payload.external_run_ref,
        webhook_event_id=payload.webhook_event_id,
        run_id=payload.run_id,
        total_events=payload.total_events,
        kept_events=payload.kept_events,
        dropped_events=payload.dropped_events,
        noise_reduction_pct=payload.noise_reduction_pct,
        estimated_storage_saved_kb=payload.estimated_storage_saved_kb,
        status=payload.status,
        payload=payload.payload,
        actor=payload.actor,
    )
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="site_not_found")
    return result


@router.post("/soar/sites/{site_code}/executions/{execution_id}/callback")
async def ingest_soar_connector_callback(
    site_code: str,
    execution_id: UUID,
    request: Request,
    payload: SoarConnectorResultCallbackRequest,
    db: Session = Depends(get_db),
    x_brp_signature: str = Header(default=""),
) -> dict[str, Any]:
    raw_body = await request.body()
    if not verify_webhook_signature(raw_body, x_brp_signature):
        raise HTTPException(status_code=403, detail="invalid_webhook_signature")
    site = _lookup_site_by_code(db, site_code)
    if site is None:
        raise HTTPException(status_code=404, detail="site_not_found")
    result = ingest_playbook_connector_result(
        db,
        execution_id=execution_id,
        site_id=site.id,
        connector_source=payload.connector_source,
        contract_code=payload.contract_code,
        external_action_ref=payload.external_action_ref,
        webhook_event_id=payload.webhook_event_id,
        status=payload.status,
        payload=payload.payload,
        actor=payload.actor,
    )
    if result.get("status") in {"execution_not_found"}:
        raise HTTPException(status_code=404, detail="execution_not_found")
    if result.get("status") in {"site_mismatch"}:
        raise HTTPException(status_code=409, detail="site_mismatch")
    if result.get("status") in {"contract_not_found"}:
        raise HTTPException(status_code=404, detail="contract_not_found")
    return result
