from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class IntegrationEventIngestRequest(BaseModel):
    source: str = Field(min_length=2, max_length=64)
    event_kind: str = Field(default="security_event", min_length=2, max_length=64)
    site_id: UUID | None = None
    tenant_code: str = Field(default="", max_length=64)
    site_code: str = Field(default="", max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    webhook_event_id: str = Field(default="", max_length=255)


class IntegrationWebhookIngestRequest(BaseModel):
    event_kind: str = Field(default="security_event", min_length=2, max_length=64)
    site_id: UUID | None = None
    tenant_code: str = Field(default="", max_length=64)
    site_code: str = Field(default="", max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    webhook_event_id: str = Field(default="", max_length=255)


class EmbeddedWorkflowInvokeRequest(BaseModel):
    source: str = Field(default="generic", min_length=2, max_length=64)
    event_kind: str = Field(default="security_event", min_length=2, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool | None = None
    actor: str = Field(default="embedded_client", min_length=2, max_length=128)
    webhook_event_id: str = Field(default="", max_length=255)


class BlueLogRefinerCallbackWebhookRequest(BaseModel):
    connector_source: str = Field(default="generic", min_length=2, max_length=64)
    callback_type: str = Field(default="stream_result", pattern="^(stream_result|storage_report|delivery_receipt)$")
    source_system: str = Field(default="", max_length=64)
    external_run_ref: str = Field(default="", max_length=128)
    webhook_event_id: str = Field(default="", max_length=255)
    total_events: int = Field(default=0, ge=0, le=1_000_000)
    kept_events: int = Field(default=0, ge=0, le=1_000_000)
    dropped_events: int = Field(default=0, ge=0, le=1_000_000)
    noise_reduction_pct: int | None = Field(default=None, ge=0, le=100)
    estimated_storage_saved_kb: int = Field(default=0, ge=0, le=100_000_000)
    status: str = Field(default="ok", pattern="^(ok|warning|error|duplicate)$")
    payload: dict[str, Any] = Field(default_factory=dict)
    actor: str = Field(default="siem_callback", min_length=2, max_length=128)
    run_id: UUID | None = None


class BlueManagedResponderCallbackWebhookRequest(BaseModel):
    connector_source: str = Field(default="generic", min_length=2, max_length=64)
    contract_code: str = Field(min_length=3, max_length=128)
    callback_type: str = Field(default="result_confirmed", max_length=32)
    webhook_event_id: str = Field(default="", max_length=255)
    external_action_ref: str = Field(default="", max_length=255)
    status: str = Field(default="received", max_length=32)
    payload: dict[str, Any] = Field(default_factory=dict)
    actor: str = Field(default="vendor_callback", min_length=2, max_length=128)
