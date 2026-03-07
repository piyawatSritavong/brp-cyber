from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventMetadata(BaseModel):
    tenant_id: UUID
    correlation_id: UUID = Field(default_factory=uuid4)
    trace_id: UUID = Field(default_factory=uuid4)
    source: str = Field(min_length=2, max_length=128)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RedEvent(BaseModel):
    event_type: Literal["red_event"] = "red_event"
    metadata: EventMetadata
    scenario_name: str
    target_asset: str
    tactic: str
    outcome: Literal["started", "partial", "stopped", "completed"]
    safety_boundary_ok: bool = True


class DetectionEvent(BaseModel):
    event_type: Literal["detection_event"] = "detection_event"
    metadata: EventMetadata
    detector: str
    severity: Literal["low", "medium", "high", "critical"]
    signal_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["new", "triaged", "false_positive", "confirmed"]


class ResponseEvent(BaseModel):
    event_type: Literal["response_event"] = "response_event"
    metadata: EventMetadata
    action: str
    reason_code: str
    actor: str
    target: str
    result: Literal["success", "failed", "skipped"]


class PurpleReportEvent(BaseModel):
    event_type: Literal["purple_report_event"] = "purple_report_event"
    metadata: EventMetadata
    report_id: str
    summary: str
    mttd_seconds: float = Field(ge=0)
    mttr_seconds: float = Field(ge=0)
    recommendation_count: int = Field(ge=0)


AnySecurityEvent = RedEvent | DetectionEvent | ResponseEvent | PurpleReportEvent
