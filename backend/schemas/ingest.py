from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AuthLoginEvent(BaseModel):
    tenant_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_ip: str = Field(min_length=7, max_length=64)
    source_asn: int | None = Field(default=None, ge=1)
    username: str = Field(min_length=1, max_length=255)
    success: bool
    auth_source: str = Field(default="system_auth", min_length=2, max_length=64)


class WafHttpEvent(BaseModel):
    tenant_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_ip: str = Field(min_length=7, max_length=64)
    source_asn: int | None = Field(default=None, ge=1)
    path: str = Field(min_length=1, max_length=1024)
    method: str = Field(min_length=3, max_length=16)
    status_code: int = Field(ge=100, le=599)
    waf_action: Literal["allow", "block", "challenge", "log_only"] = "log_only"
    username: str = Field(default="unknown", min_length=1, max_length=255)
    provider: str = Field(default="waf", min_length=2, max_length=64)


class SystemAuthEvent(BaseModel):
    tenant_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_ip: str = Field(min_length=7, max_length=64)
    source_asn: int | None = Field(default=None, ge=1)
    username: str = Field(min_length=1, max_length=255)
    event_type: Literal["login_success", "login_failure"]
    auth_source: str = Field(default="system_auth", min_length=2, max_length=64)
