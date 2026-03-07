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

