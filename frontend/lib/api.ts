import type {
  ActionCenterDispatchResponse,
  ActionCenterEventListResponse,
  ActionCenterPolicyResponse,
  BlueIncidentFeed,
  CompetitiveAuthContextResponse,
  DashboardResponse,
  CompetitiveObjectivesResponse,
  ConnectorCredentialRotationEventListResponse,
  ConnectorCredentialAutoRotateResponse,
  ConnectorCredentialHygienePolicyResponse,
  ConnectorCredentialHygieneRunListResponse,
  ConnectorCredentialHygieneRunResponse,
  ConnectorCredentialHygieneSchedulerResponse,
  ConnectorCredentialHygieneFederationResponse,
  ConnectorCredentialHygieneResponse,
  ConnectorCredentialRotationVerifyResponse,
  ConnectorCredentialVaultListResponse,
  ConnectorCredentialVaultResponse,
  ConnectorSlaBreachListResponse,
  ConnectorReliabilityBacklogResponse,
  ConnectorReliabilityFederationResponse,
  ConnectorReliabilityPolicyResponse,
  ConnectorReliabilityReplayResponse,
  ConnectorReliabilityRunListResponse,
  ConnectorReliabilitySchedulerResponse,
  ConnectorSlaEvaluateResponse,
  ConnectorSlaProfileResponse,
  FederationActionCenterSlaResponse,
  FederationSecopsDataTierResponse,
  GovernanceDashboardResponse,
  SiteCaseGraphResponse,
  SiteDetectionCopilotTuneResponse,
  SiteDetectionAutotunePolicyResponse,
  SiteDetectionAutotuneRunListResponse,
  SiteDetectionAutotuneRunResponse,
  SiteDetectionRulesResponse,
  SiteRedExploitAutopilotPolicyResponse,
  SiteRedExploitAutopilotRunListResponse,
  SiteRedExploitAutopilotRunResponse,
  SiteExploitPathRunsResponse,
  SiteExploitPathSimulationResponse,
  IntegrationAdaptersResponse,
  IntegrationEventIngestResponse,
  OrchestratorState,
  SiteBlueEventHistoryResponse,
  SoarExecutionListResponse,
  SoarPlaybookListResponse,
  SoarMarketplaceOverview,
  SoarTenantPolicyResponse,
  ConnectorEventListResponse,
  ConnectorHealthResponse,
  SiteListResponse,
  SitePurpleReportHistoryResponse,
  SitePurpleExecutiveFederationResponse,
  SitePurpleExecutiveScorecardResponse,
  SitePurpleIsoGapTemplateResponse,
  ThreatContentPackListResponse,
  ThreatContentPipelineFederationResponse,
  ThreatContentPipelinePolicyResponse,
  ThreatContentPipelineRunListResponse,
  ThreatContentPipelineRunResponse,
  PhaseScopeCheckResponse,
  SiteRedScanHistoryResponse,
  SiteRedScanResponse,
  SiteUpsertResponse,
  PurpleReport,
  RedRunResult,
  RedScenarioLibrary,
  TenantGateResponse,
  TenantHistoryResponse,
  TenantSecopsDataTierBenchmarkResponse,
  TenantRemediation,
} from "./types";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const controlPlaneToken = process.env.NEXT_PUBLIC_CONTROL_PLANE_BEARER || "";

function resolveToken(path: string, token?: string): string {
  if (token) return token;
  if (path.startsWith("/competitive/")) return controlPlaneToken;
  return "";
}

