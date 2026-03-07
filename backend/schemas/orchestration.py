from uuid import UUID

from pydantic import BaseModel, Field


class OrchestrationCycleRequest(BaseModel):
    tenant_id: UUID
    target_asset: str = Field(min_length=2, max_length=256)
    red_scenario_name: str = Field(default="credential_stuffing_sim", min_length=3, max_length=128)
    red_events_count: int = Field(default=30, ge=1, le=500)
    strategy_profile: str = Field(default="balanced", min_length=3, max_length=32)


class TenantStrategyRequest(BaseModel):
    tenant_id: UUID
    strategy_profile: str = Field(min_length=3, max_length=32)


class BluePolicyUpdateRequest(BaseModel):
    tenant_id: UUID
    failed_login_threshold_per_minute: int = Field(ge=1, le=1000)
    failure_window_seconds: int = Field(ge=10, le=3600)
    incident_cooldown_seconds: int = Field(ge=0, le=3600)


class OrchestrationMultiCycleRequest(BaseModel):
    tenant_id: UUID
    target_asset: str = Field(min_length=2, max_length=256)
    red_scenario_name: str = Field(default="credential_stuffing_sim", min_length=3, max_length=128)
    red_events_count: int = Field(default=30, ge=1, le=500)
    strategy_profile: str = Field(default="balanced", min_length=3, max_length=32)
    cycles: int = Field(default=3, ge=1, le=50)
    stop_on_no_improvement: bool = True


class ApprovalModeRequest(BaseModel):
    tenant_id: UUID
    enabled: bool


class ApprovalDecisionRequest(BaseModel):
    tenant_id: UUID
    action_id: str = Field(min_length=3, max_length=128)
    approve: bool


class OrchestrationActivationRequest(BaseModel):
    tenant_id: UUID
    target_asset: str = Field(min_length=2, max_length=256)
    red_scenario_name: str = Field(default="credential_stuffing_sim", min_length=3, max_length=128)
    red_events_count: int = Field(default=30, ge=1, le=500)
    strategy_profile: str = Field(default="balanced", min_length=3, max_length=32)
    cycle_interval_seconds: int = Field(default=300, ge=30, le=86400)
    approval_mode: bool = False


class PilotActivationRequest(BaseModel):
    tenant_id: UUID
    target_asset: str = Field(min_length=2, max_length=256)
    red_scenario_name: str = Field(default="credential_stuffing_sim", min_length=3, max_length=128)
    red_events_count: int = Field(default=30, ge=1, le=500)
    strategy_profile: str = Field(default="balanced", min_length=3, max_length=32)
    cycle_interval_seconds: int = Field(default=300, ge=30, le=86400)
    approval_mode: bool = False
    require_objective_gate_pass: bool = True
    force: bool = False


class OrchestrationSafetyPolicyRequest(BaseModel):
    tenant_id: UUID
    max_consecutive_failures: int = Field(default=3, ge=1, le=20)
    auto_stop_on_consecutive_failures: bool = True
    objective_gate_check_each_tick: bool = False
    auto_stop_on_objective_gate_fail: bool = False
    notify_on_auto_stop: bool = True


class OrchestrationRateBudgetRequest(BaseModel):
    tenant_id: UUID
    max_cycles_per_hour: int = Field(default=120, ge=1, le=5000)
    max_red_events_per_hour: int = Field(default=10000, ge=1, le=500000)
    enforce_rate_budget: bool = True
    auto_pause_on_budget_exceeded: bool = True
    notify_on_budget_exceeded: bool = True


class OrchestrationSchedulerProfileRequest(BaseModel):
    tenant_id: UUID
    priority_tier: str = Field(default="normal", min_length=3, max_length=16)
    starvation_incident_threshold: int = Field(default=3, ge=1, le=20)
    notify_on_starvation: bool = False


class OrchestrationRolloutProfileRequest(BaseModel):
    tenant_id: UUID
    rollout_stage: str = Field(default="ga", min_length=2, max_length=16)
    canary_percent: int = Field(default=100, ge=1, le=100)
    hold: bool = False
    notify_on_hold: bool = False
