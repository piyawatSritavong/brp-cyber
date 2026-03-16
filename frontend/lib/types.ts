export type GateBlocker = {
  gate: string;
  reason: string;
};

export type DashboardRow = {
  tenant_id: string;
  overall_pass: boolean;
  failed_gate_count: number;
  blockers: GateBlocker[];
};

export type DashboardResponse = {
  total_tenants: number;
  passing_tenants: number;
  failing_tenants: number;
  rows: DashboardRow[];
};

export type TenantGateResponse = {
  tenant_id: string;
  overall_pass: boolean;
  gates: Record<string, { pass: boolean }>;
};

export type TenantHistoryRow = {
  id: string;
  tenant_id: string;
  overall_pass: boolean;
};

export type TenantHistoryResponse = {
  count: number;
  rows: TenantHistoryRow[];
};

export type TenantRemediation = {
  remediation: {
    failed_gate_count: number;
    actions: Array<{ gate: string; priority: string; action: string }>;
  };
};

export type GovernancePolicy = {
  mode: string;
  require_change_ticket_for_override: boolean;
  require_change_ticket_for_production: boolean;
  require_reason_for_key_rotation: boolean;
};

export type GovernanceDashboardResponse = {
  policy: GovernancePolicy;
  summary: {
    events_analyzed: number;
    policy_warnings: number;
    policy_denies: number;
    override_actions: number;
    production_promotions: number;
  };
  status_counts: Record<string, number>;
  top_actions: Array<[string, number]>;
  risky_actors: Array<{ actor: string; risk_score: number }>;
};

export type RedScenarioLibrary = {
  count: number;
  scenarios: Record<string, { tactic: string; description: string }>;
};

export type RedRunResult = {
  status: string;
  scenario_name?: string;
  target_asset?: string;
  requested_events?: number;
  executed_events?: number;
  correlation_id?: string;
  reason?: string;
};

export type BlueIncident = {
  id: string;
  tenant_id: string;
  timestamp: string;
  threat_actor: string;
  severity: string;
  signal: string;
  action_taken: string;
  action_result: string;
  username: string;
  failed_attempts: string;
};

export type BlueIncidentFeed = {
  tenant_id: string;
  count: number;
  incidents: BlueIncident[];
};

export type OrchestratorState = {
  tenant_id: string;
  strategy_profile: string;
  blue_policy: {
    failed_login_threshold_per_minute: number;
    failure_window_seconds: number;
    incident_cooldown_seconds: number;
  };
  approval_mode: boolean;
  pending_actions: Array<Record<string, string>>;
};

export type PurpleKpi = {
  mttd_seconds: number;
  mttr_seconds: number;
  detection_coverage: number;
  blocked_before_impact_rate: number;
  mitigated_count: number;
  detected_count: number;
  attack_count: number;
};

export type PurpleRow = {
  attack_type: string;
  detection_status: string;
  mitigation_time_seconds: number | null;
  recommendation: string;
};

export type PurpleReport = {
  report_id: string;
  tenant_id: string;
  generated_at: string;
  summary: string;
  kpi: PurpleKpi;
  table: PurpleRow[];
};