async function getJson<T>(path: string, token?: string): Promise<T> {
  const headers: Record<string, string> = {};
  const resolvedToken = resolveToken(path, token);
  if (resolvedToken) {
    headers.Authorization = `Bearer ${resolvedToken}`;
  }

  const res = await fetch(`${baseUrl}${path}`, { cache: "no-store", headers });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

async function postJson<T>(path: string, body: unknown, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const resolvedToken = resolveToken(path, token);
  if (resolvedToken) {
    headers.Authorization = `Bearer ${resolvedToken}`;
  }
  const res = await fetch(`${baseUrl}${path}`, {
    method: "POST",
    cache: "no-store",
    headers,
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export function fetchDashboard(limit = 100): Promise<DashboardResponse> {
  return getJson<DashboardResponse>(`/enterprise/objective-gate-dashboard?limit=${limit}`);
}

export function fetchTenantGate(tenantId: string): Promise<TenantGateResponse> {
  return getJson<TenantGateResponse>(`/enterprise/objective-gate/${tenantId}`);
}

export function fetchTenantHistory(tenantId: string, limit = 20): Promise<TenantHistoryResponse> {
  return getJson<TenantHistoryResponse>(`/enterprise/objective-gate-history/${tenantId}?limit=${limit}`);
}

export function fetchTenantRemediation(tenantId: string): Promise<TenantRemediation> {
  return getJson<TenantRemediation>(`/enterprise/objective-gate-remediation/${tenantId}`);
}

export function fetchGovernanceDashboard(limit = 1000): Promise<GovernanceDashboardResponse> {
  return getJson<GovernanceDashboardResponse>(`/control-plane/governance/dashboard?limit=${limit}`, controlPlaneToken);
}

export function fetchRedScenarios(): Promise<RedScenarioLibrary> {
  return getJson<RedScenarioLibrary>("/red-sim/scenarios");
}

export function runRedScenario(payload: {
  tenant_id: string;
  scenario_name: string;
  target_asset: string;
  events_count: number;
}): Promise<RedRunResult> {
  return postJson<RedRunResult>("/red-sim/run", payload);
}

export function fetchBlueIncidents(tenantId: string, limit = 50): Promise<BlueIncidentFeed> {
  return getJson<BlueIncidentFeed>(`/ingest/incidents/${tenantId}?limit=${limit}`);
}

export function fetchOrchestratorState(tenantId: string): Promise<OrchestratorState> {
  return getJson<OrchestratorState>(`/orchestrator/state/${tenantId}`);
}

export function updateBluePolicy(payload: {
  tenant_id: string;
  failed_login_threshold_per_minute: number;
  failure_window_seconds: number;
  incident_cooldown_seconds: number;
}): Promise<{ tenant_id: string }> {
  return postJson<{ tenant_id: string }>("/orchestrator/blue-policy", payload);
}

export function pauseTenant(tenantId: string): Promise<{ status: string }> {
  return postJson<{ status: string }>(`/orchestrator/pause/${tenantId}`, {});
}

export function fetchPurpleReports(tenantId: string, limit = 20): Promise<{ tenant_id: string; count: number; reports: PurpleReport[] }> {
  return getJson<{ tenant_id: string; count: number; reports: PurpleReport[] }>(`/purple/report/${tenantId}?limit=${limit}`);
}

export function generatePurpleDailyReport(tenantId: string): Promise<PurpleReport> {
  return postJson<PurpleReport>(`/purple/report/${tenantId}/daily`, {});
}

export function fetchSites(tenantCode = "", limit = 200): Promise<SiteListResponse> {
  const query = new URLSearchParams();
  if (tenantCode) query.set("tenant_code", tenantCode);
  query.set("limit", String(limit));
  return getJson<SiteListResponse>(`/sites?${query.toString()}`);
}

export function upsertSite(payload: {
  tenant_code: string;
  site_code: string;
  display_name: string;
  base_url: string;
  is_active?: boolean;
  config?: Record<string, unknown>;
}): Promise<SiteUpsertResponse> {
  return postJson<SiteUpsertResponse>("/sites", payload);
}

export function runSiteRedScan(siteId: string, payload: { scan_type: string; include_paths?: string[] }): Promise<SiteRedScanResponse> {
  return postJson<SiteRedScanResponse>(`/sites/${siteId}/red/scan`, payload);
}

export function fetchSiteRedScans(siteId: string, limit = 30): Promise<SiteRedScanHistoryResponse> {
  return getJson<SiteRedScanHistoryResponse>(`/sites/${siteId}/red/scans?limit=${limit}`);
}

export function ingestSiteBlueEvent(
  siteId: string,
  payload: {
    event_type: string;
    source_ip: string;
    path: string;
    method: string;
    status_code: number;
    message: string;
    payload?: Record<string, unknown>;
  },
): Promise<{ status: string; event_id: string; ai: { severity: string; recommendation: string } }> {
  return postJson(`/sites/${siteId}/blue/events`, payload);
}

export function fetchSiteBlueEvents(siteId: string, limit = 100): Promise<SiteBlueEventHistoryResponse> {
  return getJson<SiteBlueEventHistoryResponse>(`/sites/${siteId}/blue/events?limit=${limit}`);
}

export function applySiteBlueRecommendation(
  siteId: string,
  eventId: string,
  action: "block_ip" | "notify_team" | "limit_user" | "ignore",
): Promise<{ status: string; event_id: string; action: string }> {
  return postJson(`/sites/${siteId}/blue/events/${eventId}/apply`, { action });
}

export function generateSitePurpleAnalysis(siteId: string): Promise<{
  status: string;
  report_id: string;
  summary: string;
  metrics: Record<string, unknown>;
  ai_analysis: Record<string, unknown>;
}> {
  return postJson(`/sites/${siteId}/purple/analyze`, {});
}

export function fetchSitePurpleReports(siteId: string, limit = 30): Promise<SitePurpleReportHistoryResponse> {
  return getJson<SitePurpleReportHistoryResponse>(`/sites/${siteId}/purple/reports?limit=${limit}`);
}

export function fetchSitePurpleIsoGapTemplate(siteId: string, limit = 200): Promise<SitePurpleIsoGapTemplateResponse> {
  return getJson<SitePurpleIsoGapTemplateResponse>(`/sites/${siteId}/purple/iso27001-gap-template?limit=${limit}`);
}

export function fetchSitePurpleExecutiveScorecard(
  siteId: string,
  params?: { lookback_runs?: number; lookback_events?: number; sla_target_seconds?: number },
): Promise<SitePurpleExecutiveScorecardResponse> {
  const query = new URLSearchParams();
  query.set("lookback_runs", String(params?.lookback_runs ?? 30));
  query.set("lookback_events", String(params?.lookback_events ?? 500));
  query.set("sla_target_seconds", String(params?.sla_target_seconds ?? 120));
  return getJson<SitePurpleExecutiveScorecardResponse>(`/sites/${siteId}/purple/executive-scorecard?${query.toString()}`);
}

export function fetchSitePurpleExecutiveFederation(params?: {
  limit?: number;
  lookback_runs?: number;
  lookback_events?: number;
  sla_target_seconds?: number;
}): Promise<SitePurpleExecutiveFederationResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 200));
  query.set("lookback_runs", String(params?.lookback_runs ?? 30));
  query.set("lookback_events", String(params?.lookback_events ?? 500));
  query.set("sla_target_seconds", String(params?.sla_target_seconds ?? 120));
  return getJson<SitePurpleExecutiveFederationResponse>(`/sites/purple/executive-federation?${query.toString()}`);
}

export function fetchIntegrationAdapters(): Promise<IntegrationAdaptersResponse> {
  return getJson<IntegrationAdaptersResponse>("/integrations/adapters");
}

export function ingestIntegrationEvent(payload: {
  source: string;
  event_kind?: string;
  site_id?: string;
  tenant_code?: string;
  site_code?: string;
  payload: Record<string, unknown>;
  webhook_event_id?: string;
}): Promise<IntegrationEventIngestResponse> {
  return postJson<IntegrationEventIngestResponse>("/integrations/events", payload);
}

export function fetchCompetitiveObjectives(): Promise<CompetitiveObjectivesResponse> {
  return getJson<CompetitiveObjectivesResponse>("/competitive/objectives");
}

export function fetchCompetitiveAuthContext(): Promise<CompetitiveAuthContextResponse> {
  return getJson<CompetitiveAuthContextResponse>("/competitive/auth/context");
}

export function fetchThreatContentPacks(params?: { category?: string; active_only?: boolean; limit?: number }): Promise<ThreatContentPackListResponse> {
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  if (params?.active_only !== undefined) query.set("active_only", String(params.active_only));
  query.set("limit", String(params?.limit ?? 200));
  return getJson<ThreatContentPackListResponse>(`/competitive/threat-content/packs?${query.toString()}`);
}

export function upsertThreatContentPack(payload: {
  pack_code: string;
  title: string;
  category?: string;
  mitre_techniques?: string[];
  attack_steps?: string[];
  validation_mode?: string;
  is_active?: boolean;
}): Promise<{ status: string; pack: Record<string, unknown> }> {
  return postJson<{ status: string; pack: Record<string, unknown> }>("/competitive/threat-content/packs", payload);
}

export function fetchThreatContentPipelinePolicy(scope = "global"): Promise<ThreatContentPipelinePolicyResponse> {
  const query = new URLSearchParams();
  query.set("scope", scope);
  return getJson<ThreatContentPipelinePolicyResponse>(`/competitive/threat-content/pipeline/policies?${query.toString()}`);
}

export function upsertThreatContentPipelinePolicy(payload: {
  scope?: string;
  min_refresh_interval_minutes?: number;
  preferred_categories?: string[];
  max_packs_per_run?: number;
  auto_activate?: boolean;
  route_alert?: boolean;
  enabled?: boolean;
  owner?: string;
}): Promise<ThreatContentPipelinePolicyResponse> {
  return postJson<ThreatContentPipelinePolicyResponse>("/competitive/threat-content/pipeline/policies", payload);
}

export function runThreatContentPipeline(payload?: {
  scope?: string;
  dry_run?: boolean | null;
  force?: boolean;
  actor?: string;
}): Promise<ThreatContentPipelineRunResponse> {
  return postJson<ThreatContentPipelineRunResponse>("/competitive/threat-content/pipeline/run", payload ?? {});
}

export function fetchThreatContentPipelineRuns(params?: {
  scope?: string;
  limit?: number;
}): Promise<ThreatContentPipelineRunListResponse> {
  const query = new URLSearchParams();
  if (params?.scope) query.set("scope", params.scope);
  query.set("limit", String(params?.limit ?? 100));
  return getJson<ThreatContentPipelineRunListResponse>(`/competitive/threat-content/pipeline/runs?${query.toString()}`);
}

export function runThreatContentPipelineScheduler(params?: {
  limit?: number;
  dry_run_override?: boolean;
  actor?: string;
}): Promise<{
  timestamp: string;
  scheduled_policy_count: number;
  executed_count: number;
  skipped_count: number;
}> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 200));
  if (params?.dry_run_override !== undefined) query.set("dry_run_override", String(params.dry_run_override));
  if (params?.actor) query.set("actor", params.actor);
  return postJson(`/competitive/threat-content/pipeline/scheduler/run?${query.toString()}`, {});
}

