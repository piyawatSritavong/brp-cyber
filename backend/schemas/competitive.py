from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ThreatContentPackUpsertRequest(BaseModel):
    pack_code: str = Field(min_length=3, max_length=80)
    title: str = Field(min_length=3, max_length=255)
    category: str = Field(default="generic", min_length=3, max_length=64)
    mitre_techniques: list[str] = Field(default_factory=list)
    attack_steps: list[str] = Field(default_factory=list)
    validation_mode: str = Field(default="simulation_safe", min_length=3, max_length=32)
    is_active: bool = True


class ThreatContentPipelinePolicyUpsertRequest(BaseModel):
    scope: str = Field(default="global", min_length=3, max_length=64)
    min_refresh_interval_minutes: int = Field(default=1440, ge=5, le=10080)
    preferred_categories: list[str] = Field(default_factory=lambda: ["identity", "ransomware", "phishing", "web"])
    max_packs_per_run: int = Field(default=8, ge=1, le=50)
    auto_activate: bool = True
    route_alert: bool = False
    enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class ThreatContentPipelineRunRequest(BaseModel):
    scope: str = Field(default="global", min_length=3, max_length=64)
    dry_run: bool | None = None
    force: bool = False
    actor: str = Field(default="threat_content_pipeline_ai", min_length=2, max_length=128)


class ExploitPathSimulationRequest(BaseModel):
    threat_pack_code: str = Field(default="", max_length=80)
    target_surface: str = Field(default="/admin-login", max_length=1024)
    simulation_depth: int = Field(default=3, ge=1, le=5)
    max_requests_per_minute: int = Field(default=30, ge=1, le=500)
    stop_on_critical: bool = True
    simulation_only: bool = True


class RedExploitAutopilotPolicyUpsertRequest(BaseModel):
    min_risk_score: int = Field(default=50, ge=1, le=100)
    min_risk_tier: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    preferred_pack_category: str = Field(default="identity", min_length=3, max_length=64)
    target_surface: str = Field(default="/admin-login", min_length=1, max_length=1024)
    simulation_depth: int = Field(default=3, ge=1, le=5)
    max_requests_per_minute: int = Field(default=30, ge=1, le=500)
    stop_on_critical: bool = True
    simulation_only: bool = True
    auto_run: bool = False
    route_alert: bool = True
    schedule_interval_minutes: int = Field(default=120, ge=5, le=1440)
    enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class RedExploitAutopilotRunRequest(BaseModel):
    dry_run: bool | None = None
    force: bool = False
    actor: str = Field(default="red_exploit_autopilot_ai", min_length=2, max_length=128)


class DetectionCopilotTuneRequest(BaseModel):
    exploit_path_run_id: UUID | None = None
    rule_count: int = Field(default=3, ge=1, le=10)
    auto_apply: bool = False
    dry_run: bool = True


class DetectionRuleApplyRequest(BaseModel):
    apply: bool = True


class DetectionAutotunePolicyUpsertRequest(BaseModel):
    min_risk_score: int = Field(default=60, ge=1, le=100)
    min_risk_tier: str = Field(default="high", pattern="^(low|medium|high|critical)$")
    target_detection_coverage_pct: int = Field(default=90, ge=1, le=100)
    max_rules_per_run: int = Field(default=3, ge=1, le=10)
    auto_apply: bool = False
    route_alert: bool = True
    schedule_interval_minutes: int = Field(default=60, ge=5, le=1440)
    enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class DetectionAutotuneRunRequest(BaseModel):
    dry_run: bool | None = None
    force: bool = False
    actor: str = Field(default="blue_autotune_ai", min_length=2, max_length=128)


class PhaseObjectiveCheckRequest(BaseModel):
    phase_code: str = Field(min_length=3, max_length=32)
    phase_title: str = Field(default="", max_length=255)
    objective_ids: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    site_id: UUID | None = None
    context: dict[str, Any] = Field(default_factory=dict)
