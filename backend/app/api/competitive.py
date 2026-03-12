from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.admin_auth import token_has_scope, verify_admin_token
from app.services.action_center import (
    dispatch_manual_alert,
    get_action_center_policy,
    list_action_center_events,
    upsert_action_center_policy,
)
from app.services.connector_observability import connector_health_snapshot, ingest_connector_event, list_connector_events
from app.services.connector_credential_vault import (
    auto_rotate_due_credentials,
    evaluate_connector_credential_hygiene,
    federation_connector_credential_hygiene,
    list_connector_credentials,
    list_connector_rotation_events,
    rotate_connector_credential,
    upsert_connector_credential,
    verify_connector_rotation_chain,
)
from app.services.connector_credential_hygiene import (
    get_credential_hygiene_policy,
    list_credential_hygiene_runs,
    run_credential_hygiene_for_tenant,
    run_credential_hygiene_scheduler,
    upsert_credential_hygiene_policy,
)
from app.services.connector_reliability import (
    connector_reliability_federation,
    get_connector_reliability_policy,
    list_connector_dead_letter_backlog,
    list_connector_reliability_runs,
    run_connector_dead_letter_replay,
    run_connector_replay_scheduler,
    upsert_connector_reliability_policy,
)
from app.services.detection_autotune import (
    get_detection_autotune_policy,
    list_detection_autotune_runs,
    run_detection_autotune,
    run_detection_autotune_scheduler,
    upsert_detection_autotune_policy,
)
from app.services.red_exploit_autopilot import (
    get_red_exploit_autopilot_policy,
    list_red_exploit_autopilot_runs,
    run_red_exploit_autopilot,
    run_red_exploit_autopilot_scheduler,
    upsert_red_exploit_autopilot_policy,
)
from app.services.connector_sla import (
    evaluate_connector_sla,
    get_connector_sla_profile,
    list_connector_sla_breaches,
    upsert_connector_sla_profile,
)
from app.services.competitive_federation import action_center_sla_federation_snapshot
from app.services.competitive_engine import (
    apply_detection_rule,
    build_unified_case_graph,
    create_phase_scope_check,
    list_detection_rules,
    list_detection_tuning_runs,
    list_exploit_path_runs,
    list_phase_scope_checks,
    list_roadmap_objectives,
    list_threat_content_packs,
    run_detection_copilot_tuning,
    run_exploit_path_simulation,
    upsert_threat_content_pack,
)
from app.services.threat_content_pipeline import (
    get_threat_content_pipeline_policy,
    list_threat_content_pipeline_runs,
    run_threat_content_pipeline,
    run_threat_content_pipeline_scheduler,
    threat_content_pipeline_federation,
    upsert_threat_content_pipeline_policy,
)
from app.services.soar_playbook_hub import (
    approve_playbook_execution,
    execute_playbook,
    get_tenant_playbook_policy,
    list_playbook_executions,
    list_playbooks,
    soar_marketplace_overview,
    upsert_tenant_playbook_policy,
    upsert_playbook,
)
from app.services.secops_data_tier import federation_data_tier_benchmark, tenant_data_tier_benchmark
from schemas.action_center import ActionCenterDispatchRequest, ActionCenterPolicyUpsertRequest
from schemas.connector_ops import (
    ConnectorCredentialAutoRotateRequest,
    ConnectorCredentialHygienePolicyUpsertRequest,
    ConnectorCredentialHygieneRunRequest,
    ConnectorReliabilityPolicyUpsertRequest,
    ConnectorReliabilityReplayRequest,
    ConnectorCredentialRotateRequest,
    ConnectorCredentialUpsertRequest,
    ConnectorEventIngestRequest,
    ConnectorSlaEvaluateRequest,
    ConnectorSlaProfileUpsertRequest,
)
from schemas.competitive import (
    DetectionAutotunePolicyUpsertRequest,
    DetectionAutotuneRunRequest,
    DetectionCopilotTuneRequest,
    DetectionRuleApplyRequest,
    ExploitPathSimulationRequest,
    RedExploitAutopilotPolicyUpsertRequest,
    RedExploitAutopilotRunRequest,
    ThreatContentPipelinePolicyUpsertRequest,
    ThreatContentPipelineRunRequest,
    PhaseObjectiveCheckRequest,
    ThreatContentPackUpsertRequest,
)
from schemas.soar import (
    SoarPlaybookApprovalRequest,
    SoarPlaybookExecuteRequest,
    SoarPlaybookUpsertRequest,
    TenantPlaybookPolicyUpsertRequest,
)

