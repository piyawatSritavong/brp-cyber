import type {
  ActionCenterDispatchResponse,
  ActionCenterEventListResponse,
  ActionCenterPolicyResponse,
  BlueIncidentFeed,
  BlueLogRefinerMappingPackResponse,
  CoworkerPluginCatalogResponse,
  CoworkerPluginSchedulerResponse,
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
  EmbeddedAutomationFederationReadinessResponse,
  FederationActionCenterSlaResponse,
  FederationSecopsDataTierResponse,
  GovernanceDashboardResponse,
  SiteCaseGraphResponse,
  SiteDetectionCopilotTuneResponse,
  SiteDetectionAutotunePolicyResponse,
  SiteDetectionAutotuneRunListResponse,
  SiteDetectionAutotuneRunResponse,
  SiteDetectionRulesResponse,
  SiteBlueManagedResponderPolicyResponse,
  SiteBlueManagedResponderEvidenceVerifyResponse,
  SiteBlueManagedResponderRunListResponse,
  SiteBlueManagedResponderRunResponse,
  SiteBlueManagedResponderSchedulerResponse,
  SiteBlueThreatLocalizerPolicyResponse,
  SiteBlueThreatLocalizerPromotionRunListResponse,
  SiteBlueThreatLocalizerPromotionRunResponse,
  SiteBlueThreatLocalizerRoutingPolicyResponse,
  SiteBlueThreatLocalizerRunListResponse,
  SiteBlueThreatLocalizerRunResponse,
  SiteBlueThreatLocalizerSchedulerResponse,
  BlueThreatFeedImportResponse,
  BlueThreatFeedAdapterImportResponse,
  BlueThreatFeedAdapterTemplatesResponse,
  BlueThreatFeedListResponse,
  BlueThreatSectorProfilesResponse,
  SiteRedExploitAutopilotPolicyResponse,
  SiteRedExploitAutopilotRunListResponse,
  SiteRedExploitAutopilotRunResponse,
  SiteRedShadowPentestPolicyResponse,
  SiteRedShadowPentestAssetResponse,
  SiteRedShadowPentestRunListResponse,
  SiteRedShadowPentestRunResponse,
  SiteRedShadowPentestSchedulerResponse,
  SiteRedSocialPolicyResponse,
  SiteRedSocialProviderCallbackResponse,
  SiteRedSocialRosterImportResponse,
  SiteRedSocialRosterResponse,
  SiteRedSocialSimulatorRunListResponse,
  SiteRedSocialSimulatorRunResponse,
  SiteRedSocialTelemetryResponse,
  SiteRedVulnerabilityFindingImportResponse,
  SiteRedVulnerabilityFindingListResponse,
  SiteRedVulnerabilityRemediationExportResponse,
  SiteRedVulnerabilityValidationRunListResponse,
  SiteRedVulnerabilityValidationRunResponse,
  SiteExploitPathRunsResponse,
  SiteExploitPathSimulationResponse,
  IntegrationAdaptersResponse,
  IntegrationAdapterTemplatesResponse,
  IntegrationEventIngestResponse,
  OrchestratorState,
  SiteBlueEventHistoryResponse,
  SiteBlueLogRefinerFeedbackListResponse,
  SiteBlueLogRefinerFeedbackResponse,
  SiteBlueLogRefinerCallbackListResponse,
  SiteBlueLogRefinerCallbackResponse,
  SiteBlueLogRefinerPolicyResponse,
  SiteBlueLogRefinerSchedulePolicyResponse,
  SiteBlueLogRefinerRunListResponse,
  SiteBlueLogRefinerRunResponse,
  SiteBlueLogRefinerSchedulerResponse,
  SiteCoworkerDeliveryDispatchResponse,
  SiteCoworkerDeliveryEscalationPolicyResponse,
  SiteCoworkerDeliveryEscalationFederationResponse,
  SiteCoworkerDeliveryEscalationRunResponse,
  SiteCoworkerDeliveryEscalationSchedulerResponse,
  SiteCoworkerDeliveryEventsResponse,
  SiteCoworkerDeliveryPreviewResponse,
  SiteCoworkerDeliveryProfilesResponse,
  SiteCoworkerDeliveryReviewResponse,
  SiteCoworkerDeliverySlaResponse,
  SiteEmbeddedActivationBundleResponse,
  SiteEmbeddedAutomationVerifyResponse,
  SiteEmbeddedWorkflowEndpointListResponse,
  SiteEmbeddedInvokePackResponse,
  SiteEmbeddedWorkflowEndpointUpsertResponse,
  SiteEmbeddedWorkflowInvocationListResponse,
  SiteCoworkerPluginListResponse,
  SiteCoworkerPluginRunListResponse,
  SiteCoworkerPluginRunResponse,
  SiteRedPluginExportResponse,
  SiteRedPluginIntelligenceResponse,
  SiteRedPluginLintResponse,
  SiteRedPluginSafetyPolicyResponse,
  SiteRedPluginSyncRunsResponse,
  SiteRedPluginSyncSourcesResponse,
  SiteRedPluginThreatPackPublishResponse,
  SoarExecutionListResponse,
  SoarConnectorResultContractListResponse,
  SoarConnectorResultListResponse,
  SoarConnectorResultResponse,
  SoarExecutionVerifyResponse,
  SoarPlaybookListResponse,
  SoarMarketplacePackListResponse,
  SoarMarketplaceOverview,
  SoarTenantPolicyResponse,
  ConnectorEventListResponse,
  ConnectorHealthResponse,
  SiteListResponse,
  SitePurpleReportHistoryResponse,
  SitePurpleExecutiveFederationResponse,
  SitePurpleRoiDashboardResponse,
  SitePurpleRoiDashboardSnapshotListResponse,
  SitePurpleRoiDashboardTrendResponse,
  PurpleRoiTemplatePackResponse,
  PurpleRoiPortfolioRollupResponse,
  PurpleExportTemplatePackResponse,
  SitePurpleIncidentReportExportResponse,
  SitePurpleMitreHeatmapExportResponse,
  SitePurpleReportReleaseListResponse,
  SitePurpleReportReleaseResponse,
  SitePurpleRoiBoardExportResponse,
  SitePurpleRegulatedReportExportResponse,
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

export function runSiteRedSocialSimulator(
  siteId: string,
  payload?: {
    campaign_name?: string;
    employee_segment?: string;
    email_count?: number;
    difficulty?: "low" | "medium" | "high";
    impersonation_brand?: string;
    dry_run?: boolean;
    actor?: string;
  },
): Promise<SiteRedSocialSimulatorRunResponse> {
  return postJson<SiteRedSocialSimulatorRunResponse>(`/competitive/sites/${siteId}/red/social-simulator/run`, payload ?? {});
}

export function importSiteRedSocialRoster(
  siteId: string,
  payload: {
    entries: Array<Record<string, unknown>>;
    actor?: string;
  },
): Promise<SiteRedSocialRosterImportResponse> {
  return postJson<SiteRedSocialRosterImportResponse>(`/competitive/sites/${siteId}/red/social-simulator/roster/import`, payload);
}

export function fetchSiteRedSocialRoster(
  siteId: string,
  params?: { active_only?: boolean; limit?: number },
): Promise<SiteRedSocialRosterResponse> {
  const query = new URLSearchParams();
  query.set("active_only", String(params?.active_only ?? true));
  query.set("limit", String(params?.limit ?? 200));
  return getJson<SiteRedSocialRosterResponse>(`/competitive/sites/${siteId}/red/social-simulator/roster?${query.toString()}`);
}

export function fetchSiteRedSocialPolicy(siteId: string): Promise<SiteRedSocialPolicyResponse> {
  return getJson<SiteRedSocialPolicyResponse>(`/competitive/sites/${siteId}/red/social-simulator/policy`);
}

export function upsertSiteRedSocialPolicy(
  siteId: string,
  payload: {
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
    connector_config?: Record<string, unknown>;
    enabled: boolean;
    owner: string;
  },
): Promise<SiteRedSocialPolicyResponse> {
  return postJson<SiteRedSocialPolicyResponse>(`/competitive/sites/${siteId}/red/social-simulator/policy`, payload);
}

export function fetchSiteRedSocialSimulatorRuns(siteId: string, limit = 20): Promise<SiteRedSocialSimulatorRunListResponse> {
  return getJson<SiteRedSocialSimulatorRunListResponse>(
    `/competitive/sites/${siteId}/red/social-simulator/runs?limit=${limit}`,
  );
}

export function reviewSiteRedSocialCampaign(
  siteId: string,
  runId: string,
  payload: { approve: boolean; actor?: string; note?: string },
): Promise<SiteRedSocialSimulatorRunResponse> {
  return postJson<SiteRedSocialSimulatorRunResponse>(`/competitive/sites/${siteId}/red/social-simulator/${runId}/review`, payload);
}

export function killSiteRedSocialCampaign(
  siteId: string,
  runId: string,
  payload: { actor?: string; note?: string; activate_site_kill_switch?: boolean },
): Promise<SiteRedSocialSimulatorRunResponse> {
  return postJson<SiteRedSocialSimulatorRunResponse>(`/competitive/sites/${siteId}/red/social-simulator/${runId}/kill`, payload);
}

export function fetchSiteRedSocialTelemetry(
  siteId: string,
  params?: { run_id?: string; limit?: number },
): Promise<SiteRedSocialTelemetryResponse> {
  const query = new URLSearchParams();
  if (params?.run_id) query.set("run_id", params.run_id);
  query.set("limit", String(params?.limit ?? 200));
  return getJson<SiteRedSocialTelemetryResponse>(
    `/competitive/sites/${siteId}/red/social-simulator/telemetry?${query.toString()}`,
  );
}

export function ingestSiteRedSocialProviderCallback(
  siteId: string,
  payload: {
    run_id: string;
    connector_type?: string;
    event_type?: string;
    recipient_email: string;
    occurred_at?: string;
    provider_event_id?: string;
    metadata?: Record<string, unknown>;
    actor?: string;
  },
): Promise<SiteRedSocialProviderCallbackResponse> {
  return postJson<SiteRedSocialProviderCallbackResponse>(
    `/competitive/sites/${siteId}/red/social-simulator/provider-callback`,
    payload,
  );
}

export function importSiteRedVulnerabilityFindings(
  siteId: string,
  payload: {
    source_tool: string;
    payload?: Record<string, unknown> | Array<Record<string, unknown>>;
    findings?: Array<Record<string, unknown>>;
    actor?: string;
  },
): Promise<SiteRedVulnerabilityFindingImportResponse> {
  return postJson<SiteRedVulnerabilityFindingImportResponse>(`/competitive/sites/${siteId}/red/vuln-validator/import`, payload);
}

export function fetchSiteRedVulnerabilityFindings(
  siteId: string,
  params?: { source_tool?: string; verdict?: string; limit?: number },
): Promise<SiteRedVulnerabilityFindingListResponse> {
  const query = new URLSearchParams();
  if (params?.source_tool) query.set("source_tool", params.source_tool);
  if (params?.verdict) query.set("verdict", params.verdict);
  query.set("limit", String(params?.limit ?? 100));
  return getJson<SiteRedVulnerabilityFindingListResponse>(
    `/competitive/sites/${siteId}/red/vuln-validator/findings?${query.toString()}`,
  );
}

export function runSiteRedVulnerabilityValidator(
  siteId: string,
  payload?: { finding_ids?: string[]; max_findings?: number; dry_run?: boolean; actor?: string },
): Promise<SiteRedVulnerabilityValidationRunResponse> {
  return postJson<SiteRedVulnerabilityValidationRunResponse>(`/competitive/sites/${siteId}/red/vuln-validator/run`, payload ?? {});
}

export function fetchSiteRedVulnerabilityValidationRuns(
  siteId: string,
  limit = 20,
): Promise<SiteRedVulnerabilityValidationRunListResponse> {
  return getJson<SiteRedVulnerabilityValidationRunListResponse>(
    `/competitive/sites/${siteId}/red/vuln-validator/runs?limit=${limit}`,
  );
}

export function fetchSiteRedVulnerabilityRemediationExport(
  siteId: string,
  params?: { source_tool?: string; verdict?: string; limit?: number },
): Promise<SiteRedVulnerabilityRemediationExportResponse> {
  const query = new URLSearchParams();
  if (params?.source_tool) query.set("source_tool", params.source_tool);
  if (params?.verdict) query.set("verdict", params.verdict);
  query.set("limit", String(params?.limit ?? 200));
  return getJson<SiteRedVulnerabilityRemediationExportResponse>(
    `/competitive/sites/${siteId}/red/vuln-validator/remediation-export?${query.toString()}`,
  );
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

export function runSiteBlueThreatLocalizer(
  siteId: string,
  payload?: {
    focus_region?: string;
    sector?: string;
    dry_run?: boolean;
    actor?: string;
  },
): Promise<SiteBlueThreatLocalizerRunResponse> {
  return postJson<SiteBlueThreatLocalizerRunResponse>(`/competitive/sites/${siteId}/blue/threat-localizer/run`, payload ?? {});
}

export function importBlueThreatFeedItems(
  payload: {
    source_name?: string;
    items: Array<Record<string, unknown>>;
    actor?: string;
  },
): Promise<BlueThreatFeedImportResponse> {
  return postJson<BlueThreatFeedImportResponse>(`/competitive/blue/threat-localizer/feed-items/import`, payload);
}

export function importBlueThreatFeedAdapter(
  payload: {
    source?: string;
    payload?: Record<string, unknown> | Array<Record<string, unknown>>;
    actor?: string;
  },
): Promise<BlueThreatFeedAdapterImportResponse> {
  return postJson<BlueThreatFeedAdapterImportResponse>(`/competitive/blue/threat-localizer/feed-adapters/import`, payload);
}

export function fetchBlueThreatFeedItems(
  params?: { focus_region?: string; sector?: string; category?: string; active_only?: boolean; limit?: number },
): Promise<BlueThreatFeedListResponse> {
  const query = new URLSearchParams();
  if (params?.focus_region) query.set("focus_region", params.focus_region);
  if (params?.sector) query.set("sector", params.sector);
  if (params?.category) query.set("category", params.category);
  query.set("active_only", String(params?.active_only ?? true));
  query.set("limit", String(params?.limit ?? 100));
  return getJson<BlueThreatFeedListResponse>(`/competitive/blue/threat-localizer/feed-items?${query.toString()}`);
}

export function fetchBlueThreatFeedAdapterTemplates(source = ""): Promise<BlueThreatFeedAdapterTemplatesResponse> {
  const query = new URLSearchParams();
  if (source) query.set("source", source);
  return getJson<BlueThreatFeedAdapterTemplatesResponse>(`/competitive/blue/threat-localizer/feed-adapters?${query.toString()}`);
}

export function fetchBlueThreatSectorProfiles(): Promise<BlueThreatSectorProfilesResponse> {
  return getJson<BlueThreatSectorProfilesResponse>(`/competitive/blue/threat-localizer/sector-profiles`);
}

export function fetchBlueLogRefinerMappingPacks(source = ""): Promise<BlueLogRefinerMappingPackResponse> {
  const query = new URLSearchParams();
  if (source) query.set("source", source);
  return getJson<BlueLogRefinerMappingPackResponse>(`/competitive/blue/log-refiner/mapping-packs?${query.toString()}`);
}

export function fetchSiteBlueLogRefinerPolicy(
  siteId: string,
  connectorSource = "generic",
): Promise<SiteBlueLogRefinerPolicyResponse> {
  return getJson<SiteBlueLogRefinerPolicyResponse>(
    `/competitive/sites/${siteId}/blue/log-refiner/policy?connector_source=${encodeURIComponent(connectorSource)}`,
  );
}

export function fetchSiteBlueLogRefinerSchedulePolicy(
  siteId: string,
  connectorSource = "generic",
): Promise<SiteBlueLogRefinerSchedulePolicyResponse> {
  return getJson<SiteBlueLogRefinerSchedulePolicyResponse>(
    `/competitive/sites/${siteId}/blue/log-refiner/schedule-policy?connector_source=${encodeURIComponent(connectorSource)}`,
  );
}

export function upsertSiteBlueLogRefinerPolicy(
  siteId: string,
  payload: {
    connector_source?: string;
    execution_mode?: "pre_ingest" | "post_ingest";
    lookback_limit?: number;
    min_keep_severity?: "low" | "medium" | "high" | "critical";
    drop_recommendation_codes?: string[];
    target_noise_reduction_pct?: number;
    average_event_size_kb?: number;
    enabled?: boolean;
    owner?: string;
  },
): Promise<SiteBlueLogRefinerPolicyResponse> {
  return postJson<SiteBlueLogRefinerPolicyResponse>(`/competitive/sites/${siteId}/blue/log-refiner/policy`, payload);
}

export function upsertSiteBlueLogRefinerSchedulePolicy(
  siteId: string,
  payload: {
    connector_source?: string;
    schedule_interval_minutes?: number;
    dry_run_default?: boolean;
    callback_ingest_enabled?: boolean;
    enabled?: boolean;
    owner?: string;
  },
): Promise<SiteBlueLogRefinerSchedulePolicyResponse> {
  return postJson<SiteBlueLogRefinerSchedulePolicyResponse>(
    `/competitive/sites/${siteId}/blue/log-refiner/schedule-policy`,
    payload,
  );
}

export function runSiteBlueLogRefiner(
  siteId: string,
  payload?: {
    connector_source?: string;
    dry_run?: boolean;
    actor?: string;
  },
): Promise<SiteBlueLogRefinerRunResponse> {
  return postJson<SiteBlueLogRefinerRunResponse>(`/competitive/sites/${siteId}/blue/log-refiner/run`, payload ?? {});
}

export function fetchSiteBlueLogRefinerRuns(
  siteId: string,
  params?: { connector_source?: string; limit?: number },
): Promise<SiteBlueLogRefinerRunListResponse> {
  const query = new URLSearchParams();
  if (params?.connector_source) query.set("connector_source", params.connector_source);
  query.set("limit", String(params?.limit ?? 20));
  return getJson<SiteBlueLogRefinerRunListResponse>(`/competitive/sites/${siteId}/blue/log-refiner/runs?${query.toString()}`);
}

export function runBlueLogRefinerScheduler(params?: {
  limit?: number;
  dry_run_override?: boolean;
  actor?: string;
}): Promise<SiteBlueLogRefinerSchedulerResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 200));
  if (params?.dry_run_override !== undefined) query.set("dry_run_override", String(params.dry_run_override));
  if (params?.actor) query.set("actor", params.actor);
  return postJson<SiteBlueLogRefinerSchedulerResponse>(`/competitive/blue/log-refiner/scheduler/run?${query.toString()}`, {});
}

