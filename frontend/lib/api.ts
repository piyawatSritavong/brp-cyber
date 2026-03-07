import type {
  BlueIncidentFeed,
  DashboardResponse,
  GovernanceDashboardResponse,
  IntegrationAdaptersResponse,
  IntegrationEventIngestResponse,
  OrchestratorState,
  SiteBlueEventHistoryResponse,
  SiteListResponse,
  SitePurpleReportHistoryResponse,
  SitePurpleIsoGapTemplateResponse,
  SiteRedScanHistoryResponse,
  SiteRedScanResponse,
  SiteUpsertResponse,
  PurpleReport,
  RedRunResult,
  RedScenarioLibrary,
  TenantGateResponse,
  TenantHistoryResponse,
  TenantRemediation,
} from "./types";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const controlPlaneToken = process.env.NEXT_PUBLIC_CONTROL_PLANE_BEARER || "";

async function getJson<T>(path: string, token?: string): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${baseUrl}${path}`, { cache: "no-store", headers });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

async function postJson<T>(path: string, body: unknown, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
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
