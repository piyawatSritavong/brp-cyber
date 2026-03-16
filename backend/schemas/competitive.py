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


class SiteCoworkerPluginBindingUpsertRequest(BaseModel):
    plugin_code: str = Field(min_length=3, max_length=80)
    enabled: bool = True
    auto_run: bool = False
    schedule_interval_minutes: int = Field(default=60, ge=5, le=1440)
    notify_channels: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    owner: str = Field(default="security", min_length=2, max_length=64)


class SiteCoworkerPluginRunRequest(BaseModel):
    dry_run: bool | None = None
    force: bool = False
    actor: str = Field(default="coworker_plugin_ai", min_length=2, max_length=128)


class SiteEmbeddedWorkflowEndpointUpsertRequest(BaseModel):
    endpoint_code: str = Field(min_length=3, max_length=80)
    workflow_type: str = Field(default="coworker_plugin", pattern="^(coworker_plugin|soar_playbook)$")
    plugin_code: str = Field(default="", max_length=80)
    connector_source: str = Field(default="generic", min_length=2, max_length=64)
    default_event_kind: str = Field(default="security_event", min_length=2, max_length=64)
    enabled: bool = True
    dry_run_default: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    owner: str = Field(default="security", min_length=2, max_length=64)
    rotate_secret: bool = False


class SiteCoworkerDeliveryProfileUpsertRequest(BaseModel):
    channel: str = Field(default="telegram", pattern="^(telegram|line|teams|webhook)$")
    enabled: bool = False
    min_severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    delivery_mode: str = Field(default="manual", pattern="^(manual|auto)$")
    require_approval: bool = True
    include_thai_summary: bool = True
    webhook_url: str = Field(default="", max_length=2048)
    owner: str = Field(default="security", min_length=2, max_length=64)


class SiteCoworkerDeliveryPreviewRequest(BaseModel):
    channel: str = Field(default="telegram", pattern="^(telegram|line|teams|webhook)$")


class SiteCoworkerDeliveryDispatchRequest(BaseModel):
    channel: str = Field(default="telegram", pattern="^(telegram|line|teams|webhook)$")
    dry_run: bool | None = None
    force: bool = False
    actor: str = Field(default="coworker_delivery_ai", min_length=2, max_length=128)


class SiteCoworkerDeliveryReviewRequest(BaseModel):
    approve: bool = True
    actor: str = Field(default="security_reviewer", min_length=2, max_length=128)
    note: str = Field(default="", max_length=2048)


class SiteCoworkerDeliveryEscalationPolicyUpsertRequest(BaseModel):
    plugin_code: str = Field(min_length=3, max_length=80)
    enabled: bool = False
    escalate_after_minutes: int = Field(default=15, ge=1, le=1440)
    max_escalation_count: int = Field(default=2, ge=1, le=10)
    fallback_channels: list[str] = Field(default_factory=lambda: ["telegram", "line"])
    escalate_on_statuses: list[str] = Field(default_factory=lambda: ["approval_required", "failed"])
    owner: str = Field(default="security", min_length=2, max_length=64)


class SiteCoworkerDeliveryEscalationRunRequest(BaseModel):
    plugin_code: str = Field(min_length=3, max_length=80)
    dry_run: bool | None = None
    force: bool = False
    actor: str = Field(default="delivery_escalator_ai", min_length=2, max_length=128)


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


class RedShadowPentestPolicyUpsertRequest(BaseModel):
    crawl_depth: int = Field(default=2, ge=0, le=4)
    max_pages: int = Field(default=12, ge=1, le=100)
    change_threshold: int = Field(default=2, ge=1, le=50)
    schedule_interval_minutes: int = Field(default=180, ge=5, le=1440)
    auto_assign_zero_day_pack: bool = True
    route_alert: bool = True
    enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class RedShadowPentestRunRequest(BaseModel):
    dry_run: bool | None = None
    force: bool = False
    actor: str = Field(default="red_shadow_pentest_ai", min_length=2, max_length=128)


class RedShadowPentestDeployEventRequest(BaseModel):
    deploy_id: str = Field(default="deploy-001", min_length=3, max_length=128)
    release_version: str = Field(default="", max_length=64)
    changed_paths: list[str] = Field(default_factory=list)
    actor: str = Field(default="deploy_pipeline", min_length=2, max_length=128)
    dry_run_override: bool | None = None


