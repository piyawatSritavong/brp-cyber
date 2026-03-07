from pydantic import BaseModel, Field


class TenantOnboardRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    display_name: str = Field(min_length=2, max_length=255)
    strategy_profile: str = Field(default="balanced", min_length=3, max_length=32)


class TenantQuotaBootstrap(BaseModel):
    events_per_month: int = Field(default=1_000_000, ge=1)
    actions_per_day: int = Field(default=20_000, ge=1)
    tokens_per_month: int = Field(default=20_000_000, ge=1)


class TenantStatusUpdateRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    status: str = Field(pattern="^(active|suspended|staging|production)$")
    bypass_objective_gate: bool = Field(default=False)
    change_ticket: str | None = Field(default=None, min_length=3, max_length=128)


class TenantApiKeyRotateRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    reason: str | None = Field(default=None, min_length=3, max_length=512)
    change_ticket: str | None = Field(default=None, min_length=3, max_length=128)


class AdminTokenIssueRequest(BaseModel):
    scopes: list[str] = Field(default_factory=lambda: ["*"])
    ttl_seconds: int | None = Field(default=None, ge=60, le=86400)
    tenant_scope: str | None = Field(default=None, min_length=2, max_length=64)


class SiemAckRequest(BaseModel):
    failed_batch_id: str = Field(min_length=3, max_length=64)
    ack_ref: str = Field(min_length=3, max_length=256)


class AssuranceContractUpsertRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    contract_version: str = Field(default="1.0", min_length=1, max_length=16)
    owner: str = Field(default="security", min_length=2, max_length=64)
    min_samples: int = Field(default=20, ge=1, le=100000)
    min_overall_pass_rate: float = Field(default=0.95, ge=0.0, le=1.0)
    min_gate_pass_rate: float = Field(default=0.95, ge=0.0, le=1.0)
    max_enterprise_monthly_cost_usd: float = Field(default=50.0, ge=0.0, le=1000000.0)
    required_gates: list[str] = Field(
        default_factory=lambda: ["red", "blue", "purple", "closed_loop", "enterprise", "compliance"]
    )
    required_frameworks: list[str] = Field(default_factory=list)
    min_framework_readiness_score: float = Field(default=90.0, ge=0.0, le=100.0)


class AssurancePolicyPackUpsertRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    pack_version: str = Field(default="1.0", min_length=1, max_length=16)
    owner: str = Field(default="security", min_length=2, max_length=64)
    auto_apply_actions: list[str] = Field(default_factory=list)
    force_approval_actions: list[str] = Field(default_factory=list)
    blocked_actions: list[str] = Field(default_factory=list)
    max_auto_apply_actions_per_run: int = Field(default=1, ge=0, le=100)
    notify_only: bool = False
    rollback_on_worse_result: bool = True
    min_effectiveness_delta: float = Field(default=0.0, ge=-1.0, le=1.0)


class AssuranceRemediationApprovalRequest(BaseModel):
    action_id: str = Field(min_length=3, max_length=128)
    approve: bool


class AssuranceSloProfileUpsertRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    profile_version: str = Field(default="1.0", min_length=1, max_length=16)
    owner: str = Field(default="security", min_length=2, max_length=64)
    max_breaches_per_day: int = Field(default=5, ge=1, le=100000)
    min_contract_pass_rate: float = Field(default=0.95, ge=0.0, le=1.0)
    min_effectiveness_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    max_rollback_batches: int = Field(default=0, ge=0, le=100000)
    min_availability: float = Field(default=0.995, ge=0.0, le=1.0)
    max_error_rate: float = Field(default=0.01, ge=0.0, le=1.0)


class AssuranceBulletinDistributionUpsertRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    policy_version: str = Field(default="1.0", min_length=1, max_length=16)
    owner: str = Field(default="security", min_length=2, max_length=64)
    enabled: bool = True
    signed_only: bool = True
    webhook_url: str = Field(default="", max_length=2048)
    auth_header: str = Field(default="", max_length=2048)
    timeout_seconds: float = Field(default=5.0, ge=0.1, le=60.0)
    retry_attempts: int = Field(default=3, ge=1, le=10)
    retry_backoff_seconds: float = Field(default=0.5, ge=0.1, le=30.0)


class ProdV1GoLiveRunbookUpsertRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    version: str = Field(default="1.0", min_length=1, max_length=16)
    owner: str = Field(default="ops", min_length=2, max_length=64)
    change_ticket: str = Field(default="", max_length=128)
    notes: str = Field(default="", max_length=2000)
    items: dict[str, bool] = Field(default_factory=dict)


class ProdV1GoLiveClosureRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    approved_by: str = Field(min_length=2, max_length=128)
    change_ticket: str = Field(min_length=3, max_length=128)
    dry_run: bool = True
    promote_on_pass: bool = True
    max_monthly_cost_usd: float = Field(default=50.0, ge=0.0, le=1000000.0)


class ProdV1BurnRateProfileUpsertRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    version: str = Field(default="1.0", min_length=1, max_length=16)
    owner: str = Field(default="sre", min_length=2, max_length=64)
    error_budget_fraction_per_day: float = Field(default=0.01, ge=0.0001, le=1.0)
    burn_rate_warn_threshold: float = Field(default=1.0, ge=0.1, le=1000.0)
    burn_rate_rollback_threshold: float = Field(default=2.0, ge=0.1, le=1000.0)
    min_requests_for_enforcement: int = Field(default=100, ge=1, le=100000000)
    auto_rollback_on_breach: bool = True
    rollback_target_status: str = Field(default="staging", pattern="^(staging|suspended)$")
    cooldown_minutes: int = Field(default=30, ge=1, le=1440)
    notify_on_rollback: bool = True
