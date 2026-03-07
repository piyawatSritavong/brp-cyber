from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field


class RedSimulationRunRequest(BaseModel):
    tenant_id: UUID
    scenario_name: str = Field(min_length=3, max_length=128)
    target_asset: str = Field(min_length=2, max_length=256)
    events_count: int = Field(default=20, ge=1, le=500)
    source_ips: list[str] | None = None
    usernames: list[str] | None = None


class RedSimulationScheduleRequest(BaseModel):
    tenant_id: UUID
    scenario_name: str = Field(min_length=3, max_length=128)
    target_asset: str = Field(min_length=2, max_length=256)
    events_count: int = Field(default=20, ge=1, le=500)
    run_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_ips: list[str] | None = None
    usernames: list[str] | None = None
