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
