from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ActionCenterPolicyUpsertRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    policy_version: str = Field(default="1.0", min_length=1, max_length=16)
    owner: str = Field(default="security", min_length=2, max_length=64)
    telegram_enabled: bool = True
    line_enabled: bool = False
    min_severity: str = Field(default="high", pattern="^(low|medium|high|critical)$")
    routing_tags: list[str] = Field(default_factory=list)


class ActionCenterDispatchRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    site_code: str = Field(default="", max_length=64)
    source: str = Field(default="manual", min_length=2, max_length=64)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    title: str = Field(min_length=2, max_length=255)
    message: str = Field(min_length=2, max_length=4000)
    payload: dict[str, Any] = Field(default_factory=dict)