export function fetchThreatContentPipelineFederation(params?: {
  limit?: number;
  stale_after_hours?: number;
}): Promise<ThreatContentPipelineFederationResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 200));
  query.set("stale_after_hours", String(params?.stale_after_hours ?? 48));
  return getJson<ThreatContentPipelineFederationResponse>(`/competitive/threat-content/pipeline/federation?${query.toString()}`);
}

export function simulateSiteExploitPath(
  siteId: string,
  payload?: {
    threat_pack_code?: string;
    target_surface?: string;
    simulation_depth?: number;
    max_requests_per_minute?: number;
    stop_on_critical?: boolean;
    simulation_only?: boolean;
  },
): Promise<SiteExploitPathSimulationResponse> {
  return postJson<SiteExploitPathSimulationResponse>(`/competitive/sites/${siteId}/red/exploit-path/simulate`, payload ?? {});
}

export function fetchSiteExploitPathRuns(siteId: string, limit = 20): Promise<SiteExploitPathRunsResponse> {
  return getJson<SiteExploitPathRunsResponse>(`/competitive/sites/${siteId}/red/exploit-path/runs?limit=${limit}`);
}

export function fetchSiteRedExploitAutopilotPolicy(siteId: string): Promise<SiteRedExploitAutopilotPolicyResponse> {
  return getJson<SiteRedExploitAutopilotPolicyResponse>(`/competitive/sites/${siteId}/red/exploit-autopilot/policy`);
}