export function submitSiteBlueLogRefinerFeedback(
  siteId: string,
  payload?: {
    connector_source?: string;
    feedback_type?: "keep_signal" | "drop_noise" | "false_positive" | "signal_missed";
    event_type?: string;
    recommendation_code?: string;
    note?: string;
    actor?: string;
    run_id?: string | null;
  },
): Promise<SiteBlueLogRefinerFeedbackResponse> {
  return postJson<SiteBlueLogRefinerFeedbackResponse>(`/competitive/sites/${siteId}/blue/log-refiner/feedback`, payload ?? {});
}

export function ingestSiteBlueLogRefinerCallback(
  siteId: string,
  payload?: {
    connector_source?: string;
    callback_type?: "stream_result" | "storage_report" | "delivery_receipt";
    source_system?: string;
    external_run_ref?: string;
    webhook_event_id?: string;
    run_id?: string | null;
    total_events?: number;
    kept_events?: number;
    dropped_events?: number;
    noise_reduction_pct?: number | null;
    estimated_storage_saved_kb?: number;
    status?: string;
    payload?: Record<string, unknown>;
    actor?: string;
  },
): Promise<SiteBlueLogRefinerCallbackResponse> {
  return postJson<SiteBlueLogRefinerCallbackResponse>(`/competitive/sites/${siteId}/blue/log-refiner/callback`, payload ?? {});
}

