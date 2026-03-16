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
from app.services.coworker_plugins import (
    list_coworker_plugins,
    list_site_coworker_plugin_runs,
    list_site_coworker_plugins,
    run_coworker_plugin_scheduler,
    run_site_coworker_plugin,
    upsert_site_coworker_plugin_binding,
)
from app.services.embedded_workflows import (
    embedded_automation_federation_snapshot,
    list_site_embedded_activation_bundles,
    list_site_embedded_invoke_packs,
    verify_site_embedded_automation_packs,
    list_site_embedded_workflow_endpoints,
    list_site_embedded_workflow_invocations,
    upsert_site_embedded_workflow_endpoint,
)
from app.services.coworker_delivery import (
    coworker_delivery_escalation_federation_snapshot,
    dispatch_site_coworker_delivery,
    get_site_coworker_delivery_escalation_policy,
    get_site_coworker_delivery_sla,
    list_site_coworker_delivery_events,
    list_site_coworker_delivery_profiles,
    preview_site_coworker_delivery,
    review_site_coworker_delivery_event,
    run_coworker_delivery_escalation_scheduler,
    run_site_coworker_delivery_escalation,
    upsert_site_coworker_delivery_escalation_policy,
    upsert_site_coworker_delivery_profile,
)
from app.services.red_exploit_autopilot import (
    get_red_exploit_autopilot_policy,
    list_red_exploit_autopilot_runs,
    run_red_exploit_autopilot,
    run_red_exploit_autopilot_scheduler,
    upsert_red_exploit_autopilot_policy,
)
from app.services.red_shadow_pentest import (
    get_red_shadow_pentest_pack_validation,
    get_red_shadow_pentest_policy,
    list_red_shadow_pentest_assets,
    list_red_shadow_pentest_runs,
    run_red_shadow_pentest,
    run_red_shadow_pentest_scheduler,
    trigger_red_shadow_pentest_deploy_event,
    upsert_red_shadow_pentest_policy,
)
from app.services.red_social_engineering import (
    get_social_campaign_telemetry,
    get_social_engineering_policy,
    ingest_social_provider_callback,
    import_social_roster,
    kill_social_campaign,
    list_social_template_packs,
    list_social_engineering_runs,
    list_social_roster,
    review_social_campaign,
    run_social_engineering_simulator,
    upsert_social_engineering_policy,
)
from app.services.red_vulnerability_validator import (
    export_vulnerability_remediation,
    import_vulnerability_findings,
    list_vulnerability_findings,
    list_vulnerability_validation_runs,
    run_vulnerability_auto_validator,
)
from app.services.red_plugin_intelligence import (
    export_red_plugin_output,
    get_red_plugin_safety_policy,
    import_red_plugin_intelligence,
    lint_red_plugin_output,
    list_red_plugin_intelligence,
    list_red_plugin_sync_runs,
    list_red_plugin_sync_sources,
    publish_red_template_to_threat_pack,
    run_red_plugin_sync_scheduler,
    sync_red_plugin_intelligence_source,
    upsert_red_plugin_sync_source,
    upsert_red_plugin_safety_policy,
)
from app.services.blue_log_refiner import (
    get_blue_log_refiner_schedule_policy,
    ingest_blue_log_refiner_callback,
    list_blue_log_refiner_callbacks,
    get_blue_log_refiner_policy,
    list_blue_log_refiner_feedback,
    list_blue_log_refiner_runs,
    list_log_refiner_mapping_packs,
    process_blue_log_refiner_schedules,
    run_blue_log_refiner,
    run_blue_log_refiner_scheduler,
    submit_blue_log_refiner_feedback,
    upsert_blue_log_refiner_policy,
    upsert_blue_log_refiner_schedule_policy,
)
from app.services.blue_managed_responder import (
    get_managed_responder_policy,
    ingest_managed_responder_callback,
    list_managed_responder_callbacks,
    list_managed_responder_runs,
    list_managed_responder_vendor_packs,
    review_managed_responder_run,
    rollback_managed_responder_run,
    run_managed_responder,
    run_managed_responder_scheduler,
    verify_managed_responder_evidence_chain,
    upsert_managed_responder_policy,
)
from app.services.blue_threat_localizer import (
    get_threat_localizer_policy,
    import_threat_feed_adapter_payload,
    import_threat_feed_items,
    list_threat_feed_items,
    list_threat_feed_adapter_templates,
    list_threat_localizer_runs,
    list_threat_sector_profiles,
    process_blue_threat_localizer_schedules,
    run_threat_intelligence_localizer,
    run_threat_localizer_scheduler,
    upsert_threat_localizer_policy,
)
from app.services.blue_threat_localizer_promotion import (
    get_blue_threat_localizer_routing_policy,
    list_blue_threat_localizer_promotion_runs,
    promote_blue_threat_localizer_gap,
    upsert_blue_threat_localizer_routing_policy,
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
    ingest_playbook_connector_result,
    install_marketplace_pack,
    list_connector_result_contracts,
    list_playbook_connector_results,
    list_marketplace_packs,
    list_playbook_executions,
    list_playbooks,
    soar_marketplace_overview,
    upsert_tenant_playbook_policy,
    upsert_playbook,
    verify_playbook_execution,
)
from app.services.secops_data_tier import federation_data_tier_benchmark, tenant_data_tier_benchmark
from app.services.purple_roi_dashboard import (
    build_purple_roi_portfolio_rollup,
    export_purple_roi_board_pack,
    generate_purple_roi_dashboard,
    list_purple_roi_template_packs,
    list_purple_roi_snapshots,
    list_purple_roi_trends,
)
from app.services.purple_plugin_exports import (
    export_purple_incident_report,
    export_purple_mitre_heatmap,
    export_purple_regulated_report,
    list_purple_export_template_packs,
    list_purple_report_releases,
    request_purple_report_release,
    review_purple_report_release,
)
from app.services.purple_control_mapping import build_purple_control_family_map, export_purple_control_family_map
from app.services.purple_attack_layer_workflows import (
    export_live_purple_attack_layer_graphic,
    export_purple_attack_layer_workspace,
    import_purple_attack_layer_workspace,
    list_purple_attack_layer_workspaces,
    update_purple_attack_layer_workspace,
)
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
    BlueLogRefinerCallbackIngestRequest,
    BlueLogRefinerFeedbackRequest,
    BlueLogRefinerPolicyUpsertRequest,
    BlueLogRefinerRunRequest,
    BlueLogRefinerSchedulePolicyUpsertRequest,
    BlueThreatLocalizerPromotionRequest,
    BlueThreatLocalizerRoutingPolicyUpsertRequest,
    BlueThreatLocalizerRunRequest,
    BlueThreatFeedAdapterImportRequest,
    BlueManagedResponderCallbackIngestRequest,
    BlueManagedResponderReviewRequest,
    BlueManagedResponderRollbackRequest,
    BlueManagedResponderPolicyUpsertRequest,
    BlueManagedResponderRunRequest,
    BlueThreatFeedImportRequest,
    BlueThreatLocalizerPolicyUpsertRequest,
    DetectionAutotunePolicyUpsertRequest,
    DetectionAutotuneRunRequest,
    DetectionCopilotTuneRequest,
    DetectionRuleApplyRequest,
    ExploitPathSimulationRequest,
    RedExploitAutopilotPolicyUpsertRequest,
    RedExploitAutopilotRunRequest,
    RedShadowPentestPolicyUpsertRequest,
    RedShadowPentestDeployEventRequest,
    RedShadowPentestRunRequest,
    RedSocialCampaignKillRequest,
    RedSocialCampaignPolicyUpsertRequest,
    RedSocialProviderCallbackRequest,
    RedSocialCampaignReviewRequest,
    RedSocialRosterImportRequest,
    RedSocialEngineeringRunRequest,
    RedPluginExportRequest,
    RedPluginIntelligenceImportRequest,
    RedPluginLintRequest,
    RedPluginPublishThreatPackRequest,
    RedPluginSafetyPolicyUpsertRequest,
    RedPluginSyncRunRequest,
    RedPluginSyncSourceUpsertRequest,
    RedVulnerabilityFindingImportRequest,
    RedVulnerabilityValidatorRunRequest,
    SiteEmbeddedWorkflowEndpointUpsertRequest,
    SiteCoworkerDeliveryDispatchRequest,
    SiteCoworkerDeliveryEscalationPolicyUpsertRequest,
    SiteCoworkerDeliveryEscalationRunRequest,
    SiteCoworkerDeliveryPreviewRequest,
    SiteCoworkerDeliveryProfileUpsertRequest,
    SiteCoworkerDeliveryReviewRequest,
    SiteCoworkerPluginBindingUpsertRequest,
    SiteCoworkerPluginRunRequest,
    ThreatContentPipelinePolicyUpsertRequest,
    ThreatContentPipelineRunRequest,
    PhaseObjectiveCheckRequest,
    PurpleAttackLayerExportRequest,
    PurpleAttackLayerImportRequest,
    PurpleAttackLayerUpdateRequest,
    PurpleControlFamilyMapExportRequest,
    PurpleIncidentReportExportRequest,
    PurpleMitreHeatmapExportRequest,
    PurpleReportReleaseRequest,
    PurpleReportReleaseReviewRequest,
    PurpleRegulatedReportExportRequest,
    PurpleRoiDashboardRequest,
    PurpleRoiDashboardExportRequest,
    ThreatContentPackUpsertRequest,
)
from schemas.soar import (
    SoarConnectorResultCallbackRequest,
    SoarPlaybookApprovalRequest,
    SoarPlaybookExecuteRequest,
    SoarMarketplacePackInstallRequest,
    SoarPlaybookUpsertRequest,
    SoarPlaybookVerificationRequest,
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


@router.get("/coworker/plugins")
def competitive_coworker_plugins(
    category: str = "",
    active_only: bool = True,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_coworker_plugins(db, category=category, active_only=active_only)


@router.get("/sites/{site_id}/coworker/plugins")
def competitive_site_coworker_plugins(
    site_id: UUID,
    category: str = "",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_site_coworker_plugins(db, site_id=site_id, category=category)


@router.post("/sites/{site_id}/coworker/plugins/bindings")
def competitive_site_coworker_plugin_binding_upsert(
    site_id: UUID,
    payload: SiteCoworkerPluginBindingUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_site_coworker_plugin_binding(
        db,
        site_id=site_id,
        plugin_code=payload.plugin_code,
        enabled=payload.enabled,
        auto_run=payload.auto_run,
        schedule_interval_minutes=payload.schedule_interval_minutes,
        notify_channels=payload.notify_channels,
        config=payload.config,
        owner=payload.owner,
    )


@router.post("/sites/{site_id}/coworker/plugins/{plugin_code}/run")
def competitive_site_coworker_plugin_run(
    site_id: UUID,
    plugin_code: str,
    payload: SiteCoworkerPluginRunRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_site_coworker_plugin(
        db,
        site_id=site_id,
        plugin_code=plugin_code,
        dry_run=payload.dry_run,
        force=payload.force,
        actor=payload.actor,
    )


@router.get("/sites/{site_id}/embedded/endpoints")
def competitive_site_embedded_workflow_endpoints(
    site_id: UUID,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_site_embedded_workflow_endpoints(db, site_id=site_id, limit=limit)


@router.post("/sites/{site_id}/embedded/endpoints")
def competitive_site_embedded_workflow_endpoint_upsert(
    site_id: UUID,
    payload: SiteEmbeddedWorkflowEndpointUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_site_embedded_workflow_endpoint(
        db,
        site_id=site_id,
        endpoint_code=payload.endpoint_code,
        workflow_type=payload.workflow_type,
        plugin_code=payload.plugin_code,
        connector_source=payload.connector_source,
        default_event_kind=payload.default_event_kind,
        enabled=payload.enabled,
        dry_run_default=payload.dry_run_default,
        config=payload.config,
        owner=payload.owner,
        rotate_secret=payload.rotate_secret,
    )


@router.get("/sites/{site_id}/embedded/invocations")
def competitive_site_embedded_workflow_invocations(
    site_id: UUID,
    endpoint_code: str = "",
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_site_embedded_workflow_invocations(db, site_id=site_id, endpoint_code=endpoint_code, limit=limit)


@router.get("/sites/{site_id}/embedded/invoke-packs")
def competitive_site_embedded_invoke_packs(
    site_id: UUID,
    endpoint_code: str = "",
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_site_embedded_invoke_packs(db, site_id=site_id, endpoint_code=endpoint_code, limit=limit)


@router.get("/sites/{site_id}/embedded/automation-verify")
def competitive_site_embedded_automation_verify(
    site_id: UUID,
    endpoint_code: str = "",
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return verify_site_embedded_automation_packs(db, site_id=site_id, endpoint_code=endpoint_code, limit=limit)


@router.get("/sites/{site_id}/embedded/activation-bundles")
def competitive_site_embedded_activation_bundles(
    site_id: UUID,
    endpoint_code: str = "",
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_site_embedded_activation_bundles(db, site_id=site_id, endpoint_code=endpoint_code, limit=limit)


@router.get("/embedded/federation/readiness")
def competitive_embedded_federation_readiness(
    connector_source: str = "",
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return embedded_automation_federation_snapshot(
        db,
        connector_source=connector_source,
        limit=limit,
    )


@router.get("/sites/{site_id}/coworker/plugins/runs")
def competitive_site_coworker_plugin_runs(
    site_id: UUID,
    category: str = "",
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_site_coworker_plugin_runs(
        db,
        site_id=site_id,
        category=category,
        limit=limit,
    )


@router.post("/coworker/plugins/scheduler/run")
def competitive_coworker_plugin_scheduler(
    limit: int = 200,
    dry_run_override: bool | None = None,
    actor: str = "coworker_plugin_ai",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_coworker_plugin_scheduler(
        db,
        limit=limit,
        dry_run_override=dry_run_override,
        actor=actor,
    )


@router.get("/sites/{site_id}/coworker/delivery/profiles")
def competitive_site_coworker_delivery_profiles(
    site_id: UUID,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_site_coworker_delivery_profiles(db, site_id=site_id)


@router.post("/sites/{site_id}/coworker/delivery/profiles")
def competitive_site_coworker_delivery_profile_upsert(
    site_id: UUID,
    payload: SiteCoworkerDeliveryProfileUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_site_coworker_delivery_profile(
        db,
        site_id=site_id,
        channel=payload.channel,
        enabled=payload.enabled,
        min_severity=payload.min_severity,
        delivery_mode=payload.delivery_mode,
        require_approval=payload.require_approval,
        include_thai_summary=payload.include_thai_summary,
        webhook_url=payload.webhook_url,
        owner=payload.owner,
    )


@router.post("/sites/{site_id}/coworker/delivery/{plugin_code}/preview")
def competitive_site_coworker_delivery_preview(
    site_id: UUID,
    plugin_code: str,
    payload: SiteCoworkerDeliveryPreviewRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return preview_site_coworker_delivery(
        db,
        site_id=site_id,
        plugin_code=plugin_code,
        channel=payload.channel,
    )


@router.post("/sites/{site_id}/coworker/delivery/{plugin_code}/dispatch")
def competitive_site_coworker_delivery_dispatch(
    site_id: UUID,
    plugin_code: str,
    payload: SiteCoworkerDeliveryDispatchRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return dispatch_site_coworker_delivery(
        db,
        site_id=site_id,
        plugin_code=plugin_code,
        channel=payload.channel,
        dry_run=payload.dry_run,
        force=payload.force,
        actor=payload.actor,
    )


@router.post("/sites/{site_id}/coworker/delivery/events/{event_id}/review")
def competitive_site_coworker_delivery_review(
    site_id: UUID,
    event_id: UUID,
    payload: SiteCoworkerDeliveryReviewRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return review_site_coworker_delivery_event(
        db,
        site_id=site_id,
        event_id=event_id,
        approve=payload.approve,
        actor=payload.actor,
        note=payload.note,
    )


@router.get("/sites/{site_id}/coworker/delivery/events")
def competitive_site_coworker_delivery_events(
    site_id: UUID,
    channel: str = "",
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_site_coworker_delivery_events(
        db,
        site_id=site_id,
        channel=channel,
        limit=limit,
    )


@router.get("/sites/{site_id}/coworker/delivery/sla")
def competitive_site_coworker_delivery_sla(
    site_id: UUID,
    limit: int = 100,
    approval_sla_minutes: int | None = None,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_site_coworker_delivery_sla(
        db,
        site_id=site_id,
        limit=limit,
        approval_sla_minutes=approval_sla_minutes,
    )


@router.get("/sites/{site_id}/coworker/delivery/escalation-policy")
def competitive_site_coworker_delivery_escalation_policy(
    site_id: UUID,
    plugin_code: str,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_site_coworker_delivery_escalation_policy(
        db,
        site_id=site_id,
        plugin_code=plugin_code,
    )


@router.post("/sites/{site_id}/coworker/delivery/escalation-policy")
def competitive_site_coworker_delivery_escalation_policy_upsert(
    site_id: UUID,
    payload: SiteCoworkerDeliveryEscalationPolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_site_coworker_delivery_escalation_policy(
        db,
        site_id=site_id,
        plugin_code=payload.plugin_code,
        enabled=payload.enabled,
        escalate_after_minutes=payload.escalate_after_minutes,
        max_escalation_count=payload.max_escalation_count,
        fallback_channels=payload.fallback_channels,
        escalate_on_statuses=payload.escalate_on_statuses,
        owner=payload.owner,
    )


@router.post("/sites/{site_id}/coworker/delivery/escalation/run")
def competitive_site_coworker_delivery_escalation_run(
    site_id: UUID,
    payload: SiteCoworkerDeliveryEscalationRunRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_site_coworker_delivery_escalation(
        db,
        site_id=site_id,
        plugin_code=payload.plugin_code,
        dry_run=payload.dry_run,
        force=payload.force,
        actor=payload.actor,
    )


@router.post("/coworker/delivery/escalation/scheduler/run")
def competitive_coworker_delivery_escalation_scheduler_run(
    site_id: UUID | None = None,
    plugin_code: str = "",
    limit: int = 100,
    dry_run_override: bool | None = None,
    actor: str = "delivery_escalator_scheduler",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_coworker_delivery_escalation_scheduler(
        db,
        site_id=site_id,
        plugin_code=plugin_code,
        limit=limit,
        dry_run_override=dry_run_override,
        actor=actor,
    )


@router.get("/coworker/delivery/escalation/federation")
def competitive_coworker_delivery_escalation_federation(
    plugin_code: str = "",
    approval_sla_minutes: int | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return coworker_delivery_escalation_federation_snapshot(
        db,
        plugin_code=plugin_code,
        approval_sla_minutes=approval_sla_minutes,
        limit=limit,
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


@router.post("/sites/{site_id}/red/shadow-pentest/policy")
def competitive_red_shadow_pentest_policy_upsert(
    site_id: UUID,
    payload: RedShadowPentestPolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_red_shadow_pentest_policy(
        db,
        site_id=site_id,
        crawl_depth=payload.crawl_depth,
        max_pages=payload.max_pages,
        change_threshold=payload.change_threshold,
        schedule_interval_minutes=payload.schedule_interval_minutes,
        auto_assign_zero_day_pack=payload.auto_assign_zero_day_pack,
        route_alert=payload.route_alert,
        enabled=payload.enabled,
        owner=payload.owner,
    )


@router.get("/sites/{site_id}/red/shadow-pentest/policy")
def competitive_red_shadow_pentest_policy(
    site_id: UUID,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_red_shadow_pentest_policy(db, site_id)


@router.post("/sites/{site_id}/red/shadow-pentest/run")
def competitive_red_shadow_pentest_run(
    site_id: UUID,
    payload: RedShadowPentestRunRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_red_shadow_pentest(
        db,
        site_id=site_id,
        dry_run=payload.dry_run,
        force=payload.force,
        actor=payload.actor,
    )


@router.get("/sites/{site_id}/red/shadow-pentest/runs")
def competitive_red_shadow_pentest_runs(
    site_id: UUID,
    limit: int = 30,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_red_shadow_pentest_runs(db, site_id=site_id, limit=limit)


@router.get("/sites/{site_id}/red/shadow-pentest/assets")
def competitive_red_shadow_pentest_assets(
    site_id: UUID,
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_red_shadow_pentest_assets(db, site_id=site_id, limit=limit)


@router.get("/sites/{site_id}/red/shadow-pentest/pack-validation")
def competitive_red_shadow_pentest_pack_validation(
    site_id: UUID,
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_red_shadow_pentest_pack_validation(db, site_id=site_id, limit=limit)


@router.post("/sites/{site_id}/red/shadow-pentest/deploy-event")
def competitive_red_shadow_pentest_deploy_event(
    site_id: UUID,
    payload: RedShadowPentestDeployEventRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return trigger_red_shadow_pentest_deploy_event(
        db,
        site_id=site_id,
        deploy_id=payload.deploy_id,
        release_version=payload.release_version,
        changed_paths=payload.changed_paths,
        actor=payload.actor,
        dry_run_override=payload.dry_run_override,
    )


@router.post("/red/shadow-pentest/scheduler/run")
def competitive_red_shadow_pentest_scheduler(
    limit: int = 100,
    dry_run_override: bool | None = None,
    actor: str = "red_shadow_pentest_ai",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_red_shadow_pentest_scheduler(
        db,
        limit=limit,
        dry_run_override=dry_run_override,
        actor=actor,
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


@router.post("/sites/{site_id}/red/social-simulator/run")
def competitive_red_social_simulator_run(
    site_id: UUID,
    payload: RedSocialEngineeringRunRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_social_engineering_simulator(
        db,
        site_id=site_id,
        campaign_name=payload.campaign_name,
        employee_segment=payload.employee_segment,
        email_count=payload.email_count,
        campaign_type=payload.campaign_type,
        template_pack_code=payload.template_pack_code,
        difficulty=payload.difficulty,
        impersonation_brand=payload.impersonation_brand,
        dry_run=payload.dry_run,
        actor=payload.actor,
    )


@router.post("/sites/{site_id}/red/social-simulator/roster/import")
def competitive_red_social_roster_import(
    site_id: UUID,
    payload: RedSocialRosterImportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return import_social_roster(
        db,
        site_id=site_id,
        entries=payload.entries,
        actor=payload.actor,
    )


@router.get("/sites/{site_id}/red/social-simulator/roster")
def competitive_red_social_roster(
    site_id: UUID,
    active_only: bool = True,
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_social_roster(db, site_id=site_id, active_only=active_only, limit=limit)


@router.get("/red/social-simulator/template-packs")
def competitive_red_social_template_packs(
    campaign_type: str = "",
    jurisdiction: str = "th",
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_social_template_packs(campaign_type=campaign_type, jurisdiction=jurisdiction)


@router.post("/sites/{site_id}/red/social-simulator/policy")
def competitive_red_social_policy_upsert(
    site_id: UUID,
    payload: RedSocialCampaignPolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_social_engineering_policy(
        db,
        site_id=site_id,
        connector_type=payload.connector_type,
        sender_name=payload.sender_name,
        sender_email=payload.sender_email,
        subject_prefix=payload.subject_prefix,
        landing_base_url=payload.landing_base_url,
        report_mailbox=payload.report_mailbox,
        require_approval=payload.require_approval,
        enable_open_tracking=payload.enable_open_tracking,
        enable_click_tracking=payload.enable_click_tracking,
        max_emails_per_run=payload.max_emails_per_run,
        kill_switch_active=payload.kill_switch_active,
        allowed_domains=payload.allowed_domains,
        connector_config=payload.connector_config,
        campaign_type=payload.campaign_type,
        template_pack_code=payload.template_pack_code,
        evidence_retention_days=payload.evidence_retention_days,
        legal_ack_required=payload.legal_ack_required,
        enabled=payload.enabled,
        owner=payload.owner,
    )


@router.get("/sites/{site_id}/red/social-simulator/policy")
def competitive_red_social_policy(
    site_id: UUID,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_social_engineering_policy(db, site_id=site_id)


@router.get("/sites/{site_id}/red/social-simulator/runs")
def competitive_red_social_simulator_runs(
    site_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_social_engineering_runs(db, site_id=site_id, limit=limit)


@router.post("/sites/{site_id}/red/social-simulator/{run_id}/review")
def competitive_red_social_campaign_review(
    site_id: UUID,
    run_id: UUID,
    payload: RedSocialCampaignReviewRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return review_social_campaign(
        db,
        site_id=site_id,
        run_id=run_id,
        approve=payload.approve,
        actor=payload.actor,
        note=payload.note,
    )


@router.post("/sites/{site_id}/red/social-simulator/{run_id}/kill")
def competitive_red_social_campaign_kill(
    site_id: UUID,
    run_id: UUID,
    payload: RedSocialCampaignKillRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return kill_social_campaign(
        db,
        site_id=site_id,
        run_id=run_id,
        actor=payload.actor,
        note=payload.note,
        activate_site_kill_switch=payload.activate_site_kill_switch,
    )


@router.get("/sites/{site_id}/red/social-simulator/telemetry")
def competitive_red_social_telemetry(
    site_id: UUID,
    run_id: UUID | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_social_campaign_telemetry(db, site_id=site_id, run_id=run_id, limit=limit)


@router.post("/sites/{site_id}/red/social-simulator/provider-callback")
def competitive_red_social_provider_callback(
    site_id: UUID,
    payload: RedSocialProviderCallbackRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return ingest_social_provider_callback(
        db,
        site_id=site_id,
        run_id=payload.run_id,
        connector_type=payload.connector_type,
        event_type=payload.event_type,
        recipient_email=payload.recipient_email,
        occurred_at=payload.occurred_at,
        provider_event_id=payload.provider_event_id,
        metadata=payload.metadata,
        actor=payload.actor,
    )


@router.post("/sites/{site_id}/red/vuln-validator/import")
def competitive_red_vulnerability_import(
    site_id: UUID,
    payload: RedVulnerabilityFindingImportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return import_vulnerability_findings(
        db,
        site_id=site_id,
        source_tool=payload.source_tool,
        payload=payload.payload,
        findings=payload.findings,
        actor=payload.actor,
    )


@router.get("/sites/{site_id}/red/vuln-validator/findings")
def competitive_red_vulnerability_findings(
    site_id: UUID,
    source_tool: str = "",
    verdict: str = "",
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_vulnerability_findings(
        db,
        site_id=site_id,
        source_tool=source_tool,
        verdict=verdict,
        limit=limit,
    )


@router.post("/sites/{site_id}/red/vuln-validator/run")
def competitive_red_vulnerability_validator_run(
    site_id: UUID,
    payload: RedVulnerabilityValidatorRunRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_vulnerability_auto_validator(
        db,
        site_id=site_id,
        finding_ids=payload.finding_ids,
        max_findings=payload.max_findings,
        dry_run=payload.dry_run,
        actor=payload.actor,
    )


@router.get("/sites/{site_id}/red/vuln-validator/runs")
def competitive_red_vulnerability_validator_runs(
    site_id: UUID,
    limit: int = 50,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_vulnerability_validation_runs(db, site_id=site_id, limit=limit)


@router.get("/sites/{site_id}/red/vuln-validator/remediation-export")
def competitive_red_vulnerability_remediation_export(
    site_id: UUID,
    source_tool: str = "",
    verdict: str = "",
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return export_vulnerability_remediation(
        db,
        site_id=site_id,
        source_tool=source_tool,
        verdict=verdict,
        limit=limit,
    )


@router.post("/sites/{site_id}/red/plugin-intelligence/import")
def competitive_red_plugin_intelligence_import(
    site_id: UUID,
    payload: RedPluginIntelligenceImportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return import_red_plugin_intelligence(
        db,
        site_id=site_id,
        items=payload.items,
        actor=payload.actor,
    )


@router.get("/sites/{site_id}/red/plugin-intelligence")
def competitive_red_plugin_intelligence_list(
    site_id: UUID,
    source_type: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_red_plugin_intelligence(
        db,
        site_id=site_id,
        source_type=source_type,
        limit=limit,
    )


@router.get("/sites/{site_id}/red/plugin-intelligence/sync-sources")
def competitive_red_plugin_sync_sources(
    site_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_red_plugin_sync_sources(db, site_id=site_id, limit=limit)


@router.post("/sites/{site_id}/red/plugin-intelligence/sync-sources")
def competitive_red_plugin_sync_source_upsert(
    site_id: UUID,
    payload: RedPluginSyncSourceUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_red_plugin_sync_source(
        db,
        site_id=site_id,
        source_name=payload.source_name,
        source_type=payload.source_type,
        source_url=payload.source_url,
        target_type=payload.target_type,
        parser_kind=payload.parser_kind,
        request_headers=payload.request_headers,
        sync_interval_minutes=payload.sync_interval_minutes,
        enabled=payload.enabled,
        owner=payload.owner,
    )


@router.post("/sites/{site_id}/red/plugin-intelligence/sync")
def competitive_red_plugin_sync_run(
    site_id: UUID,
    payload: RedPluginSyncRunRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return sync_red_plugin_intelligence_source(
        db,
        site_id=site_id,
        sync_source_id=payload.sync_source_id,
        dry_run=payload.dry_run,
        actor=payload.actor,
    )


@router.get("/sites/{site_id}/red/plugin-intelligence/sync-runs")
def competitive_red_plugin_sync_runs(
    site_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_red_plugin_sync_runs(db, site_id=site_id, limit=limit)


@router.post("/sites/{site_id}/red/plugin-safety-policy")
def competitive_red_plugin_safety_policy_upsert(
    site_id: UUID,
    payload: RedPluginSafetyPolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_red_plugin_safety_policy(
        db,
        site_id=site_id,
        target_type=payload.target_type,
        max_http_requests_per_run=payload.max_http_requests_per_run,
        max_script_lines=payload.max_script_lines,
        allow_network_calls=payload.allow_network_calls,
        require_comment_header=payload.require_comment_header,
        require_disclaimer=payload.require_disclaimer,
        allowed_modules=payload.allowed_modules,
        blocked_modules=payload.blocked_modules,
        enabled=payload.enabled,
        owner=payload.owner,
    )


@router.get("/sites/{site_id}/red/plugin-safety-policy")
def competitive_red_plugin_safety_policy_get(
    site_id: UUID,
    target_type: str = "web",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_red_plugin_safety_policy(db, site_id=site_id, target_type=target_type)


@router.post("/sites/{site_id}/red/plugins/{plugin_code}/lint")
def competitive_red_plugin_lint(
    site_id: UUID,
    plugin_code: str,
    payload: RedPluginLintRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return lint_red_plugin_output(
        db,
        site_id=site_id,
        plugin_code=plugin_code,
        run_id=payload.run_id,
        content_override=payload.content_override,
    )


@router.post("/sites/{site_id}/red/plugins/{plugin_code}/export")
def competitive_red_plugin_export(
    site_id: UUID,
    plugin_code: str,
    payload: RedPluginExportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return export_red_plugin_output(
        db,
        site_id=site_id,
        plugin_code=plugin_code,
        run_id=payload.run_id,
        export_kind=payload.export_kind,
        title_override=payload.title_override,
    )


@router.post("/red/plugin-intelligence/scheduler/run")
def competitive_red_plugin_sync_scheduler(
    limit: int = 100,
    dry_run_override: bool | None = None,
    actor: str = "dashboard_scheduler",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_red_plugin_sync_scheduler(
        db,
        limit=limit,
        dry_run_override=dry_run_override,
        actor=actor,
    )


@router.post("/sites/{site_id}/red/plugins/red_template_writer/publish-threat-pack")
def competitive_red_plugin_publish_threat_pack(
    site_id: UUID,
    payload: RedPluginPublishThreatPackRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return publish_red_template_to_threat_pack(
        db,
        site_id=site_id,
        run_id=payload.run_id,
        activate=payload.activate,
        actor=payload.actor,
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


@router.post("/sites/{site_id}/blue/threat-localizer/run")
def competitive_blue_threat_localizer_run(
    site_id: UUID,
    payload: BlueThreatLocalizerRunRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_threat_intelligence_localizer(
        db,
        site_id=site_id,
        focus_region=payload.focus_region,
        sector=payload.sector,
        dry_run=payload.dry_run,
        actor=payload.actor,
    )


@router.post("/blue/threat-localizer/feed-items/import")
def competitive_blue_threat_feed_import(
    payload: BlueThreatFeedImportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return import_threat_feed_items(
        db,
        items=payload.items,
        source_name=payload.source_name,
        actor=payload.actor,
    )


@router.post("/blue/threat-localizer/feed-adapters/import")
def competitive_blue_threat_feed_adapter_import(
    payload: BlueThreatFeedAdapterImportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return import_threat_feed_adapter_payload(
        db,
        source=payload.source,
        payload=payload.payload,
        actor=payload.actor,
    )


@router.get("/blue/threat-localizer/feed-items")
def competitive_blue_threat_feed_items(
    focus_region: str = "",
    sector: str = "",
    category: str = "",
    active_only: bool = True,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_threat_feed_items(
        db,
        focus_region=focus_region,
        sector=sector,
        category=category,
        active_only=active_only,
        limit=limit,
    )


@router.get("/blue/threat-localizer/feed-adapters")
def competitive_blue_threat_feed_adapters(
    source: str = "",
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_threat_feed_adapter_templates(source=source)


@router.get("/blue/threat-localizer/sector-profiles")
def competitive_blue_threat_sector_profiles(
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_threat_sector_profiles()


@router.get("/sites/{site_id}/blue/threat-localizer/policy")
def competitive_blue_threat_localizer_policy(
    site_id: UUID,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_threat_localizer_policy(db, site_id=site_id)


@router.post("/sites/{site_id}/blue/threat-localizer/policy")
def competitive_blue_threat_localizer_policy_upsert(
    site_id: UUID,
    payload: BlueThreatLocalizerPolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_threat_localizer_policy(
        db,
        site_id=site_id,
        focus_region=payload.focus_region,
        sector=payload.sector,
        subscribed_categories=payload.subscribed_categories,
        recurring_digest_enabled=payload.recurring_digest_enabled,
        schedule_interval_minutes=payload.schedule_interval_minutes,
        min_feed_priority=payload.min_feed_priority,
        enabled=payload.enabled,
        owner=payload.owner,
    )


@router.get("/sites/{site_id}/blue/threat-localizer/routing-policy")
def competitive_blue_threat_localizer_routing_policy(
    site_id: UUID,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_blue_threat_localizer_routing_policy(db, site_id=site_id)


@router.post("/sites/{site_id}/blue/threat-localizer/routing-policy")
def competitive_blue_threat_localizer_routing_policy_upsert(
    site_id: UUID,
    payload: BlueThreatLocalizerRoutingPolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_blue_threat_localizer_routing_policy(
        db,
        site_id=site_id,
        stakeholder_groups=payload.stakeholder_groups,
        group_channel_map=payload.group_channel_map,
        category_group_map=payload.category_group_map,
        min_priority_score=payload.min_priority_score,
        min_risk_tier=payload.min_risk_tier,
        auto_promote_on_gap=payload.auto_promote_on_gap,
        auto_apply_autotune=payload.auto_apply_autotune,
        dispatch_via_action_center=payload.dispatch_via_action_center,
        playbook_promotion_enabled=payload.playbook_promotion_enabled,
        owner=payload.owner,
    )


@router.get("/sites/{site_id}/blue/threat-localizer/runs")
def competitive_blue_threat_localizer_runs(
    site_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_threat_localizer_runs(db, site_id=site_id, limit=limit)


@router.get("/sites/{site_id}/blue/threat-localizer/promotion-runs")
def competitive_blue_threat_localizer_promotion_runs(
    site_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_blue_threat_localizer_promotion_runs(db, site_id=site_id, limit=limit)


@router.post("/sites/{site_id}/blue/threat-localizer/promote-gap")
def competitive_blue_threat_localizer_promote_gap(
    site_id: UUID,
    payload: BlueThreatLocalizerPromotionRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return promote_blue_threat_localizer_gap(
        db,
        site_id=site_id,
        localizer_run_id=payload.localizer_run_id,
        auto_apply_override=payload.auto_apply_override,
        playbook_promotion_override=payload.playbook_promotion_override,
        actor=payload.actor,
    )


@router.post("/blue/threat-localizer/scheduler/run")
def competitive_blue_threat_localizer_scheduler(
    limit: int = 200,
    dry_run_override: bool | None = None,
    actor: str = "blue_threat_localizer_scheduler_ai",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_threat_localizer_scheduler(
        db,
        limit=limit,
        dry_run_override=dry_run_override,
        actor=actor,
    )


@router.get("/blue/log-refiner/mapping-packs")
def competitive_blue_log_refiner_mapping_packs(
    source: str = "",
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_log_refiner_mapping_packs(source=source)


@router.get("/sites/{site_id}/blue/log-refiner/policy")
def competitive_blue_log_refiner_policy(
    site_id: UUID,
    connector_source: str = "generic",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_blue_log_refiner_policy(db, site_id=site_id, connector_source=connector_source)


@router.get("/sites/{site_id}/blue/log-refiner/schedule-policy")
def competitive_blue_log_refiner_schedule_policy(
    site_id: UUID,
    connector_source: str = "generic",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_blue_log_refiner_schedule_policy(db, site_id=site_id, connector_source=connector_source)


@router.post("/sites/{site_id}/blue/log-refiner/policy")
def competitive_blue_log_refiner_policy_upsert(
    site_id: UUID,
    payload: BlueLogRefinerPolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_blue_log_refiner_policy(
        db,
        site_id=site_id,
        connector_source=payload.connector_source,
        execution_mode=payload.execution_mode,
        lookback_limit=payload.lookback_limit,
        min_keep_severity=payload.min_keep_severity,
        drop_recommendation_codes=payload.drop_recommendation_codes,
        target_noise_reduction_pct=payload.target_noise_reduction_pct,
        average_event_size_kb=payload.average_event_size_kb,
        enabled=payload.enabled,
        owner=payload.owner,
    )


@router.post("/sites/{site_id}/blue/log-refiner/schedule-policy")
def competitive_blue_log_refiner_schedule_policy_upsert(
    site_id: UUID,
    payload: BlueLogRefinerSchedulePolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_blue_log_refiner_schedule_policy(
        db,
        site_id=site_id,
        connector_source=payload.connector_source,
        schedule_interval_minutes=payload.schedule_interval_minutes,
        dry_run_default=payload.dry_run_default,
        callback_ingest_enabled=payload.callback_ingest_enabled,
        enabled=payload.enabled,
        owner=payload.owner,
    )


@router.post("/sites/{site_id}/blue/log-refiner/run")
def competitive_blue_log_refiner_run(
    site_id: UUID,
    payload: BlueLogRefinerRunRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_blue_log_refiner(
        db,
        site_id=site_id,
        connector_source=payload.connector_source,
        dry_run=payload.dry_run,
        actor=payload.actor,
    )


@router.get("/sites/{site_id}/blue/log-refiner/runs")
def competitive_blue_log_refiner_runs(
    site_id: UUID,
    connector_source: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_blue_log_refiner_runs(db, site_id=site_id, connector_source=connector_source, limit=limit)


@router.post("/blue/log-refiner/scheduler/run")
def competitive_blue_log_refiner_scheduler(
    limit: int = 200,
    dry_run_override: bool | None = None,
    actor: str = "blue_log_refiner_scheduler_ai",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_blue_log_refiner_scheduler(
        db,
        limit=limit,
        dry_run_override=dry_run_override,
        actor=actor,
    )


@router.post("/sites/{site_id}/blue/log-refiner/feedback")
def competitive_blue_log_refiner_feedback(
    site_id: UUID,
    payload: BlueLogRefinerFeedbackRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return submit_blue_log_refiner_feedback(
        db,
        site_id=site_id,
        connector_source=payload.connector_source,
        feedback_type=payload.feedback_type,
        event_type=payload.event_type,
        recommendation_code=payload.recommendation_code,
        note=payload.note,
        actor=payload.actor,
        run_id=payload.run_id,
    )


@router.post("/sites/{site_id}/blue/log-refiner/callback")
def competitive_blue_log_refiner_callback(
    site_id: UUID,
    payload: BlueLogRefinerCallbackIngestRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return ingest_blue_log_refiner_callback(
        db,
        site_id=site_id,
        connector_source=payload.connector_source,
        callback_type=payload.callback_type,
        source_system=payload.source_system,
        external_run_ref=payload.external_run_ref,
        webhook_event_id=payload.webhook_event_id,
        run_id=payload.run_id,
        total_events=payload.total_events,
        kept_events=payload.kept_events,
        dropped_events=payload.dropped_events,
        noise_reduction_pct=payload.noise_reduction_pct,
        estimated_storage_saved_kb=payload.estimated_storage_saved_kb,
        status=payload.status,
        payload=payload.payload,
        actor=payload.actor,
    )


@router.get("/sites/{site_id}/blue/log-refiner/feedback")
def competitive_blue_log_refiner_feedback_list(
    site_id: UUID,
    connector_source: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_blue_log_refiner_feedback(db, site_id=site_id, connector_source=connector_source, limit=limit)


@router.get("/sites/{site_id}/blue/log-refiner/callbacks")
def competitive_blue_log_refiner_callback_list(
    site_id: UUID,
    connector_source: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_blue_log_refiner_callbacks(db, site_id=site_id, connector_source=connector_source, limit=limit)


@router.get("/sites/{site_id}/blue/managed-responder/policy")
def competitive_blue_managed_responder_policy(
    site_id: UUID,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return get_managed_responder_policy(db, site_id=site_id)


@router.post("/sites/{site_id}/blue/managed-responder/policy")
def competitive_blue_managed_responder_policy_upsert(
    site_id: UUID,
    payload: BlueManagedResponderPolicyUpsertRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return upsert_managed_responder_policy(
        db,
        site_id=site_id,
        min_severity=payload.min_severity,
        action_mode=payload.action_mode,
        dispatch_playbook=payload.dispatch_playbook,
        playbook_code=payload.playbook_code,
        require_approval=payload.require_approval,
        dry_run_default=payload.dry_run_default,
        enabled=payload.enabled,
        owner=payload.owner,
    )


@router.post("/sites/{site_id}/blue/managed-responder/run")
def competitive_blue_managed_responder_run(
    site_id: UUID,
    payload: BlueManagedResponderRunRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_managed_responder(
        db,
        site_id=site_id,
        dry_run=payload.dry_run,
        force=payload.force,
        actor=payload.actor,
    )


@router.get("/sites/{site_id}/blue/managed-responder/runs")
def competitive_blue_managed_responder_runs(
    site_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_managed_responder_runs(db, site_id=site_id, limit=limit)


@router.get("/blue/managed-responder/vendor-packs")
def competitive_blue_managed_responder_vendor_packs(
    source: str = "",
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_managed_responder_vendor_packs(source=source)


@router.get("/sites/{site_id}/blue/managed-responder/callbacks")
def competitive_blue_managed_responder_callbacks(
    site_id: UUID,
    run_id: UUID | None = None,
    connector_source: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_managed_responder_callbacks(
        db,
        site_id=site_id,
        run_id=run_id,
        connector_source=connector_source,
        limit=limit,
    )


@router.post("/sites/{site_id}/blue/managed-responder/runs/{run_id}/callback")
def competitive_blue_managed_responder_callback(
    site_id: UUID,
    run_id: UUID,
    payload: BlueManagedResponderCallbackIngestRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return ingest_managed_responder_callback(
        db,
        site_id=site_id,
        run_id=run_id,
        connector_source=payload.connector_source,
        contract_code=payload.contract_code,
        callback_type=payload.callback_type,
        webhook_event_id=payload.webhook_event_id,
        external_action_ref=payload.external_action_ref,
        status=payload.status,
        payload=payload.payload,
        actor=payload.actor,
    )


@router.post("/sites/{site_id}/blue/managed-responder/runs/{run_id}/review")
def competitive_blue_managed_responder_review(
    site_id: UUID,
    run_id: UUID,
    payload: BlueManagedResponderReviewRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return review_managed_responder_run(
        db,
        site_id=site_id,
        run_id=run_id,
        approve=payload.approve,
        approver=payload.approver,
        note=payload.note,
    )


@router.post("/sites/{site_id}/blue/managed-responder/runs/{run_id}/rollback")
def competitive_blue_managed_responder_rollback(
    site_id: UUID,
    run_id: UUID,
    payload: BlueManagedResponderRollbackRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return rollback_managed_responder_run(
        db,
        site_id=site_id,
        run_id=run_id,
        actor=payload.actor,
        note=payload.note,
    )


@router.get("/sites/{site_id}/blue/managed-responder/evidence/verify")
def competitive_blue_managed_responder_evidence_verify(
    site_id: UUID,
    limit: int = 100,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return verify_managed_responder_evidence_chain(db, site_id=site_id, limit=limit)


@router.post("/blue/managed-responder/scheduler/run")
def competitive_blue_managed_responder_scheduler(
    limit: int = 200,
    dry_run_override: bool | None = None,
    actor: str = "blue_managed_responder_scheduler",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return run_managed_responder_scheduler(
        db,
        limit=limit,
        dry_run_override=dry_run_override,
        actor=actor,
    )


@router.post("/sites/{site_id}/purple/roi-dashboard/generate")
def competitive_purple_roi_dashboard_generate(
    site_id: UUID,
    payload: PurpleRoiDashboardRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return generate_purple_roi_dashboard(
        db,
        site_id=site_id,
        lookback_days=payload.lookback_days,
        analyst_hourly_cost_usd=payload.analyst_hourly_cost_usd,
        analyst_minutes_per_alert=payload.analyst_minutes_per_alert,
    )


@router.get("/sites/{site_id}/purple/roi-dashboard/snapshots")
def competitive_purple_roi_dashboard_snapshots(
    site_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_purple_roi_snapshots(db, site_id=site_id, limit=limit)


@router.get("/sites/{site_id}/purple/roi-dashboard/trends")
def competitive_purple_roi_dashboard_trends(
    site_id: UUID,
    limit: int = 12,
    metric_focus: str = "",
    min_automation_coverage_pct: float = 0.0,
    min_noise_reduction_pct: float = 0.0,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_purple_roi_trends(
        db,
        site_id=site_id,
        limit=limit,
        metric_focus=metric_focus,
        min_automation_coverage_pct=min_automation_coverage_pct,
        min_noise_reduction_pct=min_noise_reduction_pct,
    )


@router.get("/purple/roi-dashboard/portfolio")
def competitive_purple_roi_dashboard_portfolio(
    tenant_code: str = "",
    site_code: str = "",
    status: str = "",
    min_automation_coverage_pct: float = 0.0,
    min_noise_reduction_pct: float = 0.0,
    sort_by: str = "estimated_manual_effort_saved_usd",
    limit: int = 200,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return build_purple_roi_portfolio_rollup(
        db,
        tenant_code=tenant_code,
        site_code=site_code,
        status=status,
        min_automation_coverage_pct=min_automation_coverage_pct,
        min_noise_reduction_pct=min_noise_reduction_pct,
        sort_by=sort_by,
        limit=limit,
    )


@router.get("/purple/roi-dashboard/template-packs")
def competitive_purple_roi_dashboard_template_packs(
    audience: str = "",
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_purple_roi_template_packs(audience=audience)


@router.post("/sites/{site_id}/purple/roi-dashboard/export")
def competitive_purple_roi_dashboard_export(
    site_id: UUID,
    payload: PurpleRoiDashboardExportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return export_purple_roi_board_pack(
        db,
        site_id=site_id,
        export_format=payload.export_format,
        template_pack=payload.template_pack,
        title_override=payload.title_override,
        include_portfolio=payload.include_portfolio,
        tenant_code=payload.tenant_code,
        site_limit=payload.site_limit,
    )


@router.get("/purple/export/template-packs")
def competitive_purple_export_template_packs(
    kind: str = "",
    audience: str = "",
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_purple_export_template_packs(kind=kind, audience=audience)


@router.get("/sites/{site_id}/purple/control-family-map")
def competitive_purple_control_family_map(
    site_id: UUID,
    framework: str = "combined",
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return build_purple_control_family_map(db, site_id=site_id, framework=framework)


@router.post("/sites/{site_id}/purple/control-family-map/export")
def competitive_purple_control_family_map_export(
    site_id: UUID,
    payload: PurpleControlFamilyMapExportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return export_purple_control_family_map(
        db,
        site_id=site_id,
        framework=payload.framework,
        export_format=payload.export_format,
    )


@router.post("/sites/{site_id}/purple/mitre-heatmap/export")
def competitive_purple_mitre_heatmap_export(
    site_id: UUID,
    payload: PurpleMitreHeatmapExportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return export_purple_mitre_heatmap(
        db,
        site_id=site_id,
        export_format=payload.export_format,
        title_override=payload.title_override,
        include_recommendations=payload.include_recommendations,
        lookback_runs=payload.lookback_runs,
        lookback_events=payload.lookback_events,
        sla_target_seconds=payload.sla_target_seconds,
    )


@router.get("/sites/{site_id}/purple/mitre-heatmap/layers")
def competitive_purple_attack_layer_workspaces(
    site_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_purple_attack_layer_workspaces(db, site_id=site_id, limit=limit)


@router.post("/sites/{site_id}/purple/mitre-heatmap/layers/import")
def competitive_purple_attack_layer_import(
    site_id: UUID,
    payload: PurpleAttackLayerImportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return import_purple_attack_layer_workspace(
        db,
        site_id=site_id,
        layer_name=payload.layer_name,
        layer_document=payload.layer_document,
        actor=payload.actor,
        notes=payload.notes,
    )


@router.post("/sites/{site_id}/purple/mitre-heatmap/layers/{layer_id}/edit")
def competitive_purple_attack_layer_edit(
    site_id: UUID,
    layer_id: UUID,
    payload: PurpleAttackLayerUpdateRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return update_purple_attack_layer_workspace(
        db,
        site_id=site_id,
        layer_id=layer_id,
        layer_name=payload.layer_name,
        notes=payload.notes,
        technique_overrides=payload.technique_overrides,
        actor=payload.actor,
    )


@router.post("/sites/{site_id}/purple/mitre-heatmap/layers/{layer_id}/export")
def competitive_purple_attack_layer_export(
    site_id: UUID,
    layer_id: UUID,
    payload: PurpleAttackLayerExportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return export_purple_attack_layer_workspace(
        db,
        site_id=site_id,
        layer_id=layer_id,
        export_format=payload.export_format,
    )


@router.post("/sites/{site_id}/purple/mitre-heatmap/graphical-export")
def competitive_purple_attack_layer_live_export(
    site_id: UUID,
    payload: PurpleAttackLayerExportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return export_live_purple_attack_layer_graphic(
        db,
        site_id=site_id,
        export_format=payload.export_format,
    )


@router.post("/sites/{site_id}/purple/incident-report/export")
def competitive_purple_incident_report_export(
    site_id: UUID,
    payload: PurpleIncidentReportExportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return export_purple_incident_report(
        db,
        site_id=site_id,
        template_pack=payload.template_pack,
        export_format=payload.export_format,
        title_override=payload.title_override,
        include_regulatory_mapping=payload.include_regulatory_mapping,
        blue_event_limit=payload.blue_event_limit,
    )


@router.post("/sites/{site_id}/purple/regulatory-report/export")
def competitive_purple_regulatory_report_export(
    site_id: UUID,
    payload: PurpleRegulatedReportExportRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return export_purple_regulated_report(
        db,
        site_id=site_id,
        template_pack=payload.template_pack,
        export_format=payload.export_format,
        title_override=payload.title_override,
        include_incident_context=payload.include_incident_context,
    )


@router.get("/sites/{site_id}/purple/report-releases")
def competitive_purple_report_releases(
    site_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_purple_report_releases(db, site_id=site_id, limit=limit)


@router.post("/sites/{site_id}/purple/report-releases")
def competitive_purple_report_release_request(
    site_id: UUID,
    payload: PurpleReportReleaseRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return request_purple_report_release(
        db,
        site_id=site_id,
        report_kind=payload.report_kind,
        export_format=payload.export_format,
        title=payload.title,
        filename=payload.filename,
        payload=payload.payload,
        requester=payload.requester,
        note=payload.note,
    )


@router.post("/purple/report-releases/{release_id}/review")
def competitive_purple_report_release_review(
    release_id: UUID,
    payload: PurpleReportReleaseReviewRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return review_purple_report_release(
        db,
        release_id=release_id,
        approve=payload.approve,
        approver=payload.approver,
        note=payload.note,
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


@router.get("/soar/marketplace/packs")
def competitive_soar_marketplace_packs(
    category: str = "",
    audience: str = "",
    scope: str = "",
    source_type: str = "",
    trust_tier: str = "",
    connector_source: str = "",
    search: str = "",
    featured_only: bool = False,
    limit: int = 200,
) -> dict[str, object]:
    return list_marketplace_packs(
        category=category,
        audience=audience,
        scope=scope,
        source_type=source_type,
        trust_tier=trust_tier,
        connector_source=connector_source,
        search=search,
        featured_only=featured_only,
        limit=limit,
    )


@router.get("/soar/contracts/results")
def competitive_soar_connector_result_contracts(
    connector_source: str = "",
    playbook_code: str = "",
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_connector_result_contracts(connector_source=connector_source, playbook_code=playbook_code)


@router.post("/soar/marketplace/packs/{pack_code}/install")
def competitive_soar_marketplace_pack_install(
    pack_code: str,
    payload: SoarMarketplacePackInstallRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_POLICY_WRITE)),
) -> dict[str, object]:
    return install_marketplace_pack(
        db,
        pack_code=pack_code,
        actor=payload.actor,
        scope_override=payload.scope_override,
    )


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


@router.post("/soar/executions/{execution_id}/verify")
def competitive_soar_execution_verify(
    execution_id: UUID,
    payload: SoarPlaybookVerificationRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return verify_playbook_execution(db, execution_id=execution_id, actor=payload.actor)


@router.post("/sites/{site_id}/soar/executions/{execution_id}/connector-result")
def competitive_soar_execution_connector_result(
    site_id: UUID,
    execution_id: UUID,
    payload: SoarConnectorResultCallbackRequest,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_APPROVE)),
) -> dict[str, object]:
    return ingest_playbook_connector_result(
        db,
        execution_id=execution_id,
        site_id=site_id,
        connector_source=payload.connector_source,
        contract_code=payload.contract_code,
        external_action_ref=payload.external_action_ref,
        webhook_event_id=payload.webhook_event_id,
        status=payload.status,
        payload=payload.payload,
        actor=payload.actor,
    )


@router.get("/sites/{site_id}/soar/executions/{execution_id}/connector-results")
def competitive_soar_execution_connector_results(
    site_id: UUID,
    execution_id: UUID,
    limit: int = 20,
    db: Session = Depends(get_db),
    _admin: dict[str, object] = Depends(require_permission(PERM_VIEW)),
) -> dict[str, object]:
    return list_playbook_connector_results(db, execution_id=execution_id, site_id=site_id, limit=limit)


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