export function upsertSiteRedExploitAutopilotPolicy(
  siteId: string,
  payload: {
    min_risk_score?: number;
    min_risk_tier?: "low" | "medium" | "high" | "critical";
    preferred_pack_category?: string;
    target_surface?: string;
    simulation_depth?: number;
    max_requests_per_minute?: number;
    stop_on_critical?: boolean;
    simulation_only?: boolean;
    auto_run?: boolean;
    route_alert?: boolean;
    schedule_interval_minutes?: number;
    enabled?: boolean;
    owner?: string;
  },
): Promise<SiteRedExploitAutopilotPolicyResponse> {
  return postJson<SiteRedExploitAutopilotPolicyResponse>(`/competitive/sites/${siteId}/red/exploit-autopilot/policy`, payload);
}

export function runSiteRedExploitAutopilot(
  siteId: string,
  payload?: { dry_run?: boolean | null; force?: boolean; actor?: string },
): Promise<SiteRedExploitAutopilotRunResponse> {
  return postJson<SiteRedExploitAutopilotRunResponse>(`/competitive/sites/${siteId}/red/exploit-autopilot/run`, payload ?? {});
}

export function fetchSiteRedExploitAutopilotRuns(siteId: string, limit = 30): Promise<SiteRedExploitAutopilotRunListResponse> {
  return getJson<SiteRedExploitAutopilotRunListResponse>(`/competitive/sites/${siteId}/red/exploit-autopilot/runs?limit=${limit}`);
}

export function runRedExploitAutopilotScheduler(params?: {
  limit?: number;
  dry_run_override?: boolean;
  actor?: string;
}): Promise<{
  timestamp: string;
  scheduled_policy_count: number;
  executed_count: number;
  skipped_count: number;
}> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 200));
  if (params?.dry_run_override !== undefined) query.set("dry_run_override", String(params.dry_run_override));
  if (params?.actor) query.set("actor", params.actor);
  return postJson(`/competitive/red/exploit-autopilot/scheduler/run?${query.toString()}`, {});
}

export function runSiteDetectionCopilotTune(
  siteId: string,
  payload?: { exploit_path_run_id?: string; rule_count?: number; auto_apply?: boolean; dry_run?: boolean },
): Promise<SiteDetectionCopilotTuneResponse> {
  return postJson<SiteDetectionCopilotTuneResponse>(`/competitive/sites/${siteId}/blue/detection-copilot/tune`, payload ?? {});
}

export function fetchSiteDetectionRules(siteId: string, limit = 100): Promise<SiteDetectionRulesResponse> {
  return getJson<SiteDetectionRulesResponse>(`/competitive/sites/${siteId}/blue/detection-copilot/rules?limit=${limit}`);
}

export function fetchSiteDetectionAutotunePolicy(siteId: string): Promise<SiteDetectionAutotunePolicyResponse> {
  return getJson<SiteDetectionAutotunePolicyResponse>(`/competitive/sites/${siteId}/blue/detection-autotune/policy`);
}

export function upsertSiteDetectionAutotunePolicy(
  siteId: string,
  payload: {
    min_risk_score?: number;
    min_risk_tier?: "low" | "medium" | "high" | "critical";
    target_detection_coverage_pct?: number;
    max_rules_per_run?: number;
    auto_apply?: boolean;
    route_alert?: boolean;
    schedule_interval_minutes?: number;
    enabled?: boolean;
    owner?: string;
  },
): Promise<SiteDetectionAutotunePolicyResponse> {
  return postJson<SiteDetectionAutotunePolicyResponse>(`/competitive/sites/${siteId}/blue/detection-autotune/policy`, payload);
}

export function runSiteDetectionAutotune(
  siteId: string,
  payload?: { dry_run?: boolean | null; force?: boolean; actor?: string },
): Promise<SiteDetectionAutotuneRunResponse> {
  return postJson<SiteDetectionAutotuneRunResponse>(`/competitive/sites/${siteId}/blue/detection-autotune/run`, payload ?? {});
}

export function fetchSiteDetectionAutotuneRuns(siteId: string, limit = 30): Promise<SiteDetectionAutotuneRunListResponse> {
  return getJson<SiteDetectionAutotuneRunListResponse>(`/competitive/sites/${siteId}/blue/detection-autotune/runs?limit=${limit}`);
}