router = APIRouter(prefix="/competitive", tags=["competitive"])
bearer = HTTPBearer(auto_error=False)

PERM_VIEW = "view"
PERM_POLICY_WRITE = "policy_write"
PERM_APPROVE = "approve"

PERMISSION_SCOPE_MAP: dict[str, list[str]] = {
    PERM_VIEW: ["competitive:read", "control_plane:read", "control_plane:write"],
    PERM_POLICY_WRITE: ["competitive:policy:write", "control_plane:write"],
    PERM_APPROVE: ["competitive:approve", "control_plane:write"],
}


def _verify_bearer_or_raise(credentials: HTTPAuthorizationCredentials | None) -> dict[str, object]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=403, detail="forbidden")
    verification = verify_admin_token(credentials.credentials)
    if not verification.get("valid"):
        raise HTTPException(status_code=403, detail=f"forbidden:{verification.get('reason', 'invalid_token')}")
    return verification


def _has_permission(verified: dict[str, object], permission: str) -> bool:
    scopes = PERMISSION_SCOPE_MAP.get(permission, [])
    return any(token_has_scope(verified, scope) for scope in scopes)


def require_permission(permission: str):
    def _dep(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict[str, object]:
        verified = _verify_bearer_or_raise(credentials)
        if not _has_permission(verified, permission):
            raise HTTPException(status_code=403, detail="forbidden:insufficient_scope")
        return verified

    return _dep


@router.get("/objectives")
def competitive_objectives() -> dict[str, object]:
    return list_roadmap_objectives()


@router.post("/phases/check")
def competitive_phase_scope_check(payload: PhaseObjectiveCheckRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    return create_phase_scope_check(db, payload)


@router.get("/phases/checks")
def competitive_phase_scope_checks(limit: int = 100, db: Session = Depends(get_db)) -> dict[str, object]:
    return list_phase_scope_checks(db, limit=limit)


@router.post("/threat-content/packs")
def competitive_threat_pack_upsert(payload: ThreatContentPackUpsertRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    return upsert_threat_content_pack(db, payload)


@router.get("/threat-content/packs")
def competitive_threat_packs(category: str = "", active_only: bool = True, limit: int = 200, db: Session = Depends(get_db)) -> dict[str, object]:
    return list_threat_content_packs(db, category=category, active_only=active_only, limit=limit)


@router.post("/threat-content/pipeline/policies")
def competitive_threat_content_pipeline_policy_upsert(
    payload: ThreatContentPipelinePolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_threat_content_pipeline_policy(
        db,
        scope=payload.scope,
        min_refresh_interval_minutes=payload.min_refresh_interval_minutes,
        preferred_categories=payload.preferred_categories,
        max_packs_per_run=payload.max_packs_per_run,
        auto_activate=payload.auto_activate,
        route_alert=payload.route_alert,
        enabled=payload.enabled,
        owner=payload.owner,
    )


@router.get("/threat-content/pipeline/policies")
def competitive_threat_content_pipeline_policy(
    scope: str = "global",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_threat_content_pipeline_policy(db, scope=scope)


@router.post("/threat-content/pipeline/run")
def competitive_threat_content_pipeline_run(
    payload: ThreatContentPipelineRunRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_threat_content_pipeline(
        db,
        scope=payload.scope,
        dry_run=payload.dry_run,
        force=payload.force,
        actor=payload.actor,
    )


@router.get("/threat-content/pipeline/runs")
def competitive_threat_content_pipeline_runs(
    scope: str = "",
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_threat_content_pipeline_runs(db, scope=scope, limit=limit)


@router.post("/threat-content/pipeline/scheduler/run")
def competitive_threat_content_pipeline_scheduler(
    limit: int = 200,
    dry_run_override: bool | None = None,
    actor: str = "threat_content_pipeline_ai",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_threat_content_pipeline_scheduler(
        db,
        limit=limit,
        dry_run_override=dry_run_override,
        actor=actor,
    )


@router.get("/threat-content/pipeline/federation")
def competitive_threat_content_pipeline_federation(
    limit: int = 200,
    stale_after_hours: int = 48,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return threat_content_pipeline_federation(
        db,
        limit=limit,
        stale_after_hours=stale_after_hours,
    )


@router.post("/sites/{site_id}/red/exploit-path/simulate")
def competitive_exploit_path_simulate(
    site_id: UUID,
    payload: ExploitPathSimulationRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return run_exploit_path_simulation(db, site_id, payload)


@router.get("/sites/{site_id}/red/exploit-path/runs")
def competitive_exploit_path_runs(site_id: UUID, limit: int = 30, db: Session = Depends(get_db)) -> dict[str, object]:
    return list_exploit_path_runs(db, site_id, limit=limit)


@router.post("/sites/{site_id}/red/exploit-autopilot/policy")
def competitive_red_exploit_autopilot_policy_upsert(
    site_id: UUID,
    payload: RedExploitAutopilotPolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_red_exploit_autopilot_policy(
        db,
        site_id=site_id,
        min_risk_score=payload.min_risk_score,
        min_risk_tier=payload.min_risk_tier,
        preferred_pack_category=payload.preferred_pack_category,
        target_surface=payload.target_surface,
        simulation_depth=payload.simulation_depth,
        max_requests_per_minute=payload.max_requests_per_minute,
        stop_on_critical=payload.stop_on_critical,
        simulation_only=payload.simulation_only,
        auto_run=payload.auto_run,
        route_alert=payload.route_alert,
        schedule_interval_minutes=payload.schedule_interval_minutes,
        enabled=payload.enabled,
        owner=payload.owner,
    )


@router.get("/sites/{site_id}/red/exploit-autopilot/policy")
def competitive_red_exploit_autopilot_policy(
    site_id: UUID,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_red_exploit_autopilot_policy(db, site_id)


@router.post("/sites/{site_id}/red/exploit-autopilot/run")
def competitive_red_exploit_autopilot_run(
    site_id: UUID,
    payload: RedExploitAutopilotRunRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_red_exploit_autopilot(
        db,
        site_id=site_id,
        dry_run=payload.dry_run,
        force=payload.force,
        actor=payload.actor,
    )


@router.get("/sites/{site_id}/red/exploit-autopilot/runs")
def competitive_red_exploit_autopilot_runs(
    site_id: UUID,
    limit: int = 50,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_red_exploit_autopilot_runs(
        db,
        site_id=site_id,
        limit=limit,
    )


@router.post("/red/exploit-autopilot/scheduler/run")
def competitive_red_exploit_autopilot_scheduler(
    limit: int = 200,
    dry_run_override: bool | None = None,
    actor: str = "red_exploit_autopilot_ai",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_red_exploit_autopilot_scheduler(
        db,
        limit=limit,
        dry_run_override=dry_run_override,
        actor=actor,
    )


@router.post("/sites/{site_id}/blue/detection-copilot/tune")
def competitive_detection_copilot_tune(
    site_id: UUID,
    payload: DetectionCopilotTuneRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return run_detection_copilot_tuning(db, site_id, payload)


@router.get("/sites/{site_id}/blue/detection-copilot/rules")
def competitive_detection_copilot_rules(site_id: UUID, limit: int = 100, db: Session = Depends(get_db)) -> dict[str, object]:
    return list_detection_rules(db, site_id, limit=limit)


@router.post("/sites/{site_id}/blue/detection-copilot/rules/{rule_id}/apply")
def competitive_detection_copilot_rule_apply(
    site_id: UUID,
    rule_id: UUID,
    payload: DetectionRuleApplyRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return apply_detection_rule(db, site_id, rule_id, apply=payload.apply)


@router.get("/sites/{site_id}/blue/detection-copilot/runs")
def competitive_detection_copilot_runs(site_id: UUID, limit: int = 30, db: Session = Depends(get_db)) -> dict[str, object]:
    return list_detection_tuning_runs(db, site_id, limit=limit)


@router.post("/sites/{site_id}/blue/detection-autotune/policy")
def competitive_detection_autotune_policy_upsert(
    site_id: UUID,
    payload: DetectionAutotunePolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_detection_autotune_policy(
        db,
        site_id=site_id,
        min_risk_score=payload.min_risk_score,
        min_risk_tier=payload.min_risk_tier,
        target_detection_coverage_pct=payload.target_detection_coverage_pct,
        max_rules_per_run=payload.max_rules_per_run,
        auto_apply=payload.auto_apply,
        route_alert=payload.route_alert,
        schedule_interval_minutes=payload.schedule_interval_minutes,
        enabled=payload.enabled,
        owner=payload.owner,
    )


@router.get("/sites/{site_id}/blue/detection-autotune/policy")
def competitive_detection_autotune_policy(
    site_id: UUID,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_detection_autotune_policy(db, site_id)


@router.post("/sites/{site_id}/blue/detection-autotune/run")
def competitive_detection_autotune_run(
    site_id: UUID,
    payload: DetectionAutotuneRunRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_detection_autotune(
        db,
        site_id=site_id,
        dry_run=payload.dry_run,
        force=payload.force,
        actor=payload.actor,
    )


@router.get("/sites/{site_id}/blue/detection-autotune/runs")
def competitive_detection_autotune_runs(
    site_id: UUID,
    limit: int = 50,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_detection_autotune_runs(db, site_id=site_id, limit=limit)


@router.post("/blue/detection-autotune/scheduler/run")
def competitive_detection_autotune_scheduler(
    limit: int = 200,
    dry_run_override: bool | None = None,
    actor: str = "blue_autotune_ai",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_detection_autotune_scheduler(
        db,
        limit=limit,
        dry_run_override=dry_run_override,
        actor=actor,
    )


@router.get("/sites/{site_id}/case-graph")
def competitive_case_graph(site_id: UUID, limit: int = 50, db: Session = Depends(get_db)) -> dict[str, object]:
    return build_unified_case_graph(db, site_id, limit=limit)


@router.post("/soar/playbooks")
def competitive_soar_playbook_upsert(payload: SoarPlaybookUpsertRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    return upsert_playbook(
        db,
        playbook_code=payload.playbook_code,
        title=payload.title,
        category=payload.category,
        description=payload.description,
        version=payload.version,
        scope=payload.scope,
        steps=payload.steps,
        action_policy=payload.action_policy,
        is_active=payload.is_active,
    )


@router.get("/soar/playbooks")
def competitive_soar_playbooks(
    category: str = "",
    scope: str = "",
    active_only: bool = True,
    limit: int = 200,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return list_playbooks(db, category=category, scope=scope, active_only=active_only, limit=limit)


@router.get("/soar/marketplace/overview")
def competitive_soar_marketplace_overview(limit: int = 500, db: Session = Depends(get_db)) -> dict[str, object]:
    return soar_marketplace_overview(db, limit=limit)


@router.post("/soar/policies/playbook")
def competitive_soar_playbook_policy_upsert(
    payload: TenantPlaybookPolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_tenant_playbook_policy(
        db,
        tenant_code=payload.tenant_code,
        policy_version=payload.policy_version,
        owner=payload.owner,
        require_approval_by_scope=payload.require_approval_by_scope,
        require_approval_by_category=payload.require_approval_by_category,
        delegated_approvers=payload.delegated_approvers,
        blocked_playbook_codes=payload.blocked_playbook_codes,
        allow_partner_scope=payload.allow_partner_scope,
        auto_approve_dry_run=payload.auto_approve_dry_run,
    )


@router.get("/soar/policies/playbook")
def competitive_soar_playbook_policy(
    tenant_code: str,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_tenant_playbook_policy(db, tenant_code)


@router.post("/sites/{site_id}/soar/playbooks/{playbook_code}/execute")
def competitive_soar_playbook_execute(
    site_id: UUID,
    playbook_code: str,
    payload: SoarPlaybookExecuteRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return execute_playbook(
        db,
        site_id=site_id,
        playbook_code=playbook_code,
        actor=payload.actor,
        require_approval=payload.require_approval,
        dry_run=payload.dry_run,
        params=payload.params,
    )


@router.get("/sites/{site_id}/soar/executions")
def competitive_soar_executions(site_id: UUID, status: str = "", limit: int = 200, db: Session = Depends(get_db)) -> dict[str, object]:
    return list_playbook_executions(db, site_id=site_id, status=status, limit=limit)


@router.post("/soar/executions/{execution_id}/approve")
def competitive_soar_execution_approve(
    execution_id: UUID,
    payload: SoarPlaybookApprovalRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return approve_playbook_execution(
        db,
        execution_id=execution_id,
        approve=payload.approve,
        approver=payload.approver,
        note=payload.note,
    )


@router.post("/connectors/events")
def competitive_connector_event_ingest(payload: ConnectorEventIngestRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    return ingest_connector_event(
        db,
        connector_source=payload.connector_source,
        event_type=payload.event_type,
        status=payload.status,
        tenant_id=payload.tenant_id,
        site_id=payload.site_id,
        latency_ms=payload.latency_ms,
        attempt=payload.attempt,
        payload=payload.payload,
        error_message=payload.error_message,
    )


@router.get("/connectors/events")
def competitive_connector_events(
    connector_source: str = "",
    status: str = "",
    tenant_id: UUID | None = None,
    site_id: UUID | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return list_connector_events(
        db,
        connector_source=connector_source,
        status=status,
        tenant_id=tenant_id,
        site_id=site_id,
        limit=limit,
    )


@router.get("/connectors/health")
def competitive_connector_health(limit: int = 2000, db: Session = Depends(get_db)) -> dict[str, object]:
    return connector_health_snapshot(db, limit=limit)


@router.post("/connectors/reliability/policies")
def competitive_connector_reliability_policy_upsert(
    payload: ConnectorReliabilityPolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_connector_reliability_policy(
        db,
        tenant_code=payload.tenant_code,
        connector_source=payload.connector_source,
        max_replay_per_run=payload.max_replay_per_run,
        max_attempts=payload.max_attempts,
        auto_replay_enabled=payload.auto_replay_enabled,
        route_alert=payload.route_alert,
        schedule_interval_minutes=payload.schedule_interval_minutes,
        enabled=payload.enabled,
        owner=payload.owner,
    )


@router.get("/connectors/reliability/policies")
def competitive_connector_reliability_policy_get(
    tenant_code: str,
    connector_source: str = "*",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_connector_reliability_policy(
        db,
        tenant_code=tenant_code,
        connector_source=connector_source,
    )


@router.get("/connectors/reliability/backlog")
def competitive_connector_reliability_backlog(
    tenant_code: str,
    connector_source: str = "",
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_connector_dead_letter_backlog(
        db,
        tenant_code=tenant_code,
        connector_source=connector_source,
        limit=limit,
    )


@router.post("/connectors/reliability/replay")
def competitive_connector_reliability_replay(
    payload: ConnectorReliabilityReplayRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_connector_dead_letter_replay(
        db,
        tenant_code=payload.tenant_code,
        connector_source=payload.connector_source,
        dry_run=payload.dry_run,
        actor=payload.actor,
    )


@router.get("/connectors/reliability/runs")
def competitive_connector_reliability_runs(
    tenant_code: str = "",
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_connector_reliability_runs(db, tenant_code=tenant_code, limit=limit)


@router.post("/connectors/reliability/scheduler/run")
def competitive_connector_reliability_scheduler_run(
    limit: int = 200,
    dry_run_override: bool | None = None,
    actor: str = "connector_replay_ai",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_connector_replay_scheduler(
        db,
        limit=limit,
        dry_run_override=dry_run_override,
        actor=actor,
    )


@router.get("/connectors/reliability/federation")
def competitive_connector_reliability_federation(
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return connector_reliability_federation(db, limit=limit)


@router.post("/connectors/credentials")
def competitive_connector_credential_upsert(
    payload: ConnectorCredentialUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_connector_credential(
        db,
        tenant_code=payload.tenant_code,
        connector_source=payload.connector_source,
        credential_name=payload.credential_name,
        secret_value=payload.secret_value,
        rotation_interval_days=payload.rotation_interval_days,
        external_ref=payload.external_ref,
        expires_at=payload.expires_at,
        metadata=payload.metadata,
        actor=payload.actor,
    )


@router.get("/connectors/credentials")
def competitive_connector_credential_list(
    tenant_code: str,
    connector_source: str = "",
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_connector_credentials(
        db,
        tenant_code=tenant_code,
        connector_source=connector_source,
        limit=limit,
    )


@router.post("/connectors/credentials/rotate")
def competitive_connector_credential_rotate(
    payload: ConnectorCredentialRotateRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return rotate_connector_credential(
        db,
        tenant_code=payload.tenant_code,
        connector_source=payload.connector_source,
        credential_name=payload.credential_name,
        new_secret_value=payload.new_secret_value,
        rotation_reason=payload.rotation_reason,
        actor=payload.actor,
    )


@router.get("/connectors/credentials/rotation-events")
def competitive_connector_credential_rotation_events(
    tenant_code: str,
    connector_source: str = "",
    credential_name: str = "",
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_connector_rotation_events(
        db,
        tenant_code=tenant_code,
        connector_source=connector_source,
        credential_name=credential_name,
        limit=limit,
    )


@router.get("/connectors/credentials/rotation-verify")
def competitive_connector_credential_rotation_verify(
    tenant_code: str,
    connector_source: str = "",
    credential_name: str = "",
    limit: int = 5000,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return verify_connector_rotation_chain(
        db,
        tenant_code=tenant_code,
        connector_source=connector_source,
        credential_name=credential_name,
        limit=limit,
    )


@router.get("/connectors/credentials/hygiene")
def competitive_connector_credential_hygiene(
    tenant_code: str,
    connector_source: str = "",
    warning_days: int = 7,
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return evaluate_connector_credential_hygiene(
        db,
        tenant_code=tenant_code,
        connector_source=connector_source,
        warning_days=warning_days,
        limit=limit,
    )


@router.post("/connectors/credentials/auto-rotate")
def competitive_connector_credential_auto_rotate(
    payload: ConnectorCredentialAutoRotateRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    result = auto_rotate_due_credentials(
        db,
        tenant_code=payload.tenant_code,
        connector_source=payload.connector_source,
        warning_days=payload.warning_days,
        max_rotate=payload.max_rotate,
        dry_run=payload.dry_run,
        actor=payload.actor,
    )
    if result.get("status") != "ok":
        return result

    hygiene = evaluate_connector_credential_hygiene(
        db,
        tenant_code=payload.tenant_code,
        connector_source=payload.connector_source,
        warning_days=payload.warning_days,
        limit=2000,
    )
    result["hygiene"] = hygiene

    should_route = bool(payload.route_alert) and (
        int(result.get("candidate_count", 0)) > 0
        or int(result.get("executed_count", 0)) > 0
        or int(result.get("failed_count", 0)) > 0
    )
    if should_route:
        risk_tier = str((hygiene.get("risk", {}) or {}).get("risk_tier", "medium"))
        severity = "critical" if risk_tier == "critical" else ("high" if risk_tier in {"high", "medium"} else "medium")
        dispatch = dispatch_manual_alert(
            db,
            tenant_code=payload.tenant_code,
            site_code="",
            source="connector_credential_hygiene",
            severity=severity,
            title="Connector Credential Hygiene Auto-Rotation",
            message=(
                f"tenant={payload.tenant_code} dry_run={payload.dry_run} "
                f"candidate={result.get('candidate_count', 0)} executed={result.get('executed_count', 0)} "
                f"failed={result.get('failed_count', 0)}"
            ),
            payload={
                "tenant_code": payload.tenant_code,
                "connector_source": payload.connector_source,
                "risk_tier": risk_tier,
                "candidate_count": result.get("candidate_count", 0),
                "executed_count": result.get("executed_count", 0),
                "failed_count": result.get("failed_count", 0),
                "dry_run": bool(payload.dry_run),
            },
        )
        result["alert"] = dispatch
    return result


@router.get("/connectors/credentials/hygiene/federation")
def competitive_connector_credential_hygiene_federation(
    warning_days: int = 7,
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return federation_connector_credential_hygiene(
        db,
        limit=limit,
        warning_days=warning_days,
    )


@router.post("/connectors/credentials/hygiene/policies")
def competitive_connector_credential_hygiene_policy_upsert(
    payload: ConnectorCredentialHygienePolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_credential_hygiene_policy(
        db,
        tenant_code=payload.tenant_code,
        connector_source=payload.connector_source,
        warning_days=payload.warning_days,
        max_rotate_per_run=payload.max_rotate_per_run,
        auto_apply=payload.auto_apply,
        route_alert=payload.route_alert,
        schedule_interval_minutes=payload.schedule_interval_minutes,
        enabled=payload.enabled,
        owner=payload.owner,
    )


@router.get("/connectors/credentials/hygiene/policies")
def competitive_connector_credential_hygiene_policy_get(
    tenant_code: str,
    connector_source: str = "*",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_credential_hygiene_policy(
        db,
        tenant_code=tenant_code,
        connector_source=connector_source,
    )


@router.post("/connectors/credentials/hygiene/run")
def competitive_connector_credential_hygiene_run(
    payload: ConnectorCredentialHygieneRunRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_credential_hygiene_for_tenant(
        db,
        tenant_code=payload.tenant_code,
        connector_source=payload.connector_source,
        dry_run=payload.dry_run,
        actor=payload.actor,
    )


@router.get("/connectors/credentials/hygiene/runs")
def competitive_connector_credential_hygiene_runs(
    tenant_code: str = "",
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_credential_hygiene_runs(
        db,
        tenant_code=tenant_code,
        limit=limit,
    )


@router.post("/connectors/credentials/hygiene/scheduler/run")
def competitive_connector_credential_hygiene_scheduler_run(
    limit: int = 200,
    dry_run_override: bool | None = None,
    actor: str = "credential_guard_ai",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_credential_hygiene_scheduler(
        db,
        limit=limit,
        dry_run_override=dry_run_override,
        actor=actor,
    )


@router.get("/federation/action-center-sla")
def competitive_action_center_sla_federation(
    lookback_hours: int = 24,
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return action_center_sla_federation_snapshot(db, lookback_hours=lookback_hours, limit=limit)


@router.get("/secops/data-tier/benchmark")
def competitive_secops_data_tier_benchmark(
    tenant_code: str,
    lookback_hours: int = 24,
    sample_limit: int = 2000,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return tenant_data_tier_benchmark(
        db,
        tenant_code=tenant_code,
        lookback_hours=lookback_hours,
        sample_limit=sample_limit,
    )


@router.get("/secops/data-tier/federation")
def competitive_secops_data_tier_federation(
    lookback_hours: int = 24,
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return federation_data_tier_benchmark(
        db,
        lookback_hours=lookback_hours,
        limit=limit,
    )


@router.post("/connectors/sla/profiles")
def competitive_connector_sla_profile_upsert(
    payload: ConnectorSlaProfileUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_connector_sla_profile(
        db,
        tenant_code=payload.tenant_code,
        connector_source=payload.connector_source,
        min_events=payload.min_events,
        min_success_rate=payload.min_success_rate,
        max_dead_letter_count=payload.max_dead_letter_count,
        max_average_latency_ms=payload.max_average_latency_ms,
        notify_on_breach=payload.notify_on_breach,
        enabled=payload.enabled,
    )


@router.get("/connectors/sla/profiles")
def competitive_connector_sla_profile(
    tenant_code: str,
    connector_source: str = "*",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_connector_sla_profile(db, tenant_code, connector_source)


@router.post("/connectors/sla/evaluate")
def competitive_connector_sla_evaluate(
    payload: ConnectorSlaEvaluateRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return evaluate_connector_sla(
        db,
        tenant_code=payload.tenant_code,
        connector_source=payload.connector_source,
        lookback_limit=payload.lookback_limit,
        route_alert_on_breach=payload.route_alert,
    )


@router.get("/connectors/sla/breaches")
def competitive_connector_sla_breach_list(
    tenant_code: str,
    connector_source: str = "",
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_connector_sla_breaches(
        db,
        tenant_code=tenant_code,
        connector_source=connector_source,
        limit=limit,
    )


@router.post("/action-center/policies")
def competitive_action_center_policy_upsert(
    payload: ActionCenterPolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_action_center_policy(
        db,
        tenant_code=payload.tenant_code,
        policy_version=payload.policy_version,
        owner=payload.owner,
        telegram_enabled=payload.telegram_enabled,
        line_enabled=payload.line_enabled,
        min_severity=payload.min_severity,
        routing_tags=payload.routing_tags,
    )


@router.get("/action-center/policies")
def competitive_action_center_policy(
    tenant_code: str,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_action_center_policy(db, tenant_code)


@router.post("/action-center/dispatch")
def competitive_action_center_dispatch(
    payload: ActionCenterDispatchRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return dispatch_manual_alert(
        db,
        tenant_code=payload.tenant_code,
        site_code=payload.site_code,
        source=payload.source,
        severity=payload.severity,
        title=payload.title,
        message=payload.message,
        payload=payload.payload,
    )


@router.get("/action-center/events")
def competitive_action_center_events(
    tenant_code: str = "",
    severity: str = "",
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_action_center_events(db, tenant_code=tenant_code, severity=severity, limit=limit)


@router.get("/auth/context")
def competitive_auth_context(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict[str, object]:
    if credentials is None:
        return {
            "authenticated": False,
            "actor": "",
            "scopes": [],
            "roles": ["viewer"],
            "permissions": {
                "can_view": False,
                "can_edit_policy": False,
                "can_approve": False,
            },
        }
    verified = _verify_bearer_or_raise(credentials)
    can_view = _has_permission(verified, PERM_VIEW)
    can_edit_policy = _has_permission(verified, PERM_POLICY_WRITE)
    can_approve = _has_permission(verified, PERM_APPROVE)
    roles: list[str] = []
    if can_view:
        roles.append("viewer")
    if can_edit_policy:
        roles.append("policy_editor")
    if can_approve:
        roles.append("approver")
    if not roles:
        roles = ["none"]
    return {
        "authenticated": True,
        "actor": str(verified.get("actor", "")),
        "scopes": verified.get("scopes", []),
        "roles": roles,
        "permissions": {
            "can_view": can_view,
            "can_edit_policy": can_edit_policy,
            "can_approve": can_approve,
        },
    }
