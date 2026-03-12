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

export type IntegrationAdaptersResponse = {
  count: number;
  adapters: Record<string, { name: string; ocsf_class: string }>;
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

export type SoarMarketplaceOverview = {
  total_playbooks: number;
  active_playbooks: number;
  scope_counts: Record<string, number>;
  category_counts: Record<string, number>;
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