export function runDetectionAutotuneScheduler(params?: {
  limit?: number;
  dry_run_override?: boolean;
  actor?: string;
}): Promise<{
  timestamp: string;
  scheduled_policy_count: number;
  executed_count: number;
  skipped_count: number;
}> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 200));
  if (params?.dry_run_override !== undefined) query.set("dry_run_override", String(params.dry_run_override));
  if (params?.actor) query.set("actor", params.actor);
  return postJson(`/competitive/blue/detection-autotune/scheduler/run?${query.toString()}`, {});
}

export function applySiteDetectionRule(siteId: string, ruleId: string, apply = true): Promise<{ status: string; rule_status: string }> {
  return postJson<{ status: string; rule_status: string }>(
    `/competitive/sites/${siteId}/blue/detection-copilot/rules/${ruleId}/apply`,
    { apply },
  );
}

export function fetchSiteCaseGraph(siteId: string, limit = 50): Promise<SiteCaseGraphResponse> {
  return getJson<SiteCaseGraphResponse>(`/competitive/sites/${siteId}/case-graph?limit=${limit}`);
}

export function createPhaseScopeCheck(payload: {
  phase_code: string;
  phase_title?: string;
  objective_ids: string[];
  deliverables: string[];
  site_id?: string;
  context?: Record<string, unknown>;
}): Promise<PhaseScopeCheckResponse> {
  return postJson<PhaseScopeCheckResponse>("/competitive/phases/check", payload);
}

export function fetchSoarPlaybooks(params?: { category?: string; scope?: string; active_only?: boolean; limit?: number }): Promise<SoarPlaybookListResponse> {
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  if (params?.scope) query.set("scope", params.scope);
  if (params?.active_only !== undefined) query.set("active_only", String(params.active_only));
  query.set("limit", String(params?.limit ?? 200));
  return getJson<SoarPlaybookListResponse>(`/competitive/soar/playbooks?${query.toString()}`);
}

export function upsertSoarPlaybook(payload: {
  playbook_code: string;
  title: string;
  category?: string;
  description?: string;
  version?: string;
  scope?: "community" | "partner" | "private";
  steps?: string[];
  action_policy?: Record<string, unknown>;
  is_active?: boolean;
}): Promise<{ status: string; playbook: Record<string, unknown> }> {
  return postJson<{ status: string; playbook: Record<string, unknown> }>("/competitive/soar/playbooks", payload);
}

export function fetchSoarMarketplaceOverview(limit = 500): Promise<SoarMarketplaceOverview> {
  return getJson<SoarMarketplaceOverview>(`/competitive/soar/marketplace/overview?limit=${limit}`);
}

export function upsertTenantPlaybookPolicy(payload: {
  tenant_code: string;
  policy_version?: string;
  owner?: string;
  require_approval_by_scope?: Record<string, boolean>;
  require_approval_by_category?: Record<string, boolean>;
  delegated_approvers?: string[];
  blocked_playbook_codes?: string[];
  allow_partner_scope?: boolean;
  auto_approve_dry_run?: boolean;
}): Promise<{ status: string; policy: Record<string, unknown> }> {
  return postJson<{ status: string; policy: Record<string, unknown> }>("/competitive/soar/policies/playbook", payload);
}

export function fetchTenantPlaybookPolicy(tenantCode: string): Promise<SoarTenantPolicyResponse> {
  const query = new URLSearchParams();
  query.set("tenant_code", tenantCode);
  return getJson<SoarTenantPolicyResponse>(`/competitive/soar/policies/playbook?${query.toString()}`);
}

export function executeSoarPlaybook(
  siteId: string,
  playbookCode: string,
  payload?: { actor?: string; require_approval?: boolean; dry_run?: boolean; params?: Record<string, unknown> },
): Promise<{ status: string; execution: Record<string, unknown>; playbook: Record<string, unknown> }> {
  return postJson<{ status: string; execution: Record<string, unknown>; playbook: Record<string, unknown> }>(
    `/competitive/sites/${siteId}/soar/playbooks/${playbookCode}/execute`,
    payload ?? {},
  );
}

export function fetchSiteSoarExecutions(siteId: string, params?: { status?: string; limit?: number }): Promise<SoarExecutionListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  query.set("limit", String(params?.limit ?? 200));
  return getJson<SoarExecutionListResponse>(`/competitive/sites/${siteId}/soar/executions?${query.toString()}`);
}

export function approveSoarExecution(
  executionId: string,
  payload: { approve: boolean; approver: string; note?: string },
): Promise<{ status: string; execution: Record<string, unknown> }> {
  return postJson<{ status: string; execution: Record<string, unknown> }>(`/competitive/soar/executions/${executionId}/approve`, payload);
}

export function ingestConnectorEvent(payload: {
  connector_source: string;
  event_type?: "delivery_attempt" | "retry" | "dead_letter" | "health";
  status?: "success" | "retrying" | "failed" | "degraded";
  tenant_id?: string;
  site_id?: string;
  latency_ms?: number;
  attempt?: number;
  payload?: Record<string, unknown>;
  error_message?: string;
}): Promise<{ status: string; event_id: string; connector_source: string; event_type: string; event_status: string }> {
  return postJson("/competitive/connectors/events", payload);
}

