import { useMemo, useState } from "react";

import {
  fetchSiteExploitPathRuns,
  fetchSiteRedExploitAutopilotPolicy,
  fetchSiteRedExploitAutopilotRuns,
  fetchSiteRedScans,
  fetchThreatContentPipelineFederation,
  fetchThreatContentPipelinePolicy,
  fetchThreatContentPipelineRuns,
  fetchThreatContentPacks,
  runRedExploitAutopilotScheduler,
  runSiteRedExploitAutopilot,
  runSiteRedScan,
  runThreatContentPipeline,
  runThreatContentPipelineScheduler,
  simulateSiteExploitPath,
  upsertThreatContentPipelinePolicy,
  upsertSiteRedExploitAutopilotPolicy,
} from "@/lib/api";
import type {
  SiteExploitPathRunsResponse,
  SiteRedExploitAutopilotPolicyResponse,
  SiteRedExploitAutopilotRunListResponse,
  SiteRedScanHistoryResponse,
  SiteRow,
  ThreatContentPipelineFederationResponse,
  ThreatContentPipelinePolicyResponse,
  ThreatContentPipelineRunListResponse,
  ThreatContentPackRow,
} from "@/lib/types";

type Props = {
  sites: SiteRow[];
  selectedSiteId: string;
  onSelectSite: (siteId: string) => void;
  canView: boolean;
  canEditPolicy: boolean;
  canApprove: boolean;
};

const SCAN_CASES = [
  { key: "baseline_scan", label: "Baseline Web Scan" },
  { key: "vuln_scan", label: "Vulnerability Sweep" },
  { key: "pentest_sim", label: "Pentest Simulation" },
];

type RiskTier = "low" | "medium" | "high" | "critical";

