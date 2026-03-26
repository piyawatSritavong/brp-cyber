from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Tenant
from app.db.session import get_db
from app.services.admin_auth import (
    auth_posture,
    issue_admin_token,
    revoke_admin_token,
    rotate_admin_token,
    token_allows_tenant,
    token_has_scope,
    verify_admin_token,
)
from app.services.audit import list_control_plane_audit, write_control_plane_audit
from app.services.audit_archive import archive_status as get_archive_status
from app.services.audit_archive import verify_archive_chain
from app.services.audit_export import export_control_plane_audit_to_siem, get_export_status
from app.services.audit_immutable_store import export_store_snapshot, immutable_store_status
from app.services.audit_offload import offload_archive_batches, offload_status
from app.services.audit_recovery import (
    acknowledge_failed_batch,
    list_failed_batches,
    reconcile_failed_batches,
    recovery_status,
    replay_failed_batches,
)
from app.services.control_plane import (
    onboard_tenant,
    rotate_tenant_api_key,
    tenant_detail_by_id,
    update_tenant_status,
)
from app.services.control_plane_audit_pack import (
    audit_pack_status,
    generate_external_audit_pack,
    verify_external_audit_pack,
)
from app.services.control_plane_audit_pack_attestation import (
    audit_pack_manifest_attestation_status,
    verify_audit_pack_manifest_attestation_chain,
)
from app.services.control_plane_audit_pack_publication import publication_status, publish_latest_audit_pack
from app.services.control_plane_legal_evidence import export_legal_evidence_profile
from app.services.control_plane_assurance_contracts import (
    evaluate_assurance_contract,
    get_assurance_contract,
    upsert_assurance_contract,
)
from app.services.control_plane_assurance_policy_packs import (
    get_assurance_policy_pack,
    upsert_assurance_policy_pack,
)
from app.services.control_plane_assurance_remediation import (
    approve_assurance_remediation_action,
    assurance_remediation_effectiveness,
    assurance_remediation_status,
    remediate_assurance_breach,
)
from app.services.control_plane_assurance_risk import (
    apply_assurance_risk_recommendations,
    assurance_risk_heatmap,
    assurance_risk_recommendations,
)
from app.services.control_plane_rollout_handoff_federation import (
    apply_rollout_handoff_escalation_matrix,
    evaluate_rollout_handoff_federation_slo,
    get_rollout_handoff_federation_slo_profile,
    rollout_handoff_federation_executive_digest,
    rollout_handoff_escalation_matrix,
    rollout_handoff_federation_heatmap,
    rollout_handoff_federation_slo_breach_history,
    upsert_rollout_handoff_federation_slo_profile,
)
from app.services.control_plane_rollout_handoff_federation_signing import (
    create_signed_rollout_handoff_federation_digest,
    signed_rollout_handoff_federation_digest_status,
    verify_signed_rollout_handoff_federation_digest_chain,
)
from app.services.control_plane_rollout_handoff_policy_drift import (
    apply_rollout_handoff_policy_drift_reconciliation,
    evaluate_rollout_handoff_policy_drift,
    get_rollout_handoff_policy_drift_baseline,
    rollout_handoff_policy_drift_heatmap,
    rollout_handoff_policy_drift_history,
    upsert_rollout_handoff_policy_drift_baseline,
)
from app.services.control_plane_rollout_handoff_policy_drift_signing import (
    create_signed_rollout_handoff_policy_drift_report,
    signed_rollout_handoff_policy_drift_report_status,
    verify_signed_rollout_handoff_policy_drift_report_chain,
)
from app.services.control_plane_orchestration_failover import (
    evaluate_orchestration_failover_health,
    get_orchestration_failover_profile,
    get_orchestration_failover_state,
    orchestration_failover_enterprise_snapshot,
    orchestration_failover_events,
    trigger_orchestration_failover_drill,
    upsert_orchestration_failover_profile,
)
from app.services.control_plane_orchestration_failover_signing import (
    create_signed_orchestration_failover_report,
    signed_orchestration_failover_report_status,
    verify_signed_orchestration_failover_report_chain,
)
from app.services.control_plane_orchestration_cost_guardrail import (
    evaluate_orchestration_cost_guardrail,
    get_orchestration_cost_anomaly_state,
    get_orchestration_cost_guardrail_profile,
    get_orchestration_cost_routing_override,
    get_orchestration_cost_throttle_override,
    orchestration_cost_guardrail_enterprise_snapshot,
    orchestration_cost_guardrail_events,
    upsert_orchestration_cost_guardrail_profile,
)
from app.services.control_plane_orchestration_cost_federation import (
    apply_orchestration_cost_policy_tightening_matrix,
    orchestration_cost_anomaly_federation_heatmap,
    orchestration_cost_policy_tightening_matrix,
)
from app.services.control_plane_orchestration_cost_guardrail_signing import (
    create_signed_orchestration_cost_guardrail_report,
    signed_orchestration_cost_guardrail_report_status,
    verify_signed_orchestration_cost_guardrail_report_chain,
)
from app.services.control_plane_production_readiness import (
    close_prod_v1_go_live,
    evaluate_prod_v1_readiness_final,
    evaluate_prod_v1_burn_rate_guard,
    get_prod_v1_go_live_runbook,
    get_prod_v1_burn_rate_profile,
    prod_v1_burn_rate_guard_history,
    prod_v1_go_live_closure_history,
    upsert_prod_v1_burn_rate_profile,
    upsert_prod_v1_go_live_runbook,
)
from app.services.control_plane_production_rollout_playbook import production_rollout_integration_playbook
from app.services.control_plane_assurance_slo import (
    assurance_executive_risk_digest,
    assurance_slo_breach_history,
    evaluate_assurance_slo,
    get_assurance_slo_profile,
    upsert_assurance_slo_profile,
)
from app.services.control_plane_assurance_digest_signing import (
    create_signed_assurance_executive_digest,
    create_signed_tenant_risk_bulletin,
    signed_assurance_executive_digest_status,
    signed_tenant_risk_bulletin_status,
    verify_signed_assurance_executive_digest_chain,
    verify_signed_tenant_risk_bulletin_chain,
)
from app.services.control_plane_assurance_bulletin_delivery import (
    bulletin_delivery_receipts,
    deliver_signed_tenant_bulletin,
    get_bulletin_distribution_policy,
    upsert_bulletin_distribution_policy,
)
from app.services.control_plane_assurance_delivery_proof import (
    export_signed_delivery_proof_bundle,
    signed_delivery_proof_status,
    verify_signed_delivery_proof_chain,
)
from app.services.control_plane_assurance_proof_index import (
    assurance_delivery_proof_index,
    export_assurance_delivery_proof_index,
)
from app.services.control_plane_compliance_package_index import (
    export_tenant_compliance_package_index,
    tenant_compliance_package_index_status,
)
from app.services.control_plane_assurance_evidence_package_signing import (
    create_signed_tenant_evidence_package,
    signed_tenant_evidence_package_status,
    verify_signed_tenant_evidence_package_chain,
)
from app.services.control_plane_external_verifier_attestation import (
    compute_zero_trust_attestation,
    external_verifier_status,
    get_external_verifier_policy,
    import_external_verifier_bundle,
    upsert_external_verifier_policy,
    verifier_receipt_status,
    verify_verifier_receipt_chain,
    zero_trust_attestation_status,
    zero_trust_overview,
)
from app.services.control_plane_verifier_registry import issue_verifier_token, revoke_verifier_token
from app.services.pilot_operator_auth import issue_pilot_operator_token, revoke_pilot_operator_token
from app.services.rollout_handoff_auth import (
    get_rollout_handoff_policy,
    issue_rollout_handoff_token,
    revoke_rollout_handoff_token,
    rollout_handoff_anomalies,
    rollout_handoff_containment_events,
    rollout_handoff_governance_snapshot,
    rollout_handoff_risk_snapshot,
    rollout_handoff_receipts,
    rollout_handoff_trust_events,
    upsert_rollout_handoff_policy,
)
from app.services.orchestrator_pilot_onboarding import (
    get_pilot_onboarding_profile,
    pilot_onboarding_checklist,
    upsert_pilot_onboarding_profile,
)
from app.services.orchestrator import (
    approve_pending_rollout_decision,
    evaluate_tenant_rollout_posture,
    export_rollout_evidence_bundle,
    get_tenant_rate_budget,
    get_tenant_rate_budget_usage,
    get_tenant_rollout_profile,
    get_tenant_rollout_policy,
    get_tenant_scheduler_profile,
    get_tenant_safety_policy,
    get_rollout_guard_state,
    list_pending_rollout_decisions,
    rollout_decision_history,
    rollout_evidence_history,
    rollout_evidence_bundle_status,
    verify_rollout_evidence_chain,
    upsert_tenant_rate_budget,
    upsert_tenant_rollout_profile,
    upsert_tenant_rollout_policy,
    upsert_tenant_scheduler_profile,
    upsert_tenant_safety_policy,
)
from app.services.control_plane_verifier_kit import (
    export_tenant_verifier_kit,
    tenant_verifier_kit_status,
)
from app.services.control_plane_public_assurance_signing import (
    create_signed_public_assurance_snapshot,
    signed_public_assurance_status,
    verify_signed_public_assurance_chain,
)
from app.services.control_plane_compliance import build_control_plane_compliance_evidence
from app.services.control_plane_governance import governance_dashboard
from app.services.control_plane_governance_attestation import (
    create_governance_attestation,
    export_latest_governance_attestation,
    governance_attestation_status,
    verify_governance_attestation_chain,
)
from app.services.control_plane_policy import evaluate_policy, policy_config
from app.services.control_plane_transparency import publish_transparency_entry, transparency_status
from app.services.s3_object_lock_validator import validate_s3_object_lock
from schemas.control_plane import (
    AssuranceBulletinDistributionUpsertRequest,
    AssurancePolicyPackUpsertRequest,
    AssuranceRemediationApprovalRequest,
    AssuranceSloProfileUpsertRequest,
    AssuranceContractUpsertRequest,
    AdminTokenIssueRequest,
    ProdV1BurnRateProfileUpsertRequest,
    ProdV1GoLiveClosureRequest,
    ProdV1GoLiveRunbookUpsertRequest,
    SiemAckRequest,
    TenantApiKeyRotateRequest,
    TenantOnboardRequest,
    TenantQuotaBootstrap,
    TenantStatusUpdateRequest,
)