export function fetchConnectorEvents(params?: {
  connector_source?: string;
  status?: string;
  tenant_id?: string;
  site_id?: string;
  limit?: number;
}): Promise<ConnectorEventListResponse> {
  const query = new URLSearchParams();
  if (params?.connector_source) query.set("connector_source", params.connector_source);
  if (params?.status) query.set("status", params.status);
  if (params?.tenant_id) query.set("tenant_id", params.tenant_id);
  if (params?.site_id) query.set("site_id", params.site_id);
  query.set("limit", String(params?.limit ?? 200));
  return getJson<ConnectorEventListResponse>(`/competitive/connectors/events?${query.toString()}`);
}

export function fetchConnectorHealth(limit = 2000): Promise<ConnectorHealthResponse> {
  return getJson<ConnectorHealthResponse>(`/competitive/connectors/health?limit=${limit}`);
}

export function upsertConnectorReliabilityPolicy(payload: {
  tenant_code: string;
  connector_source?: string;
  max_replay_per_run?: number;
  max_attempts?: number;
  auto_replay_enabled?: boolean;
  route_alert?: boolean;
  schedule_interval_minutes?: number;
  enabled?: boolean;
  owner?: string;
}): Promise<ConnectorReliabilityPolicyResponse> {
  return postJson<ConnectorReliabilityPolicyResponse>("/competitive/connectors/reliability/policies", payload);
}

export function fetchConnectorReliabilityPolicy(params: {
  tenant_code: string;
  connector_source?: string;
}): Promise<ConnectorReliabilityPolicyResponse> {
  const query = new URLSearchParams();
  query.set("tenant_code", params.tenant_code);
  query.set("connector_source", params.connector_source ?? "*");
  return getJson<ConnectorReliabilityPolicyResponse>(`/competitive/connectors/reliability/policies?${query.toString()}`);
}

export function fetchConnectorReliabilityBacklog(params: {
  tenant_code: string;
  connector_source?: string;
  limit?: number;
}): Promise<ConnectorReliabilityBacklogResponse> {
  const query = new URLSearchParams();
  query.set("tenant_code", params.tenant_code);
  if (params.connector_source) query.set("connector_source", params.connector_source);
  query.set("limit", String(params.limit ?? 200));
  return getJson<ConnectorReliabilityBacklogResponse>(`/competitive/connectors/reliability/backlog?${query.toString()}`);
}

export function runConnectorReliabilityReplay(payload: {
  tenant_code: string;
  connector_source?: string;
  dry_run?: boolean | null;
  actor?: string;
}): Promise<ConnectorReliabilityReplayResponse> {
  return postJson<ConnectorReliabilityReplayResponse>("/competitive/connectors/reliability/replay", payload);
}

export function fetchConnectorReliabilityRuns(params?: {
  tenant_code?: string;
  limit?: number;
}): Promise<ConnectorReliabilityRunListResponse> {
  const query = new URLSearchParams();
  if (params?.tenant_code) query.set("tenant_code", params.tenant_code);
  query.set("limit", String(params?.limit ?? 100));
  return getJson<ConnectorReliabilityRunListResponse>(`/competitive/connectors/reliability/runs?${query.toString()}`);
}

export function runConnectorReliabilityScheduler(params?: {
  limit?: number;
  dry_run_override?: boolean;
  actor?: string;
}): Promise<ConnectorReliabilitySchedulerResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 200));
  if (params?.dry_run_override !== undefined) query.set("dry_run_override", String(params.dry_run_override));
  if (params?.actor) query.set("actor", params.actor);
  return postJson<ConnectorReliabilitySchedulerResponse>(
    `/competitive/connectors/reliability/scheduler/run?${query.toString()}`,
    {},
  );
}

export function fetchConnectorReliabilityFederation(limit = 200): Promise<ConnectorReliabilityFederationResponse> {
  return getJson<ConnectorReliabilityFederationResponse>(`/competitive/connectors/reliability/federation?limit=${limit}`);
}

export function upsertConnectorCredential(payload: {
  tenant_code: string;
  connector_source: string;
  credential_name?: string;
  secret_value: string;
  rotation_interval_days?: number;
  external_ref?: string;
  expires_at?: string;
  metadata?: Record<string, unknown>;
  actor?: string;
}): Promise<ConnectorCredentialVaultResponse> {
  return postJson<ConnectorCredentialVaultResponse>("/competitive/connectors/credentials", payload);
}

export function fetchConnectorCredentials(params: {
  tenant_code: string;
  connector_source?: string;
  limit?: number;
}): Promise<ConnectorCredentialVaultListResponse> {
  const query = new URLSearchParams();
  query.set("tenant_code", params.tenant_code);
  if (params.connector_source) query.set("connector_source", params.connector_source);
  query.set("limit", String(params.limit ?? 200));
  return getJson<ConnectorCredentialVaultListResponse>(`/competitive/connectors/credentials?${query.toString()}`);
}

export function rotateConnectorCredential(payload: {
  tenant_code: string;
  connector_source: string;
  credential_name?: string;
  new_secret_value?: string;
  rotation_reason?: string;
  actor?: string;
}): Promise<{ status: string; credential: ConnectorCredentialVaultResponse["credential"]; generated_secret: boolean }> {
  return postJson<{ status: string; credential: ConnectorCredentialVaultResponse["credential"]; generated_secret: boolean }>(
    "/competitive/connectors/credentials/rotate",
    payload,
  );
}