class RedSocialEngineeringRunRequest(BaseModel):
    campaign_name: str = Field(default="thai_phishing_awareness", min_length=3, max_length=255)
    employee_segment: str = Field(default="all_staff", min_length=2, max_length=128)
    email_count: int = Field(default=50, ge=1, le=5000)
    campaign_type: str = Field(default="awareness", pattern="^(awareness|credential_reset|hr_notice|finance_notice|brand_protection)$")
    template_pack_code: str = Field(default="", max_length=64)
    difficulty: str = Field(default="medium", pattern="^(low|medium|high)$")
    impersonation_brand: str = Field(default="", max_length=128)
    dry_run: bool = True
    actor: str = Field(default="red_social_sim_ai", min_length=2, max_length=128)


class RedSocialRosterImportRequest(BaseModel):
    entries: list[dict[str, Any]] = Field(default_factory=list)
    actor: str = Field(default="red_social_roster_ai", min_length=2, max_length=128)


class RedSocialCampaignPolicyUpsertRequest(BaseModel):
    connector_type: str = Field(default="simulated", pattern="^(simulated|smtp|webhook)$")
    sender_name: str = Field(default="Security Awareness AI", min_length=2, max_length=128)
    sender_email: str = Field(default="security-awareness@example.local", min_length=5, max_length=255)
    subject_prefix: str = Field(default="[Awareness]", max_length=64)
    landing_base_url: str = Field(default="", max_length=1024)
    report_mailbox: str = Field(default="", max_length=255)
    require_approval: bool = True
    enable_open_tracking: bool = True
    enable_click_tracking: bool = True
    max_emails_per_run: int = Field(default=200, ge=1, le=5000)
    kill_switch_active: bool = False
    allowed_domains: list[str] = Field(default_factory=list)
    connector_config: dict[str, Any] = Field(default_factory=dict)
    campaign_type: str = Field(default="awareness", pattern="^(awareness|credential_reset|hr_notice|finance_notice|brand_protection)$")
    template_pack_code: str = Field(default="th_awareness_basic", max_length=64)
    evidence_retention_days: int = Field(default=90, ge=1, le=3650)
    legal_ack_required: bool = True
    enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class RedSocialCampaignReviewRequest(BaseModel):
    approve: bool = True
    actor: str = Field(default="security_lead", min_length=2, max_length=128)
    note: str = Field(default="", max_length=2048)


class RedSocialCampaignKillRequest(BaseModel):
    actor: str = Field(default="security_operator", min_length=2, max_length=128)
    note: str = Field(default="", max_length=2048)
    activate_site_kill_switch: bool = False


class RedSocialProviderCallbackRequest(BaseModel):
    run_id: UUID
    connector_type: str = Field(default="smtp", min_length=2, max_length=64)
    event_type: str = Field(default="delivered", min_length=2, max_length=32)
    recipient_email: str = Field(min_length=5, max_length=255)
    occurred_at: str = Field(default="", max_length=64)
    provider_event_id: str = Field(default="", max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)
    actor: str = Field(default="provider_callback_ingest", min_length=2, max_length=128)


class RedVulnerabilityFindingImportRequest(BaseModel):
    source_tool: str = Field(default="nessus", min_length=2, max_length=32)
    payload: Any = Field(default_factory=dict)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    actor: str = Field(default="red_vuln_import_ai", min_length=2, max_length=128)


class RedVulnerabilityValidatorRunRequest(BaseModel):
    finding_ids: list[UUID] = Field(default_factory=list)
    max_findings: int = Field(default=50, ge=1, le=200)
    dry_run: bool = True
    actor: str = Field(default="red_vuln_validator_ai", min_length=2, max_length=128)