export function fetchSiteBlueLogRefinerFeedback(
  siteId: string,
  params?: { connector_source?: string; limit?: number },
): Promise<SiteBlueLogRefinerFeedbackListResponse> {
  const query = new URLSearchParams();
  if (params?.connector_source) query.set("connector_source", params.connector_source);
  query.set("limit", String(params?.limit ?? 20));
  return getJson<SiteBlueLogRefinerFeedbackListResponse>(`/competitive/sites/${siteId}/blue/log-refiner/feedback?${query.toString()}`);
}

export function fetchSiteBlueLogRefinerCallbacks(
  siteId: string,
  params?: { connector_source?: string; limit?: number },
): Promise<SiteBlueLogRefinerCallbackListResponse> {
  const query = new URLSearchParams();
  if (params?.connector_source) query.set("connector_source", params.connector_source);
  query.set("limit", String(params?.limit ?? 20));
  return getJson<SiteBlueLogRefinerCallbackListResponse>(`/competitive/sites/${siteId}/blue/log-refiner/callbacks?${query.toString()}`);
}

export function fetchSiteBlueThreatLocalizerPolicy(siteId: string): Promise<SiteBlueThreatLocalizerPolicyResponse> {
  return getJson<SiteBlueThreatLocalizerPolicyResponse>(`/competitive/sites/${siteId}/blue/threat-localizer/policy`);
}

export function fetchSiteBlueThreatLocalizerRoutingPolicy(siteId: string): Promise<SiteBlueThreatLocalizerRoutingPolicyResponse> {
  return getJson<SiteBlueThreatLocalizerRoutingPolicyResponse>(`/competitive/sites/${siteId}/blue/threat-localizer/routing-policy`);
}