export function fetchConnectorCredentialRotationEvents(params: {
  tenant_code: string;
  connector_source?: string;
  credential_name?: string;
  limit?: number;
}): Promise<ConnectorCredentialRotationEventListResponse> {
  const query = new URLSearchParams();
  query.set("tenant_code", params.tenant_code);
  if (params.connector_source) query.set("connector_source", params.connector_source);
  if (params.credential_name) query.set("credential_name", params.credential_name);
  query.set("limit", String(params.limit ?? 200));
  return getJson<ConnectorCredentialRotationEventListResponse>(
    `/competitive/connectors/credentials/rotation-events?${query.toString()}`,
  );
}

export function verifyConnectorCredentialRotation(params: {
  tenant_code: string;
  connector_source?: string;
  credential_name?: string;
  limit?: number;
}): Promise<ConnectorCredentialRotationVerifyResponse> {
  const query = new URLSearchParams();
  query.set("tenant_code", params.tenant_code);
  if (params.connector_source) query.set("connector_source", params.connector_source);
  if (params.credential_name) query.set("credential_name", params.credential_name);
  query.set("limit", String(params.limit ?? 5000));
  return getJson<ConnectorCredentialRotationVerifyResponse>(
    `/competitive/connectors/credentials/rotation-verify?${query.toString()}`,
  );
}

export function fetchConnectorCredentialHygiene(params: {
  tenant_code: string;
  connector_source?: string;
  warning_days?: number;
  limit?: number;
}): Promise<ConnectorCredentialHygieneResponse> {
  const query = new URLSearchParams();
  query.set("tenant_code", params.tenant_code);
  if (params.connector_source) query.set("connector_source", params.connector_source);
  query.set("warning_days", String(params.warning_days ?? 7));
  query.set("limit", String(params.limit ?? 200));
  return getJson<ConnectorCredentialHygieneResponse>(`/competitive/connectors/credentials/hygiene?${query.toString()}`);
}

export function runConnectorCredentialAutoRotate(payload: {
  tenant_code: string;
  connector_source?: string;
  warning_days?: number;
  max_rotate?: number;
  dry_run?: boolean;
  actor?: string;
  route_alert?: boolean;
}): Promise<ConnectorCredentialAutoRotateResponse> {
  return postJson<ConnectorCredentialAutoRotateResponse>("/competitive/connectors/credentials/auto-rotate", payload);
}

export function fetchConnectorCredentialHygieneFederation(params?: {
  warning_days?: number;
  limit?: number;
}): Promise<ConnectorCredentialHygieneFederationResponse> {
  const query = new URLSearchParams();
  query.set("warning_days", String(params?.warning_days ?? 7));
  query.set("limit", String(params?.limit ?? 200));
  return getJson<ConnectorCredentialHygieneFederationResponse>(
    `/competitive/connectors/credentials/hygiene/federation?${query.toString()}`,
  );
}

export function upsertConnectorCredentialHygienePolicy(payload: {
  tenant_code: string;
  connector_source?: string;
  warning_days?: number;
  max_rotate_per_run?: number;
  auto_apply?: boolean;
  route_alert?: boolean;
  schedule_interval_minutes?: number;
  enabled?: boolean;
  owner?: string;
}): Promise<ConnectorCredentialHygienePolicyResponse> {
  return postJson<ConnectorCredentialHygienePolicyResponse>("/competitive/connectors/credentials/hygiene/policies", payload);
}

export function fetchConnectorCredentialHygienePolicy(params: {
  tenant_code: string;
  connector_source?: string;
}): Promise<ConnectorCredentialHygienePolicyResponse> {
  const query = new URLSearchParams();
  query.set("tenant_code", params.tenant_code);
  query.set("connector_source", params.connector_source ?? "*");
  return getJson<ConnectorCredentialHygienePolicyResponse>(
    `/competitive/connectors/credentials/hygiene/policies?${query.toString()}`,
  );
}

export function runConnectorCredentialHygiene(payload: {
  tenant_code: string;
  connector_source?: string;
  dry_run?: boolean | null;
  actor?: string;
}): Promise<ConnectorCredentialHygieneRunResponse> {
  return postJson<ConnectorCredentialHygieneRunResponse>("/competitive/connectors/credentials/hygiene/run", payload);
}

export function fetchConnectorCredentialHygieneRuns(params?: {
  tenant_code?: string;
  limit?: number;
}): Promise<ConnectorCredentialHygieneRunListResponse> {
  const query = new URLSearchParams();
  if (params?.tenant_code) query.set("tenant_code", params.tenant_code);
  query.set("limit", String(params?.limit ?? 100));
  return getJson<ConnectorCredentialHygieneRunListResponse>(`/competitive/connectors/credentials/hygiene/runs?${query.toString()}`);
}

export function runConnectorCredentialHygieneScheduler(params?: {
  limit?: number;
  dry_run_override?: boolean;
  actor?: string;
}): Promise<ConnectorCredentialHygieneSchedulerResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 200));
  if (params?.dry_run_override !== undefined) query.set("dry_run_override", String(params.dry_run_override));
  if (params?.actor) query.set("actor", params.actor);
  return postJson<ConnectorCredentialHygieneSchedulerResponse>(
    `/competitive/connectors/credentials/hygiene/scheduler/run?${query.toString()}`,
    {},
  );
}

