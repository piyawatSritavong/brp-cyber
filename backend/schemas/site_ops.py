from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class SiteUpsertRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    site_code: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=2, max_length=255)
    base_url: HttpUrl
    is_active: bool = True
    config: dict[str, object] = Field(default_factory=dict)


class RedSiteScanRequest(BaseModel):
    scan_type: str = Field(default="baseline_scan", min_length=3, max_length=64)
    include_paths: list[str] = Field(default_factory=lambda: ["/", "/login", "/admin", "/wp-login.php", "/api/health"])


class BlueSiteEventIngestRequest(BaseModel):
    event_type: str = Field(default="http_event", min_length=3, max_length=64)
    source_ip: str = Field(default="unknown", min_length=2, max_length=64)
    path: str = Field(default="/", min_length=1, max_length=1024)
    method: str = Field(default="GET", min_length=3, max_length=16)
    status_code: int = Field(default=200, ge=100, le=599)
    message: str = Field(default="", max_length=4000)
    payload: dict[str, object] = Field(default_factory=dict)


class BlueRecommendationActionRequest(BaseModel):
    action: str = Field(default="notify_team", pattern="^(block_ip|notify_team|limit_user|ignore)$")