class RedPluginIntelligenceImportRequest(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    actor: str = Field(default="red_plugin_intel_ai", min_length=2, max_length=128)


class RedPluginSyncSourceUpsertRequest(BaseModel):
    source_name: str = Field(default="external_feed", min_length=2, max_length=64)
    source_type: str = Field(default="article", pattern="^(cve|news|article)$")
    source_url: str = Field(default="https://example.com/feed.json", min_length=8, max_length=1024)
    target_type: str = Field(default="web", min_length=2, max_length=32)
    parser_kind: str = Field(default="json_feed", pattern="^(json_feed|jsonl)$")
    request_headers: dict[str, Any] = Field(default_factory=dict)
    sync_interval_minutes: int = Field(default=1440, ge=5, le=10080)
    enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class RedPluginSyncRunRequest(BaseModel):
    sync_source_id: UUID | None = None
    dry_run: bool = True
    actor: str = Field(default="red_plugin_sync_ai", min_length=2, max_length=128)


class RedPluginSafetyPolicyUpsertRequest(BaseModel):
    target_type: str = Field(default="web", min_length=2, max_length=32)
    max_http_requests_per_run: int = Field(default=5, ge=1, le=50)
    max_script_lines: int = Field(default=80, ge=10, le=500)
    allow_network_calls: bool = True
    require_comment_header: bool = True
    require_disclaimer: bool = True
    allowed_modules: list[str] = Field(default_factory=lambda: ["requests"])
    blocked_modules: list[str] = Field(default_factory=lambda: ["subprocess", "socket", "paramiko"])
    enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class RedPluginLintRequest(BaseModel):
    run_id: UUID | None = None
    content_override: str = Field(default="", max_length=50000)


class RedPluginExportRequest(BaseModel):
    run_id: UUID | None = None
    export_kind: str = Field(default="bundle", min_length=3, max_length=64)
    title_override: str = Field(default="", max_length=255)


class RedPluginPublishThreatPackRequest(BaseModel):
    run_id: UUID | None = None
    activate: bool = True
    actor: str = Field(default="red_plugin_publish_ai", min_length=2, max_length=128)


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


class BlueThreatLocalizerRunRequest(BaseModel):
    focus_region: str = Field(default="thailand", min_length=2, max_length=64)
    sector: str = Field(default="general", min_length=2, max_length=64)
    dry_run: bool = True
    actor: str = Field(default="blue_threat_localizer_ai", min_length=2, max_length=128)


class BlueThreatFeedImportRequest(BaseModel):
    source_name: str = Field(default="manual", min_length=2, max_length=64)
    items: list[dict[str, Any]] = Field(default_factory=list)
    actor: str = Field(default="blue_threat_feed_ai", min_length=2, max_length=128)


class BlueThreatFeedAdapterImportRequest(BaseModel):
    source: str = Field(default="generic", min_length=2, max_length=64)
    payload: Any = Field(default_factory=dict)
    actor: str = Field(default="blue_threat_feed_adapter_ai", min_length=2, max_length=128)


class BlueThreatLocalizerPolicyUpsertRequest(BaseModel):
    focus_region: str = Field(default="thailand", min_length=2, max_length=64)
    sector: str = Field(default="general", min_length=2, max_length=64)
    subscribed_categories: list[str] = Field(default_factory=lambda: ["identity", "phishing", "ransomware", "web"])
    recurring_digest_enabled: bool = True
    schedule_interval_minutes: int = Field(default=240, ge=15, le=10080)
    min_feed_priority: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class BlueThreatLocalizerRoutingPolicyUpsertRequest(BaseModel):
    stakeholder_groups: list[str] = Field(default_factory=lambda: ["soc_l1", "threat_hunting", "security_lead"])
    group_channel_map: dict[str, list[str]] = Field(
        default_factory=lambda: {"soc_l1": ["telegram"], "threat_hunting": ["teams"], "security_lead": ["line"]}
    )
    category_group_map: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "identity": ["soc_l1", "security_lead"],
            "phishing": ["soc_l1", "security_lead"],
            "web": ["threat_hunting", "soc_l1"],
            "ransomware": ["threat_hunting", "security_lead"],
            "malware": ["threat_hunting"],
            "insider": ["security_lead"],
        }
    )
    min_priority_score: int = Field(default=60, ge=1, le=100)
    min_risk_tier: str = Field(default="high", pattern="^(low|medium|high|critical)$")
    auto_promote_on_gap: bool = True
    auto_apply_autotune: bool = False
    dispatch_via_action_center: bool = True
    playbook_promotion_enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class BlueThreatLocalizerPromotionRequest(BaseModel):
    localizer_run_id: UUID | None = None
    auto_apply_override: bool | None = None
    playbook_promotion_override: bool | None = None
    actor: str = Field(default="blue_threat_promotion_ai", min_length=2, max_length=128)