export function fetchActionCenterSlaFederation(params?: {
  lookback_hours?: number;
  limit?: number;
}): Promise<FederationActionCenterSlaResponse> {
  const query = new URLSearchParams();
  query.set("lookback_hours", String(params?.lookback_hours ?? 24));
  query.set("limit", String(params?.limit ?? 200));
  return getJson<FederationActionCenterSlaResponse>(`/competitive/federation/action-center-sla?${query.toString()}`);
}

export function fetchTenantSecopsDataTierBenchmark(
  tenantCode: string,
  params?: { lookback_hours?: number; sample_limit?: number },
): Promise<TenantSecopsDataTierBenchmarkResponse> {
  const query = new URLSearchParams();
  query.set("tenant_code", tenantCode);
  query.set("lookback_hours", String(params?.lookback_hours ?? 24));
  query.set("sample_limit", String(params?.sample_limit ?? 2000));
  return getJson<TenantSecopsDataTierBenchmarkResponse>(`/competitive/secops/data-tier/benchmark?${query.toString()}`);
}

export function fetchFederationSecopsDataTier(params?: {
  lookback_hours?: number;
  limit?: number;
}): Promise<FederationSecopsDataTierResponse> {
  const query = new URLSearchParams();
  query.set("lookback_hours", String(params?.lookback_hours ?? 24));
  query.set("limit", String(params?.limit ?? 200));
  return getJson<FederationSecopsDataTierResponse>(`/competitive/secops/data-tier/federation?${query.toString()}`);
}

export function upsertConnectorSlaProfile(payload: {
  tenant_code: string;
  connector_source?: string;
  min_events?: number;
  min_success_rate?: number;
  max_dead_letter_count?: number;
  max_average_latency_ms?: number;
  notify_on_breach?: boolean;
  enabled?: boolean;
}): Promise<{ status: string; profile: Record<string, unknown> }> {
  return postJson<{ status: string; profile: Record<string, unknown> }>("/competitive/connectors/sla/profiles", payload);
}

export function fetchConnectorSlaProfile(tenantCode: string, connectorSource = "*"): Promise<ConnectorSlaProfileResponse> {
  const query = new URLSearchParams();
  query.set("tenant_code", tenantCode);
  query.set("connector_source", connectorSource);
  return getJson<ConnectorSlaProfileResponse>(`/competitive/connectors/sla/profiles?${query.toString()}`);
}

export function evaluateConnectorSla(payload: {
  tenant_code: string;
  connector_source?: string;
  lookback_limit?: number;
  route_alert?: boolean;
}): Promise<ConnectorSlaEvaluateResponse> {
  return postJson<ConnectorSlaEvaluateResponse>("/competitive/connectors/sla/evaluate", payload);
}

export function fetchConnectorSlaBreaches(params: {
  tenant_code: string;
  connector_source?: string;
  limit?: number;
}): Promise<ConnectorSlaBreachListResponse> {
  const query = new URLSearchParams();
  query.set("tenant_code", params.tenant_code);
  if (params.connector_source) query.set("connector_source", params.connector_source);
  query.set("limit", String(params.limit ?? 200));
  return getJson<ConnectorSlaBreachListResponse>(`/competitive/connectors/sla/breaches?${query.toString()}`);
}

export function upsertActionCenterPolicy(payload: {
  tenant_code: string;
  policy_version?: string;
  owner?: string;
  telegram_enabled?: boolean;
  line_enabled?: boolean;
  min_severity?: "low" | "medium" | "high" | "critical";
  routing_tags?: string[];
}): Promise<{ status: string; policy: Record<string, unknown> }> {
  return postJson<{ status: string; policy: Record<string, unknown> }>("/competitive/action-center/policies", payload);
}

export function fetchActionCenterPolicy(tenantCode: string): Promise<ActionCenterPolicyResponse> {
  const query = new URLSearchParams();
  query.set("tenant_code", tenantCode);
  return getJson<ActionCenterPolicyResponse>(`/competitive/action-center/policies?${query.toString()}`);
}

export function dispatchActionCenterAlert(payload: {
  tenant_code: string;
  site_code?: string;
  source?: string;
  severity?: "low" | "medium" | "high" | "critical";
  title: string;
  message: string;
  payload?: Record<string, unknown>;
}): Promise<ActionCenterDispatchResponse> {
  return postJson<ActionCenterDispatchResponse>("/competitive/action-center/dispatch", payload);
}

export function fetchActionCenterEvents(params: {
  tenant_code?: string;
  severity?: "low" | "medium" | "high" | "critical" | "";
  limit?: number;
} = {}): Promise<ActionCenterEventListResponse> {
  const query = new URLSearchParams();
  if (params.tenant_code) query.set("tenant_code", params.tenant_code);
  if (params.severity) query.set("severity", params.severity);
  query.set("limit", String(params.limit ?? 200));
  return getJson<ActionCenterEventListResponse>(`/competitive/action-center/events?${query.toString()}`);
}