export function upsertSiteBlueThreatLocalizerPolicy(
  siteId: string,
  payload: {
    focus_region: string;
    sector: string;
    subscribed_categories: string[];
    recurring_digest_enabled: boolean;
    schedule_interval_minutes: number;
    min_feed_priority: string;
    enabled: boolean;
    owner: string;
  },
): Promise<SiteBlueThreatLocalizerPolicyResponse> {
  return postJson<SiteBlueThreatLocalizerPolicyResponse>(`/competitive/sites/${siteId}/blue/threat-localizer/policy`, payload);
}

export function upsertSiteBlueThreatLocalizerRoutingPolicy(
  siteId: string,
  payload: {
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
  },
): Promise<SiteBlueThreatLocalizerRoutingPolicyResponse> {
  return postJson<SiteBlueThreatLocalizerRoutingPolicyResponse>(
    `/competitive/sites/${siteId}/blue/threat-localizer/routing-policy`,
    payload,
  );
}

export function fetchSiteBlueThreatLocalizerRuns(
  siteId: string,
  limit = 20,
): Promise<SiteBlueThreatLocalizerRunListResponse> {
  return getJson<SiteBlueThreatLocalizerRunListResponse>(
    `/competitive/sites/${siteId}/blue/threat-localizer/runs?limit=${limit}`,
  );
}

export function fetchSiteBlueThreatLocalizerPromotionRuns(
  siteId: string,
  limit = 20,
): Promise<SiteBlueThreatLocalizerPromotionRunListResponse> {
  return getJson<SiteBlueThreatLocalizerPromotionRunListResponse>(
    `/competitive/sites/${siteId}/blue/threat-localizer/promotion-runs?limit=${limit}`,
  );
}

export function promoteSiteBlueThreatLocalizerGap(
  siteId: string,
  payload?: {
    localizer_run_id?: string | null;
    auto_apply_override?: boolean | null;
    playbook_promotion_override?: boolean | null;
    actor?: string;
  },
): Promise<SiteBlueThreatLocalizerPromotionRunResponse> {
  return postJson<SiteBlueThreatLocalizerPromotionRunResponse>(
    `/competitive/sites/${siteId}/blue/threat-localizer/promote-gap`,
    payload ?? {},
  );
}

export function runBlueThreatLocalizerScheduler(params?: {
  limit?: number;
  dry_run_override?: boolean | null;
  actor?: string;
}): Promise<SiteBlueThreatLocalizerSchedulerResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 100));
  if (typeof params?.dry_run_override === "boolean") query.set("dry_run_override", String(params.dry_run_override));
  if (params?.actor) query.set("actor", params.actor);
  return postJson<SiteBlueThreatLocalizerSchedulerResponse>(`/competitive/blue/threat-localizer/scheduler/run?${query.toString()}`, {});
}

export function fetchSiteBlueManagedResponderPolicy(siteId: string): Promise<SiteBlueManagedResponderPolicyResponse> {
  return getJson<SiteBlueManagedResponderPolicyResponse>(`/competitive/sites/${siteId}/blue/managed-responder/policy`);
}

export function upsertSiteBlueManagedResponderPolicy(
  siteId: string,
  payload: {
    min_severity?: "low" | "medium" | "high" | "critical";
    action_mode?: "ai_recommended" | "block_ip" | "notify_team" | "limit_user" | "ignore";
    dispatch_playbook?: boolean;
    playbook_code?: string;
    require_approval?: boolean;
    dry_run_default?: boolean;
    enabled?: boolean;
    owner?: string;
  },
): Promise<SiteBlueManagedResponderPolicyResponse> {
  return postJson<SiteBlueManagedResponderPolicyResponse>(`/competitive/sites/${siteId}/blue/managed-responder/policy`, payload);
}

export function runSiteBlueManagedResponder(
  siteId: string,
  payload?: {
    dry_run?: boolean | null;
    force?: boolean;
    actor?: string;
  },
): Promise<SiteBlueManagedResponderRunResponse> {
  return postJson<SiteBlueManagedResponderRunResponse>(`/competitive/sites/${siteId}/blue/managed-responder/run`, payload ?? {});
}

export function fetchSiteBlueManagedResponderRuns(siteId: string, limit = 20): Promise<SiteBlueManagedResponderRunListResponse> {
  return getJson<SiteBlueManagedResponderRunListResponse>(`/competitive/sites/${siteId}/blue/managed-responder/runs?limit=${limit}`);
}

export function reviewSiteBlueManagedResponderRun(
  siteId: string,
  runId: string,
  payload?: { approve?: boolean; approver?: string; note?: string },
): Promise<SiteBlueManagedResponderRunResponse> {
  return postJson<SiteBlueManagedResponderRunResponse>(
    `/competitive/sites/${siteId}/blue/managed-responder/runs/${runId}/review`,
    payload ?? {},
  );
}

export function rollbackSiteBlueManagedResponderRun(
  siteId: string,
  runId: string,
  payload?: { actor?: string; note?: string },
): Promise<SiteBlueManagedResponderRunResponse> {
  return postJson<SiteBlueManagedResponderRunResponse>(
    `/competitive/sites/${siteId}/blue/managed-responder/runs/${runId}/rollback`,
    payload ?? {},
  );
}

export function verifySiteBlueManagedResponderEvidence(
  siteId: string,
  limit = 50,
): Promise<SiteBlueManagedResponderEvidenceVerifyResponse> {
  return getJson<SiteBlueManagedResponderEvidenceVerifyResponse>(
    `/competitive/sites/${siteId}/blue/managed-responder/evidence/verify?limit=${limit}`,
  );
}

export function runBlueManagedResponderScheduler(payload?: {
  limit?: number;
  dry_run_override?: boolean | null;
  actor?: string;
}): Promise<SiteBlueManagedResponderSchedulerResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(payload?.limit ?? 200));
  if (payload?.dry_run_override !== undefined && payload?.dry_run_override !== null) {
    query.set("dry_run_override", String(payload.dry_run_override));
  }
  if (payload?.actor) query.set("actor", payload.actor);
  return postJson<SiteBlueManagedResponderSchedulerResponse>(`/competitive/blue/managed-responder/scheduler/run?${query.toString()}`, {});
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

export function generateSitePurpleRoiDashboard(
  siteId: string,
  payload?: {
    lookback_days?: number;
    analyst_hourly_cost_usd?: number;
    analyst_minutes_per_alert?: number;
  },
): Promise<SitePurpleRoiDashboardResponse> {
  return postJson<SitePurpleRoiDashboardResponse>(`/competitive/sites/${siteId}/purple/roi-dashboard/generate`, payload ?? {});
}

export function fetchSitePurpleRoiDashboardSnapshots(
  siteId: string,
  limit = 20,
): Promise<SitePurpleRoiDashboardSnapshotListResponse> {
  return getJson<SitePurpleRoiDashboardSnapshotListResponse>(
    `/competitive/sites/${siteId}/purple/roi-dashboard/snapshots?limit=${limit}`,
  );
}