class BlueLogRefinerPolicyUpsertRequest(BaseModel):
    connector_source: str = Field(default="generic", min_length=2, max_length=64)
    execution_mode: str = Field(default="pre_ingest", pattern="^(pre_ingest|post_ingest)$")
    lookback_limit: int = Field(default=200, ge=20, le=2000)
    min_keep_severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    drop_recommendation_codes: list[str] = Field(default_factory=lambda: ["ignore"])
    target_noise_reduction_pct: int = Field(default=80, ge=10, le=99)
    average_event_size_kb: int = Field(default=4, ge=1, le=512)
    enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class BlueLogRefinerRunRequest(BaseModel):
    connector_source: str = Field(default="generic", min_length=2, max_length=64)
    dry_run: bool = True
    actor: str = Field(default="blue_log_refiner_ai", min_length=2, max_length=128)


class BlueLogRefinerFeedbackRequest(BaseModel):
    connector_source: str = Field(default="generic", min_length=2, max_length=64)
    feedback_type: str = Field(default="keep_signal", pattern="^(keep_signal|drop_noise|false_positive|signal_missed)$")
    event_type: str = Field(default="", max_length=64)
    recommendation_code: str = Field(default="", max_length=64)
    note: str = Field(default="", max_length=2048)
    actor: str = Field(default="analyst", min_length=2, max_length=128)
    run_id: UUID | None = None


class BlueLogRefinerSchedulePolicyUpsertRequest(BaseModel):
    connector_source: str = Field(default="generic", min_length=2, max_length=64)
    schedule_interval_minutes: int = Field(default=60, ge=5, le=1440)
    dry_run_default: bool = True
    callback_ingest_enabled: bool = True
    enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class BlueLogRefinerCallbackIngestRequest(BaseModel):
    connector_source: str = Field(default="generic", min_length=2, max_length=64)
    callback_type: str = Field(default="stream_result", pattern="^(stream_result|storage_report|delivery_receipt)$")
    source_system: str = Field(default="", max_length=64)
    external_run_ref: str = Field(default="", max_length=128)
    webhook_event_id: str = Field(default="", max_length=255)
    run_id: UUID | None = None
    total_events: int = Field(default=0, ge=0, le=1_000_000)
    kept_events: int = Field(default=0, ge=0, le=1_000_000)
    dropped_events: int = Field(default=0, ge=0, le=1_000_000)
    noise_reduction_pct: int | None = Field(default=None, ge=0, le=100)
    estimated_storage_saved_kb: int = Field(default=0, ge=0, le=100_000_000)
    status: str = Field(default="ok", pattern="^(ok|warning|error|duplicate)$")
    payload: dict[str, object] = Field(default_factory=dict)
    actor: str = Field(default="siem_callback", min_length=2, max_length=128)


class BlueManagedResponderPolicyUpsertRequest(BaseModel):
    min_severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    action_mode: str = Field(default="ai_recommended", pattern="^(ai_recommended|block_ip|notify_team|limit_user|ignore)$")
    dispatch_playbook: bool = True
    playbook_code: str = Field(default="block-ip-and-waf-tighten", max_length=80)
    require_approval: bool = True
    dry_run_default: bool = True
    enabled: bool = True
    owner: str = Field(default="security", min_length=2, max_length=64)


class BlueManagedResponderRunRequest(BaseModel):
    dry_run: bool | None = None
    force: bool = False
    actor: str = Field(default="managed_ai_responder", min_length=2, max_length=128)


class BlueManagedResponderReviewRequest(BaseModel):
    approve: bool = True
    approver: str = Field(default="security_lead", min_length=2, max_length=128)
    note: str = Field(default="", max_length=2048)


class BlueManagedResponderRollbackRequest(BaseModel):
    actor: str = Field(default="security_operator", min_length=2, max_length=128)
    note: str = Field(default="", max_length=2048)


