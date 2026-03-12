import { useEffect, useMemo, useState } from "react";

import {
  fetchConnectorCredentialHygiene,
  fetchConnectorCredentialHygieneFederation,
  fetchConnectorCredentialHygienePolicy,
  fetchConnectorCredentialHygieneRuns,
  fetchConnectorCredentialRotationEvents,
  fetchConnectorCredentials,
  fetchFederationSecopsDataTier,
  fetchTenantSecopsDataTierBenchmark,
  runConnectorCredentialHygiene,
  runConnectorCredentialHygieneScheduler,
  runConnectorCredentialAutoRotate,
  rotateConnectorCredential,
  upsertConnectorCredentialHygienePolicy,
  upsertConnectorCredential,
  verifyConnectorCredentialRotation,
} from "@/lib/api";
import type {
  ConnectorCredentialAutoRotateResponse,
  ConnectorCredentialHygieneFederationResponse,
  ConnectorCredentialHygienePolicyResponse,
  ConnectorCredentialHygieneRunListResponse,
  ConnectorCredentialHygieneSchedulerResponse,
  ConnectorCredentialHygieneResponse,
  ConnectorCredentialRotationEventListResponse,
  ConnectorCredentialVaultListResponse,
  FederationSecopsDataTierResponse,
  SiteRow,
  TenantSecopsDataTierBenchmarkResponse,
} from "@/lib/types";

type Props = {
  selectedSite: SiteRow | null;
  canView: boolean;
  canEditPolicy: boolean;
  canApprove: boolean;
};