export function fetchSitePurpleRoiDashboardTrends(
  siteId: string,
  limit = 12,
): Promise<SitePurpleRoiDashboardTrendResponse> {
  return getJson<SitePurpleRoiDashboardTrendResponse>(
    `/competitive/sites/${siteId}/purple/roi-dashboard/trends?limit=${limit}`,
  );
}

export function fetchPurpleRoiPortfolioRollup(
  params?: { tenant_code?: string; limit?: number },
): Promise<PurpleRoiPortfolioRollupResponse> {
  const query = new URLSearchParams();
  if (params?.tenant_code) query.set("tenant_code", params.tenant_code);
  query.set("limit", String(params?.limit ?? 200));
  return getJson<PurpleRoiPortfolioRollupResponse>(`/competitive/purple/roi-dashboard/portfolio?${query.toString()}`);
}

export function fetchPurpleRoiTemplatePacks(params?: { audience?: string }): Promise<PurpleRoiTemplatePackResponse> {
  const query = new URLSearchParams();
  if (params?.audience) query.set("audience", params.audience);
  return getJson<PurpleRoiTemplatePackResponse>(`/competitive/purple/roi-dashboard/template-packs?${query.toString()}`);
}

export function exportSitePurpleRoiBoardPack(
  siteId: string,
  payload?: {
    export_format?: "pdf" | "ppt";
    template_pack?: string;
    title_override?: string;
    include_portfolio?: boolean;
    tenant_code?: string;
    site_limit?: number;
  },
): Promise<SitePurpleRoiBoardExportResponse> {
  return postJson<SitePurpleRoiBoardExportResponse>(`/competitive/sites/${siteId}/purple/roi-dashboard/export`, payload ?? {});
}

export function fetchPurpleExportTemplatePacks(params?: {
  kind?: string;
  audience?: string;
}): Promise<PurpleExportTemplatePackResponse> {
  const query = new URLSearchParams();
  if (params?.kind) query.set("kind", params.kind);
  if (params?.audience) query.set("audience", params.audience);
  return getJson<PurpleExportTemplatePackResponse>(`/competitive/purple/export/template-packs?${query.toString()}`);
}

export function exportSitePurpleMitreHeatmap(
  siteId: string,
  payload?: {
    export_format?: "markdown" | "csv" | "attack_layer_json";
    title_override?: string;
    include_recommendations?: boolean;
    lookback_runs?: number;
    lookback_events?: number;
    sla_target_seconds?: number;
  },
): Promise<SitePurpleMitreHeatmapExportResponse> {
  return postJson<SitePurpleMitreHeatmapExportResponse>(`/competitive/sites/${siteId}/purple/mitre-heatmap/export`, payload ?? {});
}

export function exportSitePurpleIncidentReport(
  siteId: string,
  payload?: {
    template_pack?: string;
    export_format?: "markdown" | "json" | "pdf" | "docx";
    title_override?: string;
    include_regulatory_mapping?: boolean;
    blue_event_limit?: number;
  },
): Promise<SitePurpleIncidentReportExportResponse> {
  return postJson<SitePurpleIncidentReportExportResponse>(`/competitive/sites/${siteId}/purple/incident-report/export`, payload ?? {});
}

export function exportSitePurpleRegulatedReport(
  siteId: string,
  payload?: {
    template_pack?: string;
    export_format?: "markdown" | "json" | "pdf" | "docx";
    title_override?: string;
    include_incident_context?: boolean;
  },
): Promise<SitePurpleRegulatedReportExportResponse> {
  return postJson<SitePurpleRegulatedReportExportResponse>(`/competitive/sites/${siteId}/purple/regulatory-report/export`, payload ?? {});
}

export function requestSitePurpleReportRelease(
  siteId: string,
  payload: {
    report_kind: string;
    export_format: "markdown" | "json" | "pdf" | "docx";
    title: string;
    filename: string;
    payload: Record<string, unknown>;
    requester?: string;
    note?: string;
  },
): Promise<SitePurpleReportReleaseResponse> {
  return postJson<SitePurpleReportReleaseResponse>(`/competitive/sites/${siteId}/purple/report-releases`, payload);
}

export function reviewPurpleReportRelease(
  releaseId: string,
  payload: { approve: boolean; approver?: string; note?: string },
): Promise<SitePurpleReportReleaseResponse> {
  return postJson<SitePurpleReportReleaseResponse>(`/competitive/purple/report-releases/${releaseId}/review`, payload);
}

export function fetchSitePurpleReportReleases(siteId: string, limit = 20): Promise<SitePurpleReportReleaseListResponse> {
  return getJson<SitePurpleReportReleaseListResponse>(`/competitive/sites/${siteId}/purple/report-releases?limit=${limit}`);
}

export function fetchSitePurpleIsoGapTemplate(siteId: string, limit = 200): Promise<SitePurpleIsoGapTemplateResponse> {
  return getJson<SitePurpleIsoGapTemplateResponse>(`/sites/${siteId}/purple/iso27001-gap-template?limit=${limit}`);
}

export function fetchSitePurpleNistGapTemplate(siteId: string, limit = 200): Promise<SitePurpleIsoGapTemplateResponse> {
  return getJson<SitePurpleIsoGapTemplateResponse>(`/sites/${siteId}/purple/nist-csf-gap-template?limit=${limit}`);
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

export function fetchIntegrationAdapterTemplates(source = ""): Promise<IntegrationAdapterTemplatesResponse> {
  const query = new URLSearchParams();
  if (source) query.set("source", source);
  return getJson<IntegrationAdapterTemplatesResponse>(`/integrations/adapters/templates?${query.toString()}`);
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

export function fetchCoworkerPlugins(params?: {
  category?: string;
  active_only?: boolean;
}): Promise<CoworkerPluginCatalogResponse> {
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  if (params?.active_only !== undefined) query.set("active_only", String(params.active_only));
  return getJson<CoworkerPluginCatalogResponse>(`/competitive/coworker/plugins?${query.toString()}`);
}

export function fetchSiteCoworkerPlugins(
  siteId: string,
  params?: { category?: string },
): Promise<SiteCoworkerPluginListResponse> {
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  const suffix = query.toString();
  return getJson<SiteCoworkerPluginListResponse>(
    `/competitive/sites/${siteId}/coworker/plugins${suffix ? `?${suffix}` : ""}`,
  );
}

export function upsertSiteCoworkerPluginBinding(
  siteId: string,
  payload: {
    plugin_code: string;
    enabled?: boolean;
    auto_run?: boolean;
    schedule_interval_minutes?: number;
    notify_channels?: string[];
    config?: Record<string, unknown>;
    owner?: string;
  },
): Promise<{ status: string; plugin: Record<string, unknown>; binding: Record<string, unknown> }> {
  return postJson(`/competitive/sites/${siteId}/coworker/plugins/bindings`, payload);
}

export function runSiteCoworkerPlugin(
  siteId: string,
  pluginCode: string,
  payload?: { dry_run?: boolean | null; force?: boolean; actor?: string },
): Promise<SiteCoworkerPluginRunResponse> {
  return postJson<SiteCoworkerPluginRunResponse>(
    `/competitive/sites/${siteId}/coworker/plugins/${pluginCode}/run`,
    payload ?? {},
  );
}

export function fetchSiteCoworkerPluginRuns(
  siteId: string,
  params?: { category?: string; limit?: number },
): Promise<SiteCoworkerPluginRunListResponse> {
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  query.set("limit", String(params?.limit ?? 100));
  return getJson<SiteCoworkerPluginRunListResponse>(
    `/competitive/sites/${siteId}/coworker/plugins/runs?${query.toString()}`,
  );
}

export function importSiteRedPluginIntelligence(
  siteId: string,
  payload: {
    items: Array<Record<string, unknown>>;
    actor?: string;
  },
): Promise<SiteRedPluginIntelligenceResponse> {
  return postJson<SiteRedPluginIntelligenceResponse>(`/competitive/sites/${siteId}/red/plugin-intelligence/import`, payload);
}

export function fetchSiteRedPluginIntelligence(
  siteId: string,
  params?: { source_type?: string; limit?: number },
): Promise<SiteRedPluginIntelligenceResponse> {
  const query = new URLSearchParams();
  if (params?.source_type) query.set("source_type", params.source_type);
  query.set("limit", String(params?.limit ?? 20));
  return getJson<SiteRedPluginIntelligenceResponse>(
    `/competitive/sites/${siteId}/red/plugin-intelligence?${query.toString()}`,
  );
}

export function fetchSiteRedPluginSyncSources(
  siteId: string,
  params?: { limit?: number },
): Promise<SiteRedPluginSyncSourcesResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 20));
  return getJson<SiteRedPluginSyncSourcesResponse>(
    `/competitive/sites/${siteId}/red/plugin-intelligence/sync-sources?${query.toString()}`,
  );
}