router = APIRouter(prefix="/control-plane", tags=["control-plane"])

bearer = HTTPBearer(auto_error=False)


def require_control_plane_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, object]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=403, detail="forbidden")

    result = verify_admin_token(credentials.credentials)
    if not result.get("valid"):
        raise HTTPException(status_code=403, detail=f"forbidden:{result.get('reason', 'invalid')}")
    return result


def require_scope(scope: str) -> Callable[[dict[str, object]], dict[str, object]]:
    def _dep(admin: dict[str, object] = Depends(require_control_plane_admin)) -> dict[str, object]:
        if not token_has_scope(admin, scope):
            raise HTTPException(status_code=403, detail="forbidden:insufficient_scope")
        return admin

    return _dep


def _enforce_policy_or_raise(
    *,
    admin: dict[str, object],
    action: str,
    target: str,
    context: dict[str, object],
) -> dict[str, object]:
    decision = evaluate_policy(action=action, admin=admin, context=context)
    if not decision.get("has_violations"):
        return decision

    details = {
        "mode": decision.get("mode"),
        "severity": decision.get("severity"),
        "violations": decision.get("violations"),
        "context": context,
    }

    if not decision.get("allowed"):
        write_control_plane_audit(
            actor=str(admin.get("actor", "admin")),
            action=f"policy:{action}",
            status="denied",
            target=target,
            details=details,
        )
        raise HTTPException(status_code=403, detail="policy_denied")

    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action=f"policy:{action}",
        status="warning",
        target=target,
        details=details,
    )
    return decision


@router.post("/auth/token")
def issue_token(
    payload: AdminTokenIssueRequest = Body(default_factory=AdminTokenIssueRequest),
    x_bootstrap_token: str = Header(default=""),
) -> dict[str, object]:
    posture = auth_posture()
    if not posture["local_bootstrap_available"]:
        raise HTTPException(status_code=400, detail=f"local_token_issue_disabled:{posture['reason']}")
    if not settings.control_plane_bootstrap_token:
        raise HTTPException(status_code=503, detail="control_plane_bootstrap_token_not_configured")
    if x_bootstrap_token != settings.control_plane_bootstrap_token:
        raise HTTPException(status_code=403, detail="forbidden")

    issued = issue_admin_token(
        actor="bootstrap",
        scopes=payload.scopes,
        ttl_seconds=payload.ttl_seconds,
        tenant_scope=payload.tenant_scope,
    )
    write_control_plane_audit(
        actor="bootstrap",
        action="issue_admin_token",
        status="success",
        target=issued["token_id"],
        details={
            "expires_at": issued["expires_at"],
            "scopes": issued.get("scopes", []),
            "tenant_scope": issued.get("tenant_scope", "*"),
        },
    )
    return issued


@router.get("/auth/posture")
def auth_posture_status(
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return auth_posture()


@router.post("/auth/rotate")
def rotate_token(
    admin: dict[str, object] = Depends(require_scope("admin:token:write")),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, object]:
    if credentials is None:
        raise HTTPException(status_code=403, detail="forbidden")

    result = rotate_admin_token(credentials.credentials)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="rotate_admin_token",
        status=result.get("status", "unknown"),
        target=str(result.get("new_token_id", "n/a")),
        details={"revoked_token_id": result.get("revoked_token_id", ""), "scopes": result.get("scopes", [])},
    )
    return result


@router.post("/auth/revoke")
def revoke_token(
    admin: dict[str, object] = Depends(require_scope("admin:token:write")),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, object]:
    if credentials is None:
        raise HTTPException(status_code=403, detail="forbidden")

    result = revoke_admin_token(credentials.credentials)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="revoke_admin_token",
        status=result.get("status", "unknown"),
        target=str(result.get("token_id", "n/a")),
        details={},
    )
    return result


@router.get("/auth/introspect")
def introspect(admin: dict[str, object] = Depends(require_scope("control_plane:read"))) -> dict[str, object]:
    return admin


@router.post("/onboard")
def onboard(
    payload: TenantOnboardRequest,
    quota: TenantQuotaBootstrap | None = None,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, payload.tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    resolved_quota = quota or TenantQuotaBootstrap()
    result = onboard_tenant(db, payload, resolved_quota)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="tenant_onboard",
        status=str(result.get("status", "unknown")),
        target=str(result.get("tenant_code", payload.tenant_code)),
        details={"tenant_id": result.get("tenant_id", "")},
    )
    return result


@router.get("/tenant/{tenant_id}")
def tenant_detail(
    tenant_id: UUID,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    result = tenant_detail_by_id(db, tenant_id)
    if result.get("status") == "ok" and not token_allows_tenant(admin, str(result.get("tenant_code", ""))):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="tenant_detail",
        status=str(result.get("status", "unknown")),
        target=str(tenant_id),
        details={},
    )
    return result