export type SiteRow = {
  site_id: string;
  tenant_id: string;
  tenant_code: string;
  site_code: string;
  display_name: string;
  base_url: string;
  is_active: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SiteListResponse = {
  count: number;
  rows: SiteRow[];
};

export type SiteUpsertResponse = {
  status: string;
  site: SiteRow;
};

export type SiteRedScanResponse = {
  status: string;
  scan_id: string;
  scan_type: string;
  findings: Record<string, unknown>;
  ai_summary: string;
};

export type SiteRedScanHistoryResponse = {
  count: number;
  rows: Array<{
    scan_id: string;
    scan_type: string;
    status: string;
    ai_summary: string;
    findings: Record<string, unknown>;
    created_at: string;
  }>;
};

export type SiteBlueEventHistoryResponse = {
  count: number;
  rows: Array<{
    event_id: string;
    event_type: string;
    source_ip: string;
    payload: Record<string, unknown>;
    ai_severity: string;
    ai_recommendation: string;
    status: string;
    action_taken: string;
    created_at: string;
  }>;
};

export type SitePurpleReportHistoryResponse = {
  count: number;
  rows: Array<{
    report_id: string;
    summary: string;
    metrics: Record<string, unknown>;
    ai_analysis: Record<string, unknown>;
    created_at: string;
  }>;
};

export type SitePurpleIsoGapTemplateResponse = {
  status: string;
  framework: string;
  summary: {
    site_id: string;
    site_code: string;
    generated_at: string;
    red_scan_count: number;
    blue_event_count: number;
    purple_report_count: number;
    blue_applied_ratio: number;
    mttr_hint_seconds: number;
  };
  controls: Array<{
    control_id: string;
    control_name: string;
    status: "pass" | "partial" | "gap";
    evidence: string;
    recommendation: string;
  }>;
};

export type SitePurpleExecutiveScorecardResponse = {
  status: string;
  framework: string;
  summary: {
    site_id: string;
    site_code: string;
    generated_at: string;
    red_exploit_runs: number;
    blue_events: number;
    detection_rules: number;
    attacked_techniques: number;
    covered_techniques: number;
    partial_techniques: number;
    heatmap_coverage: number;
  };
  heatmap: Array<{
    technique_id: string;
    attack_count: number;
    detection_status: "covered" | "partial" | "gap";
    mitigation_time_seconds: number | null;
    sla_status: "pass" | "at_risk";
    recommendation: string;
  }>;
  remediation_sla: {
    target_mttr_seconds: number;
    estimated_mttr_seconds: number;
    suspicious_event_count: number;
    applied_event_count: number;
    apply_rate: number;
    detection_event_count: number;
    sla_status: "pass" | "at_risk";
    recommendation: string;
  };
};

export type SitePurpleExecutiveFederationResponse = {
  status: string;
  generated_at: string;
  count: number;
  passing_sites: number;
  at_risk_sites: number;
  rows: Array<{
    site_id: string;
    site_code: string;
    tenant_code: string;
    heatmap_coverage: number;
    attacked_techniques: number;
    covered_techniques: number;
    estimated_mttr_seconds: number;
    target_mttr_seconds: number;
    sla_status: "pass" | "at_risk";
    apply_rate: number;
  }>;
};

export type SiteRedSocialSimulatorRunRow = {
  run_id: string;
  site_id: string;
  campaign_name: string;
  employee_segment: string;
  language: string;
  difficulty: string;
  impersonation_brand: string;
  email_count: number;
  dry_run: boolean;
  risk_score: number;
  risk_tier: string;
  summary_th: string;
  details: Record<string, unknown>;
  execution: {
    execution_id: string;
    status: string;
    connector_type: string;
    approval_required: boolean;
    dispatch_mode: string;
    requested_by: string;
    reviewed_by: string;
    review_note: string;
    reviewed_at: string;
    dispatched_at: string;
    completed_at: string;
    killed_at: string;
    killed_by: string;
    kill_reason: string;
    telemetry_summary: Record<string, unknown>;
    connector_config: Record<string, unknown>;
  };
  created_at: string;
};

export type SiteRedSocialSimulatorRunResponse = {
  status: string;
  site_id: string;
  site_code: string;
  run: SiteRedSocialSimulatorRunRow;
};

export type SiteRedSocialSimulatorRunListResponse = {
  status: string;
  count: number;
  rows: SiteRedSocialSimulatorRunRow[];
};

export type SiteRedSocialRosterRow = {
  roster_entry_id: string;
  site_id: string;
  employee_code: string;
  full_name: string;
  email: string;
  department: string;
  role_title: string;
  locale: string;
  risk_level: string;
  tags: string[];
  metadata: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type SiteRedSocialRosterResponse = {
  status: string;
  count: number;
  summary: {
    departments: string[];
    active_count: number;
    high_risk_count: number;
  };
  rows: SiteRedSocialRosterRow[];
};

export type SiteRedSocialRosterImportResponse = {
  status: string;
  site_id: string;
  site_code: string;
  actor: string;
  received_count: number;
  imported_count: number;
  updated_count: number;
  rows: SiteRedSocialRosterRow[];
};

export type SiteRedSocialPolicyResponse = {
  status: string;
  policy: {
    policy_id: string;
    site_id: string;
    connector_type: string;
    sender_name: string;
    sender_email: string;
    subject_prefix: string;
    landing_base_url: string;
    report_mailbox: string;
    require_approval: boolean;
    enable_open_tracking: boolean;
    enable_click_tracking: boolean;
    max_emails_per_run: number;
    kill_switch_active: boolean;
    allowed_domains: string[];
    connector_config: Record<string, unknown>;
    enabled: boolean;
    owner: string;
    created_at: string;
    updated_at: string;
  };
};

export type SiteRedSocialTelemetryRow = {
  recipient_id: string;
  run_id: string;
  roster_entry_id: string;
  recipient_email: string;
  recipient_name: string;
  department: string;
  delivery_status: string;
  sent_at: string;
  opened_at: string;
  clicked_at: string;
  reported_at: string;
  telemetry: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SiteRedSocialTelemetryResponse = {
  status: string;
  site_id: string;
  run_id: string;
  summary: {
    expected_count: number;
    delivered_count: number;
    opened_count: number;
    clicked_count: number;
    reported_count: number;
    killed_count: number;
    open_rate_pct: number;
    click_rate_pct: number;
    report_rate_pct: number;
  };
  rows: SiteRedSocialTelemetryRow[];
};

export type SiteRedSocialProviderCallbackResponse = {
  status: string;
  site_id: string;
  site_code: string;
  run: SiteRedSocialSimulatorRunRow;
  recipient: SiteRedSocialTelemetryRow;
  callback: {
    event_type: string;
    connector_type: string;
    occurred_at: string;
    provider_event_id: string;
  };
};

export type SiteRedVulnerabilityFindingRow = {
  finding_id: string;
  site_id: string;
  source_tool: string;
  source_finding_id: string;
  fingerprint: string;
  title: string;
  severity: string;
  cve_id: string;
  asset: string;
  endpoint: string;
  status: string;
  import_count: number;
  exploitability_score: number;
  false_positive_score: number;
  verdict: string;
  ai_summary: string;
  remediation_summary: string;
  normalized: Record<string, unknown>;
  validation_details: Record<string, unknown>;
  first_seen_at: string;
  last_seen_at: string;
  last_validated_at: string;
  created_at: string;
  updated_at: string;
};

export type SiteRedVulnerabilityFindingImportResponse = {
  status: string;
  site: {
    site_id: string;
    site_code: string;
    display_name: string;
    base_url: string;
  };
  source_tool: string;
  actor: string;
  received_count: number;
  imported_count: number;
  deduped_count: number;
  rows: SiteRedVulnerabilityFindingRow[];
};

export type SiteRedVulnerabilityFindingListResponse = {
  count: number;
  rows: SiteRedVulnerabilityFindingRow[];
};

export type SiteRedVulnerabilityValidationRunRow = {
  run_id: string;
  site_id: string;
  status: string;
  dry_run: boolean;
  actor: string;
  source_tools: string[];
  finding_count: number;
  validated_count: number;
  exploitable_count: number;
  false_positive_count: number;
  needs_review_count: number;
  summary_th: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type SiteRedVulnerabilityValidationRunResponse = {
  status: string;
  site: {
    site_id: string;
    site_code: string;
    display_name: string;
    base_url: string;
  };
  summary: {
    finding_count: number;
    validated_count: number;
    exploitable_count: number;
    false_positive_count: number;
    needs_review_count: number;
    source_tools: string[];
  };
  run: SiteRedVulnerabilityValidationRunRow;
  rows: Array<SiteRedVulnerabilityFindingRow & { remediation_export: Record<string, unknown> }>;
  remediation_export: {
    count: number;
    rows: Record<string, unknown>[];
  };
};

export type SiteRedVulnerabilityValidationRunListResponse = {
  count: number;
  rows: SiteRedVulnerabilityValidationRunRow[];
};

export type SiteRedVulnerabilityRemediationExportResponse = {
  count: number;
  rows: Array<{
    finding_id: string;
    source_tool: string;
    source_finding_id: string;
    title: string;
    severity: string;
    verdict: string;
    exploitability_score: number;
    false_positive_score: number;
    scanner_status: string;
    payload: Record<string, unknown>;
    comment: string;
  }>;
};

export type SiteBlueThreatLocalizerRunRow = {
  run_id: string;
  site_id: string;
  focus_region: string;
  sector: string;
  dry_run: boolean;
  priority_score: number;
  risk_tier: string;
  headline: string;
  summary_th: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type BlueThreatSectorProfileRow = {
  sector: string;
  label_th: string;
  priority_categories: string[];
  keywords: string[];
  risk_bias: number;
};

export type BlueThreatSectorProfilesResponse = {
  status: string;
  count: number;
  rows: BlueThreatSectorProfileRow[];
};

export type BlueThreatFeedAdapterTemplateRow = {
  source: string;
  display_name: string;
  description: string;
  field_mapping: Array<{ incoming: string; mapped_to: string }>;
  categories_supported: string[];
  sample_payload: Record<string, unknown>;
};

export type BlueThreatFeedAdapterTemplatesResponse = {
  status: string;
  count: number;
  rows: BlueThreatFeedAdapterTemplateRow[];
};

export type BlueThreatFeedItemRow = {
  feed_item_id: string;
  source_name: string;
  source_item_id: string;
  title: string;
  summary_th: string;
  category: string;
  severity: string;
  focus_region: string;
  sectors: string[];
  iocs: unknown[];
  references: unknown[];
  payload: Record<string, unknown>;
  published_at: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type BlueThreatFeedImportResponse = {
  status: string;
  source_name: string;
  actor: string;
  received_count: number;
  imported_count: number;
  updated_count: number;
  rows: BlueThreatFeedItemRow[];
};

export type BlueThreatFeedAdapterImportResponse = BlueThreatFeedImportResponse & {
  adapter_source: string;
  normalized_count: number;
};

export type BlueThreatFeedListResponse = {
  status: string;
  count: number;
  rows: BlueThreatFeedItemRow[];
};

export type SiteBlueThreatLocalizerPolicy = {
  policy_id: string;
  site_id: string;
  focus_region: string;
  sector: string;
  subscribed_categories: string[];
  recurring_digest_enabled: boolean;
  schedule_interval_minutes: number;
  min_feed_priority: string;
  enabled: boolean;
  owner: string;
  created_at: string;
  updated_at: string;
};

export type SiteBlueThreatLocalizerPolicyResponse = {
  status: string;
  policy: SiteBlueThreatLocalizerPolicy;
};

export type SiteBlueThreatLocalizerRoutingPolicy = {
  routing_policy_id: string;
  site_id: string;
  stakeholder_groups: string[];
  group_channel_map: Record<string, string[]>;
  category_group_map: Record<string, string[]>;
  min_priority_score: number;
  min_risk_tier: string;
  auto_promote_on_gap: boolean;
  auto_apply_autotune: boolean;
  dispatch_via_action_center: boolean;
  playbook_promotion_enabled: boolean;
  owner: string;
  created_at: string;
  updated_at: string;
};

export type SiteBlueThreatLocalizerRoutingPolicyResponse = {
  status: string;
  policy: SiteBlueThreatLocalizerRoutingPolicy;
};

export type SiteBlueThreatLocalizerPromotionRunRow = {
  promotion_run_id: string;
  site_id: string;
  localizer_run_id: string;
  status: string;
  promoted_categories: string[];
  routed_groups: string[];
  playbook_codes: string[];
  autotune_run_id: string;
  details: Record<string, unknown>;
  actor: string;
  created_at: string;
};

export type SiteBlueThreatLocalizerPromotionRunResponse = {
  status: string;
  site_id: string;
  site_code: string;
  routing_policy: SiteBlueThreatLocalizerRoutingPolicy;
  promotion: SiteBlueThreatLocalizerPromotionRunRow;
};

export type SiteBlueThreatLocalizerPromotionRunListResponse = {
  status: string;
  count: number;
  rows: SiteBlueThreatLocalizerPromotionRunRow[];
};

export type SiteBlueThreatLocalizerRunResponse = {
  status: string;
  site_id: string;
  site_code: string;
  run: SiteBlueThreatLocalizerRunRow;
};

export type SiteBlueThreatLocalizerRunListResponse = {
  status: string;
  count: number;
  rows: SiteBlueThreatLocalizerRunRow[];
};

export type SiteBlueThreatLocalizerSchedulerResponse = {
  status: string;
  scheduled_policy_count: number;
  executed_count: number;
  skipped_count: number;
  executed: Array<{ site_id: string; status: string; run_id: string; promotion_status?: string }>;
  skipped: Array<{ site_id: string; reason: string }>;
  generated_at: string;
};

export type BlueLogRefinerMappingPackRow = {
  source: string;
  display_name: string;
  execution_mode: string;
  notes: string[];
  field_mapping: Array<{ incoming: string; mapped_to: string }>;
};

export type BlueLogRefinerMappingPackResponse = {
  status: string;
  count: number;
  rows: BlueLogRefinerMappingPackRow[];
};

export type SiteBlueLogRefinerPolicy = {
  policy_id: string;
  site_id: string;
  connector_source: string;
  execution_mode: "pre_ingest" | "post_ingest";
  lookback_limit: number;
  min_keep_severity: "low" | "medium" | "high" | "critical";
  drop_recommendation_codes: string[];
  target_noise_reduction_pct: number;
  average_event_size_kb: number;
  enabled: boolean;
  owner: string;
  created_at: string;
  updated_at: string;
};

export type SiteBlueLogRefinerPolicyResponse = {
  status: string;
  policy: SiteBlueLogRefinerPolicy;
};

export type SiteBlueLogRefinerSchedulePolicy = {
  schedule_policy_id: string;
  site_id: string;
  connector_source: string;
  schedule_interval_minutes: number;
  dry_run_default: boolean;
  callback_ingest_enabled: boolean;
  enabled: boolean;
  owner: string;
  created_at: string;
  updated_at: string;
};

export type SiteBlueLogRefinerSchedulePolicyResponse = {
  status: string;
  policy: SiteBlueLogRefinerSchedulePolicy;
};

export type SiteBlueLogRefinerRunRow = {
  run_id: string;
  site_id: string;
  connector_source: string;
  execution_mode: "pre_ingest" | "post_ingest";
  dry_run: boolean;
  status: string;
  total_events: number;
  kept_events: number;
  dropped_events: number;
  feedback_adjusted_events: number;
  noise_reduction_pct: number;
  estimated_storage_saved_kb: number;
  details: Record<string, unknown>;
  created_at: string;
};

export type SiteBlueLogRefinerRunResponse = {
  status: string;
  site_id: string;
  site_code: string;
  policy: SiteBlueLogRefinerPolicy;
  run: SiteBlueLogRefinerRunRow;
};

export type SiteBlueLogRefinerRunListResponse = {
  status: string;
  count: number;
  rows: SiteBlueLogRefinerRunRow[];
};

export type SiteBlueLogRefinerFeedbackRow = {
  feedback_id: string;
  site_id: string;
  run_id: string;
  connector_source: string;
  event_type: string;
  recommendation_code: string;
  feedback_type: "keep_signal" | "drop_noise" | "false_positive" | "signal_missed";
  note: string;
  actor: string;
  created_at: string;
};

export type SiteBlueLogRefinerFeedbackResponse = {
  status: string;
  feedback: SiteBlueLogRefinerFeedbackRow;
};

export type SiteBlueLogRefinerFeedbackListResponse = {
  status: string;
  count: number;
  rows: SiteBlueLogRefinerFeedbackRow[];
};

export type SiteBlueLogRefinerCallbackRow = {
  callback_id: string;
  site_id: string;
  run_id: string;
  connector_source: string;
  callback_type: "stream_result" | "storage_report" | "delivery_receipt";
  source_system: string;
  external_run_ref: string;
  webhook_event_id: string;
  status: string;
  total_events: number;
  kept_events: number;
  dropped_events: number;
  noise_reduction_pct: number;
  estimated_storage_saved_kb: number;
  actor: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type SiteBlueLogRefinerCallbackResponse = {
  status: string;
  site_id: string;
  site_code: string;
  callback: SiteBlueLogRefinerCallbackRow;
  matched_run: SiteBlueLogRefinerRunRow | null;
};

export type SiteBlueLogRefinerCallbackListResponse = {
  status: string;
  count: number;
  rows: SiteBlueLogRefinerCallbackRow[];
};

export type SiteBlueLogRefinerSchedulerResponse = {
  timestamp: string;
  scheduled_policy_count: number;
  executed_count: number;
  skipped_count: number;
  executed: Array<{
    site_id: string;
    site_code: string;
    connector_source: string;
    status: string;
    run_id: string;
    noise_reduction_pct: number;
  }>;
  skipped: Array<{
    site_id: string;
    site_code: string;
    connector_source?: string;
    reason: string;
  }>;
};

export type SiteBlueManagedResponderPolicy = {
  policy_id: string;
  site_id: string;
  min_severity: "low" | "medium" | "high" | "critical";
  action_mode: "ai_recommended" | "block_ip" | "notify_team" | "limit_user" | "ignore";
  dispatch_playbook: boolean;
  playbook_code: string;
  require_approval: boolean;
  dry_run_default: boolean;
  enabled: boolean;
  owner: string;
  created_at: string;
  updated_at: string;
};

export type SiteBlueManagedResponderPolicyResponse = {
  status: string;
  policy: SiteBlueManagedResponderPolicy;
};

export type SiteBlueManagedResponderRunRow = {
  run_id: string;
  site_id: string;
  event_id: string;
  status: string;
  dry_run: boolean;
  selected_severity: string;
  selected_action: string;
  playbook_code: string;
  playbook_execution_id: string;
  action_applied: boolean;
  playbook_dispatched: boolean;
  approval_required: boolean;
  rollback_supported: boolean;
  evidence_sequence: number;
  evidence_signature: string;
  connector_source: string;
  connector_action_status: string;
  connector_confirmation_status: string;
  connector_rollback_status: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type SiteBlueManagedResponderRunResponse = {
  status: string;
  site_id: string;
  site_code?: string;
  policy: SiteBlueManagedResponderPolicy;
  guardrails?: Record<string, unknown>;
  candidate_event?: {
    event_id: string;
    event_type: string;
    source_ip: string;
    ai_severity: string;
    ai_recommendation: string;
    status: string;
  };
  action_result?: Record<string, unknown>;
  playbook_result?: Record<string, unknown>;
  connector_result?: Record<string, unknown>;
  run?: SiteBlueManagedResponderRunRow;
};

export type SiteBlueManagedResponderRunListResponse = {
  site_id: string;
  count: number;
  rows: SiteBlueManagedResponderRunRow[];
};

export type SiteBlueManagedResponderSchedulerResponse = {
  timestamp: string;
  scheduled_policy_count: number;
  executed_count: number;
  skipped_count: number;
  executed: Array<{
    site_id: string;
    site_code: string;
    status: string;
    run_id: string;
    candidate_event_id: string;
    selected_action: string;
  }>;
  skipped: Array<Record<string, unknown>>;
};

export type SiteBlueManagedResponderEvidenceVerifyResponse = {
  status: string;
  site_id: string;
  site_code: string;
  count: number;
  valid: boolean;
  rows: Array<{
    run_id: string;
    status: string;
    sequence: number;
    signature: string;
    previous_signature: string;
    valid: boolean;
    created_at: string;
  }>;
};

export type SitePurpleRoiDashboardSnapshotRow = {
  snapshot_id: string;
  site_id: string;
  lookback_days: number;
  status: string;
  summary: Record<string, unknown>;
  details: Record<string, unknown>;
  created_at: string;
};

export type SitePurpleRoiDashboardResponse = {
  status: string;
  site_id: string;
  site_code: string;
  snapshot: SitePurpleRoiDashboardSnapshotRow;
};

export type SitePurpleRoiDashboardSnapshotListResponse = {
  status: string;
  count: number;
  rows: SitePurpleRoiDashboardSnapshotRow[];
};

export type SitePurpleRoiDashboardTrendRow = {
  snapshot_id: string;
  created_at: string;
  validated_findings: number;
  high_risk_findings: number;
  automation_coverage_pct: number;
  noise_reduction_pct: number;
  estimated_manual_effort_saved_usd: number;
};

export type SitePurpleRoiDashboardTrendResponse = {
  status: string;
  site_id: string;
  count: number;
  summary: {
    trend_points: number;
    latest_created_at: string;
    validated_findings_delta: number;
    automation_coverage_delta_pct: number;
    noise_reduction_delta_pct: number;
    estimated_manual_effort_saved_delta_usd: number;
    direction: string;
  };
  rows: SitePurpleRoiDashboardTrendRow[];
};

export type PurpleRoiPortfolioRow = {
  tenant_code: string;
  site_id: string;
  site_code: string;
  display_name: string;
  status: string;
  validated_findings: number;
  automation_coverage_pct: number;
  noise_reduction_pct: number;
  estimated_manual_effort_saved_usd: number;
  high_risk_findings: number;
  created_at: string;
  headline_th: string;
  board_statement_th: string;
};

export type PurpleRoiPortfolioRollupResponse = {
  status: string;
  tenant_code: string;
  count: number;
  summary: {
    tenant_code: string;
    total_sites: number;
    sites_with_snapshots: number;
    no_snapshot_sites: number;
    total_validated_findings: number;
    total_estimated_manual_effort_saved_usd: number;
    average_automation_coverage_pct: number;
    average_noise_reduction_pct: number;
    highest_value_site_code: string;
  };
  rows: PurpleRoiPortfolioRow[];
};

export type PurpleRoiTemplatePackResponse = {
  status: string;
  count: number;
  rows: Array<{
    pack_code: string;
    display_name: string;
    audience: string;
    description: string;
    layout_style: string;
    accent_hex: string;
    cover_label: string;
    footer_label: string;
    section_order: string[];
  }>;
};

export type SitePurpleRoiBoardExportResponse = {
  status: string;
  site_id: string;
  site_code: string;
  export: {
    export_format: string;
    renderer: string;
    title: string;
    filename: string;
    generated_at: string;
    snapshot_id: string;
    includes_portfolio: boolean;
    portfolio_tenant_code: string;
    template_pack: {
      pack_code: string;
      display_name: string;
      audience: string;
      description: string;
      layout_style: string;
      accent_hex: string;
      cover_label: string;
      footer_label: string;
      section_order: string[];
    };
    mime_type: string;
    byte_size: number;
    content_base64: string;
    sections: Array<{ section: string; content: string[] }>;
    slides: Array<{ title: string; bullets: string[] }>;
    preview_text: string;
  };
};

export type PurpleExportTemplatePackResponse = {
  status: string;
  count: number;
  rows: Array<{
    pack_code: string;
    kind: string;
    display_name: string;
    audience: string;
    output_profile: string;
    description: string;
    sections: string[];
  }>;
};

export type SitePurpleMitreHeatmapExportResponse = {
  status: string;
  site_id: string;
  site_code: string;
  export: {
    export_type: string;
    export_format: string;
    title: string;
    filename: string;
    generated_at: string;
    summary: Record<string, unknown>;
    remediation_sla: Record<string, unknown>;
    rows: Array<Record<string, unknown>>;
    content: string;
  };
};

export type SitePurpleIncidentReportExportResponse = {
  status: string;
  site_id: string;
  site_code: string;
  export: {
    export_type: string;
    export_format: string;
    template_pack: Record<string, unknown>;
    title: string;
    filename: string;
    generated_at: string;
    sections: Array<{ section: string; content: string[] }>;
    content: string;
    renderer?: string;
    mime_type?: string;
    byte_size?: number;
    content_base64?: string;
  };
};

export type SitePurpleRegulatedReportExportResponse = {
  status: string;
  site_id: string;
  site_code: string;
  export: {
    export_type: string;
    export_format: string;
    template_pack: Record<string, unknown>;
    title: string;
    filename: string;
    generated_at: string;
    sections: Array<{ section: string; content: string[] }>;
    content: string;
    renderer?: string;
    mime_type?: string;
    byte_size?: number;
    content_base64?: string;
  };
};

export type SitePurpleReportReleaseRow = {
  release_id: string;
  site_id: string;
  report_kind: string;
  export_format: string;
  title: string;
  filename: string;
  status: string;
  requested_by: string;
  approved_by: string;
  note: string;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SitePurpleReportReleaseResponse = {
  status: string;
  release: SitePurpleReportReleaseRow;
};

export type SitePurpleReportReleaseListResponse = {
  status: string;
  count: number;
  rows: SitePurpleReportReleaseRow[];
};

export type IntegrationAdaptersResponse = {
  count: number;
  adapters: Record<string, { name: string; ocsf_class: string }>;
};

export type IntegrationAdapterTemplateRow = {
  source: string;
  display_name: string;
  default_event_kind: string;
  recommended_plugin_codes: string[];
  notes: string[];
  field_mapping: Array<{
    incoming: string;
    mapped_to: string;
    note: string;
  }>;
  invoke_payload: Record<string, unknown>;
};

export type IntegrationAdapterTemplatesResponse = {
  count: number;
  rows: IntegrationAdapterTemplateRow[];
};

export type IntegrationEventIngestResponse = {
  status: string;
  integration_event_id: string;
  site_id: string;
  blue_event_id: string;
  normalized: Record<string, unknown>;
};

export type CompetitiveObjectivesResponse = {
  count: number;
  top_priority_objective_ids: string[];
  objectives: Record<string, { title: string; description: string }>;
};

export type CompetitiveAuthContextResponse = {
  authenticated: boolean;
  actor: string;
  scopes: string[];
  roles: string[];
  permissions: {
    can_view: boolean;
    can_edit_policy: boolean;
    can_approve: boolean;
  };
};

export type ThreatContentPackRow = {
  pack_id: string;
  pack_code: string;
  title: string;
  category: string;
  mitre_techniques: string[];
  attack_steps: string[];
  validation_mode: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ThreatContentPackListResponse = {
  count: number;
  rows: ThreatContentPackRow[];
};

export type ThreatContentPipelinePolicyResponse = {
  status: string;
  policy: {
    policy_id: string;
    scope: string;
    min_refresh_interval_minutes: number;
    preferred_categories: string[];
    max_packs_per_run: number;
    auto_activate: boolean;
    route_alert: boolean;
    enabled: boolean;
    owner: string;
    created_at: string;
    updated_at: string;
  };
};

export type ThreatContentPipelineRunRow = {
  run_id: string;
  scope: string;
  status: string;
  dry_run: boolean;
  selected_categories: string[];
  candidate_count: number;
  refreshed_count: number;
  created_count: number;
  activated_count: number;
  skipped_count: number;
  alert_routed: boolean;
  details: Record<string, unknown>;
  created_at: string;
};

export type ThreatContentPipelineRunResponse = {
  status: string;
  scope: string;
  policy: ThreatContentPipelinePolicyResponse["policy"];
  execution: {
    should_run: boolean;
    dry_run: boolean;
    reason: string;
    candidate_count: number;
    created_count: number;
    refreshed_count: number;
    activated_count: number;
    skipped_count: number;
  };
  run: ThreatContentPipelineRunRow;
  federation: ThreatContentPipelineFederationResponse;
  generated_at: string;
};

export type ThreatContentPipelineRunListResponse = {
  count: number;
  rows: ThreatContentPipelineRunRow[];
};

export type ThreatContentPipelineFederationResponse = {
  generated_at: string;
  count: number;
  stale_count: number;
  rows: Array<{
    category: string;
    pack_count: number;
    unique_mitre_techniques: number;
    latest_updated_at: string;
    is_stale: boolean;
  }>;
};

export type CoworkerPluginCatalogRow = {
  plugin_id: string;
  plugin_code: string;
  display_name: string;
  display_name_th: string;
  category: string;
  plugin_kind: string;
  execution_mode: string;
  description: string;
  value_statement: string;
  default_config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type CoworkerPluginCatalogResponse = {
  count: number;
  rows: CoworkerPluginCatalogRow[];
};

export type SiteCoworkerPluginBinding = {
  binding_id: string;
  site_id: string;
  plugin_id: string;
  enabled: boolean;
  auto_run: boolean;
  schedule_interval_minutes: number;
  notify_channels: string[];
  config: Record<string, unknown>;
  owner: string;
  created_at: string;
  updated_at: string;
};

export type SiteCoworkerPluginRow = CoworkerPluginCatalogRow & {
  installed: boolean;
  binding: SiteCoworkerPluginBinding | null;
};

export type SiteCoworkerPluginListResponse = {
  site_id: string;
  count: number;
  rows: SiteCoworkerPluginRow[];
};

export type CoworkerPluginRunCore = {
  run_id: string;
  plugin_id: string;
  site_id: string;
  status: string;
  dry_run: boolean;
  input_summary: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  alert_routed: boolean;
  created_at: string;
};

export type SiteCoworkerPluginRunResponse = {
  status: string;
  site_id: string;
  site_code: string;
  plugin: CoworkerPluginCatalogRow;
  binding: SiteCoworkerPluginBinding | null;
  run: CoworkerPluginRunCore;
  alert: Record<string, unknown>;
};

export type SiteCoworkerPluginRunRow = CoworkerPluginRunCore & {
  plugin_code: string;
  display_name: string;
  display_name_th: string;
  category: string;
};

export type SiteCoworkerPluginRunListResponse = {
  site_id: string;
  count: number;
  rows: SiteCoworkerPluginRunRow[];
};

export type RedPluginIntelligenceRow = {
  intel_id: string;
  site_id: string;
  source_type: string;
  source_name: string;
  source_item_id: string;
  title: string;
  summary_th: string;
  cve_id: string;
  target_surface: string;
  target_type: string;
  tags: string[];
  references: string[];
  payload: Record<string, unknown>;
  published_at: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type SiteRedPluginIntelligenceResponse = {
  status: string;
  site_id: string;
  count: number;
  rows: RedPluginIntelligenceRow[];
  created_count?: number;
  updated_count?: number;
};

export type RedPluginSyncSourceRow = {
  sync_source_id: string;
  site_id: string;
  source_name: string;
  source_type: string;
  source_url: string;
  target_type: string;
  parser_kind: string;
  request_headers: Record<string, unknown>;
  sync_interval_minutes: number;
  enabled: boolean;
  last_synced_at: string;
  owner: string;
  created_at: string;
  updated_at: string;
};

export type SiteRedPluginSyncSourcesResponse = {
  status: string;
  site_id: string;
  count: number;
  rows: RedPluginSyncSourceRow[];
  source?: RedPluginSyncSourceRow;
};

export type RedPluginSyncRunRow = {
  sync_run_id: string;
  site_id: string;
  sync_source_id: string;
  status: string;
  dry_run: boolean;
  fetched_count: number;
  imported_count: number;
  updated_count: number;
  details: Record<string, unknown>;
  actor: string;
  created_at: string;
};

export type SiteRedPluginSyncRunsResponse = {
  status: string;
  site_id: string;
  count?: number;
  fetched_count?: number;
  executed_count?: number;
  skipped_count?: number;
  scheduled_source_count?: number;
  rows?: RedPluginSyncRunRow[];
  run?: RedPluginSyncRunRow;
  sync_source?: RedPluginSyncSourceRow;
  import_result?: Record<string, unknown>;
  executed?: Array<Record<string, unknown>>;
  skipped?: Array<Record<string, unknown>>;
  generated_at?: string;
};

export type RedPluginSafetyPolicy = {
  policy_id: string;
  site_id: string;
  target_type: string;
  max_http_requests_per_run: number;
  max_script_lines: number;
  allow_network_calls: boolean;
  require_comment_header: boolean;
  require_disclaimer: boolean;
  allowed_modules: string[];
  blocked_modules: string[];
  enabled: boolean;
  owner: string;
  created_at: string;
  updated_at: string;
};

export type SiteRedPluginSafetyPolicyResponse = {
  status: string;
  site_id?: string;
  policy: RedPluginSafetyPolicy;
};

export type SiteRedPluginLintResponse = {
  status: string;
  site_id: string;
  plugin_code: string;
  run_id: string;
  lint: {
    status: string;
    issues: string[];
    warnings: string[];
    line_count: number;
    kind: string;
    target_type: string;
    preview_excerpt: string;
  };
  safety_policy: RedPluginSafetyPolicy;
};

export type SiteRedPluginExportResponse = {
  status: string;
  site_id: string;
  plugin_code: string;
  run_id: string;
  export: {
    filename: string;
    title: string;
    export_kind: string;
    artifact_type: string;
    content: string;
    metadata: Record<string, unknown>;
    lint: Record<string, unknown>;
    threat_content_suggestion?: Record<string, unknown>;
  };
};

export type SiteRedPluginThreatPackPublishResponse = {
  status: string;
  site_id: string;
  actor: string;
  pack: {
    pack_code: string;
    title: string;
    category: string;
    mitre_techniques: string[];
    attack_steps: string[];
    validation_mode: string;
    is_active: boolean;
    updated_at: string;
  };
  source_export: Record<string, unknown>;
};

export type SiteEmbeddedWorkflowEndpointRow = {
  endpoint_id: string;
  site_id: string;
  endpoint_code: string;
  workflow_type: "coworker_plugin" | "soar_playbook";
  plugin_code: string;
  connector_source: string;
  default_event_kind: string;
  enabled: boolean;
  dry_run_default: boolean;
  config: Record<string, unknown>;
  owner: string;
  created_at: string;
  updated_at: string;
};

export type SiteEmbeddedWorkflowEndpointListResponse = {
  site_id: string;
  count: number;
  rows: SiteEmbeddedWorkflowEndpointRow[];
};

export type SiteEmbeddedInvokePackResponse = {
  site_id: string;
  site_code: string;
  count: number;
  rows: Array<{
    endpoint: SiteEmbeddedWorkflowEndpointRow;
    invoke_pack: {
      display_name: string;
      vendor_preset_code: string;
      notes: string[];
      activation_steps: string[];
      field_mapping: Array<{ incoming: string; mapped_to: string; note: string }>;
      recommended_plugin_codes: string[];
      automation_pack: {
        workflow_type: "coworker_plugin" | "soar_playbook";
        default_playbook_code: string;
        allowed_playbook_codes: string[];
        require_playbook_approval: boolean;
      };
      guardrails: {
        rate_limit_per_minute: number;
        replay_window_seconds: number;
        require_webhook_event_id: boolean;
      };
      invoke_path: string;
      headers: Record<string, string>;
      invoke_payload: Record<string, unknown>;
      curl_example: string;
    };
  }>;
};

export type SiteEmbeddedActivationBundleResponse = {
  status: string;
  site_id: string;
  site_code: string;
  count: number;
  ready_count: number;
  needs_attention_count: number;
  blocked_count: number;
  rows: Array<{
    endpoint: SiteEmbeddedWorkflowEndpointRow;
    activation_bundle: SiteEmbeddedInvokePackResponse["rows"][number]["invoke_pack"] & {
      operator_checklist: string[];
    };
    verification: SiteEmbeddedAutomationVerifyResponse["rows"][number]["verification"];
    handoff: {
      status: "ready" | "needs_attention" | "blocked";
      customer_handoff_ready: boolean;
      missing_items: string[];
      summary: string;
    };
  }>;
};

export type SiteEmbeddedAutomationVerifyResponse = {
  status: string;
  site_id: string;
  site_code: string;
  count: number;
  ok_count: number;
  warning_count: number;
  error_count: number;
  rows: Array<{
    endpoint: SiteEmbeddedWorkflowEndpointRow;
    verification: {
      status: "ok" | "warning" | "error";
      workflow_type: "coworker_plugin" | "soar_playbook";
      playbook_code: string;
      effective_approval_required: boolean;
      tenant_policy: {
        allow_partner_scope: boolean;
        blocked_playbook_codes: string[];
      };
      issues: Array<{ level: "warning" | "error"; code: string; message: string }>;
      recommendations: string[];
    };
  }>;
};

export type EmbeddedAutomationFederationReadinessResponse = {
  status: string;
  generated_at: string;
  connector_source: string;
  count: number;
  summary: {
    total_sites: number;
    ready_sites: number;
    warning_sites: number;
    error_sites: number;
    not_configured_sites: number;
    total_endpoints: number;
    ready_endpoints: number;
    warning_endpoints: number;
    error_endpoints: number;
  };
  rows: Array<{
    site_id: string;
    site_code: string;
    tenant_code: string;
    status: "ready" | "warning" | "error" | "not_configured";
    endpoint_count: number;
    ready_endpoint_count: number;
    warning_endpoint_count: number;
    error_endpoint_count: number;
    plugin_endpoint_count: number;
    playbook_endpoint_count: number;
    approval_required_count: number;
    connector_sources: string[];
    vendor_preset_codes: string[];
    recommended_action: string;
  }>;
};

export type SiteEmbeddedWorkflowEndpointUpsertResponse = {
  status: string;
  endpoint: SiteEmbeddedWorkflowEndpointRow;
  token: string;
  invoke_path: string;
};

export type SiteEmbeddedWorkflowInvocationRow = {
  invocation_id: string;
  endpoint_id: string;
  site_id: string;
  endpoint_code: string;
  workflow_type: string;
  plugin_code: string;
  source: string;
  status: string;
  dry_run: boolean;
  request_summary: Record<string, unknown>;
  response_summary: Record<string, unknown>;
  error_message: string;
  created_at: string;
};

export type SiteEmbeddedWorkflowInvocationListResponse = {
  site_id: string;
  count: number;
  rows: SiteEmbeddedWorkflowInvocationRow[];
};

export type CoworkerPluginSchedulerResponse = {
  timestamp: string;
  scheduled_binding_count: number;
  executed_count: number;
  skipped_count: number;
  executed?: Array<{
    site_id: string;
    site_code: string;
    plugin_code: string;
    status: string;
    run_id: string;
  }>;
  skipped?: Array<Record<string, unknown>>;
};

export type SiteCoworkerDeliveryProfileRow = {
  profile_id: string;
  site_id: string;
  channel: "telegram" | "line" | "teams" | "webhook";
  enabled: boolean;
  min_severity: "low" | "medium" | "high" | "critical";
  delivery_mode: "manual" | "auto";
  require_approval: boolean;
  include_thai_summary: boolean;
  webhook_url: string;
  owner: string;
  created_at: string;
  updated_at: string;
};

export type SiteCoworkerDeliveryProfilesResponse = {
  site_id: string;
  count: number;
  rows: SiteCoworkerDeliveryProfileRow[];
};

export type SiteCoworkerDeliveryPreviewResponse = {
  status: string;
  site_id: string;
  site_code: string;
  plugin: {
    plugin_id: string;
    plugin_code: string;
    display_name: string;
    display_name_th: string;
    category: string;
  };
  profile: SiteCoworkerDeliveryProfileRow;
  preview: {
    channel: string;
    severity: string;
    title: string;
    message: string;
    payload: Record<string, unknown>;
  };
  run: {
    run_id: string;
    status: string;
    created_at: string;
  };
};

export type SiteCoworkerDeliveryDispatchResponse = {
  status: string;
  site_id: string;
  site_code: string;
  plugin: Record<string, unknown>;
  profile: SiteCoworkerDeliveryProfileRow;
  preview: {
    channel: string;
    severity: string;
    title: string;
    message: string;
    payload: Record<string, unknown>;
  };
  event: SiteCoworkerDeliveryEventRow;
};

export type SiteCoworkerDeliveryEventRow = {
  event_id: string;
  site_id: string;
  plugin_id: string;
  plugin_code: string;
  display_name_th: string;
  channel: string;
  status: string;
  dry_run: boolean;
  severity: string;
  title: string;
  preview_text: string;
  actor: string;
  response: Record<string, unknown>;
  approval_required: boolean;
  created_at: string;
};

export type SiteCoworkerDeliveryEventsResponse = {
  site_id: string;
  count: number;
  rows: SiteCoworkerDeliveryEventRow[];
};

export type SiteCoworkerDeliveryReviewResponse = {
  status: string;
  site_id: string;
  site_code: string;
  event: SiteCoworkerDeliveryEventRow;
};

export type SiteCoworkerDeliverySlaResponse = {
  status: string;
  site_id: string;
  site_code: string;
  approval_sla_minutes: number;
  summary: {
    total_events: number;
    pending_approval_count: number;
    overdue_count: number;
    approved_or_reviewed_count: number;
    average_approval_latency_seconds: number;
  };
  pending_rows: Array<{
    event_id: string;
    channel: string;
    title: string;
    created_at: string;
    due_at: string;
    overdue: boolean;
  }>;
};

export type SiteCoworkerDeliveryEscalationPolicy = {
  policy_id: string;
  site_id: string;
  plugin_code: string;
  enabled: boolean;
  escalate_after_minutes: number;
  max_escalation_count: number;
  fallback_channels: Array<"telegram" | "line" | "teams" | "webhook">;
  escalate_on_statuses: string[];
  owner: string;
  created_at: string;
  updated_at: string;
};

export type SiteCoworkerDeliveryEscalationPolicyResponse = {
  status: string;
  site_id: string;
  site_code: string;
  policy: SiteCoworkerDeliveryEscalationPolicy;
};

export type SiteCoworkerDeliveryEscalationRunResponse = {
  status: string;
  site_id: string;
  site_code: string;
  policy: SiteCoworkerDeliveryEscalationPolicy;
  executed_count: number;
  skipped_count: number;
  executed: Array<Record<string, unknown>>;
  skipped: Array<Record<string, unknown>>;
};

export type SiteCoworkerDeliveryEscalationSchedulerResponse = {
  timestamp: string;
  dry_run: boolean;
  scheduled_policy_count: number;
  executed_count: number;
  skipped_count: number;
  executed: Array<Record<string, unknown>>;
  skipped: Array<Record<string, unknown>>;
};

export type SiteCoworkerDeliveryEscalationFederationResponse = {
  status: string;
  generated_at: string;
  plugin_code: string;
  approval_sla_minutes: number;
  count: number;
  summary: {
    total_sites: number;
    healthy_sites: number;
    attention_sites: number;
    not_configured_sites: number;
    pending_approval_total: number;
    overdue_total: number;
    enabled_profile_total: number;
    enabled_escalation_policy_total: number;
  };
  rows: Array<{
    site_id: string;
    site_code: string;
    tenant_code: string;
    status: "healthy" | "attention" | "not_configured";
    enabled_profile_count: number;
    auto_profile_count: number;
    enabled_escalation_policy_count: number;
    pending_approval_count: number;
    overdue_count: number;
    average_approval_latency_seconds: number;
    plugin_codes: string[];
    recommended_action: string;
  }>;
};

export type SiteExploitPathRunsResponse = {
  count: number;
  rows: Array<{
    run_id: string;
    site_id: string;
    threat_pack_id: string;
    status: string;
    risk_score: number;
    path_graph: Record<string, unknown>;
    proof: Record<string, unknown>;
    safe_mode: Record<string, unknown>;
    created_at: string;
  }>;
};

export type SiteExploitPathSimulationResponse = {
  status: string;
  run_id: string;
  site_id: string;
  site_code: string;
  threat_pack_code: string;
  risk_score: number;
  path_graph: Record<string, unknown>;
  proof: Record<string, unknown>;
  safe_mode: Record<string, unknown>;
};

export type SiteRedExploitAutopilotPolicyResponse = {
  status: string;
  policy: {
    policy_id: string;
    site_id: string;
    min_risk_score: number;
    min_risk_tier: "low" | "medium" | "high" | "critical";
    preferred_pack_category: string;
    target_surface: string;
    simulation_depth: number;
    max_requests_per_minute: number;
    stop_on_critical: boolean;
    simulation_only: boolean;
    auto_run: boolean;
    route_alert: boolean;
    schedule_interval_minutes: number;
    enabled: boolean;
    owner: string;
    created_at: string;
    updated_at: string;
  };
};

export type SiteRedShadowPentestPolicyResponse = {
  status: string;
  policy: {
    policy_id: string;
    site_id: string;
    crawl_depth: number;
    max_pages: number;
    change_threshold: number;
    schedule_interval_minutes: number;
    auto_assign_zero_day_pack: boolean;
    route_alert: boolean;
    enabled: boolean;
    owner: string;
    created_at: string;
    updated_at: string;
  };
};

export type SiteRedShadowPentestRunRow = {
  run_id: string;
  site_id: string;
  status: string;
  dry_run: boolean;
  site_changed: boolean;
  content_hash: string;
  page_count: number;
  new_page_count: number;
  removed_page_count: number;
  changed_page_count: number;
  assigned_pack_code: string;
  assigned_pack_category: string;
  alert_routed: boolean;
  details: Record<string, unknown>;
  created_at: string;
};

export type SiteRedShadowPentestRunResponse = {
  status: string;
  site: {
    site_id: string;
    site_code: string;
    display_name: string;
    base_url: string;
  };
  policy: SiteRedShadowPentestPolicyResponse["policy"];
  crawl: {
    page_count: number;
    content_hash: string;
    errors: string[];
  };
  diff: {
    new_paths: string[];
    removed_paths: string[];
    changed_paths: string[];
    total_change_count: number;
    threshold: number;
    site_changed: boolean;
  };
  pack_assignment: {
    pack_code: string;
    category: string;
    title: string;
    auto_assign_enabled: boolean;
  };
  pack_validation: {
    summary: {
      pack_code: string;
      pack_category: string;
      total_assets: number;
      matched_assets: number;
      targeted_assets: number;
      changed_asset_hits: number;
      unmatched_assets: number;
      coverage_pct: number;
      attack_step_count: number;
    };
    rows: Array<{
      path: string;
      asset_kind: string;
      risk_hint: string;
      candidate_categories: string[];
      matched: boolean;
      validation_status: string;
      priority: string;
      rationale: string;
      validation_steps: string[];
      mitre_techniques: string[];
    }>;
  };
  asset_inventory: {
    total_assets: number;
    kind_counts: Record<string, number>;
    rows: Array<{
      path: string;
      url: string;
      title: string;
      status_code: number;
      asset_kind: string;
      risk_hint: string;
    }>;
  };
  alert: Record<string, unknown>;
  deploy_event?: Record<string, unknown>;
  run: SiteRedShadowPentestRunRow;
  generated_at: string;
};

export type SiteRedShadowPentestRunListResponse = {
  status: string;
  site_id: string;
  count: number;
  rows: SiteRedShadowPentestRunRow[];
};

export type SiteRedShadowPentestAssetResponse = {
  status: string;
  site_id: string;
  latest_run_id: string;
  count: number;
  summary: {
    total_assets: number;
    kind_counts: Record<string, number>;
  };
  pack_validation: {
    summary: {
      pack_code: string;
      pack_category: string;
      total_assets: number;
      matched_assets: number;
      targeted_assets: number;
      changed_asset_hits: number;
      unmatched_assets: number;
      coverage_pct: number;
      attack_step_count: number;
    };
    rows: Array<{
      path: string;
      asset_kind: string;
      risk_hint: string;
      candidate_categories: string[];
      matched: boolean;
      validation_status: string;
      priority: string;
      rationale: string;
      validation_steps: string[];
      mitre_techniques: string[];
    }>;
  };
  rows: Array<{
    path: string;
    url: string;
    title: string;
    status_code: number;
    asset_kind: string;
    risk_hint: string;
  }>;
};

export type SiteRedShadowPentestSchedulerResponse = {
  status: string;
  scheduled_policy_count: number;
  executed_count: number;
  skipped_count: number;
  executed: Array<{
    site_id: string;
    site_code: string;
    status: string;
    site_changed: boolean;
  }>;
  skipped: Array<{
    site_id: string;
    site_code: string;
    reason: string;
  }>;
  generated_at: string;
};

export type SiteRedExploitAutopilotRunRow = {
  run_id: string;
  site_id: string;
  exploit_path_run_id: string;
  status: string;
  dry_run: boolean;
  risk_score: number;
  risk_tier: "low" | "medium" | "high" | "critical";
  threat_pack_code: string;
  path_node_count: number;
  path_edge_count: number;
  proof_confidence: string;
  should_run: boolean;
  executed: boolean;
  alert_routed: boolean;
  details: Record<string, unknown>;
  created_at: string;
};

export type SiteRedExploitAutopilotRunResponse = {
  status: string;
  site_id: string;
  site_code: string;
  policy: SiteRedExploitAutopilotPolicyResponse["policy"];
  risk: {
    risk_score: number;
    risk_tier: "low" | "medium" | "high" | "critical";
    scan_risk: number;
    latest_exploit_risk: number;
    missing_security_headers: number;
    sensitive_paths_open: number;
    blue_event_count: number;
    high_blue_events: number;
    medium_blue_events: number;
  };
  execution: {
    should_run: boolean;
    executed: boolean;
    dry_run: boolean;
    reason: string;
  };
  simulation: Record<string, unknown>;
  alert: Record<string, unknown>;
  run: SiteRedExploitAutopilotRunRow;
  generated_at: string;
};

export type SiteRedExploitAutopilotRunListResponse = {
  site_id: string;
  count: number;
  rows: SiteRedExploitAutopilotRunRow[];
};

export type SiteDetectionCopilotTuneResponse = {
  status: string;
  tuning_run_id: string;
  site_id: string;
  exploit_path_run_id: string;
  recommendations: Array<{
    rule_name: string;
    rule_logic: Record<string, unknown>;
    reason: string;
    evidence_refs?: string[];
  }>;
  before_metrics: Record<string, number>;
  after_metrics: Record<string, number>;
  expected_detection_coverage_delta: number;
};

export type SiteDetectionRulesResponse = {
  count: number;
  rows: Array<{
    rule_id: string;
    site_id: string;
    rule_name: string;
    rule_logic: Record<string, unknown>;
    source: string;
    status: string;
    created_at: string;
    updated_at: string;
  }>;
};

export type SiteDetectionAutotunePolicyResponse = {
  status: string;
  policy: {
    policy_id: string;
    site_id: string;
    min_risk_score: number;
    min_risk_tier: "low" | "medium" | "high" | "critical";
    target_detection_coverage_pct: number;
    max_rules_per_run: number;
    auto_apply: boolean;
    route_alert: boolean;
    schedule_interval_minutes: number;
    enabled: boolean;
    owner: string;
    created_at: string;
    updated_at: string;
  };
};

export type SiteDetectionAutotuneRunRow = {
  run_id: string;
  site_id: string;
  status: string;
  dry_run: boolean;
  risk_score: number;
  risk_tier: "low" | "medium" | "high" | "critical";
  coverage_before_pct: number;
  coverage_after_pct: number;
  recommendation_count: number;
  applied_count: number;
  alert_routed: boolean;
  details: Record<string, unknown>;
  created_at: string;
};

export type SiteDetectionAutotuneRunResponse = {
  status: string;
  site_id: string;
  site_code: string;
  policy: SiteDetectionAutotunePolicyResponse["policy"];
  risk: {
    risk_score: number;
    risk_tier: "low" | "medium" | "high" | "critical";
    exploit_risk: number;
    blue_event_count: number;
    suspicious_event_count: number;
    open_suspicious_count: number;
    applied_suspicious_count: number;
    detection_coverage: number;
    apply_rate: number;
  };
  execution: {
    should_tune: boolean;
    dry_run: boolean;
    recommendation_count: number;
    applied_count: number;
    reason: string;
  };
  tuning: Record<string, unknown>;
  alert: Record<string, unknown>;
  run: SiteDetectionAutotuneRunRow;
  generated_at: string;
};

export type SiteDetectionAutotuneRunListResponse = {
  site_id: string;
  count: number;
  rows: SiteDetectionAutotuneRunRow[];
};

export type SiteCaseGraphResponse = {
  status: string;
  site_id: string;
  site_code: string;
  summary: {
    node_count: number;
    edge_count: number;
    exploit_paths: number;
    blue_events: number;
    detection_rules: number;
    soar_executions?: number;
    connector_events?: number;
    connector_replay_runs?: number;
    risk_score?: number;
    risk_tier?: "low" | "medium" | "high" | "critical";
    has_purple_report: boolean;
  };
  risk?: {
    score: number;
    tier: "low" | "medium" | "high" | "critical";
    max_exploit_risk: number;
    high_blue_events: number;
    open_blue_events: number;
    pending_soar_executions: number;
    unresolved_connector_dlq: number;
    high_risk_replay_runs: number;
    recommendation: string;
  };
  timeline?: Array<{
    timestamp: string;
    source: string;
    node_id: string;
    summary: string;
  }>;
  graph: {
    nodes: Array<Record<string, unknown>>;
    edges: Array<Record<string, unknown>>;
  };
};

export type PhaseScopeCheckResponse = {
  status: string;
  phase_check_id: string;
  phase_code: string;
  scope_status: string;
  scope_reason: string;
  evaluation: Record<string, unknown>;
  context: Record<string, unknown>;
};

export type SoarPlaybookRow = {
  playbook_id: string;
  playbook_code: string;
  title: string;
  category: string;
  description: string;
  version: string;
  scope: "community" | "partner" | "private";
  steps: string[];
  action_policy: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type SoarPlaybookListResponse = {
  count: number;
  rows: SoarPlaybookRow[];
};

export type SoarExecutionRow = {
  execution_id: string;
  site_id: string;
  playbook_id: string;
  status: string;
  requested_by: string;
  approved_by: string;
  approval_required: boolean;
  run_params: Record<string, unknown>;
  result: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type SoarExecutionListResponse = {
  count: number;
  rows: SoarExecutionRow[];
};

export type SoarConnectorResultContractRow = {
  contract_code: string;
  connector_source: string;
  playbook_codes: string[];
  required_fields: string[];
  success_statuses: string[];
  description: string;
  sample_payload: Record<string, unknown>;
};

export type SoarConnectorResultContractListResponse = {
  status: string;
  count: number;
  rows: SoarConnectorResultContractRow[];
};

export type SoarConnectorResultRow = {
  connector_result_id: string;
  site_id: string;
  execution_id: string;
  connector_source: string;
  contract_code: string;
  external_action_ref: string;
  webhook_event_id: string;
  status: string;
  actor: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type SoarConnectorResultResponse = {
  status: string;
  execution: SoarExecutionRow;
  connector_result: SoarConnectorResultRow;
  contract: {
    contract_code: string;
    connector_source: string;
    required_fields: string[];
    success_statuses: string[];
  };
};

export type SoarConnectorResultListResponse = {
  status: string;
  count: number;
  execution: SoarExecutionRow;
  rows: SoarConnectorResultRow[];
};

export type SoarMarketplaceOverview = {
  total_playbooks: number;
  active_playbooks: number;
  scope_counts: Record<string, number>;
  category_counts: Record<string, number>;
  marketplace_pack_count: number;
};

export type SoarMarketplacePackRow = {
  pack_code: string;
  title: string;
  audience: string;
  category: string;
  description: string;
  scope: "community" | "partner" | "private";
  playbook_count: number;
  playbooks: Array<{
    playbook_code: string;
    title: string;
    category: string;
    scope: string;
  }>;
};

export type SoarMarketplacePackListResponse = {
  count: number;
  rows: SoarMarketplacePackRow[];
};

export type SoarExecutionVerifyResponse = {
  status: string;
  execution: SoarExecutionRow;
  verification: {
    status: string;
    verified_at: string;
    verified_by: string;
    target_event_id: string;
    event_status: string;
    action_taken: string;
    action_reflected: boolean;
    connector_callback_confirmed: boolean;
    connector_results: SoarConnectorResultRow[];
    rollback_supported: boolean;
    issues: string[];
    recommendations: string[];
  };
};

export type ConnectorEventRow = {
  event_id: string;
  site_id: string;
  tenant_id: string;
  connector_source: string;
  event_type: string;
  status: string;
  latency_ms: number;
  attempt: number;
  payload: Record<string, unknown>;
  error_message: string;
  created_at: string;
};

export type ConnectorEventListResponse = {
  count: number;
  rows: ConnectorEventRow[];
};

export type ConnectorHealthResponse = {
  total_events: number;
  success_count: number;
  retry_count: number;
  dead_letter_count: number;
  failed_count: number;
  success_rate: number;
  average_latency_ms: number;
  sources: Array<{
    source: string;
    events: number;
    success_rate: number;
    dead_letter_count: number;
  }>;
};

export type ConnectorReliabilityPolicyResponse = {
  status: string;
  tenant_code?: string;
  policy: {
    policy_id: string;
    tenant_id: string;
    connector_source: string;
    max_replay_per_run: number;
    max_attempts: number;
    auto_replay_enabled: boolean;
    route_alert: boolean;
    schedule_interval_minutes: number;
    enabled: boolean;
    owner: string;
    created_at: string;
    updated_at: string;
  };
};

export type ConnectorReliabilityBacklogResponse = {
  status: string;
  tenant_id?: string;
  tenant_code?: string;
  connector_source?: string;
  count?: number;
  summary?: {
    dead_letter_count: number;
    replayed_count: number;
    unresolved_count: number;
  };
  rows?: Array<{
    event_id: string;
    tenant_id: string;
    site_id: string;
    connector_source: string;
    event_type: string;
    status: string;
    attempt: number;
    latency_ms: number;
    error_message: string;
    payload: Record<string, unknown>;
    replayed: boolean;
    created_at: string;
  }>;
  generated_at?: string;
};

export type ConnectorReliabilityRunRow = {
  run_id: string;
  tenant_id: string;
  connector_source: string;
  dry_run: boolean;
  status: string;
  backlog_count: number;
  selected_count: number;
  replayed_count: number;
  failed_count: number;
  skipped_count: number;
  risk_score: number;
  risk_tier: "low" | "medium" | "high" | "critical";
  alert_routed: boolean;
  details: Record<string, unknown>;
  created_at: string;
};

export type ConnectorReliabilityRunListResponse = {
  tenant_code?: string;
  count: number;
  rows: ConnectorReliabilityRunRow[];
};

export type ConnectorReliabilityReplayResponse = {
  status: string;
  tenant_id?: string;
  tenant_code?: string;
  dry_run?: boolean;
  policy?: ConnectorReliabilityPolicyResponse["policy"];
  execution?: {
    backlog_count: number;
    selected_count: number;
    replayed_count: number;
    failed_count: number;
    skipped_count: number;
    actions: Array<{
      event_id: string;
      connector_source: string;
      status: string;
      next_attempt: number;
    }>;
  };
  risk?: {
    risk_score: number;
    risk_tier: "low" | "medium" | "high" | "critical";
    recommendation: string;
  };
  alert?: Record<string, unknown>;
  run?: ConnectorReliabilityRunRow;
  generated_at?: string;
};

export type ConnectorReliabilitySchedulerResponse = {
  timestamp: string;
  scheduled_policy_count: number;
  executed_count: number;
  skipped_count: number;
  executed: Array<{
    tenant_code: string;
    connector_source: string;
    status: string;
    run_id: string;
    risk_tier: string;
  }>;
  skipped: Array<{
    tenant_id?: string;
    tenant_code?: string;
    connector_source: string;
    reason: string;
  }>;
};

export type ConnectorReliabilityFederationResponse = {
  count: number;
  tier_counts: Record<string, number>;
  summary: {
    total_unresolved_dead_letter: number;
    total_failed_replay: number;
    average_replay_success_rate: number;
  };
  rows: Array<{
    tenant_id: string;
    tenant_code: string;
    unresolved_dead_letter_count: number;
    replayed_count: number;
    failed_replay_count: number;
    replay_success_rate: number;
    risk_score: number;
    risk_tier: "low" | "medium" | "high" | "critical";
    recommendation: string;
  }>;
  generated_at: string;
};

export type SoarTenantPolicyResponse = {
  status: string;
  policy: {
    policy_id: string;
    tenant_id: string;
    policy_version: string;
    owner: string;
    require_approval_by_scope: Record<string, boolean>;
    require_approval_by_category: Record<string, boolean>;
    delegated_approvers: string[];
    blocked_playbook_codes: string[];
    allow_partner_scope: boolean;
    auto_approve_dry_run: boolean;
    created_at: string;
    updated_at: string;
  };
};

export type ConnectorSlaProfileResponse = {
  status: string;
  profile: {
    profile_id: string;
    tenant_id: string;
    connector_source: string;
    min_events: number;
    min_success_rate: number;
    max_dead_letter_count: number;
    max_average_latency_ms: number;
    notify_on_breach: boolean;
    enabled: boolean;
    created_at: string;
    updated_at: string;
  };
};

export type ConnectorSlaEvaluateResponse = {
  status: string;
  tenant_code: string;
  profile: ConnectorSlaProfileResponse["profile"];
  metrics: {
    total_events: number;
    success_count: number;
    success_rate: number;
    dead_letter_count: number;
    average_latency_ms: number;
    connector_source: string;
  };
  breach_detected: boolean;
  breach_reasons: string[];
  breach_severity: string;
  breach_id: string;
  routing: {
    status: string;
    event_id?: string;
    policy_min_severity?: string;
    telegram_status?: string;
    line_status?: string;
  };
};

export type ConnectorSlaBreachListResponse = {
  count: number;
  rows: Array<{
    breach_id: string;
    tenant_id: string;
    site_id: string;
    connector_source: string;
    severity: string;
    breach_reason: string;
    metrics: Record<string, unknown>;
    routed: boolean;
    created_at: string;
  }>;
};

export type ActionCenterPolicyResponse = {
  status: string;
  policy: {
    policy_id: string;
    tenant_id: string;
    policy_version: string;
    owner: string;
    telegram_enabled: boolean;
    line_enabled: boolean;
    min_severity: "low" | "medium" | "high" | "critical";
    routing_tags: string[];
    created_at: string;
    updated_at: string;
  };
};

export type ActionCenterDispatchResponse = {
  status: string;
  routing: {
    status: string;
    event_id: string;
    policy_min_severity: string;
    telegram_status: string;
    line_status: string;
  };
};

export type ActionCenterEventListResponse = {
  count: number;
  rows: Array<{
    event_id: string;
    tenant_id: string;
    site_id: string;
    source: string;
    severity: string;
    title: string;
    message: string;
    telegram_status: string;
    line_status: string;
    created_at: string;
  }>;
};

export type FederationActionCenterSlaResponse = {
  window_hours: number;
  count: number;
  tier_counts: Record<string, number>;
  generated_at: string;
  rows: Array<{
    tenant_id: string;
    tenant_code: string;
    breach_count: number;
    critical_breach_count: number;
    high_breach_count: number;
    routed_breach_count: number;
    dispatch_count: number;
    dispatch_high_or_critical_count: number;
    failed_channel_count: number;
    last_breach_at: string;
    last_dispatch_at: string;
    risk_score: number;
    risk_tier: "low" | "medium" | "high" | "critical";
    recommended_action: string;
  }>;
};

export type ConnectorCredentialVaultResponse = {
  status: string;
  credential: {
    credential_id: string;
    tenant_id: string;
    connector_source: string;
    credential_name: string;
    secret_version: number;
    secret_fingerprint_prefix: string;
    external_ref: string;
    rotation_interval_days: number;
    expires_at: string;
    metadata: Record<string, unknown>;
    is_active: boolean;
    last_rotated_at: string;
    created_at: string;
    updated_at: string;
  };
};

export type ConnectorCredentialVaultListResponse = {
  count: number;
  rows: ConnectorCredentialVaultResponse["credential"][];
};

export type ConnectorCredentialRotationEventListResponse = {
  count: number;
  rows: Array<{
    event_id: string;
    tenant_id: string;
    connector_source: string;
    credential_name: string;
    actor: string;
    rotation_reason: string;
    old_version: number;
    new_version: number;
    prev_signature: string;
    signature: string;
    details: Record<string, unknown>;
    created_at: string;
  }>;
};

export type ConnectorCredentialRotationVerifyResponse = {
  valid: boolean;
  count?: number;
  last_signature?: string;
  index?: number;
  reason?: string;
  expected_prev_signature?: string;
  actual_prev_signature?: string;
};

export type ConnectorCredentialHygieneResponse = {
  status: string;
  tenant_id?: string;
  tenant_code?: string;
  count?: number;
  summary?: {
    severity_counts: Record<string, number>;
    expired_count: number;
    rotation_due_count: number;
    warning_days: number;
  };
  risk?: {
    risk_score: number;
    risk_tier: "low" | "medium" | "high" | "critical";
    recommendation: string;
  };
  rows?: Array<{
    credential_id: string;
    tenant_id: string;
    connector_source: string;
    credential_name: string;
    secret_version: number;
    is_active: boolean;
    rotation_interval_days: number;
    age_days: number;
    expires_at: string;
    expires_in_days: number | null;
    rotation_due: boolean;
    expires_soon: boolean;
    expired: boolean;
    severity: "low" | "medium" | "high" | "critical";
    risk_score: number;
    recommendation: string;
  }>;
  generated_at?: string;
};

export type ConnectorCredentialAutoRotateResponse = {
  status: string;
  tenant_id?: string;
  tenant_code?: string;
  dry_run?: boolean;
  warning_days?: number;
  candidate_count?: number;
  selected_count?: number;
  planned_count?: number;
  executed_count?: number;
  failed_count?: number;
  actions?: Array<{
    connector_source: string;
    credential_name: string;
    status: string;
    reason?: string;
    severity?: string;
  }>;
  hygiene?: ConnectorCredentialHygieneResponse;
  alert?: Record<string, unknown>;
  generated_at?: string;
};

export type ConnectorCredentialHygieneFederationResponse = {
  count: number;
  tier_counts: Record<string, number>;
  summary: {
    total_credentials: number;
    total_rotation_due: number;
    total_expired: number;
  };
  rows: Array<{
    tenant_id: string;
    tenant_code: string;
    credential_count: number;
    rotation_due_count: number;
    expired_count: number;
    risk_score: number;
    risk_tier: "low" | "medium" | "high" | "critical";
    recommendation: string;
  }>;
  generated_at: string;
};

export type ConnectorCredentialHygienePolicyResponse = {
  status: string;
  tenant_code?: string;
  policy: {
    policy_id: string;
    tenant_id: string;
    connector_source: string;
    warning_days: number;
    max_rotate_per_run: number;
    auto_apply: boolean;
    route_alert: boolean;
    schedule_interval_minutes: number;
    enabled: boolean;
    owner: string;
    created_at: string;
    updated_at: string;
  };
};

export type ConnectorCredentialHygieneRunListResponse = {
  count: number;
  rows: Array<{
    run_id: string;
    tenant_id: string;
    connector_source: string;
    dry_run: boolean;
    status: string;
    candidate_count: number;
    selected_count: number;
    planned_count: number;
    executed_count: number;
    failed_count: number;
    risk_score: number;
    risk_tier: "low" | "medium" | "high" | "critical";
    alert_routed: boolean;
    details: Record<string, unknown>;
    created_at: string;
  }>;
};

export type ConnectorCredentialHygieneRunResponse = {
  status: string;
  tenant_id?: string;
  tenant_code?: string;
  policy?: ConnectorCredentialHygienePolicyResponse["policy"];
  execution?: ConnectorCredentialAutoRotateResponse;
  hygiene?: ConnectorCredentialHygieneResponse;
  alert?: Record<string, unknown>;
  run?: ConnectorCredentialHygieneRunListResponse["rows"][number];
};

export type ConnectorCredentialHygieneSchedulerResponse = {
  timestamp: string;
  scheduled_policy_count: number;
  executed_count: number;
  skipped_count: number;
  executed: Array<{
    tenant_code: string;
    connector_source: string;
    status: string;
    run_id: string;
    risk_tier: string;
  }>;
  skipped: Array<{
    tenant_id?: string;
    tenant_code?: string;
    connector_source: string;
    reason: string;
  }>;
};

export type TenantSecopsDataTierBenchmarkResponse = {
  status: string;
  tenant_id?: string;
  tenant_code?: string;
  lookback_hours?: number;
  event_counts?: {
    connector_events: number;
    integration_events: number;
    blue_events: number;
    total_events: number;
  };
  performance?: {
    throughput_eps: number;
    ingest_avg_latency_ms: number;
    search_latency_p50_ms: number;
    search_latency_p95_ms: number;
    dead_letter_count: number;
  };
  retention?: {
    estimated_storage_bytes: number;
    estimated_storage_gb: number;
    event_trend_hourly: Array<{ hour_epoch: number; event_count: number }>;
  };
  cost?: {
    monthly_storage_cost_usd: number;
    monthly_ingest_cost_usd: number;
    monthly_search_cost_usd: number;
    monthly_total_cost_usd: number;
    cost_budget_usd: number;
  };
  risk?: {
    risk_score: number;
    risk_tier: "low" | "medium" | "high" | "critical";
    recommendation: string;
  };
  generated_at?: string;
};

export type FederationSecopsDataTierResponse = {
  lookback_hours: number;
  count: number;
  tier_counts: Record<string, number>;
  summary: {
    average_throughput_eps: number;
    average_search_p95_ms: number;
    total_monthly_cost_usd: number;
  };
  rows: Array<{
    tenant_id: string;
    tenant_code: string;
    throughput_eps: number;
    ingest_avg_latency_ms: number;
    search_latency_p95_ms: number;
    monthly_total_cost_usd: number;
    risk_score: number;
    risk_tier: "low" | "medium" | "high" | "critical";
    recommendation: string;
  }>;
  generated_at: string;
};