export function upsertSiteRedPluginSyncSource(
  siteId: string,
  payload: {
    source_name?: string;
    source_type?: string;
    source_url?: string;
    target_type?: string;
    parser_kind?: string;
    request_headers?: Record<string, unknown>;
    sync_interval_minutes?: number;
    enabled?: boolean;
    owner?: string;
  },
): Promise<SiteRedPluginSyncSourcesResponse> {
  return postJson<SiteRedPluginSyncSourcesResponse>(
    `/competitive/sites/${siteId}/red/plugin-intelligence/sync-sources`,
    payload,
  );
}

export function runSiteRedPluginSync(
  siteId: string,
  payload?: { sync_source_id?: string | null; dry_run?: boolean; actor?: string },
): Promise<SiteRedPluginSyncRunsResponse> {
  return postJson<SiteRedPluginSyncRunsResponse>(
    `/competitive/sites/${siteId}/red/plugin-intelligence/sync`,
    payload ?? {},
  );
}

export function fetchSiteRedPluginSyncRuns(
  siteId: string,
  params?: { limit?: number },
): Promise<SiteRedPluginSyncRunsResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 20));
  return getJson<SiteRedPluginSyncRunsResponse>(
    `/competitive/sites/${siteId}/red/plugin-intelligence/sync-runs?${query.toString()}`,
  );
}

export function fetchSiteRedPluginSafetyPolicy(
  siteId: string,
  targetType = "web",
): Promise<SiteRedPluginSafetyPolicyResponse> {
  return getJson<SiteRedPluginSafetyPolicyResponse>(
    `/competitive/sites/${siteId}/red/plugin-safety-policy?target_type=${encodeURIComponent(targetType)}`,
  );
}

export function upsertSiteRedPluginSafetyPolicy(
  siteId: string,
  payload: {
    target_type?: string;
    max_http_requests_per_run?: number;
    max_script_lines?: number;
    allow_network_calls?: boolean;
    require_comment_header?: boolean;
    require_disclaimer?: boolean;
    allowed_modules?: string[];
    blocked_modules?: string[];
    enabled?: boolean;
    owner?: string;
  },
): Promise<SiteRedPluginSafetyPolicyResponse> {
  return postJson<SiteRedPluginSafetyPolicyResponse>(`/competitive/sites/${siteId}/red/plugin-safety-policy`, payload);
}

export function lintSiteRedPluginOutput(
  siteId: string,
  pluginCode: string,
  payload?: { run_id?: string | null; content_override?: string },
): Promise<SiteRedPluginLintResponse> {
  return postJson<SiteRedPluginLintResponse>(
    `/competitive/sites/${siteId}/red/plugins/${pluginCode}/lint`,
    payload ?? {},
  );
}

export function exportSiteRedPluginOutput(
  siteId: string,
  pluginCode: string,
  payload?: { run_id?: string | null; export_kind?: string; title_override?: string },
): Promise<SiteRedPluginExportResponse> {
  return postJson<SiteRedPluginExportResponse>(
    `/competitive/sites/${siteId}/red/plugins/${pluginCode}/export`,
    payload ?? {},
  );
}

export function runRedPluginSyncScheduler(params?: {
  limit?: number;
  dry_run_override?: boolean | null;
  actor?: string;
}): Promise<SiteRedPluginSyncRunsResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 100));
  if (params?.dry_run_override !== undefined && params?.dry_run_override !== null) {
    query.set("dry_run_override", String(params.dry_run_override));
  }
  if (params?.actor) query.set("actor", params.actor);
  return postJson<SiteRedPluginSyncRunsResponse>(
    `/competitive/red/plugin-intelligence/scheduler/run?${query.toString()}`,
    {},
  );
}

export function publishSiteRedTemplateThreatPack(
  siteId: string,
  payload?: { run_id?: string | null; activate?: boolean; actor?: string },
): Promise<SiteRedPluginThreatPackPublishResponse> {
  return postJson<SiteRedPluginThreatPackPublishResponse>(
    `/competitive/sites/${siteId}/red/plugins/red_template_writer/publish-threat-pack`,
    payload ?? {},
  );
}

export function fetchSiteEmbeddedWorkflowEndpoints(
  siteId: string,
  limit = 100,
): Promise<SiteEmbeddedWorkflowEndpointListResponse> {
  return getJson<SiteEmbeddedWorkflowEndpointListResponse>(
    `/competitive/sites/${siteId}/embedded/endpoints?limit=${limit}`,
  );
}

export function upsertSiteEmbeddedWorkflowEndpoint(
  siteId: string,
  payload: {
    endpoint_code: string;
    workflow_type?: "coworker_plugin" | "soar_playbook";
    plugin_code?: string;
    connector_source?: string;
    default_event_kind?: string;
    enabled?: boolean;
    dry_run_default?: boolean;
    config?: Record<string, unknown>;
    owner?: string;
    rotate_secret?: boolean;
  },
): Promise<SiteEmbeddedWorkflowEndpointUpsertResponse> {
  return postJson<SiteEmbeddedWorkflowEndpointUpsertResponse>(
    `/competitive/sites/${siteId}/embedded/endpoints`,
    payload,
  );
}

export function fetchSiteEmbeddedWorkflowInvocations(
  siteId: string,
  params?: { endpoint_code?: string; limit?: number },
): Promise<SiteEmbeddedWorkflowInvocationListResponse> {
  const query = new URLSearchParams();
  if (params?.endpoint_code) query.set("endpoint_code", params.endpoint_code);
  query.set("limit", String(params?.limit ?? 100));
  return getJson<SiteEmbeddedWorkflowInvocationListResponse>(
    `/competitive/sites/${siteId}/embedded/invocations?${query.toString()}`,
  );
}