class BlueManagedResponderCallbackIngestRequest(BaseModel):
    connector_source: str = Field(default="generic", min_length=2, max_length=64)
    contract_code: str = Field(min_length=3, max_length=128)
    callback_type: str = Field(default="result_confirmed", max_length=32)
    webhook_event_id: str = Field(default="", max_length=255)
    external_action_ref: str = Field(default="", max_length=255)
    status: str = Field(default="received", max_length=32)
    payload: dict[str, Any] = Field(default_factory=dict)
    actor: str = Field(default="vendor_callback", min_length=2, max_length=128)


class PurpleRoiDashboardRequest(BaseModel):
    lookback_days: int = Field(default=30, ge=1, le=365)
    analyst_hourly_cost_usd: float = Field(default=18.0, ge=1.0, le=1000.0)
    analyst_minutes_per_alert: int = Field(default=12, ge=1, le=240)


class PurpleRoiDashboardExportRequest(BaseModel):
    export_format: str = Field(default="pdf", pattern="^(pdf|ppt)$")
    template_pack: str = Field(default="roi_board_minimal", min_length=3, max_length=80)
    title_override: str = Field(default="", max_length=255)
    include_portfolio: bool = True
    tenant_code: str = Field(default="", max_length=64)
    site_limit: int = Field(default=50, ge=1, le=500)


class PurpleMitreHeatmapExportRequest(BaseModel):
    export_format: str = Field(default="markdown", pattern="^(markdown|csv|attack_layer_json|svg)$")
    title_override: str = Field(default="", max_length=255)
    include_recommendations: bool = True
    lookback_runs: int = Field(default=30, ge=1, le=500)
    lookback_events: int = Field(default=500, ge=1, le=2000)
    sla_target_seconds: int = Field(default=120, ge=30, le=3600)


class PurpleControlFamilyMapExportRequest(BaseModel):
    framework: str = Field(default="combined", pattern="^(combined|iso27001|nist_csf)$")
    export_format: str = Field(default="markdown", pattern="^(markdown|json|csv)$")


class PurpleAttackLayerImportRequest(BaseModel):
    layer_name: str = Field(default="Imported Layer", min_length=3, max_length=255)
    layer_document: dict[str, Any] | str = Field(default_factory=dict)
    actor: str = Field(default="purple_operator", min_length=2, max_length=128)
    notes: str = Field(default="", max_length=4000)


class PurpleAttackLayerUpdateRequest(BaseModel):
    layer_name: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=4000)
    technique_overrides: list[dict[str, Any]] = Field(default_factory=list)
    actor: str = Field(default="purple_operator", min_length=2, max_length=128)


class PurpleAttackLayerExportRequest(BaseModel):
    export_format: str = Field(default="attack_layer_json", pattern="^(attack_layer_json|svg)$")


class PurpleIncidentReportExportRequest(BaseModel):
    template_pack: str = Field(default="incident_company_standard", min_length=3, max_length=80)
    export_format: str = Field(default="markdown", pattern="^(markdown|json|pdf|docx)$")
    title_override: str = Field(default="", max_length=255)
    include_regulatory_mapping: bool = True
    blue_event_limit: int = Field(default=20, ge=1, le=200)


class PurpleRegulatedReportExportRequest(BaseModel):
    template_pack: str = Field(default="regulated_nca_th", min_length=3, max_length=80)
    export_format: str = Field(default="markdown", pattern="^(markdown|json|pdf|docx)$")
    title_override: str = Field(default="", max_length=255)
    include_incident_context: bool = True


class PurpleReportReleaseRequest(BaseModel):
    report_kind: str = Field(min_length=3, max_length=64)
    export_format: str = Field(default="pdf", pattern="^(pdf|docx|markdown|json)$")
    title: str = Field(default="", max_length=255)
    filename: str = Field(default="", max_length=255)
    payload: dict[str, Any] = Field(default_factory=dict)
    requester: str = Field(default="purple_ai", min_length=2, max_length=128)
    note: str = Field(default="", max_length=2000)


class PurpleReportReleaseReviewRequest(BaseModel):
    approve: bool = True
    approver: str = Field(default="security_lead", min_length=2, max_length=128)
    note: str = Field(default="", max_length=2000)


class PhaseObjectiveCheckRequest(BaseModel):
    phase_code: str = Field(min_length=3, max_length=32)
    phase_title: str = Field(default="", max_length=255)
    objective_ids: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    site_id: UUID | None = None
    context: dict[str, Any] = Field(default_factory=dict)
