from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SoarPlaybookUpsertRequest(BaseModel):
    playbook_code: str = Field(min_length=3, max_length=80)
    title: str = Field(min_length=3, max_length=255)
    category: str = Field(default="response", min_length=3, max_length=64)
    description: str = Field(default="", max_length=5000)
    version: str = Field(default="1.0.0", min_length=1, max_length=32)
    scope: str = Field(default="community", pattern="^(community|partner|private)$")
    steps: list[str] = Field(default_factory=list)
    action_policy: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class SoarPlaybookExecuteRequest(BaseModel):
    actor: str = Field(default="ai_agent", min_length=2, max_length=128)
    require_approval: bool = True
    dry_run: bool = True
    params: dict[str, Any] = Field(default_factory=dict)


class SoarPlaybookApprovalRequest(BaseModel):
    approve: bool = True
    approver: str = Field(default="security_lead", min_length=2, max_length=128)
    note: str = Field(default="", max_length=2000)


class SoarMarketplacePackInstallRequest(BaseModel):
    actor: str = Field(default="marketplace_installer", min_length=2, max_length=128)
    scope_override: str = Field(default="", pattern="^(|community|partner|private)$")


class SoarPlaybookVerificationRequest(BaseModel):
    actor: str = Field(default="soar_verifier", min_length=2, max_length=128)


class SoarConnectorResultCallbackRequest(BaseModel):
    connector_source: str = Field(default="generic", min_length=2, max_length=64)
    contract_code: str = Field(min_length=3, max_length=128)
    external_action_ref: str = Field(default="", max_length=255)
    webhook_event_id: str = Field(default="", max_length=255)
    status: str = Field(default="received", max_length=32)
    payload: dict[str, Any] = Field(default_factory=dict)
    actor: str = Field(default="connector_callback", min_length=2, max_length=128)


class TenantPlaybookPolicyUpsertRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    policy_version: str = Field(default="1.0", min_length=1, max_length=16)
    owner: str = Field(default="security", min_length=2, max_length=64)
    require_approval_by_scope: dict[str, bool] = Field(default_factory=dict)
    require_approval_by_category: dict[str, bool] = Field(default_factory=dict)
    delegated_approvers: list[str] = Field(default_factory=list)
    blocked_playbook_codes: list[str] = Field(default_factory=list)
    allow_partner_scope: bool = True
    auto_approve_dry_run: bool = True