export function fetchSiteEmbeddedWorkflowInvokePacks(
  siteId: string,
  params?: { endpoint_code?: string; limit?: number },
): Promise<SiteEmbeddedInvokePackResponse> {
  const query = new URLSearchParams();
  if (params?.endpoint_code) query.set("endpoint_code", params.endpoint_code);
  query.set("limit", String(params?.limit ?? 100));
  return getJson<SiteEmbeddedInvokePackResponse>(
    `/competitive/sites/${siteId}/embedded/invoke-packs?${query.toString()}`,
  );
}

export function fetchSiteEmbeddedAutomationVerify(
  siteId: string,
  params?: { endpoint_code?: string; limit?: number },
): Promise<SiteEmbeddedAutomationVerifyResponse> {
  const query = new URLSearchParams();
  if (params?.endpoint_code) query.set("endpoint_code", params.endpoint_code);
  query.set("limit", String(params?.limit ?? 100));
  return getJson<SiteEmbeddedAutomationVerifyResponse>(
    `/competitive/sites/${siteId}/embedded/automation-verify?${query.toString()}`,
  );
}

export function fetchSiteEmbeddedActivationBundles(
  siteId: string,
  params?: { endpoint_code?: string; limit?: number },
): Promise<SiteEmbeddedActivationBundleResponse> {
  const query = new URLSearchParams();
  if (params?.endpoint_code) query.set("endpoint_code", params.endpoint_code);
  query.set("limit", String(params?.limit ?? 100));
  return getJson<SiteEmbeddedActivationBundleResponse>(
    `/competitive/sites/${siteId}/embedded/activation-bundles?${query.toString()}`,
  );
}

export function fetchEmbeddedAutomationFederationReadiness(params?: {
  connector_source?: string;
  limit?: number;
}): Promise<EmbeddedAutomationFederationReadinessResponse> {
  const query = new URLSearchParams();
  if (params?.connector_source) query.set("connector_source", params.connector_source);
  query.set("limit", String(params?.limit ?? 200));
  return getJson<EmbeddedAutomationFederationReadinessResponse>(
    `/competitive/embedded/federation/readiness?${query.toString()}`,
  );
}

export function runCoworkerPluginScheduler(params?: {
  limit?: number;
  dry_run_override?: boolean;
  actor?: string;
}): Promise<CoworkerPluginSchedulerResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 200));
  if (params?.dry_run_override !== undefined) query.set("dry_run_override", String(params.dry_run_override));
  if (params?.actor) query.set("actor", params.actor);
  return postJson<CoworkerPluginSchedulerResponse>(`/competitive/coworker/plugins/scheduler/run?${query.toString()}`, {});
}

export function fetchSiteCoworkerDeliveryProfiles(siteId: string): Promise<SiteCoworkerDeliveryProfilesResponse> {
  return getJson<SiteCoworkerDeliveryProfilesResponse>(`/competitive/sites/${siteId}/coworker/delivery/profiles`);
}

export function upsertSiteCoworkerDeliveryProfile(
  siteId: string,
  payload: {
    channel?: "telegram" | "line" | "teams" | "webhook";
    enabled?: boolean;
    min_severity?: "low" | "medium" | "high" | "critical";
    delivery_mode?: "manual" | "auto";
    require_approval?: boolean;
    include_thai_summary?: boolean;
    webhook_url?: string;
    owner?: string;
  },
): Promise<{ status: string; profile: Record<string, unknown> }> {
  return postJson(`/competitive/sites/${siteId}/coworker/delivery/profiles`, payload);
}

export function previewSiteCoworkerDelivery(
  siteId: string,
  pluginCode: string,
  payload?: { channel?: "telegram" | "line" | "teams" | "webhook" },
): Promise<SiteCoworkerDeliveryPreviewResponse> {
  return postJson<SiteCoworkerDeliveryPreviewResponse>(
    `/competitive/sites/${siteId}/coworker/delivery/${pluginCode}/preview`,
    payload ?? {},
  );
}

export function dispatchSiteCoworkerDelivery(
  siteId: string,
  pluginCode: string,
  payload?: {
    channel?: "telegram" | "line" | "teams" | "webhook";
    dry_run?: boolean | null;
    force?: boolean;
    actor?: string;
  },
): Promise<SiteCoworkerDeliveryDispatchResponse> {
  return postJson<SiteCoworkerDeliveryDispatchResponse>(
    `/competitive/sites/${siteId}/coworker/delivery/${pluginCode}/dispatch`,
    payload ?? {},
  );
}

export function fetchSiteCoworkerDeliveryEvents(
  siteId: string,
  params?: { channel?: "telegram" | "line" | "teams" | "webhook" | ""; limit?: number },
): Promise<SiteCoworkerDeliveryEventsResponse> {
  const query = new URLSearchParams();
  if (params?.channel) query.set("channel", params.channel);
  query.set("limit", String(params?.limit ?? 100));
  return getJson<SiteCoworkerDeliveryEventsResponse>(
    `/competitive/sites/${siteId}/coworker/delivery/events?${query.toString()}`,
  );
}

export function reviewSiteCoworkerDeliveryEvent(
  siteId: string,
  eventId: string,
  payload?: { approve?: boolean; actor?: string; note?: string },
): Promise<SiteCoworkerDeliveryReviewResponse> {
  return postJson<SiteCoworkerDeliveryReviewResponse>(
    `/competitive/sites/${siteId}/coworker/delivery/events/${eventId}/review`,
    payload ?? {},
  );
}

export function fetchSiteCoworkerDeliverySla(
  siteId: string,
  params?: { limit?: number; approval_sla_minutes?: number },
): Promise<SiteCoworkerDeliverySlaResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 100));
  if (typeof params?.approval_sla_minutes === "number") {
    query.set("approval_sla_minutes", String(params.approval_sla_minutes));
  }
  return getJson<SiteCoworkerDeliverySlaResponse>(
    `/competitive/sites/${siteId}/coworker/delivery/sla?${query.toString()}`,
  );
}

export function fetchSiteCoworkerDeliveryEscalationPolicy(
  siteId: string,
  pluginCode: string,
): Promise<SiteCoworkerDeliveryEscalationPolicyResponse> {
  const query = new URLSearchParams();
  query.set("plugin_code", pluginCode);
  return getJson<SiteCoworkerDeliveryEscalationPolicyResponse>(
    `/competitive/sites/${siteId}/coworker/delivery/escalation-policy?${query.toString()}`,
  );
}

export function upsertSiteCoworkerDeliveryEscalationPolicy(
  siteId: string,
  payload: {
    plugin_code: string;
    enabled?: boolean;
    escalate_after_minutes?: number;
    max_escalation_count?: number;
    fallback_channels?: Array<"telegram" | "line" | "teams" | "webhook">;
    escalate_on_statuses?: string[];
    owner?: string;
  },
): Promise<SiteCoworkerDeliveryEscalationPolicyResponse> {
  return postJson<SiteCoworkerDeliveryEscalationPolicyResponse>(
    `/competitive/sites/${siteId}/coworker/delivery/escalation-policy`,
    payload,
  );
}

export function runSiteCoworkerDeliveryEscalation(
  siteId: string,
  payload: {
    plugin_code: string;
    dry_run?: boolean | null;
    force?: boolean;
    actor?: string;
  },
): Promise<SiteCoworkerDeliveryEscalationRunResponse> {
  return postJson<SiteCoworkerDeliveryEscalationRunResponse>(
    `/competitive/sites/${siteId}/coworker/delivery/escalation/run`,
    payload,
  );
}

