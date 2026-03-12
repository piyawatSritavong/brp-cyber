from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConnectorEventIngestRequest(BaseModel):
    connector_source: str = Field(min_length=2, max_length=64)
    event_type: str = Field(default="delivery_attempt", pattern="^(delivery_attempt|retry|dead_letter|health)$")
    status: str = Field(default="success", pattern="^(success|retrying|failed|degraded)$")
    tenant_id: UUID | None = None
    site_id: UUID | None = None
    latency_ms: int = Field(default=0, ge=0, le=600000)
    attempt: int = Field(default=1, ge=1, le=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    error_message: str = Field(default="", max_length=4000)


class ConnectorSlaProfileUpsertRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    connector_source: str = Field(default="*", min_length=1, max_length=64)
    min_events: int = Field(default=20, ge=1, le=1000000)
    min_success_rate: int = Field(default=95, ge=1, le=100)
    max_dead_letter_count: int = Field(default=5, ge=0, le=1000000)
    max_average_latency_ms: int = Field(default=5000, ge=1, le=600000)
    notify_on_breach: bool = True
    enabled: bool = True


class ConnectorSlaEvaluateRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    connector_source: str = Field(default="*", min_length=1, max_length=64)
    lookback_limit: int = Field(default=1000, ge=1, le=5000)
    route_alert: bool = True


class ConnectorCredentialUpsertRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    connector_source: str = Field(min_length=2, max_length=64)
    credential_name: str = Field(default="api_key", min_length=2, max_length=64)
    secret_value: str = Field(min_length=2, max_length=4096)
    rotation_interval_days: int = Field(default=30, ge=1, le=365)
    external_ref: str = Field(default="", max_length=255)
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor: str = Field(default="policy_editor", min_length=2, max_length=128)


class ConnectorCredentialRotateRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    connector_source: str = Field(min_length=2, max_length=64)
    credential_name: str = Field(default="api_key", min_length=2, max_length=64)
    new_secret_value: str = Field(default="", max_length=4096)
    rotation_reason: str = Field(default="scheduled_rotation", min_length=2, max_length=255)
    actor: str = Field(default="approver", min_length=2, max_length=128)


class ConnectorCredentialAutoRotateRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    connector_source: str = Field(default="", max_length=64)
    warning_days: int = Field(default=7, ge=1, le=90)
    max_rotate: int = Field(default=20, ge=1, le=200)
    dry_run: bool = True
    actor: str = Field(default="credential_guard_ai", min_length=2, max_length=128)
    route_alert: bool = True


class ConnectorCredentialHygienePolicyUpsertRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    connector_source: str = Field(default="*", min_length=1, max_length=64)
    warning_days: int = Field(default=7, ge=1, le=90)
    max_rotate_per_run: int = Field(default=20, ge=1, le=200)
    auto_apply: bool = False
    route_alert: bool = True
    schedule_interval_minutes: int = Field(default=60, ge=5, le=1440)
    enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class ConnectorCredentialHygieneRunRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    connector_source: str = Field(default="*", min_length=1, max_length=64)
    dry_run: bool | None = None
    actor: str = Field(default="credential_guard_ai", min_length=2, max_length=128)


class ConnectorReliabilityPolicyUpsertRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    connector_source: str = Field(default="*", min_length=1, max_length=64)
    max_replay_per_run: int = Field(default=25, ge=1, le=1000)
    max_attempts: int = Field(default=3, ge=1, le=20)
    auto_replay_enabled: bool = False
    route_alert: bool = True
    schedule_interval_minutes: int = Field(default=60, ge=5, le=1440)
    enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class ConnectorReliabilityReplayRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    connector_source: str = Field(default="*", min_length=1, max_length=64)
    dry_run: bool | None = None
    actor: str = Field(default="connector_replay_ai", min_length=2, max_length=128)