export function SecOpsDataTierPanel({ selectedSite, canView, canEditPolicy, canApprove }: Props) {
  const [connectorSource, setConnectorSource] = useState("splunk");
  const [credentialName, setCredentialName] = useState("api_key");
  const [secretValue, setSecretValue] = useState("");
  const [vault, setVault] = useState<ConnectorCredentialVaultListResponse | null>(null);
  const [rotationEvents, setRotationEvents] = useState<ConnectorCredentialRotationEventListResponse | null>(null);
  const [hygiene, setHygiene] = useState<ConnectorCredentialHygieneResponse | null>(null);
  const [hygieneFederation, setHygieneFederation] = useState<ConnectorCredentialHygieneFederationResponse | null>(null);
  const [hygienePolicy, setHygienePolicy] = useState<ConnectorCredentialHygienePolicyResponse | null>(null);
  const [hygieneRuns, setHygieneRuns] = useState<ConnectorCredentialHygieneRunListResponse | null>(null);
  const [hygieneScheduler, setHygieneScheduler] = useState<ConnectorCredentialHygieneSchedulerResponse | null>(null);
  const [benchmark, setBenchmark] = useState<TenantSecopsDataTierBenchmarkResponse | null>(null);
  const [federation, setFederation] = useState<FederationSecopsDataTierResponse | null>(null);
  const [rotationVerify, setRotationVerify] = useState<string>("");
  const [autoRotateDryRun, setAutoRotateDryRun] = useState(true);
  const [autoRotate, setAutoRotate] = useState<ConnectorCredentialAutoRotateResponse | null>(null);
  const [policyWarningDays, setPolicyWarningDays] = useState(7);
  const [policyMaxRotatePerRun, setPolicyMaxRotatePerRun] = useState(20);
  const [policyScheduleMinutes, setPolicyScheduleMinutes] = useState(60);
  const [policyAutoApply, setPolicyAutoApply] = useState(false);
  const [policyRouteAlert, setPolicyRouteAlert] = useState(true);
  const [policyEnabled, setPolicyEnabled] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const tenantCode = selectedSite?.tenant_code || "";

  const load = async () => {
    if (!tenantCode || !canView) {
      setVault(null);
      setRotationEvents(null);
      setHygiene(null);
      setHygieneFederation(null);
      setHygienePolicy(null);
      setHygieneRuns(null);
      setHygieneScheduler(null);
      setBenchmark(null);
      setFederation(null);
      setAutoRotate(null);
      setError(canView ? "Select tenant/site first" : "Viewer permission required");
      return;
    }
    setError("");
    try {
      const [vaultData, rotationData, hygieneData, hygieneFedData, policyData, runsData, benchData, fedData] = await Promise.all([
        fetchConnectorCredentials({ tenant_code: tenantCode, connector_source: connectorSource, limit: 50 }),
        fetchConnectorCredentialRotationEvents({ tenant_code: tenantCode, connector_source: connectorSource, limit: 50 }),
        fetchConnectorCredentialHygiene({
          tenant_code: tenantCode,
          connector_source: connectorSource,
          warning_days: 7,
          limit: 100,
        }),
        fetchConnectorCredentialHygieneFederation({ warning_days: 7, limit: 200 }),
        fetchConnectorCredentialHygienePolicy({ tenant_code: tenantCode, connector_source: connectorSource }),
        fetchConnectorCredentialHygieneRuns({ tenant_code: tenantCode, limit: 50 }),
        fetchTenantSecopsDataTierBenchmark(tenantCode, { lookback_hours: 24, sample_limit: 2000 }),
        fetchFederationSecopsDataTier({ lookback_hours: 24, limit: 200 }),
      ]);
      setVault(vaultData);
      setRotationEvents(rotationData);
      setHygiene(hygieneData);
      setHygieneFederation(hygieneFedData);
      setHygienePolicy(policyData);
      setHygieneRuns(runsData);
      setPolicyWarningDays(policyData.policy.warning_days);
      setPolicyMaxRotatePerRun(policyData.policy.max_rotate_per_run);
      setPolicyScheduleMinutes(policyData.policy.schedule_interval_minutes);
      setPolicyAutoApply(Boolean(policyData.policy.auto_apply));
      setPolicyRouteAlert(Boolean(policyData.policy.route_alert));
      setPolicyEnabled(Boolean(policyData.policy.enabled));
      setBenchmark(benchData);
      setFederation(fedData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "secops_data_tier_load_failed");
    }
  };

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), 30000);
    return () => clearInterval(timer);
  }, [tenantCode, connectorSource, canView]);

  const saveCredential = async () => {
    if (!tenantCode || !secretValue.trim()) {
      setError("tenant/site and secret value are required");
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await upsertConnectorCredential({
        tenant_code: tenantCode,
        connector_source: connectorSource,
        credential_name: credentialName,
        secret_value: secretValue.trim(),
        rotation_interval_days: 30,
        actor: "policy_editor_ui",
        metadata: { source: "secops_data_tier_panel" },
      });
      setSecretValue("");
      setMessage(`Credential ${response.status}: ${response.credential.connector_source}/${response.credential.credential_name}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "save_connector_credential_failed");
    } finally {
      setBusy(false);
    }
  };

  const rotateCredential = async () => {
    if (!tenantCode) {
      setError("tenant/site required");
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await rotateConnectorCredential({
        tenant_code: tenantCode,
        connector_source: connectorSource,
        credential_name: credentialName,
        rotation_reason: "manual_operator_rotation",
        actor: "approver_ui",
      });
      setMessage(`Credential rotated v${response.credential.secret_version} generated_secret=${response.generated_secret}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "rotate_connector_credential_failed");
    } finally {
      setBusy(false);
    }
  };

  const verifyRotationChain = async () => {
    if (!tenantCode) {
      setError("tenant/site required");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const response = await verifyConnectorCredentialRotation({
        tenant_code: tenantCode,
        connector_source: connectorSource,
        credential_name: credentialName,
        limit: 5000,
      });
      setRotationVerify(response.valid ? `valid chain count=${response.count || 0}` : `invalid at=${response.index} reason=${response.reason}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "verify_rotation_chain_failed");
    } finally {
      setBusy(false);
    }
  };

  const runAutoRotate = async () => {
    if (!tenantCode) {
      setError("tenant/site required");
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await runConnectorCredentialAutoRotate({
        tenant_code: tenantCode,
        connector_source: connectorSource,
        warning_days: 7,
        max_rotate: 20,
        dry_run: autoRotateDryRun,
        actor: "approver_ui",
        route_alert: true,
      });
      setAutoRotate(response);
      setMessage(
        `auto_rotate dry_run=${response.dry_run} candidate=${response.candidate_count || 0} executed=${response.executed_count || 0} failed=${response.failed_count || 0}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "auto_rotate_failed");
    } finally {
      setBusy(false);
    }
  };

  const saveHygienePolicy = async () => {
    if (!tenantCode) {
      setError("tenant/site required");
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await upsertConnectorCredentialHygienePolicy({
        tenant_code: tenantCode,
        connector_source: connectorSource,
        warning_days: policyWarningDays,
        max_rotate_per_run: policyMaxRotatePerRun,
        auto_apply: policyAutoApply,
        route_alert: policyRouteAlert,
        schedule_interval_minutes: policyScheduleMinutes,
        enabled: policyEnabled,
        owner: "policy_editor_ui",
      });
      setHygienePolicy(response);
      setMessage(
        `policy saved source=${response.policy.connector_source} warning_days=${response.policy.warning_days} auto_apply=${response.policy.auto_apply}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "save_hygiene_policy_failed");
    } finally {
      setBusy(false);
    }
  };

  const runManualHygiene = async () => {
    if (!tenantCode) {
      setError("tenant/site required");
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await runConnectorCredentialHygiene({
        tenant_code: tenantCode,
        connector_source: connectorSource,
        dry_run: autoRotateDryRun,
        actor: "approver_ui",
      });
      setMessage(
        `manual_hygiene run_id=${response.run?.run_id || "-"} risk=${response.run?.risk_tier || "unknown"} candidate=${response.execution?.candidate_count || 0}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "run_manual_hygiene_failed");
    } finally {
      setBusy(false);
    }
  };

  const runScheduler = async () => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await runConnectorCredentialHygieneScheduler({
        limit: 200,
        dry_run_override: autoRotateDryRun,
        actor: "approver_ui",
      });
      setHygieneScheduler(response);
      setMessage(`scheduler executed=${response.executed_count} skipped=${response.skipped_count}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "run_hygiene_scheduler_failed");
    } finally {
      setBusy(false);
    }
  };

  const benchmarkSummary = useMemo(() => {
    if (!benchmark || benchmark.status !== "ok") return "No benchmark data";
    return `events=${benchmark.event_counts?.total_events || 0} eps=${benchmark.performance?.throughput_eps || 0} search_p95_ms=${
      benchmark.performance?.search_latency_p95_ms || 0
    } cost_usd=${benchmark.cost?.monthly_total_cost_usd || 0} risk=${benchmark.risk?.risk_tier || "unknown"}`;
  }, [benchmark]);

  return (
    <section className="card mt-4 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">SecOps Data Tier</h2>
        <button
          type="button"
          className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400"
          onClick={() => void load()}
        >
          Refresh
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-400">
        Credential vault + rotation evidence + ingestion/search/retention benchmark and federation cost trend.
      </p>
      <p className="mt-1 text-xs text-slate-500">
        RBAC: viewer={String(canView)} policy_editor={String(canEditPolicy)} approver={String(canApprove)}
      </p>
      {error ? <p className="mt-2 text-sm text-danger">{error}</p> : null}
      {message ? <p className="mt-2 text-xs text-accent wrap-anywhere">{message}</p> : null}

      <div className="mt-3 grid gap-4 xl:grid-cols-2">
        <div className="rounded border border-slate-800 bg-panelAlt/20 p-3 text-xs">
          <p className="text-slate-300">Connector Credential Vault</p>
          <p className="mt-1 text-slate-400 wrap-anywhere">
            hygiene_risk={hygiene?.risk?.risk_tier || "unknown"} score={hygiene?.risk?.risk_score || 0} due=
            {hygiene?.summary?.rotation_due_count || 0} expired={hygiene?.summary?.expired_count || 0}
          </p>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <label className="text-[11px] text-slate-400">
              Connector
              <input
                value={connectorSource}
                onChange={(event) => setConnectorSource(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Credential Name
              <input
                value={credentialName}
                onChange={(event) => setCredentialName(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400 col-span-2">
              Secret Value
              <input
                value={secretValue}
                onChange={(event) => setSecretValue(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy || !canEditPolicy}
              onClick={() => void saveCredential()}
              className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
            >
              Save Credential
            </button>
            <button
              type="button"
              disabled={busy || !canApprove}
              onClick={() => void rotateCredential()}
              className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
            >
              Rotate Credential
            </button>
            <button
              type="button"
              disabled={busy || !canView}
              onClick={() => void verifyRotationChain()}
              className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
            >
              Verify Rotation Chain
            </button>
            <label className="flex items-center gap-1 rounded border border-slate-700 px-2 py-1 text-[11px] text-slate-300">
              <input type="checkbox" checked={autoRotateDryRun} onChange={(event) => setAutoRotateDryRun(event.target.checked)} />
              auto-rotate dry-run
            </label>
            <button
              type="button"
              disabled={busy || !canApprove}
              onClick={() => void runAutoRotate()}
              className="rounded border border-danger/60 bg-danger/10 px-2 py-1 text-[11px] text-danger hover:bg-danger/20 disabled:opacity-60"
            >
              Run Auto-Rotate Due
            </button>
          </div>
          {rotationVerify ? <p className="mt-2 text-slate-300 wrap-anywhere">rotation_chain={rotationVerify}</p> : null}
          {autoRotate ? (
            <p className="mt-1 text-slate-300 wrap-anywhere">
              auto_rotate selected={autoRotate.selected_count || 0} planned={autoRotate.planned_count || 0} executed=
              {autoRotate.executed_count || 0}
            </p>
          ) : null}
          {hygiene?.risk?.recommendation ? <p className="mt-1 text-slate-400 wrap-anywhere">{hygiene.risk.recommendation}</p> : null}

          <div className="mt-3 rounded border border-slate-800 p-2">
            <p className="text-slate-300">Hygiene Policy</p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              source={hygienePolicy?.policy.connector_source || connectorSource} owner={hygienePolicy?.policy.owner || "system"}
            </p>
            <div className="mt-2 grid grid-cols-2 gap-2">
              <label className="text-[11px] text-slate-400">
                Warning Days
                <input
                  type="number"
                  value={policyWarningDays}
                  onChange={(event) => setPolicyWarningDays(Number(event.target.value))}
                  className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
                />
              </label>
              <label className="text-[11px] text-slate-400">
                Max Rotate/Run
                <input
                  type="number"
                  value={policyMaxRotatePerRun}
                  onChange={(event) => setPolicyMaxRotatePerRun(Number(event.target.value))}
                  className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
                />
              </label>
              <label className="text-[11px] text-slate-400 col-span-2">
                Schedule Interval (minutes)
                <input
                  type="number"
                  value={policyScheduleMinutes}
                  onChange={(event) => setPolicyScheduleMinutes(Number(event.target.value))}
                  className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
                />
              </label>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
              <label className="flex items-center gap-1">
                <input type="checkbox" checked={policyAutoApply} onChange={(event) => setPolicyAutoApply(event.target.checked)} />
                auto-apply
              </label>
              <label className="flex items-center gap-1">
                <input type="checkbox" checked={policyRouteAlert} onChange={(event) => setPolicyRouteAlert(event.target.checked)} />
                route-alert
              </label>
              <label className="flex items-center gap-1">
                <input type="checkbox" checked={policyEnabled} onChange={(event) => setPolicyEnabled(event.target.checked)} />
                enabled
              </label>
              <button
                type="button"
                disabled={busy || !canEditPolicy}
                onClick={() => void saveHygienePolicy()}
                className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
              >
                Save Hygiene Policy
              </button>
              <button
                type="button"
                disabled={busy || !canApprove}
                onClick={() => void runManualHygiene()}
                className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
              >
                Run Hygiene Now
              </button>
              <button
                type="button"
                disabled={busy || !canApprove}
                onClick={() => void runScheduler()}
                className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
              >
                Run Scheduler
              </button>
            </div>
            {hygieneScheduler ? (
              <p className="mt-2 text-slate-400 wrap-anywhere">
                scheduler executed={hygieneScheduler.executed_count} skipped={hygieneScheduler.skipped_count}
              </p>
            ) : null}
          </div>

          <div className="mt-3 max-h-36 overflow-auto rounded border border-slate-800 p-2">
            <p className="mb-2 text-slate-400">Vault Records</p>
            {(vault?.rows || []).length === 0 ? <p className="text-slate-500">No credential record.</p> : null}
            {(vault?.rows || []).map((row) => (
              <div key={row.credential_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {row.connector_source}/{row.credential_name} v{row.secret_version}
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">
                  fp={row.secret_fingerprint_prefix} ref={row.external_ref || "-"} expires={row.expires_at || "-"}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-3 max-h-36 overflow-auto rounded border border-slate-800 p-2">
            <p className="mb-2 text-slate-400">Rotation Events</p>
            {(rotationEvents?.rows || []).length === 0 ? <p className="text-slate-500">No rotation events.</p> : null}
            {(rotationEvents?.rows || []).map((row) => (
              <div key={row.event_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {row.rotation_reason} {row.old_version}→{row.new_version}
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">
                  actor={row.actor} sig={row.signature.slice(0, 12)}... prev={row.prev_signature.slice(0, 12) || "-"}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-3 max-h-36 overflow-auto rounded border border-slate-800 p-2">
            <p className="mb-2 text-slate-400">Credential Hygiene</p>
            {(hygiene?.rows || []).length === 0 ? <p className="text-slate-500">No credential hygiene records.</p> : null}
            {(hygiene?.rows || []).slice(0, 15).map((row) => (
              <div key={row.credential_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {row.connector_source}/{row.credential_name} sev={row.severity} score={row.risk_score}
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">
                  age={row.age_days}d expires_in={row.expires_in_days ?? "n/a"} due={String(row.rotation_due)} expired=
                  {String(row.expired)}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-3 max-h-36 overflow-auto rounded border border-slate-800 p-2">
            <p className="mb-2 text-slate-400">Hygiene Run History</p>
            {(hygieneRuns?.rows || []).length === 0 ? <p className="text-slate-500">No hygiene run history.</p> : null}
            {(hygieneRuns?.rows || []).slice(0, 12).map((row) => (
              <div key={row.run_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {row.connector_source} risk={row.risk_tier} dry_run={String(row.dry_run)}
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">
                  candidate={row.candidate_count} executed={row.executed_count} failed={row.failed_count} alert={String(row.alert_routed)}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded border border-slate-800 bg-panelAlt/20 p-3 text-xs">
          <p className="text-slate-300">Tenant + Federation Benchmark</p>
          <p className="mt-2 text-slate-200 wrap-anywhere">{benchmarkSummary}</p>
          {benchmark?.risk?.recommendation ? (
            <p className="mt-1 text-slate-400 wrap-anywhere">{benchmark.risk.recommendation}</p>
          ) : null}

          <div className="mt-3 rounded border border-slate-800 p-2">
            <p className="mb-2 text-slate-400">Hourly Event Trend (sample)</p>
            {(benchmark?.retention?.event_trend_hourly || []).length === 0 ? <p className="text-slate-500">No trend data.</p> : null}
            {(benchmark?.retention?.event_trend_hourly || []).slice(-8).map((row) => (
              <p key={row.hour_epoch} className="text-slate-300 wrap-anywhere">
                {row.hour_epoch}: {row.event_count}
              </p>
            ))}
          </div>

          <div className="mt-3 max-h-44 overflow-auto rounded border border-slate-800 p-2">
            <p className="mb-2 text-slate-400">Federation Cost/Performance</p>
            {federation ? (
              <p className="text-slate-300 wrap-anywhere">
                tenants={federation.count} avg_eps={federation.summary.average_throughput_eps} avg_p95={federation.summary.average_search_p95_ms}
                total_cost={federation.summary.total_monthly_cost_usd}
              </p>
            ) : null}
            {(federation?.rows || []).slice(0, 10).map((row) => (
              <div key={row.tenant_id} className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {row.tenant_code} risk={row.risk_tier} score={row.risk_score}
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">
                  eps={row.throughput_eps} p95={row.search_latency_p95_ms}ms cost={row.monthly_total_cost_usd}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-3 max-h-44 overflow-auto rounded border border-slate-800 p-2">
            <p className="mb-2 text-slate-400">Federation Credential Hygiene</p>
            {hygieneFederation ? (
              <p className="text-slate-300 wrap-anywhere">
                tenants={hygieneFederation.count} due_total={hygieneFederation.summary.total_rotation_due} expired_total=
                {hygieneFederation.summary.total_expired}
              </p>
            ) : null}
            {(hygieneFederation?.rows || []).slice(0, 10).map((row) => (
              <div key={row.tenant_id} className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {row.tenant_code} risk={row.risk_tier} score={row.risk_score}
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">
                  credentials={row.credential_count} due={row.rotation_due_count} expired={row.expired_count}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