export function runCoworkerDeliveryEscalationScheduler(params?: {
  site_id?: string;
  plugin_code?: string;
  limit?: number;
  dry_run_override?: boolean | null;
  actor?: string;
}): Promise<SiteCoworkerDeliveryEscalationSchedulerResponse> {
  const query = new URLSearchParams();
  if (params?.site_id) query.set("site_id", params.site_id);
  if (params?.plugin_code) query.set("plugin_code", params.plugin_code);
  query.set("limit", String(params?.limit ?? 100));
  if (typeof params?.dry_run_override === "boolean") {
    query.set("dry_run_override", String(params.dry_run_override));
  }
  if (params?.actor) query.set("actor", params.actor);
  return postJson<SiteCoworkerDeliveryEscalationSchedulerResponse>(
    `/competitive/coworker/delivery/escalation/scheduler/run?${query.toString()}`,
    {},
  );
}

export function fetchCoworkerDeliveryEscalationFederation(params?: {
  plugin_code?: string;
  approval_sla_minutes?: number;
  limit?: number;
}): Promise<SiteCoworkerDeliveryEscalationFederationResponse> {
  const query = new URLSearchParams();
  if (params?.plugin_code) query.set("plugin_code", params.plugin_code);
  if (typeof params?.approval_sla_minutes === "number") {
    query.set("approval_sla_minutes", String(params.approval_sla_minutes));
  }
  query.set("limit", String(params?.limit ?? 200));
  return getJson<SiteCoworkerDeliveryEscalationFederationResponse>(
    `/competitive/coworker/delivery/escalation/federation?${query.toString()}`,
  );
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

export function fetchSiteRedShadowPentestPolicy(siteId: string): Promise<SiteRedShadowPentestPolicyResponse> {
  return getJson<SiteRedShadowPentestPolicyResponse>(`/competitive/sites/${siteId}/red/shadow-pentest/policy`);
}

export function upsertSiteRedShadowPentestPolicy(
  siteId: string,
  payload: {
    crawl_depth?: number;
    max_pages?: number;
    change_threshold?: number;
    schedule_interval_minutes?: number;
    auto_assign_zero_day_pack?: boolean;
    route_alert?: boolean;
    enabled?: boolean;
    owner?: string;
  },
): Promise<SiteRedShadowPentestPolicyResponse> {
  return postJson<SiteRedShadowPentestPolicyResponse>(`/competitive/sites/${siteId}/red/shadow-pentest/policy`, payload);
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

export function runSiteRedShadowPentest(
  siteId: string,
  payload?: { dry_run?: boolean | null; force?: boolean; actor?: string },
): Promise<SiteRedShadowPentestRunResponse> {
  return postJson<SiteRedShadowPentestRunResponse>(`/competitive/sites/${siteId}/red/shadow-pentest/run`, payload ?? {});
}

export function fetchSiteRedExploitAutopilotRuns(siteId: string, limit = 30): Promise<SiteRedExploitAutopilotRunListResponse> {
  return getJson<SiteRedExploitAutopilotRunListResponse>(`/competitive/sites/${siteId}/red/exploit-autopilot/runs?limit=${limit}`);
}

export function fetchSiteRedShadowPentestRuns(siteId: string, limit = 30): Promise<SiteRedShadowPentestRunListResponse> {
  return getJson<SiteRedShadowPentestRunListResponse>(`/competitive/sites/${siteId}/red/shadow-pentest/runs?limit=${limit}`);
}

export function fetchSiteRedShadowPentestAssets(siteId: string, limit = 200): Promise<SiteRedShadowPentestAssetResponse> {
  return getJson<SiteRedShadowPentestAssetResponse>(`/competitive/sites/${siteId}/red/shadow-pentest/assets?limit=${limit}`);
}

export function triggerSiteRedShadowPentestDeployEvent(
  siteId: string,
  payload: {
    deploy_id: string;
    release_version?: string;
    changed_paths?: string[];
    actor?: string;
    dry_run_override?: boolean | null;
  },
): Promise<SiteRedShadowPentestRunResponse> {
  return postJson<SiteRedShadowPentestRunResponse>(`/competitive/sites/${siteId}/red/shadow-pentest/deploy-event`, payload);
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

export function runRedShadowPentestScheduler(params?: {
  limit?: number;
  dry_run_override?: boolean;
  actor?: string;
}): Promise<SiteRedShadowPentestSchedulerResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(params?.limit ?? 100));
  if (params?.dry_run_override !== undefined) query.set("dry_run_override", String(params.dry_run_override));
  if (params?.actor) query.set("actor", params.actor);
  return postJson<SiteRedShadowPentestSchedulerResponse>(`/competitive/red/shadow-pentest/scheduler/run?${query.toString()}`, {});
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

export function fetchSoarMarketplacePacks(params?: { category?: string; audience?: string; limit?: number }): Promise<SoarMarketplacePackListResponse> {
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  if (params?.audience) query.set("audience", params.audience);
  query.set("limit", String(params?.limit ?? 200));
  return getJson<SoarMarketplacePackListResponse>(`/competitive/soar/marketplace/packs?${query.toString()}`);
}

export function fetchSoarConnectorResultContracts(params?: {
  connector_source?: string;
  playbook_code?: string;
}): Promise<SoarConnectorResultContractListResponse> {
  const query = new URLSearchParams();
  if (params?.connector_source) query.set("connector_source", params.connector_source);
  if (params?.playbook_code) query.set("playbook_code", params.playbook_code);
  return getJson<SoarConnectorResultContractListResponse>(`/competitive/soar/contracts/results?${query.toString()}`);
}

export function installSoarMarketplacePack(
  packCode: string,
  payload?: { actor?: string; scope_override?: "" | "community" | "partner" | "private" },
): Promise<{ status: string; pack: Record<string, unknown>; installed_count: number; installed_playbooks: Record<string, unknown>[] }> {
  return postJson<{ status: string; pack: Record<string, unknown>; installed_count: number; installed_playbooks: Record<string, unknown>[] }>(
    `/competitive/soar/marketplace/packs/${packCode}/install`,
    payload ?? {},
  );
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

export function verifySoarExecution(
  executionId: string,
  payload?: { actor?: string },
): Promise<SoarExecutionVerifyResponse> {
  return postJson<SoarExecutionVerifyResponse>(`/competitive/soar/executions/${executionId}/verify`, payload ?? {});
}

export function ingestSoarConnectorResult(
  siteId: string,
  executionId: string,
  payload: {
    connector_source?: string;
    contract_code: string;
    external_action_ref?: string;
    webhook_event_id?: string;
    status?: string;
    payload?: Record<string, unknown>;
    actor?: string;
  },
): Promise<SoarConnectorResultResponse> {
  return postJson<SoarConnectorResultResponse>(
    `/competitive/sites/${siteId}/soar/executions/${executionId}/connector-result`,
    payload,
  );
}

export function fetchSoarConnectorResults(
  siteId: string,
  executionId: string,
  limit = 20,
): Promise<SoarConnectorResultListResponse> {
  return getJson<SoarConnectorResultListResponse>(
    `/competitive/sites/${siteId}/soar/executions/${executionId}/connector-results?limit=${limit}`,
  );
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