@router.post("/tenant/status")
def tenant_status_update(
    payload: TenantStatusUpdateRequest,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, payload.tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    _enforce_policy_or_raise(
        admin=admin,
        action="tenant_status_update",
        target=payload.tenant_code,
        context={
            "status": payload.status,
            "bypass_objective_gate": payload.bypass_objective_gate,
            "change_ticket": payload.change_ticket or "",
        },
    )
    result = update_tenant_status(
        db,
        payload.tenant_code,
        payload.status,
        bypass_objective_gate=payload.bypass_objective_gate,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="tenant_status_update",
        status=str(result.get("status", "unknown")),
        target=payload.tenant_code,
        details={
            "new_status": payload.status,
            "bypass_objective_gate": payload.bypass_objective_gate,
            "change_ticket": payload.change_ticket or "",
            "objective_gate_enforced": result.get("objective_gate_enforced", False),
        },
    )
    return result


@router.post("/tenant/rotate-key")
def tenant_rotate_key(
    payload: TenantApiKeyRotateRequest,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, payload.tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    _enforce_policy_or_raise(
        admin=admin,
        action="tenant_rotate_key",
        target=payload.tenant_code,
        context={
            "reason": payload.reason or "",
            "change_ticket": payload.change_ticket or "",
        },
    )
    result = rotate_tenant_api_key(db, payload.tenant_code)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="tenant_rotate_key",
        status=str(result.get("status", "unknown")),
        target=payload.tenant_code,
        details={
            "new_api_key_id": result.get("new_api_key_id", ""),
            "reason": payload.reason or "",
            "change_ticket": payload.change_ticket or "",
        },
    )
    return result


@router.post("/assurance/contracts/upsert")
def assurance_contract_upsert(
    payload: AssuranceContractUpsertRequest,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, payload.tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")

    result = upsert_assurance_contract(
        tenant_code=payload.tenant_code,
        payload=payload.model_dump(),
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_contract_upsert",
        status=str(result.get("status", "unknown")),
        target=payload.tenant_code,
        details={"contract_version": payload.contract_version, "owner": payload.owner},
    )
    return result


@router.get("/assurance/contracts/{tenant_code}")
def assurance_contract_detail(
    tenant_code: str,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return get_assurance_contract(tenant_code)


@router.get("/assurance/contracts/{tenant_code}/evaluate")
def assurance_contract_evaluate(
    tenant_code: str,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")

    tenant = db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}

    result = evaluate_assurance_contract(tenant.id, tenant_code, limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_contract_evaluate",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={
            "contract_pass": bool(result.get("evaluation", {}).get("contract_pass", False)),
            "sample_count": int(result.get("evaluation", {}).get("sample_count", 0)),
        },
    )
    return result


@router.post("/assurance/policy-packs/upsert")
def assurance_policy_pack_upsert(
    payload: AssurancePolicyPackUpsertRequest,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, payload.tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")

    result = upsert_assurance_policy_pack(payload.tenant_code, payload.model_dump())
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_policy_pack_upsert",
        status=str(result.get("status", "unknown")),
        target=payload.tenant_code,
        details={"pack_version": payload.pack_version, "owner": payload.owner},
    )
    return result


@router.get("/assurance/policy-packs/{tenant_code}")
def assurance_policy_pack_detail(
    tenant_code: str,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return get_assurance_policy_pack(tenant_code)


@router.post("/assurance/contracts/{tenant_code}/remediate")
def assurance_contract_remediate(
    tenant_code: str,
    limit: int = 100,
    auto_apply: bool = False,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")

    tenant = db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}

    result = remediate_assurance_breach(tenant.id, tenant_code, limit=limit, auto_apply=auto_apply)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_contract_remediate",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"auto_apply": auto_apply, "actions": len(result.get("actions", []))},
    )
    return result


@router.get("/assurance/contracts/{tenant_code}/remediation-status")
def assurance_contract_remediation_status(
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return assurance_remediation_status(tenant_code=tenant_code, limit=limit)


@router.get("/assurance/contracts/{tenant_code}/effectiveness")
def assurance_contract_effectiveness(
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return assurance_remediation_effectiveness(tenant_code=tenant_code, limit=limit)


@router.get("/assurance/risk/heatmap")
def assurance_risk_heatmap_endpoint(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return assurance_risk_heatmap(db, limit=limit)


@router.get("/assurance/risk/recommendations")
def assurance_risk_recommendations_endpoint(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return assurance_risk_recommendations(db, limit=limit)


@router.post("/assurance/risk/recommendations/apply")
def assurance_risk_recommendations_apply_endpoint(
    limit: int = 200,
    max_tier: str = "critical",
    dry_run: bool = True,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = apply_assurance_risk_recommendations(
        db,
        limit=limit,
        max_tier=max_tier,
        dry_run=dry_run,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_risk_recommendations_apply",
        status="success",
        target="assurance_risk_recommendations",
        details={"dry_run": dry_run, "max_tier": max_tier, "count": result.get("count", 0)},
    )
    return result


@router.get("/orchestrator/pilot/rollout-handoff/federation/heatmap")
def rollout_handoff_federation_heatmap_endpoint(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return rollout_handoff_federation_heatmap(db, limit=limit)


@router.get("/orchestrator/pilot/rollout-handoff/federation/escalation-matrix")
def rollout_handoff_escalation_matrix_endpoint(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return rollout_handoff_escalation_matrix(db, limit=limit)


@router.post("/orchestrator/pilot/rollout-handoff/federation/escalation/apply")
def rollout_handoff_escalation_apply_endpoint(
    limit: int = 200,
    min_tier: str = "high",
    dry_run: bool = True,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = apply_rollout_handoff_escalation_matrix(
        db,
        limit=limit,
        min_tier=min_tier,
        dry_run=dry_run,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_rollout_handoff_federation_apply",
        status="success",
        target="rollout_handoff_federation",
        details={"dry_run": dry_run, "min_tier": min_tier, "count": result.get("count", 0)},
    )
    return result


@router.post("/orchestrator/pilot/rollout-handoff/federation/slo/upsert")
def rollout_handoff_federation_slo_upsert_endpoint(
    tenant_code: str,
    payload: dict[str, object] = Body(default_factory=dict),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_rollout_handoff_federation_slo_profile(tenant_code, dict(payload))
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_rollout_handoff_federation_slo_upsert",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"profile_version": result.get("profile", {}).get("profile_version", "1.0")},
    )
    return result


@router.get("/orchestrator/pilot/rollout-handoff/federation/slo/{tenant_code}")
def rollout_handoff_federation_slo_get_endpoint(
    tenant_code: str,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return get_rollout_handoff_federation_slo_profile(tenant_code)


@router.get("/orchestrator/pilot/rollout-handoff/federation/slo/{tenant_code}/evaluate")
def rollout_handoff_federation_slo_evaluate_endpoint(
    tenant_code: str,
    limit: int = 200,
    dry_run_escalation: bool = False,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return evaluate_rollout_handoff_federation_slo(
        db,
        tenant_code=tenant_code,
        limit=limit,
        dry_run_escalation=dry_run_escalation,
    )


@router.get("/orchestrator/pilot/rollout-handoff/federation/slo/{tenant_code}/breaches")
def rollout_handoff_federation_slo_breaches_endpoint(
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return rollout_handoff_federation_slo_breach_history(tenant_code, limit=limit)


@router.get("/orchestrator/pilot/rollout-handoff/federation/slo/executive-digest")
def rollout_handoff_federation_slo_executive_digest_endpoint(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return rollout_handoff_federation_executive_digest(db, limit=limit)


@router.post("/orchestrator/pilot/rollout-handoff/federation/slo/executive-digest/sign")
def rollout_handoff_federation_slo_executive_digest_sign_endpoint(
    destination_dir: str = "./tmp/compliance/rollout_handoff_federation_digest",
    limit: int = 200,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = create_signed_rollout_handoff_federation_digest(db, destination_dir=destination_dir, limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_rollout_handoff_federation_digest_sign",
        status=str(result.get("status", "unknown")),
        target=destination_dir,
        details={"path": result.get("path", ""), "limit": limit, "snapshot_id": result.get("snapshot_id", "")},
    )
    return result


@router.get("/orchestrator/pilot/rollout-handoff/federation/slo/executive-digest/sign-status")
def rollout_handoff_federation_slo_executive_digest_sign_status_endpoint(
    limit: int = 100,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return signed_rollout_handoff_federation_digest_status(limit=limit)


@router.get("/orchestrator/pilot/rollout-handoff/federation/slo/executive-digest/sign-verify")
def rollout_handoff_federation_slo_executive_digest_sign_verify_endpoint(
    limit: int = 1000,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return verify_signed_rollout_handoff_federation_digest_chain(limit=limit)


@router.post("/orchestrator/pilot/rollout-handoff/policy-drift/baseline/upsert")
def rollout_handoff_policy_drift_baseline_upsert_endpoint(
    payload: dict[str, object] = Body(default_factory=dict),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = upsert_rollout_handoff_policy_drift_baseline(dict(payload))
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_rollout_handoff_policy_drift_baseline_upsert",
        status=str(result.get("status", "unknown")),
        target="rollout_handoff_policy_drift_baseline",
        details={"profile_version": result.get("baseline", {}).get("profile_version", "1.0")},
    )
    return result


@router.get("/orchestrator/pilot/rollout-handoff/policy-drift/baseline")
def rollout_handoff_policy_drift_baseline_endpoint(
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return get_rollout_handoff_policy_drift_baseline()


@router.get("/orchestrator/pilot/rollout-handoff/policy-drift/heatmap")
def rollout_handoff_policy_drift_heatmap_endpoint(
    limit: int = 200,
    notify: bool = False,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return rollout_handoff_policy_drift_heatmap(db, limit=limit, notify=notify)


@router.get("/orchestrator/pilot/rollout-handoff/policy-drift/{tenant_id}")
def rollout_handoff_policy_drift_tenant_endpoint(
    tenant_id: UUID,
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    drift = evaluate_rollout_handoff_policy_drift(tenant_id, tenant_code, notify=False)
    history = rollout_handoff_policy_drift_history(tenant_code, limit=limit)
    return {"drift": drift, "history": history}


@router.post("/orchestrator/pilot/rollout-handoff/policy-drift/reconcile")
def rollout_handoff_policy_drift_reconcile_endpoint(
    limit: int = 200,
    min_severity: str = "high",
    dry_run: bool = True,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = apply_rollout_handoff_policy_drift_reconciliation(
        db,
        limit=limit,
        min_severity=min_severity,
        dry_run=dry_run,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_rollout_handoff_policy_drift_reconcile",
        status="success",
        target="rollout_handoff_policy_drift",
        details={"count": result.get("count", 0), "dry_run": dry_run, "min_severity": min_severity},
    )
    return result


@router.post("/orchestrator/pilot/rollout-handoff/policy-drift/sign")
def rollout_handoff_policy_drift_sign_endpoint(
    destination_dir: str = "./tmp/compliance/rollout_handoff_policy_drift",
    limit: int = 200,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = create_signed_rollout_handoff_policy_drift_report(db, destination_dir=destination_dir, limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_rollout_handoff_policy_drift_sign",
        status=str(result.get("status", "unknown")),
        target=destination_dir,
        details={"path": result.get("path", ""), "snapshot_id": result.get("snapshot_id", ""), "limit": limit},
    )
    return result


@router.get("/orchestrator/pilot/rollout-handoff/policy-drift/sign-status")
def rollout_handoff_policy_drift_sign_status_endpoint(
    limit: int = 100,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return signed_rollout_handoff_policy_drift_report_status(limit=limit)


@router.get("/orchestrator/pilot/rollout-handoff/policy-drift/sign-verify")
def rollout_handoff_policy_drift_sign_verify_endpoint(
    limit: int = 1000,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return verify_signed_rollout_handoff_policy_drift_report_chain(limit=limit)


@router.post("/orchestrator/failover/profile/upsert")
def orchestration_failover_profile_upsert_endpoint(
    tenant_id: UUID,
    tenant_code: str,
    payload: dict[str, object] = Body(default_factory=dict),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_orchestration_failover_profile(tenant_id, dict(payload))
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_orchestration_failover_profile_upsert",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"tenant_id": str(tenant_id)},
    )
    return result


@router.get("/orchestrator/failover/profile/{tenant_id}")
def orchestration_failover_profile_endpoint(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_orchestration_failover_profile(tenant_id)


@router.get("/orchestrator/failover/state/{tenant_id}")
def orchestration_failover_state_endpoint(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_orchestration_failover_state(tenant_id)


@router.get("/orchestrator/failover/health/{tenant_id}")
def orchestration_failover_health_endpoint(
    tenant_id: UUID,
    tenant_code: str,
    allow_auto_failover: bool = False,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return evaluate_orchestration_failover_health(
        tenant_id,
        tenant_code=tenant_code,
        allow_auto_failover=allow_auto_failover,
    )


@router.post("/orchestrator/failover/drill/{tenant_id}")
def orchestration_failover_drill_endpoint(
    tenant_id: UUID,
    tenant_code: str,
    reason: str = "manual_drill",
    dry_run: bool = True,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = trigger_orchestration_failover_drill(
        tenant_id,
        tenant_code=tenant_code,
        reason=reason,
        dry_run=dry_run,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_orchestration_failover_drill",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"tenant_id": str(tenant_id), "reason": reason, "dry_run": dry_run},
    )
    return result


@router.get("/orchestrator/failover/events/{tenant_id}")
def orchestration_failover_events_endpoint(
    tenant_id: UUID,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return orchestration_failover_events(tenant_id, limit=limit)


@router.get("/orchestrator/failover/enterprise-snapshot")
def orchestration_failover_enterprise_snapshot_endpoint(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return orchestration_failover_enterprise_snapshot(db, limit=limit)


@router.post("/orchestrator/failover/sign")
def orchestration_failover_sign_endpoint(
    destination_dir: str = "./tmp/compliance/orchestration_failover",
    limit: int = 200,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = create_signed_orchestration_failover_report(db, destination_dir=destination_dir, limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_orchestration_failover_sign",
        status=str(result.get("status", "unknown")),
        target=destination_dir,
        details={"path": result.get("path", ""), "snapshot_id": result.get("snapshot_id", ""), "limit": limit},
    )
    return result


@router.get("/orchestrator/failover/sign-status")
def orchestration_failover_sign_status_endpoint(
    limit: int = 100,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return signed_orchestration_failover_report_status(limit=limit)


@router.get("/orchestrator/failover/sign-verify")
def orchestration_failover_sign_verify_endpoint(
    limit: int = 1000,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return verify_signed_orchestration_failover_report_chain(limit=limit)


@router.post("/orchestrator/cost-guardrail/profile/upsert")
def orchestration_cost_guardrail_profile_upsert_endpoint(
    tenant_id: UUID,
    tenant_code: str,
    payload: dict[str, object] = Body(default_factory=dict),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_orchestration_cost_guardrail_profile(tenant_id, dict(payload))
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_orchestration_cost_guardrail_profile_upsert",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"tenant_id": str(tenant_id)},
    )
    return result


@router.get("/orchestrator/cost-guardrail/profile/{tenant_id}")
def orchestration_cost_guardrail_profile_endpoint(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_orchestration_cost_guardrail_profile(tenant_id)


@router.get("/orchestrator/cost-guardrail/evaluate/{tenant_id}")
def orchestration_cost_guardrail_evaluate_endpoint(
    tenant_id: UUID,
    tenant_code: str,
    apply_actions: bool = False,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return evaluate_orchestration_cost_guardrail(tenant_id, tenant_code, apply_actions=apply_actions)


@router.get("/orchestrator/cost-guardrail/events/{tenant_id}")
def orchestration_cost_guardrail_events_endpoint(
    tenant_id: UUID,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return orchestration_cost_guardrail_events(tenant_id, limit=limit)


@router.get("/orchestrator/cost-guardrail/routing-override/{tenant_id}")
def orchestration_cost_guardrail_routing_override_endpoint(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_orchestration_cost_routing_override(tenant_id)


@router.get("/orchestrator/cost-guardrail/throttle-override/{tenant_id}")
def orchestration_cost_guardrail_throttle_override_endpoint(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_orchestration_cost_throttle_override(tenant_id)


@router.get("/orchestrator/cost-guardrail/anomaly-state/{tenant_id}")
def orchestration_cost_guardrail_anomaly_state_endpoint(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_orchestration_cost_anomaly_state(tenant_id)


@router.get("/orchestrator/cost-guardrail/enterprise-snapshot")
def orchestration_cost_guardrail_enterprise_snapshot_endpoint(
    limit: int = 200,
    apply_actions: bool = False,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return orchestration_cost_guardrail_enterprise_snapshot(db, limit=limit, apply_actions=apply_actions)


@router.post("/orchestrator/cost-guardrail/sign")
def orchestration_cost_guardrail_sign_endpoint(
    destination_dir: str = "./tmp/compliance/orchestration_cost_guardrail",
    limit: int = 200,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = create_signed_orchestration_cost_guardrail_report(db, destination_dir=destination_dir, limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_orchestration_cost_guardrail_sign",
        status=str(result.get("status", "unknown")),
        target=destination_dir,
        details={"path": result.get("path", ""), "snapshot_id": result.get("snapshot_id", ""), "limit": limit},
    )
    return result


@router.get("/orchestrator/cost-guardrail/sign-status")
def orchestration_cost_guardrail_sign_status_endpoint(
    limit: int = 100,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return signed_orchestration_cost_guardrail_report_status(limit=limit)


@router.get("/orchestrator/cost-guardrail/sign-verify")
def orchestration_cost_guardrail_sign_verify_endpoint(
    limit: int = 1000,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return verify_signed_orchestration_cost_guardrail_report_chain(limit=limit)


@router.get("/orchestrator/cost-guardrail/federation/heatmap")
def orchestration_cost_guardrail_federation_heatmap_endpoint(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return orchestration_cost_anomaly_federation_heatmap(db, limit=limit)


@router.get("/orchestrator/cost-guardrail/federation/policy-matrix")
def orchestration_cost_guardrail_federation_policy_matrix_endpoint(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return orchestration_cost_policy_tightening_matrix(db, limit=limit)


@router.post("/orchestrator/cost-guardrail/federation/policy-apply")
def orchestration_cost_guardrail_federation_policy_apply_endpoint(
    limit: int = 200,
    min_tier: str = "high",
    dry_run: bool = True,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = apply_orchestration_cost_policy_tightening_matrix(
        db,
        limit=limit,
        min_tier=min_tier,
        dry_run=dry_run,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_orchestration_cost_federation_policy_apply",
        status="success",
        target="orchestration_cost_guardrail_federation",
        details={"limit": limit, "min_tier": min_tier, "dry_run": dry_run, "count": result.get("count", 0)},
    )
    return result


@router.post("/production-v1/runbook/upsert")
def production_v1_runbook_upsert_endpoint(
    payload: ProdV1GoLiveRunbookUpsertRequest,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, payload.tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_prod_v1_go_live_runbook(payload.tenant_code, payload.model_dump())
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_production_v1_runbook_upsert",
        status=str(result.get("status", "unknown")),
        target=payload.tenant_code,
        details={"version": payload.version, "owner": payload.owner},
    )
    return result


@router.get("/production-v1/runbook/{tenant_code}")
def production_v1_runbook_get_endpoint(
    tenant_code: str,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return get_prod_v1_go_live_runbook(tenant_code)


@router.get("/production-v1/readiness-final/{tenant_code}")
def production_v1_readiness_final_endpoint(
    tenant_code: str,
    max_monthly_cost_usd: float = 50.0,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return evaluate_prod_v1_readiness_final(db, tenant_code, max_monthly_cost_usd=max_monthly_cost_usd)


@router.get("/production-v1/playbook/{tenant_code}")
def production_v1_playbook_endpoint(
    tenant_code: str,
    max_monthly_cost_usd: float = 50.0,
    handoff_limit: int = 200,
    closure_limit: int = 20,
    burn_rate_limit: int = 20,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return production_rollout_integration_playbook(
        db,
        tenant_code,
        max_monthly_cost_usd=max_monthly_cost_usd,
        handoff_limit=handoff_limit,
        closure_limit=closure_limit,
        burn_rate_limit=burn_rate_limit,
    )


@router.post("/production-v1/go-live/close")
def production_v1_go_live_close_endpoint(
    payload: ProdV1GoLiveClosureRequest,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, payload.tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = close_prod_v1_go_live(
        db,
        payload.tenant_code,
        approved_by=payload.approved_by,
        change_ticket=payload.change_ticket,
        dry_run=payload.dry_run,
        promote_on_pass=payload.promote_on_pass,
        max_monthly_cost_usd=payload.max_monthly_cost_usd,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_production_v1_go_live_close",
        status=str(result.get("status", "unknown")),
        target=payload.tenant_code,
        details={
            "approved_by": payload.approved_by,
            "change_ticket": payload.change_ticket,
            "dry_run": payload.dry_run,
            "promote_on_pass": payload.promote_on_pass,
            "production_v1_ready": result.get("production_v1_ready", False),
        },
    )
    return result


@router.get("/production-v1/go-live/closure-history")
def production_v1_go_live_closure_history_endpoint(
    tenant_code: str = "",
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if tenant_code and not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return prod_v1_go_live_closure_history(tenant_code=tenant_code, limit=limit)


@router.post("/production-v1/burn-rate/profile/upsert")
def production_v1_burn_rate_profile_upsert_endpoint(
    payload: ProdV1BurnRateProfileUpsertRequest,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, payload.tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_prod_v1_burn_rate_profile(payload.tenant_code, payload.model_dump())
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_production_v1_burn_rate_profile_upsert",
        status=str(result.get("status", "unknown")),
        target=payload.tenant_code,
        details={"version": payload.version, "owner": payload.owner},
    )
    return result


@router.get("/production-v1/burn-rate/profile/{tenant_code}")
def production_v1_burn_rate_profile_get_endpoint(
    tenant_code: str,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return get_prod_v1_burn_rate_profile(tenant_code)


@router.post("/production-v1/burn-rate/evaluate/{tenant_code}")
def production_v1_burn_rate_evaluate_endpoint(
    tenant_code: str,
    apply: bool = False,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = evaluate_prod_v1_burn_rate_guard(db, tenant_code, apply=apply)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_production_v1_burn_rate_evaluate",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={
            "apply": apply,
            "burn_rate": result.get("burn_rate", {}).get("value", 0.0),
            "should_rollback": result.get("decision", {}).get("should_rollback", False),
            "action_executed": result.get("action", {}).get("executed", False),
        },
    )
    return result


@router.get("/production-v1/burn-rate/history")
def production_v1_burn_rate_history_endpoint(
    tenant_code: str = "",
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if tenant_code and not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return prod_v1_burn_rate_guard_history(tenant_code=tenant_code, limit=limit)


@router.post("/assurance/slo/upsert")
def assurance_slo_profile_upsert_endpoint(
    payload: AssuranceSloProfileUpsertRequest,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, payload.tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_assurance_slo_profile(payload.tenant_code, payload.model_dump())
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_slo_profile_upsert",
        status=str(result.get("status", "unknown")),
        target=payload.tenant_code,
        details={"profile_version": payload.profile_version},
    )
    return result


@router.get("/assurance/slo/{tenant_code}")
def assurance_slo_profile_endpoint(
    tenant_code: str,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return get_assurance_slo_profile(tenant_code)


@router.get("/assurance/slo/{tenant_code}/evaluate")
def assurance_slo_evaluate_endpoint(
    tenant_code: str,
    limit: int = 200,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    tenant = db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}
    return evaluate_assurance_slo(tenant.id, tenant_code, limit=limit)


@router.get("/assurance/slo/{tenant_code}/breaches")
def assurance_slo_breaches_endpoint(
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return assurance_slo_breach_history(tenant_code, limit=limit)


@router.get("/assurance/slo/executive-digest")
def assurance_slo_executive_digest_endpoint(
    limit: int = 200,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return assurance_executive_risk_digest(db, limit=limit)


@router.post("/assurance/slo/executive-digest/sign")
def assurance_slo_executive_digest_sign(
    destination_dir: str = "./tmp/compliance/assurance_executive_digest",
    limit: int = 200,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = create_signed_assurance_executive_digest(db, destination_dir=destination_dir, limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_slo_executive_digest_sign",
        status=str(result.get("status", "unknown")),
        target=str(result.get("snapshot_id", "assurance_exec_digest")),
        details={"path": result.get("path", ""), "limit": limit},
    )
    return result


@router.get("/assurance/slo/executive-digest/sign-status")
def assurance_slo_executive_digest_sign_status(
    limit: int = 100,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return signed_assurance_executive_digest_status(limit=limit)


@router.get("/assurance/slo/executive-digest/sign-verify")
def assurance_slo_executive_digest_sign_verify(
    limit: int = 1000,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return verify_signed_assurance_executive_digest_chain(limit=limit)


@router.post("/assurance/slo/{tenant_code}/bulletin/sign")
def assurance_slo_tenant_bulletin_sign(
    tenant_code: str,
    destination_dir: str = "./tmp/compliance/assurance_tenant_bulletin",
    limit: int = 200,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    tenant = db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}
    result = create_signed_tenant_risk_bulletin(
        tenant_id=tenant.id,
        tenant_code=tenant_code,
        destination_dir=destination_dir,
        limit=limit,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_slo_tenant_bulletin_sign",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"path": result.get("path", ""), "limit": limit},
    )
    return result


@router.get("/assurance/slo/{tenant_code}/bulletin/sign-status")
def assurance_slo_tenant_bulletin_sign_status(
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return signed_tenant_risk_bulletin_status(tenant_code=tenant_code, limit=limit)


@router.get("/assurance/slo/{tenant_code}/bulletin/sign-verify")
def assurance_slo_tenant_bulletin_sign_verify(
    tenant_code: str,
    limit: int = 1000,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return verify_signed_tenant_risk_bulletin_chain(tenant_code=tenant_code, limit=limit)


@router.post("/assurance/slo/{tenant_code}/distribution/upsert")
def assurance_slo_tenant_bulletin_distribution_upsert(
    tenant_code: str,
    payload: AssuranceBulletinDistributionUpsertRequest,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if tenant_code != payload.tenant_code:
        raise HTTPException(status_code=400, detail="tenant_code_mismatch")
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")

    result = upsert_bulletin_distribution_policy(tenant_code, payload.model_dump())
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_bulletin_distribution_upsert",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"enabled": payload.enabled, "signed_only": payload.signed_only},
    )
    return result


@router.get("/assurance/slo/{tenant_code}/distribution")
def assurance_slo_tenant_bulletin_distribution(
    tenant_code: str,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return get_bulletin_distribution_policy(tenant_code)


@router.post("/assurance/slo/{tenant_code}/bulletin/deliver")
def assurance_slo_tenant_bulletin_deliver(
    tenant_code: str,
    limit: int = 1,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")

    result = deliver_signed_tenant_bulletin(tenant_code=tenant_code, limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_bulletin_deliver",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"receipt_id": result.get("receipt_id", ""), "http_status": result.get("http_status", 0)},
    )
    return result


@router.get("/assurance/slo/{tenant_code}/bulletin/receipts")
def assurance_slo_tenant_bulletin_receipts(
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return bulletin_delivery_receipts(tenant_code=tenant_code, limit=limit)


@router.post("/assurance/slo/{tenant_code}/bulletin/proof/export")
def assurance_slo_tenant_bulletin_proof_export(
    tenant_code: str,
    destination_dir: str = "./tmp/compliance/assurance_delivery_proofs",
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = export_signed_delivery_proof_bundle(tenant_code=tenant_code, destination_dir=destination_dir, limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_delivery_proof_export",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"path": result.get("path", ""), "limit": limit},
    )
    return result


@router.get("/assurance/slo/{tenant_code}/bulletin/proof/status")
def assurance_slo_tenant_bulletin_proof_status(
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return signed_delivery_proof_status(tenant_code=tenant_code, limit=limit)


@router.get("/assurance/slo/{tenant_code}/bulletin/proof/verify")
def assurance_slo_tenant_bulletin_proof_verify(
    tenant_code: str,
    limit: int = 1000,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return verify_signed_delivery_proof_chain(tenant_code=tenant_code, limit=limit)


@router.get("/assurance/proof-index")
def assurance_proof_index(
    limit: int = 500,
    db: Session = Depends(get_db),
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return assurance_delivery_proof_index(db, limit=limit)


@router.post("/assurance/proof-index/export")
def assurance_proof_index_export(
    destination_dir: str = "./tmp/compliance/assurance_proof_index",
    limit: int = 500,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = export_assurance_delivery_proof_index(db, destination_dir=destination_dir, limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_proof_index_export",
        status=str(result.get("status", "unknown")),
        target=destination_dir,
        details={"limit": limit, "path": result.get("path", "")},
    )
    return result


@router.post("/assurance/slo/{tenant_code}/verifier-kit/export")
def assurance_tenant_verifier_kit_export(
    tenant_code: str,
    destination_dir: str = "./tmp/compliance/verifier_kits",
    limit: int = 1000,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    tenant = db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}

    result = export_tenant_verifier_kit(tenant_code=tenant_code, destination_dir=destination_dir, limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_verifier_kit_export",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"kit_dir": result.get("kit_dir", ""), "limit": limit},
    )
    return result


@router.get("/assurance/slo/{tenant_code}/verifier-kit/status")
def assurance_tenant_verifier_kit_status(
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return tenant_verifier_kit_status(tenant_code=tenant_code, limit=limit)


@router.post("/assurance/slo/{tenant_code}/evidence-package/export")
def assurance_tenant_evidence_package_export(
    tenant_code: str,
    destination_dir: str = "./tmp/compliance/evidence_package_index",
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    tenant = db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}
    result = export_tenant_compliance_package_index(
        tenant_id=tenant.id,
        tenant_code=tenant_code,
        destination_dir=destination_dir,
        limit=limit,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_evidence_package_export",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"path": result.get("path", ""), "limit": limit},
    )
    return result


@router.get("/assurance/slo/{tenant_code}/evidence-package/status")
def assurance_tenant_evidence_package_status(
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return tenant_compliance_package_index_status(tenant_code=tenant_code, limit=limit)


@router.post("/assurance/slo/{tenant_code}/evidence-package/sign")
def assurance_tenant_evidence_package_sign(
    tenant_code: str,
    destination_dir: str = "./tmp/compliance/assurance_tenant_evidence_package_signed",
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    tenant = db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}

    result = create_signed_tenant_evidence_package(
        tenant_id=tenant.id,
        tenant_code=tenant_code,
        destination_dir=destination_dir,
        limit=limit,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_evidence_package_sign",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"path": result.get("path", ""), "limit": limit, "snapshot_id": result.get("snapshot_id", "")},
    )
    return result


@router.get("/assurance/slo/{tenant_code}/evidence-package/sign-status")
def assurance_tenant_evidence_package_sign_status(
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return signed_tenant_evidence_package_status(tenant_code=tenant_code, limit=limit)


@router.get("/assurance/slo/{tenant_code}/evidence-package/sign-verify")
def assurance_tenant_evidence_package_sign_verify(
    tenant_code: str,
    limit: int = 1000,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return verify_signed_tenant_evidence_package_chain(tenant_code=tenant_code, limit=limit)


@router.post("/assurance/slo/{tenant_code}/external-verifier/import")
def assurance_tenant_external_verifier_import(
    tenant_code: str,
    payload: dict[str, object] = Body(default_factory=dict),
    source: str = "external_auditor",
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = import_external_verifier_bundle(tenant_code=tenant_code, verifier_payload=payload, source=source)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_external_verifier_import",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"source": source, "event_id": result.get("event_id", ""), "valid": result.get("valid", False)},
    )
    return result


@router.get("/assurance/slo/{tenant_code}/external-verifier/status")
def assurance_tenant_external_verifier_status(
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return external_verifier_status(tenant_code=tenant_code, limit=limit)


@router.post("/assurance/slo/{tenant_code}/external-verifier/policy/upsert")
def assurance_tenant_external_verifier_policy_upsert(
    tenant_code: str,
    payload: dict[str, object] = Body(default_factory=dict),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_external_verifier_policy(tenant_code=tenant_code, payload=payload)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_external_verifier_policy_upsert",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details=result.get("policy", {}),
    )
    return result


@router.get("/assurance/slo/{tenant_code}/external-verifier/policy")
def assurance_tenant_external_verifier_policy(
    tenant_code: str,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return get_external_verifier_policy(tenant_code=tenant_code)


@router.post("/assurance/slo/{tenant_code}/external-verifier/tokens/issue")
def assurance_tenant_external_verifier_token_issue(
    tenant_code: str,
    verifier_name: str = "external_auditor",
    ttl_seconds: int = 86400,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = issue_verifier_token(tenant_code=tenant_code, verifier_name=verifier_name, ttl_seconds=ttl_seconds)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_external_verifier_token_issue",
        status="success",
        target=tenant_code,
        details={"token_id": result.get("token_id", ""), "verifier_name": verifier_name, "ttl_seconds": ttl_seconds},
    )
    return result


@router.post("/assurance/slo/{tenant_code}/external-verifier/tokens/revoke")
def assurance_tenant_external_verifier_token_revoke(
    tenant_code: str,
    token: str = "",
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = revoke_verifier_token(token)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_external_verifier_token_revoke",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"token_prefix": token.split('.', 1)[0] if token else ""},
    )
    return result


@router.post("/assurance/slo/{tenant_code}/zero-trust/attest")
def assurance_tenant_zero_trust_attest(
    tenant_code: str,
    limit: int = 100,
    freshness_hours: int = 24,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = compute_zero_trust_attestation(tenant_code=tenant_code, limit=limit, freshness_hours=freshness_hours)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_zero_trust_attest",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"trusted": result.get("trusted", False), "event_id": result.get("event_id", "")},
    )
    return result


@router.get("/assurance/slo/{tenant_code}/zero-trust/status")
def assurance_tenant_zero_trust_status(
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return zero_trust_attestation_status(tenant_code=tenant_code, limit=limit)


@router.get("/assurance/slo/{tenant_code}/external-verifier/receipts")
def assurance_tenant_external_verifier_receipts(
    tenant_code: str,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return verifier_receipt_status(tenant_code=tenant_code, limit=limit)


@router.get("/assurance/slo/{tenant_code}/external-verifier/receipts/verify")
def assurance_tenant_external_verifier_receipts_verify(
    tenant_code: str,
    limit: int = 1000,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    return verify_verifier_receipt_chain(tenant_code=tenant_code, limit=limit)


@router.get("/assurance/zero-trust/overview")
def assurance_zero_trust_overview(
    limit: int = 200,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return zero_trust_overview(limit=limit)


@router.post("/orchestrator/pilot/operators/issue")
def control_plane_issue_pilot_operator_token(
    tenant_code: str,
    actor: str = "pilot_admin",
    ttl_seconds: int = 86400,
    scopes: str = "pilot:read,pilot:write",
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = issue_pilot_operator_token(
        actor=actor,
        tenant_code=tenant_code,
        ttl_seconds=ttl_seconds,
        scopes=[s.strip() for s in scopes.split(",") if s.strip()],
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_pilot_operator_token_issue",
        status="success",
        target=tenant_code,
        details={"token_id": result.get("token_id", ""), "actor": actor, "scopes": result.get("scopes", [])},
    )
    return result


@router.post("/orchestrator/pilot/operators/revoke")
def control_plane_revoke_pilot_operator_token(
    tenant_code: str,
    token: str,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = revoke_pilot_operator_token(token)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_pilot_operator_token_revoke",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"token_prefix": token.split(".", 1)[0] if token else ""},
    )
    return result


@router.post("/orchestrator/pilot/rollout-handoff/issue")
def control_plane_issue_rollout_handoff_token(
    tenant_id: UUID,
    tenant_code: str,
    auditor_name: str = "external_auditor",
    actor: str = "control_plane_admin",
    ttl_seconds: int = 86400,
    session_ttl_seconds: int = 3600,
    max_accesses: int = 100,
    allowed_ip_cidrs: str = "",
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = issue_rollout_handoff_token(
        tenant_id=tenant_id,
        actor=actor,
        auditor_name=auditor_name,
        ttl_seconds=ttl_seconds,
        session_ttl_seconds=session_ttl_seconds,
        max_accesses=max_accesses,
        allowed_ip_cidrs=allowed_ip_cidrs,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_rollout_handoff_token_issue",
        status="success",
        target=tenant_code,
        details={
            "tenant_id": str(tenant_id),
            "token_id": result.get("token_id", ""),
            "auditor_name": auditor_name,
            "session_ttl_seconds": session_ttl_seconds,
            "max_accesses": max_accesses,
            "allowed_ip_cidrs": allowed_ip_cidrs,
        },
    )
    return result


@router.post("/orchestrator/pilot/rollout-handoff/revoke")
def control_plane_revoke_rollout_handoff_token(
    tenant_code: str,
    token: str,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = revoke_rollout_handoff_token(token)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_rollout_handoff_token_revoke",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"token_prefix": token.split(".", 1)[0] if token else ""},
    )
    return result


@router.get("/orchestrator/pilot/rollout-handoff/receipts/{tenant_id}")
def control_plane_rollout_handoff_receipts(
    tenant_id: UUID,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return rollout_handoff_receipts(tenant_id, limit=limit)


@router.post("/orchestrator/pilot/rollout-handoff/policy/upsert")
def control_plane_rollout_handoff_policy_upsert(
    tenant_id: UUID,
    tenant_code: str,
    anomaly_detection_enabled: bool = True,
    auto_revoke_on_ip_mismatch: bool = True,
    max_denied_attempts_before_revoke: int = 3,
    adaptive_hardening_enabled: bool = True,
    risk_threshold_block: int = 85,
    risk_threshold_harden: int = 60,
    harden_session_ttl_seconds: int = 300,
    containment_playbook_enabled: bool = True,
    containment_high_threshold: int = 60,
    containment_critical_threshold: int = 85,
    containment_action_high: str = "harden_session",
    containment_action_critical: str = "revoke_token",
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_rollout_handoff_policy(
        tenant_id=tenant_id,
        anomaly_detection_enabled=anomaly_detection_enabled,
        auto_revoke_on_ip_mismatch=auto_revoke_on_ip_mismatch,
        max_denied_attempts_before_revoke=max_denied_attempts_before_revoke,
        adaptive_hardening_enabled=adaptive_hardening_enabled,
        risk_threshold_block=risk_threshold_block,
        risk_threshold_harden=risk_threshold_harden,
        harden_session_ttl_seconds=harden_session_ttl_seconds,
        containment_playbook_enabled=containment_playbook_enabled,
        containment_high_threshold=containment_high_threshold,
        containment_critical_threshold=containment_critical_threshold,
        containment_action_high=containment_action_high,
        containment_action_critical=containment_action_critical,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_rollout_handoff_policy_upsert",
        status="success",
        target=tenant_code,
        details={"tenant_id": str(tenant_id), "policy": result.get("policy", {})},
    )
    return result


@router.get("/orchestrator/pilot/rollout-handoff/policy/{tenant_id}")
def control_plane_rollout_handoff_policy_detail(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_rollout_handoff_policy(tenant_id)


@router.get("/orchestrator/pilot/rollout-handoff/anomalies/{tenant_id}")
def control_plane_rollout_handoff_anomalies(
    tenant_id: UUID,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return rollout_handoff_anomalies(tenant_id, limit=limit)


@router.get("/orchestrator/pilot/rollout-handoff/risk-events/{tenant_id}")
def control_plane_rollout_handoff_risk_events(
    tenant_id: UUID,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return rollout_handoff_trust_events(tenant_id, limit=limit)


@router.get("/orchestrator/pilot/rollout-handoff/risk/{tenant_id}")
def control_plane_rollout_handoff_risk_snapshot(
    tenant_id: UUID,
    limit: int = 200,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return rollout_handoff_risk_snapshot(tenant_id, limit=limit)


@router.get("/orchestrator/pilot/rollout-handoff/containment/{tenant_id}")
def control_plane_rollout_handoff_containment_events(
    tenant_id: UUID,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return rollout_handoff_containment_events(tenant_id, limit=limit)


@router.get("/orchestrator/pilot/rollout-handoff/governance/{tenant_id}")
def control_plane_rollout_handoff_governance_snapshot(
    tenant_id: UUID,
    limit: int = 200,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return rollout_handoff_governance_snapshot(tenant_id, limit=limit)


@router.post("/orchestrator/pilot/onboarding/upsert")
def control_plane_pilot_onboarding_upsert(
    tenant_id: UUID,
    tenant_code: str,
    target_asset: str,
    strategy_profile: str = "balanced",
    red_scenario_name: str = "credential_stuffing_sim",
    cycle_interval_seconds: int = 300,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_pilot_onboarding_profile(
        tenant_id=tenant_id,
        tenant_code=tenant_code,
        target_asset=target_asset,
        strategy_profile=strategy_profile,
        red_scenario_name=red_scenario_name,
        cycle_interval_seconds=cycle_interval_seconds,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_pilot_onboarding_upsert",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"tenant_id": str(tenant_id), "target_asset": target_asset},
    )
    return result


@router.get("/orchestrator/pilot/onboarding/{tenant_id}")
def control_plane_pilot_onboarding_detail(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_pilot_onboarding_profile(tenant_id)


@router.get("/orchestrator/pilot/onboarding/{tenant_id}/checklist")
def control_plane_pilot_onboarding_checklist(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return pilot_onboarding_checklist(tenant_id)


@router.post("/orchestrator/pilot/safety-policy/upsert")
def control_plane_pilot_safety_policy_upsert(
    tenant_id: UUID,
    tenant_code: str,
    max_consecutive_failures: int = 3,
    auto_stop_on_consecutive_failures: bool = True,
    objective_gate_check_each_tick: bool = False,
    auto_stop_on_objective_gate_fail: bool = False,
    notify_on_auto_stop: bool = True,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_tenant_safety_policy(
        tenant_id=tenant_id,
        max_consecutive_failures=max_consecutive_failures,
        auto_stop_on_consecutive_failures=auto_stop_on_consecutive_failures,
        objective_gate_check_each_tick=objective_gate_check_each_tick,
        auto_stop_on_objective_gate_fail=auto_stop_on_objective_gate_fail,
        notify_on_auto_stop=notify_on_auto_stop,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_pilot_safety_policy_upsert",
        status="success",
        target=tenant_code,
        details={"tenant_id": str(tenant_id), "policy": result.get("policy", {})},
    )
    return result


@router.get("/orchestrator/pilot/safety-policy/{tenant_id}")
def control_plane_pilot_safety_policy_detail(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_tenant_safety_policy(tenant_id)


@router.post("/orchestrator/pilot/rate-budget/upsert")
def control_plane_pilot_rate_budget_upsert(
    tenant_id: UUID,
    tenant_code: str,
    max_cycles_per_hour: int = 120,
    max_red_events_per_hour: int = 10000,
    enforce_rate_budget: bool = True,
    auto_pause_on_budget_exceeded: bool = True,
    notify_on_budget_exceeded: bool = True,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_tenant_rate_budget(
        tenant_id=tenant_id,
        max_cycles_per_hour=max_cycles_per_hour,
        max_red_events_per_hour=max_red_events_per_hour,
        enforce_rate_budget=enforce_rate_budget,
        auto_pause_on_budget_exceeded=auto_pause_on_budget_exceeded,
        notify_on_budget_exceeded=notify_on_budget_exceeded,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_pilot_rate_budget_upsert",
        status="success",
        target=tenant_code,
        details={"tenant_id": str(tenant_id), "budget": result.get("budget", {})},
    )
    return result


@router.get("/orchestrator/pilot/rate-budget/{tenant_id}")
def control_plane_pilot_rate_budget_detail(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_tenant_rate_budget(tenant_id)


@router.get("/orchestrator/pilot/rate-budget/{tenant_id}/usage")
def control_plane_pilot_rate_budget_usage(
    tenant_id: UUID,
    hour_epoch: int | None = None,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_tenant_rate_budget_usage(tenant_id, hour_epoch=hour_epoch)


@router.post("/orchestrator/pilot/scheduler-profile/upsert")
def control_plane_pilot_scheduler_profile_upsert(
    tenant_id: UUID,
    tenant_code: str,
    priority_tier: str = "normal",
    starvation_incident_threshold: int = 3,
    notify_on_starvation: bool = False,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_tenant_scheduler_profile(
        tenant_id=tenant_id,
        priority_tier=priority_tier,
        starvation_incident_threshold=starvation_incident_threshold,
        notify_on_starvation=notify_on_starvation,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_pilot_scheduler_profile_upsert",
        status="success",
        target=tenant_code,
        details={"tenant_id": str(tenant_id), "profile": result.get("profile", {})},
    )
    return result


@router.get("/orchestrator/pilot/scheduler-profile/{tenant_id}")
def control_plane_pilot_scheduler_profile_detail(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_tenant_scheduler_profile(tenant_id)


@router.post("/orchestrator/pilot/rollout-profile/upsert")
def control_plane_pilot_rollout_profile_upsert(
    tenant_id: UUID,
    tenant_code: str,
    rollout_stage: str = "ga",
    canary_percent: int = 100,
    hold: bool = False,
    notify_on_hold: bool = False,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_tenant_rollout_profile(
        tenant_id=tenant_id,
        rollout_stage=rollout_stage,
        canary_percent=canary_percent,
        hold=hold,
        notify_on_hold=notify_on_hold,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_pilot_rollout_profile_upsert",
        status="success",
        target=tenant_code,
        details={"tenant_id": str(tenant_id), "profile": result.get("profile", {})},
    )
    return result


@router.get("/orchestrator/pilot/rollout-profile/{tenant_id}")
def control_plane_pilot_rollout_profile_detail(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_tenant_rollout_profile(tenant_id)


@router.post("/orchestrator/pilot/rollout-policy/upsert")
def control_plane_pilot_rollout_policy_upsert(
    tenant_id: UUID,
    tenant_code: str,
    auto_promote_enabled: bool = True,
    auto_demote_enabled: bool = True,
    require_approval_for_promote: bool = False,
    require_approval_for_demote: bool = True,
    require_dual_control_for_promote: bool = False,
    require_dual_control_for_demote: bool = False,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = upsert_tenant_rollout_policy(
        tenant_id=tenant_id,
        auto_promote_enabled=auto_promote_enabled,
        auto_demote_enabled=auto_demote_enabled,
        require_approval_for_promote=require_approval_for_promote,
        require_approval_for_demote=require_approval_for_demote,
        require_dual_control_for_promote=require_dual_control_for_promote,
        require_dual_control_for_demote=require_dual_control_for_demote,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_pilot_rollout_policy_upsert",
        status="success",
        target=tenant_code,
        details={"tenant_id": str(tenant_id), "policy": result.get("policy", {})},
    )
    return result


@router.get("/orchestrator/pilot/rollout-policy/{tenant_id}")
def control_plane_pilot_rollout_policy_detail(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_tenant_rollout_policy(tenant_id)


@router.post("/orchestrator/pilot/rollout/evaluate/{tenant_id}")
def control_plane_pilot_rollout_evaluate(
    tenant_id: UUID,
    apply: bool = True,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    _ = admin
    return evaluate_tenant_rollout_posture(tenant_id, apply=apply)


@router.get("/orchestrator/pilot/rollout/decisions/{tenant_id}")
def control_plane_pilot_rollout_decisions(
    tenant_id: UUID,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return rollout_decision_history(tenant_id, limit=limit)


@router.get("/orchestrator/pilot/rollout/evidence/{tenant_id}")
def control_plane_pilot_rollout_evidence(
    tenant_id: UUID,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return rollout_evidence_history(tenant_id, limit=limit)


@router.get("/orchestrator/pilot/rollout/evidence/verify/{tenant_id}")
def control_plane_pilot_rollout_evidence_verify(
    tenant_id: UUID,
    limit: int = 1000,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return verify_rollout_evidence_chain(tenant_id, limit=limit)


@router.post("/orchestrator/pilot/rollout/evidence/export")
def control_plane_pilot_rollout_evidence_export(
    tenant_id: UUID,
    destination_dir: str = "./tmp/compliance/rollout_evidence",
    limit: int = 1000,
    notarize: bool = True,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    _ = admin
    return export_rollout_evidence_bundle(
        tenant_id=tenant_id,
        destination_dir=destination_dir,
        limit=limit,
        notarize=notarize,
    )


@router.get("/orchestrator/pilot/rollout/evidence/export-status/{tenant_id}")
def control_plane_pilot_rollout_evidence_export_status(
    tenant_id: UUID,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return rollout_evidence_bundle_status(tenant_id=tenant_id, limit=limit)


@router.get("/orchestrator/pilot/rollout/pending/{tenant_id}")
def control_plane_pilot_rollout_pending(
    tenant_id: UUID,
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return list_pending_rollout_decisions(tenant_id, limit=limit)


@router.post("/orchestrator/pilot/rollout/pending/approve")
def control_plane_pilot_rollout_pending_approve(
    tenant_id: UUID,
    tenant_code: str,
    decision_id: str,
    approve: bool = True,
    reviewer: str = "control_plane_admin",
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")
    result = approve_pending_rollout_decision(tenant_id, decision_id, approve=approve, reviewer=reviewer)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_pilot_rollout_pending_approve",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"tenant_id": str(tenant_id), "decision_id": decision_id, "approve": approve},
    )
    return result


@router.get("/orchestrator/pilot/rollout/guard/{tenant_id}")
def control_plane_pilot_rollout_guard(
    tenant_id: UUID,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    _ = admin
    return get_rollout_guard_state(tenant_id)


@router.post("/assurance/contracts/{tenant_code}/approve")
def assurance_contract_approve_action(
    tenant_code: str,
    payload: AssuranceRemediationApprovalRequest,
    db: Session = Depends(get_db),
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    if not token_allows_tenant(admin, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden:tenant_scope")

    tenant = db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}

    result = approve_assurance_remediation_action(
        tenant_id=tenant.id,
        tenant_code=tenant_code,
        action_id=payload.action_id,
        approve=payload.approve,
    )
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_assurance_contract_approve",
        status=str(result.get("status", "unknown")),
        target=tenant_code,
        details={"action_id": payload.action_id, "approve": payload.approve},
    )
    return result


@router.get("/audit")
def audit(limit: int = 100, _: dict[str, object] = Depends(require_scope("control_plane:read"))) -> dict[str, object]:
    rows = list_control_plane_audit(limit=limit)
    return {"count": len(rows), "rows": rows}


@router.post("/audit/export")
def audit_export(admin: dict[str, object] = Depends(require_scope("control_plane:write"))) -> dict[str, object]:
    result = export_control_plane_audit_to_siem()
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_audit_export",
        status=str(result.get("status", "unknown")),
        target="siem",
        details={k: v for k, v in result.items() if k != "status"},
    )
    return result


@router.get("/audit/export-status")
def audit_export_status(_: dict[str, object] = Depends(require_scope("control_plane:read"))) -> dict[str, object]:
    return get_export_status()


@router.get("/audit/archive-status")
def audit_archive_status(_: dict[str, object] = Depends(require_scope("control_plane:read"))) -> dict[str, object]:
    return get_archive_status()


@router.get("/audit/archive-verify")
def audit_archive_verify(
    limit: int = 1000,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return verify_archive_chain(limit=limit)


@router.get("/audit/failed-batches")
def audit_failed_batches(
    limit: int = 100,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    rows = list_failed_batches(limit=limit)
    return {"count": len(rows), "rows": rows}


@router.post("/audit/replay")
def audit_replay(
    limit: int = 50,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = replay_failed_batches(limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_audit_replay",
        status="success",
        target="siem",
        details=result,
    )
    return result


@router.get("/audit/recovery-status")
def audit_recovery_status(
    limit: int = 100,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return recovery_status(limit=limit)


@router.post("/audit/ack")
def audit_ack(
    payload: SiemAckRequest,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = acknowledge_failed_batch(payload.failed_batch_id, payload.ack_ref)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_audit_ack",
        status=str(result.get("status", "unknown")),
        target=payload.failed_batch_id,
        details={"ack_ref": payload.ack_ref},
    )
    return result


@router.get("/audit/reconcile")
def audit_reconcile(
    limit: int = 1000,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return reconcile_failed_batches(limit=limit)


@router.get("/audit/immutable-status")
def audit_immutable_status(
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return immutable_store_status()


@router.post("/audit/immutable-snapshot")
def audit_immutable_snapshot(
    destination_dir: str = "./tmp/immutable_snapshots",
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = export_store_snapshot(destination_dir=destination_dir)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_immutable_snapshot",
        status=str(result.get("status", "unknown")),
        target=destination_dir,
        details=result,
    )
    return result


@router.post("/audit/offload")
def audit_offload(
    limit: int = 100,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = offload_archive_batches(limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_audit_offload",
        status=str(result.get("status", "unknown")),
        target=str(result.get("mode", "offload")),
        details={k: v for k, v in result.items() if k != "status"},
    )
    return result


@router.get("/audit/offload-status")
def audit_offload_status(
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return offload_status()


@router.get("/audit/offload/s3-object-lock-validate")
def audit_s3_object_lock_validate(
    dry_run: bool = True,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    result = validate_s3_object_lock(dry_run=dry_run)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_s3_object_lock_validate",
        status="success" if result.get("overall_pass") else "failed",
        target="s3_object_lock",
        details={"dry_run": dry_run, "overall_pass": result.get("overall_pass", False)},
    )
    return result


@router.get("/compliance/evidence")
def control_plane_compliance_evidence(
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    result = build_control_plane_compliance_evidence()
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_compliance_evidence",
        status="success" if result.get("overall_pass") else "warning",
        target="control_plane_compliance",
        details={"overall_pass": result.get("overall_pass", False)},
    )
    return result


@router.get("/governance/policy")
def control_plane_policy_status(
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return {"policy": policy_config()}


@router.get("/governance/dashboard")
def control_plane_governance_dashboard(
    limit: int = 1000,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return governance_dashboard(limit=limit)


@router.post("/governance/attest")
def control_plane_governance_attest(
    limit: int = 5000,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = create_governance_attestation(limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_governance_attest",
        status=str(result.get("status", "unknown")),
        target="governance_attestation",
        details={"event_id": result.get("event_id", ""), "signature": result.get("signature", "")},
    )
    return result


@router.get("/governance/attestation-status")
def control_plane_governance_attestation_status(
    limit: int = 100,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return governance_attestation_status(limit=limit)


@router.get("/governance/attestation-verify")
def control_plane_governance_attestation_verify(
    limit: int = 1000,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return verify_governance_attestation_chain(limit=limit)


@router.post("/governance/attestation-export")
def control_plane_governance_attestation_export(
    destination_dir: str = "./tmp/compliance/exports",
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = export_latest_governance_attestation(destination_dir=destination_dir)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_governance_attestation_export",
        status=str(result.get("status", "unknown")),
        target=destination_dir,
        details={k: v for k, v in result.items() if k != "status"},
    )
    return result


@router.post("/audit-pack/generate")
def control_plane_audit_pack_generate(
    limit: int = 5000,
    destination_dir: str = "./tmp/compliance/audit_packs",
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = generate_external_audit_pack(limit=limit, destination_dir=destination_dir)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_audit_pack_generate",
        status=str(result.get("status", "unknown")),
        target=destination_dir,
        details={
            "pack_id": result.get("pack_id", ""),
            "overall_pass": result.get("overall_pass", False),
            "manifest_path": result.get("manifest_path", ""),
        },
    )
    return result


@router.get("/audit-pack/status")
def control_plane_audit_pack_status(
    limit: int = 100,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return audit_pack_status(limit=limit)


@router.get("/audit-pack/manifest-attestation/status")
def control_plane_audit_pack_manifest_attestation_status_route(
    limit: int = 100,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return audit_pack_manifest_attestation_status(limit=limit)


@router.get("/audit-pack/manifest-attestation/verify")
def control_plane_audit_pack_manifest_attestation_verify(
    limit: int = 1000,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    result = verify_audit_pack_manifest_attestation_chain(limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_audit_pack_manifest_attestation_verify",
        status="success" if result.get("valid", False) else "failed",
        target="audit_pack_manifest_attestation_chain",
        details={"limit": limit, "valid": result.get("valid", False)},
    )
    return result


@router.post("/audit-pack/verify")
def control_plane_audit_pack_verify(
    manifest_path: str,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    result = verify_external_audit_pack(manifest_path=manifest_path)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_audit_pack_verify",
        status=str(result.get("status", "unknown")),
        target=manifest_path,
        details={"valid": result.get("valid", False), "failure_count": result.get("failure_count", 0)},
    )
    return result


@router.post("/audit-pack/publish")
def control_plane_audit_pack_publish(
    dry_run: bool = False,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = publish_latest_audit_pack(dry_run=dry_run)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_audit_pack_publish",
        status=str(result.get("status", "unknown")),
        target=str(result.get("pack_id", "latest")),
        details={
            "dry_run": dry_run,
            "mode": result.get("mode", ""),
            "publication_id": result.get("publication_id", ""),
        },
    )
    return result


@router.get("/audit-pack/publication-status")
def control_plane_audit_pack_publication_status(
    limit: int = 100,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return publication_status(limit=limit)


@router.post("/audit-pack/transparency/publish")
def control_plane_transparency_publish(
    dry_run: bool = False,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = publish_transparency_entry(dry_run=dry_run)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_transparency_publish",
        status=str(result.get("status", "unknown")),
        target=str(result.get("entry_hash", "transparency")),
        details={"dry_run": dry_run, "mode": result.get("mode", "")},
    )
    return result


@router.get("/audit-pack/transparency/status")
def control_plane_transparency_status(
    limit: int = 100,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return transparency_status(limit=limit)


@router.post("/audit-pack/legal-evidence/export")
def control_plane_legal_evidence_export(
    destination_dir: str = "./tmp/compliance/legal_evidence",
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = export_legal_evidence_profile(destination_dir=destination_dir)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_legal_evidence_export",
        status=str(result.get("status", "unknown")),
        target=destination_dir,
        details={"pack_id": result.get("pack_id", ""), "path": result.get("path", "")},
    )
    return result


@router.post("/audit-pack/public-assurance/sign")
def control_plane_public_assurance_sign(
    destination_dir: str = "./tmp/compliance/public_assurance",
    limit: int = 1000,
    admin: dict[str, object] = Depends(require_scope("control_plane:write")),
) -> dict[str, object]:
    result = create_signed_public_assurance_snapshot(destination_dir=destination_dir, limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_public_assurance_sign",
        status=str(result.get("status", "unknown")),
        target=str(result.get("snapshot_id", "public_assurance")),
        details={"path": result.get("path", ""), "enterprise_ready": result.get("enterprise_ready", False)},
    )
    return result


@router.get("/audit-pack/public-assurance/sign-status")
def control_plane_public_assurance_sign_status(
    limit: int = 100,
    _: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    return signed_public_assurance_status(limit=limit)


@router.get("/audit-pack/public-assurance/sign-verify")
def control_plane_public_assurance_sign_verify(
    limit: int = 1000,
    admin: dict[str, object] = Depends(require_scope("control_plane:read")),
) -> dict[str, object]:
    result = verify_signed_public_assurance_chain(limit=limit)
    write_control_plane_audit(
        actor=str(admin.get("actor", "admin")),
        action="control_plane_public_assurance_sign_verify",
        status="success" if result.get("valid", False) else "failed",
        target="public_assurance_signature_chain",
        details={"limit": limit, "valid": result.get("valid", False)},
    )
    return result