export function RedTeamPanel({ sites, selectedSiteId, onSelectSite, canView, canEditPolicy, canApprove }: Props) {
  const [busyKey, setBusyKey] = useState("");
  const [error, setError] = useState("");
  const [historyBySite, setHistoryBySite] = useState<Record<string, SiteRedScanHistoryResponse>>({});
  const [exploitRunsBySite, setExploitRunsBySite] = useState<Record<string, SiteExploitPathRunsResponse>>({});
  const [threatPacks, setThreatPacks] = useState<ThreatContentPackRow[]>([]);
  const [autopilotPolicyBySite, setAutopilotPolicyBySite] = useState<Record<string, SiteRedExploitAutopilotPolicyResponse["policy"]>>({});
  const [autopilotRunsBySite, setAutopilotRunsBySite] = useState<Record<string, SiteRedExploitAutopilotRunListResponse>>({});
  const [autopilotRunSummary, setAutopilotRunSummary] = useState("No autopilot run yet");
  const [pipelineScope, setPipelineScope] = useState("global");
  const [pipelinePolicySummary, setPipelinePolicySummary] = useState("No threat-content pipeline policy loaded");
  const [pipelineRunSummary, setPipelineRunSummary] = useState("No pipeline run yet");
  const [pipelineRuns, setPipelineRuns] = useState<ThreatContentPipelineRunListResponse | null>(null);
  const [pipelineFederation, setPipelineFederation] = useState<ThreatContentPipelineFederationResponse | null>(null);

  const [pipelineMinRefreshMinutes, setPipelineMinRefreshMinutes] = useState(1440);
  const [pipelinePreferredCategoriesCsv, setPipelinePreferredCategoriesCsv] = useState("identity,ransomware,phishing,web");
  const [pipelineMaxPacksPerRun, setPipelineMaxPacksPerRun] = useState(8);
  const [pipelineAutoActivate, setPipelineAutoActivate] = useState(true);
  const [pipelineEnabled, setPipelineEnabled] = useState(true);

  const [minRiskScore, setMinRiskScore] = useState(50);
  const [minRiskTier, setMinRiskTier] = useState<RiskTier>("medium");
  const [preferredPackCategory, setPreferredPackCategory] = useState("identity");
  const [targetSurface, setTargetSurface] = useState("/admin-login");
  const [simulationDepth, setSimulationDepth] = useState(3);
  const [maxRequestsPerMinute, setMaxRequestsPerMinute] = useState(30);
  const [stopOnCritical, setStopOnCritical] = useState(true);
  const [simulationOnly, setSimulationOnly] = useState(true);
  const [autoRun, setAutoRun] = useState(false);
  const [routeAlert, setRouteAlert] = useState(true);
  const [scheduleMinutes, setScheduleMinutes] = useState(120);

  const selectedSite = useMemo(() => sites.find((site) => site.site_id === selectedSiteId) || null, [sites, selectedSiteId]);

  const applyPolicyForm = (policy: SiteRedExploitAutopilotPolicyResponse["policy"]) => {
    setMinRiskScore(policy.min_risk_score);
    setMinRiskTier(policy.min_risk_tier);
    setPreferredPackCategory(policy.preferred_pack_category);
    setTargetSurface(policy.target_surface);
    setSimulationDepth(policy.simulation_depth);
    setMaxRequestsPerMinute(policy.max_requests_per_minute);
    setStopOnCritical(Boolean(policy.stop_on_critical));
    setSimulationOnly(Boolean(policy.simulation_only));
    setAutoRun(Boolean(policy.auto_run));
    setRouteAlert(Boolean(policy.route_alert));
    setScheduleMinutes(policy.schedule_interval_minutes);
  };

  const applyPipelinePolicyForm = (policy: ThreatContentPipelinePolicyResponse["policy"]) => {
    setPipelineScope(policy.scope || "global");
    setPipelineMinRefreshMinutes(policy.min_refresh_interval_minutes);
    setPipelinePreferredCategoriesCsv((policy.preferred_categories || []).join(","));
    setPipelineMaxPacksPerRun(policy.max_packs_per_run);
    setPipelineAutoActivate(Boolean(policy.auto_activate));
    setPipelineEnabled(Boolean(policy.enabled));
    setPipelinePolicySummary(
      `scope=${policy.scope} refresh=${policy.min_refresh_interval_minutes}m categories=${(policy.preferred_categories || []).join(",")} max_packs=${policy.max_packs_per_run} auto_activate=${String(policy.auto_activate)}`,
    );
  };

  const loadThreatPacks = async (): Promise<ThreatContentPackRow[]> => {
    try {
      const response = await fetchThreatContentPacks({ active_only: true, limit: 20 });
      setThreatPacks(response.rows || []);
      return response.rows || [];
    } catch {
      return [];
    }
  };

  const loadHistory = async (siteId: string) => {
    try {
      const history = await fetchSiteRedScans(siteId, 10);
      setHistoryBySite((prev) => ({ ...prev, [siteId]: history }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_history_load_failed");
    }
  };

  const loadExploitRuns = async (siteId: string) => {
    try {
      const runs = await fetchSiteExploitPathRuns(siteId, 10);
      setExploitRunsBySite((prev) => ({ ...prev, [siteId]: runs }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "exploit_runs_load_failed");
    }
  };

  const loadAutopilotPolicy = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedExploitAutopilotPolicy(siteId);
      setAutopilotPolicyBySite((prev) => ({ ...prev, [siteId]: response.policy }));
      applyPolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "autopilot_policy_load_failed");
    }
  };

  const loadAutopilotRuns = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedExploitAutopilotRuns(siteId, 10);
      setAutopilotRunsBySite((prev) => ({ ...prev, [siteId]: response }));
      const latest = response.rows?.[0];
      if (latest) {
        setAutopilotRunSummary(
          `${latest.status} risk=${latest.risk_tier}/${latest.risk_score} pack=${latest.threat_pack_code || "none"} executed=${String(latest.executed)}`,
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "autopilot_runs_load_failed");
    }
  };

  const loadThreatContentPipelinePolicy = async () => {
    if (!canView) return;
    try {
      const response = await fetchThreatContentPipelinePolicy(pipelineScope || "global");
      applyPipelinePolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_pipeline_policy_load_failed");
    }
  };

  const loadThreatContentPipelineRuns = async () => {
    if (!canView) return;
    try {
      const response = await fetchThreatContentPipelineRuns({ scope: pipelineScope || "global", limit: 10 });
      setPipelineRuns(response);
      const latest = response.rows?.[0];
      if (latest) {
        setPipelineRunSummary(
          `${latest.status} categories=${latest.selected_categories.join(",")} candidate=${latest.candidate_count} created=${latest.created_count} refreshed=${latest.refreshed_count}`,
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_pipeline_runs_load_failed");
    }
  };

  const loadThreatContentPipelineFederation = async () => {
    if (!canView) return;
    try {
      const response = await fetchThreatContentPipelineFederation({ limit: 200, stale_after_hours: 48 });
      setPipelineFederation(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_pipeline_federation_load_failed");
    }
  };

  const runCase = async (siteId: string, scanType: string) => {
    setError("");
    setBusyKey(`${siteId}:${scanType}`);
    try {
      await runSiteRedScan(siteId, { scan_type: scanType });
      await loadHistory(siteId);
      await loadAutopilotPolicy(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_scan_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runExploitPath = async (siteId: string) => {
    setError("");
    setBusyKey(`${siteId}:exploit_path`);
    try {
      const packs = threatPacks.length > 0 ? threatPacks : await loadThreatPacks();
      await simulateSiteExploitPath(siteId, {
        threat_pack_code: packs[0]?.pack_code || "",
        simulation_depth: 3,
        target_surface: "/admin-login",
        max_requests_per_minute: 20,
        simulation_only: true,
      });
      await loadExploitRuns(siteId);
      await loadAutopilotRuns(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "exploit_path_failed");
    } finally {
      setBusyKey("");
    }
  };

  const saveAutopilotPolicy = async (siteId: string) => {
    setError("");
    setBusyKey(`${siteId}:autopilot_policy`);
    try {
      const response = await upsertSiteRedExploitAutopilotPolicy(siteId, {
        min_risk_score: minRiskScore,
        min_risk_tier: minRiskTier,
        preferred_pack_category: preferredPackCategory,
        target_surface: targetSurface,
        simulation_depth: simulationDepth,
        max_requests_per_minute: maxRequestsPerMinute,
        stop_on_critical: stopOnCritical,
        simulation_only: simulationOnly,
        auto_run: autoRun,
        route_alert: routeAlert,
        schedule_interval_minutes: scheduleMinutes,
        enabled: true,
        owner: "security",
      });
      setAutopilotPolicyBySite((prev) => ({ ...prev, [siteId]: response.policy }));
      applyPolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "autopilot_policy_save_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runAutopilot = async (siteId: string, dryRun: boolean, force: boolean) => {
    setError("");
    setBusyKey(`${siteId}:autopilot_run`);
    try {
      const response = await runSiteRedExploitAutopilot(siteId, {
        dry_run: dryRun,
        force,
        actor: "dashboard_operator",
      });
      setAutopilotRunSummary(
        `${response.status} risk=${response.risk.risk_tier}/${response.risk.risk_score} should_run=${String(response.execution.should_run)} executed=${String(response.execution.executed)}`,
      );
      await loadExploitRuns(siteId);
      await loadAutopilotRuns(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "autopilot_run_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runAutopilotScheduler = async () => {
    setError("");
    setBusyKey("red_autopilot_scheduler");
    try {
      const response = await runRedExploitAutopilotScheduler({
        limit: 200,
        dry_run_override: true,
        actor: "dashboard_scheduler",
      });
      setAutopilotRunSummary(
        `scheduler policies=${response.scheduled_policy_count} executed=${response.executed_count} skipped=${response.skipped_count}`,
      );
      if (selectedSiteId) {
        await loadAutopilotRuns(selectedSiteId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "autopilot_scheduler_failed");
    } finally {
      setBusyKey("");
    }
  };

  const saveThreatContentPipelinePolicy = async () => {
    setError("");
    setBusyKey("threat_pipeline_policy");
    try {
      const preferredCategories = pipelinePreferredCategoriesCsv
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      const response = await upsertThreatContentPipelinePolicy({
        scope: pipelineScope || "global",
        min_refresh_interval_minutes: pipelineMinRefreshMinutes,
        preferred_categories: preferredCategories,
        max_packs_per_run: pipelineMaxPacksPerRun,
        auto_activate: pipelineAutoActivate,
        route_alert: false,
        enabled: pipelineEnabled,
        owner: "security",
      });
      applyPipelinePolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_pipeline_policy_save_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runThreatPipeline = async (dryRun: boolean, force: boolean) => {
    setError("");
    setBusyKey("threat_pipeline_run");
    try {
      const response = await runThreatContentPipeline({
        scope: pipelineScope || "global",
        dry_run: dryRun,
        force,
        actor: "dashboard_operator",
      });
      setPipelineRunSummary(
        `${response.status} should_run=${String(response.execution.should_run)} candidate=${response.execution.candidate_count} created=${response.execution.created_count} refreshed=${response.execution.refreshed_count}`,
      );
      await loadThreatContentPipelineRuns();
      await loadThreatContentPipelineFederation();
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_pipeline_run_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runThreatPipelineScheduler = async () => {
    setError("");
    setBusyKey("threat_pipeline_scheduler");
    try {
      const response = await runThreatContentPipelineScheduler({
        limit: 20,
        dry_run_override: true,
        actor: "dashboard_scheduler",
      });
      setPipelineRunSummary(
        `scheduler policies=${response.scheduled_policy_count} executed=${response.executed_count} skipped=${response.skipped_count}`,
      );
      await loadThreatContentPipelineRuns();
      await loadThreatContentPipelineFederation();
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_pipeline_scheduler_failed");
    } finally {
      setBusyKey("");
    }
  };

  return (
    <section className="card p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Red Team Service</h2>
      <p className="mt-1 text-xs text-slate-400">AI-driven authorized simulation scans by site.</p>
      <p className="mt-1 text-xs text-slate-500">
        RBAC: viewer={String(canView)} policy_editor={String(canEditPolicy)} approver={String(canApprove)}
      </p>

      {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}

      <div className="mt-3 space-y-2">
        {sites.length === 0 ? <p className="text-xs text-slate-500">No site found. Add site in Configuration menu.</p> : null}
        {sites.map((site) => {
          const expanded = selectedSiteId === site.site_id;
          const history = historyBySite[site.site_id];
          const autopilotPolicy = autopilotPolicyBySite[site.site_id];
          return (
            <div key={site.site_id} className="rounded-md border border-slate-800 bg-panelAlt/30 p-3">
              <button
                type="button"
                onClick={() => {
                  onSelectSite(site.site_id);
                  void loadHistory(site.site_id);
                  void loadExploitRuns(site.site_id);
                  void loadThreatPacks();
                  void loadAutopilotPolicy(site.site_id);
                  void loadAutopilotRuns(site.site_id);
                  void loadThreatContentPipelinePolicy();
                  void loadThreatContentPipelineRuns();
                  void loadThreatContentPipelineFederation();
                }}
                className="w-full text-left"
              >
                <p className="text-xs font-semibold text-slate-100 wrap-anywhere">{site.display_name}</p>
                <p className="mt-1 font-mono text-[11px] text-slate-400 wrap-anywhere">{site.base_url}</p>
              </button>

              {expanded ? (
                <div className="mt-3 space-y-2">
                  <div className="grid gap-2 sm:grid-cols-3">
                    {SCAN_CASES.map((scan) => (
                      <button
                        key={scan.key}
                        type="button"
                        onClick={() => void runCase(site.site_id, scan.key)}
                        disabled={busyKey.length > 0}
                        className="rounded-md border border-danger/50 bg-danger/10 px-2 py-2 text-[11px] text-danger hover:bg-danger/20 disabled:opacity-60"
                      >
                        {scan.label}
                      </button>
                    ))}
                  </div>

                  <button
                    type="button"
                    onClick={() => void runExploitPath(site.site_id)}
                    disabled={busyKey.length > 0}
                    className="w-full rounded-md border border-warning/50 bg-warning/10 px-2 py-2 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                  >
                    Exploit Path Simulation (AI)
                  </button>

                  <div className="rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
                    <p className="text-slate-300 wrap-anywhere">Red Exploit Autopilot Policy</p>
                    {canView ? (
                      <p className="mt-1 text-slate-500 wrap-anywhere">
                        Current: risk&gt;={autopilotPolicy?.min_risk_score ?? minRiskScore}/{autopilotPolicy?.min_risk_tier ?? minRiskTier} category={autopilotPolicy?.preferred_pack_category ?? preferredPackCategory} auto_run={String(autopilotPolicy?.auto_run ?? autoRun)}
                      </p>
                    ) : (
                      <p className="mt-1 text-slate-500">No permission to view policy.</p>
                    )}

                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Min Risk Score</span>
                        <input
                          type="number"
                          min={1}
                          max={100}
                          value={minRiskScore}
                          onChange={(event) => setMinRiskScore(Number(event.target.value || 50))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Min Risk Tier</span>
                        <select
                          value={minRiskTier}
                          onChange={(event) => setMinRiskTier(event.target.value as RiskTier)}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        >
                          <option value="low">low</option>
                          <option value="medium">medium</option>
                          <option value="high">high</option>
                          <option value="critical">critical</option>
                        </select>
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Pack Category</span>
                        <input
                          value={preferredPackCategory}
                          onChange={(event) => setPreferredPackCategory(event.target.value)}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Target Surface</span>
                        <input
                          value={targetSurface}
                          onChange={(event) => setTargetSurface(event.target.value)}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Simulation Depth</span>
                        <input
                          type="number"
                          min={1}
                          max={5}
                          value={simulationDepth}
                          onChange={(event) => setSimulationDepth(Number(event.target.value || 3))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Max RPM</span>
                        <input
                          type="number"
                          min={1}
                          max={500}
                          value={maxRequestsPerMinute}
                          onChange={(event) => setMaxRequestsPerMinute(Number(event.target.value || 30))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Schedule (minutes)</span>
                        <input
                          type="number"
                          min={5}
                          max={1440}
                          value={scheduleMinutes}
                          onChange={(event) => setScheduleMinutes(Number(event.target.value || 120))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                    </div>

                    <div className="mt-2 flex flex-wrap gap-3 text-slate-300">
                      <label className="flex items-center gap-1 text-[11px]">
                        <input type="checkbox" checked={stopOnCritical} onChange={(event) => setStopOnCritical(event.target.checked)} />
                        stop_on_critical
                      </label>
                      <label className="flex items-center gap-1 text-[11px]">
                        <input type="checkbox" checked={simulationOnly} onChange={(event) => setSimulationOnly(event.target.checked)} />
                        simulation_only
                      </label>
                      <label className="flex items-center gap-1 text-[11px]">
                        <input type="checkbox" checked={autoRun} onChange={(event) => setAutoRun(event.target.checked)} />
                        auto_run
                      </label>
                      <label className="flex items-center gap-1 text-[11px]">
                        <input type="checkbox" checked={routeAlert} onChange={(event) => setRouteAlert(event.target.checked)} />
                        route_alert
                      </label>
                    </div>

                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                      <button
                        type="button"
                        disabled={!canEditPolicy || busyKey.length > 0}
                        onClick={() => void saveAutopilotPolicy(site.site_id)}
                        className="rounded-md border border-accent/60 bg-accent/10 px-2 py-2 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                      >
                        Save Red Autopilot Policy
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runAutopilot(site.site_id, true, false)}
                        className="rounded-md border border-slate-600 px-2 py-2 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                      >
                        Run Autopilot Dry-Run
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runAutopilot(site.site_id, false, true)}
                        className="rounded-md border border-warning/50 bg-warning/10 px-2 py-2 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                      >
                        Run Autopilot Apply
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runAutopilotScheduler()}
                        className="rounded-md border border-slate-600 px-2 py-2 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                      >
                        Trigger Autopilot Scheduler
                      </button>
                    </div>

                    <p className="mt-2 text-slate-500 wrap-anywhere">{autopilotRunSummary}</p>
                  </div>

                  <div className="rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
                    <p className="text-slate-300 wrap-anywhere">Threat Content Pipeline (O2)</p>
                    <p className="mt-1 text-slate-500 wrap-anywhere">{pipelinePolicySummary}</p>
                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Scope</span>
                        <input
                          value={pipelineScope}
                          onChange={(event) => setPipelineScope(event.target.value || "global")}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Refresh Interval (minutes)</span>
                        <input
                          type="number"
                          min={5}
                          max={10080}
                          value={pipelineMinRefreshMinutes}
                          onChange={(event) => setPipelineMinRefreshMinutes(Number(event.target.value || 1440))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400 md:col-span-2">
                        <span className="mb-1 block text-[11px]">Preferred Categories (comma-separated)</span>
                        <input
                          value={pipelinePreferredCategoriesCsv}
                          onChange={(event) => setPipelinePreferredCategoriesCsv(event.target.value)}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Max Packs per Run</span>
                        <input
                          type="number"
                          min={1}
                          max={50}
                          value={pipelineMaxPacksPerRun}
                          onChange={(event) => setPipelineMaxPacksPerRun(Number(event.target.value || 8))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-3 text-slate-300">
                      <label className="flex items-center gap-1 text-[11px]">
                        <input
                          type="checkbox"
                          checked={pipelineAutoActivate}
                          onChange={(event) => setPipelineAutoActivate(event.target.checked)}
                        />
                        auto_activate
                      </label>
                      <label className="flex items-center gap-1 text-[11px]">
                        <input type="checkbox" checked={pipelineEnabled} onChange={(event) => setPipelineEnabled(event.target.checked)} />
                        enabled
                      </label>
                    </div>
                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                      <button
                        type="button"
                        disabled={!canEditPolicy || busyKey.length > 0}
                        onClick={() => void saveThreatContentPipelinePolicy()}
                        className="rounded-md border border-accent/60 bg-accent/10 px-2 py-2 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                      >
                        Save Pipeline Policy
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runThreatPipeline(true, false)}
                        className="rounded-md border border-slate-600 px-2 py-2 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                      >
                        Run Pipeline Dry-Run
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runThreatPipeline(false, true)}
                        className="rounded-md border border-warning/50 bg-warning/10 px-2 py-2 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                      >
                        Run Pipeline Apply
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runThreatPipelineScheduler()}
                        className="rounded-md border border-slate-600 px-2 py-2 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                      >
                        Trigger Pipeline Scheduler
                      </button>
                    </div>
                    <p className="mt-2 text-slate-500 wrap-anywhere">{pipelineRunSummary}</p>
                    <div className="mt-2 max-h-32 overflow-auto rounded border border-slate-800 p-2">
                      {(pipelineRuns?.rows || []).length === 0 ? <p className="text-slate-500">No pipeline runs yet.</p> : null}
                      {(pipelineRuns?.rows || []).slice(0, 4).map((run) => (
                        <p key={run.run_id} className="text-slate-300 wrap-anywhere">
                          {run.created_at} [{run.status}] candidate={run.candidate_count} created={run.created_count} refreshed=
                          {run.refreshed_count}
                        </p>
                      ))}
                    </div>
                    {pipelineFederation ? (
                      <div className="mt-2 max-h-28 overflow-auto rounded border border-slate-800 p-2">
                        <p className="text-slate-400 wrap-anywhere">
                          federation categories={pipelineFederation.count} stale={pipelineFederation.stale_count}
                        </p>
                        {pipelineFederation.rows.slice(0, 4).map((row) => (
                          <p key={row.category} className="text-slate-300 wrap-anywhere">
                            {row.category}: packs={row.pack_count} mitre={row.unique_mitre_techniques} stale={String(row.is_stale)}
                          </p>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  <div className="max-h-52 overflow-auto rounded border border-slate-800 p-2 text-xs">
                    <p className="mb-2 text-slate-400">Scan Results</p>
                    {history?.rows?.length ? null : <p className="text-slate-500">No scans yet.</p>}
                    {(history?.rows || []).map((row) => (
                      <div key={row.scan_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/40 p-2">
                        <p className="text-slate-200">{row.scan_type}</p>
                        <p className="mt-1 text-slate-400 wrap-anywhere">{row.ai_summary}</p>
                      </div>
                    ))}
                  </div>

                  <div className="max-h-44 overflow-auto rounded border border-slate-800 p-2 text-xs">
                    <p className="mb-2 text-slate-400">Exploit Path Runs</p>
                    {(exploitRunsBySite[site.site_id]?.rows || []).length === 0 ? (
                      <p className="text-slate-500">No exploit-path runs yet.</p>
                    ) : null}
                    {(exploitRunsBySite[site.site_id]?.rows || []).map((run) => (
                      <div key={run.run_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/40 p-2">
                        <p className="text-slate-200">risk_score={run.risk_score}</p>
                        <p className="mt-1 text-slate-400 wrap-anywhere">proof: {JSON.stringify(run.proof)}</p>
                      </div>
                    ))}
                  </div>

                  <div className="max-h-44 overflow-auto rounded border border-slate-800 p-2 text-xs">
                    <p className="mb-2 text-slate-400">Exploit Autopilot Runs</p>
                    {(autopilotRunsBySite[site.site_id]?.rows || []).length === 0 ? (
                      <p className="text-slate-500">No autopilot runs yet.</p>
                    ) : null}
                    {(autopilotRunsBySite[site.site_id]?.rows || []).map((run) => (
                      <div key={run.run_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/40 p-2">
                        <p className="text-slate-200 wrap-anywhere">
                          {run.status} risk={run.risk_tier}/{run.risk_score} executed={String(run.executed)}
                        </p>
                        <p className="mt-1 text-slate-400 wrap-anywhere">
                          pack={run.threat_pack_code || "none"} path={run.path_node_count}n/{run.path_edge_count}e confidence={run.proof_confidence}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      {selectedSite ? (
        <p className="mt-3 text-[11px] text-slate-500">
          Selected site: <span className="font-mono">{selectedSite.site_code}</span>
        </p>
      ) : null}
    </section>
  );
}
