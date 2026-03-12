import { useEffect, useState } from "react";

import {
  evaluateConnectorSla,
  fetchConnectorReliabilityBacklog,
  fetchConnectorReliabilityFederation,
  fetchConnectorReliabilityPolicy,
  fetchConnectorReliabilityRuns,
  fetchConnectorEvents,
  fetchConnectorHealth,
  fetchConnectorSlaBreaches,
  fetchConnectorSlaProfile,
  ingestConnectorEvent,
  runConnectorReliabilityReplay,
  runConnectorReliabilityScheduler,
  upsertConnectorReliabilityPolicy,
  upsertConnectorSlaProfile,
} from "@/lib/api";
import type {
  ConnectorEventListResponse,
  ConnectorHealthResponse,
  ConnectorReliabilityRunListResponse,
  SiteRow,
} from "@/lib/types";

type Props = {
  selectedSite: SiteRow | null;
  canView: boolean;
  canEditPolicy: boolean;
  canApprove: boolean;
};

export function ConnectorReliabilityPanel({ selectedSite, canView, canEditPolicy, canApprove }: Props) {
  const [events, setEvents] = useState<ConnectorEventListResponse | null>(null);
  const [health, setHealth] = useState<ConnectorHealthResponse | null>(null);
  const [replayRuns, setReplayRuns] = useState<ConnectorReliabilityRunListResponse | null>(null);

  const [slaSummary, setSlaSummary] = useState("No SLA profile loaded");
  const [slaEvalSummary, setSlaEvalSummary] = useState("");
  const [breachSummary, setBreachSummary] = useState("breaches=0");

  const [replayPolicySummary, setReplayPolicySummary] = useState("No replay policy loaded");
  const [backlogSummary, setBacklogSummary] = useState("backlog unresolved=0");
  const [federationSummary, setFederationSummary] = useState("federation risk=unknown");
  const [replayRunSummary, setReplayRunSummary] = useState("");

  const [connectorSource, setConnectorSource] = useState("splunk");

  const [minEvents, setMinEvents] = useState(20);
  const [minSuccessRate, setMinSuccessRate] = useState(95);
  const [maxDeadLetter, setMaxDeadLetter] = useState(5);
  const [maxAvgLatencyMs, setMaxAvgLatencyMs] = useState(5000);
  const [notifyOnBreach, setNotifyOnBreach] = useState(true);

  const [maxReplayPerRun, setMaxReplayPerRun] = useState(25);
  const [maxReplayAttempts, setMaxReplayAttempts] = useState(3);
  const [replayScheduleMinutes, setReplayScheduleMinutes] = useState(60);
  const [replayAutoEnabled, setReplayAutoEnabled] = useState(false);
  const [replayRouteAlert, setReplayRouteAlert] = useState(true);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const [eventData, healthData] = await Promise.all([
        fetchConnectorEvents({ site_id: selectedSite?.site_id || "", limit: 80 }),
        fetchConnectorHealth(2000),
      ]);
      setEvents(eventData);
      setHealth(healthData);

      if (selectedSite?.tenant_code && canView) {
        const [profile, breaches, replayPolicy, backlog, runs, federation] = await Promise.all([
          fetchConnectorSlaProfile(selectedSite.tenant_code, connectorSource),
          fetchConnectorSlaBreaches({ tenant_code: selectedSite.tenant_code, connector_source: connectorSource, limit: 20 }),
          fetchConnectorReliabilityPolicy({ tenant_code: selectedSite.tenant_code, connector_source: connectorSource }),
          fetchConnectorReliabilityBacklog({ tenant_code: selectedSite.tenant_code, connector_source: connectorSource, limit: 200 }),
          fetchConnectorReliabilityRuns({ tenant_code: selectedSite.tenant_code, limit: 20 }),
          fetchConnectorReliabilityFederation(200),
        ]);

        const p = profile.profile;
        setMinEvents(p.min_events);
        setMinSuccessRate(p.min_success_rate);
        setMaxDeadLetter(p.max_dead_letter_count);
        setMaxAvgLatencyMs(p.max_average_latency_ms);
        setNotifyOnBreach(Boolean(p.notify_on_breach));
        setSlaSummary(
          `${p.connector_source}: min_events=${p.min_events} success>=${p.min_success_rate}% dead_letter<=${p.max_dead_letter_count} latency<=${p.max_average_latency_ms}ms`,
        );
        setBreachSummary(`breaches=${breaches.count}`);

        const rp = replayPolicy.policy;
        setMaxReplayPerRun(rp.max_replay_per_run);
        setMaxReplayAttempts(rp.max_attempts);
        setReplayScheduleMinutes(rp.schedule_interval_minutes);
        setReplayAutoEnabled(Boolean(rp.auto_replay_enabled));
        setReplayRouteAlert(Boolean(rp.route_alert));
        setReplayPolicySummary(
          `${rp.connector_source}: max_replay=${rp.max_replay_per_run} max_attempts=${rp.max_attempts} schedule=${rp.schedule_interval_minutes}m auto=${String(rp.auto_replay_enabled)}`,
        );

        const unresolved = backlog.summary?.unresolved_count ?? 0;
        const replayed = backlog.summary?.replayed_count ?? 0;
        setBacklogSummary(`backlog unresolved=${unresolved} replayed=${replayed} total=${backlog.summary?.dead_letter_count ?? 0}`);

        setReplayRuns(runs);
        const latestRun = runs.rows?.[0];
        if (latestRun) {
          setReplayRunSummary(
            `latest=${latestRun.status} risk=${latestRun.risk_tier} replayed=${latestRun.replayed_count} failed=${latestRun.failed_count}`,
          );
        } else {
          setReplayRunSummary("No replay runs yet");
        }

        const fRow = (federation.rows || []).find((row) => row.tenant_code === selectedSite.tenant_code);
        if (fRow) {
          setFederationSummary(
            `federation tier=${fRow.risk_tier} unresolved=${fRow.unresolved_dead_letter_count} success_rate=${fRow.replay_success_rate}`,
          );
        } else {
          setFederationSummary("federation risk=unknown");
        }
      } else {
        setSlaSummary(canView ? "No tenant selected" : "No permission to view SLA profile");
        setBreachSummary("breaches=0");
        setReplayPolicySummary(canView ? "No tenant selected" : "No permission to view replay policy");
        setBacklogSummary("backlog unresolved=0");
        setFederationSummary("federation risk=unknown");
        setReplayRunSummary("No replay runs yet");
        setReplayRuns(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "connector_load_failed");
    }
  };

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), 15000);
    return () => clearInterval(timer);
  }, [selectedSite?.site_id, selectedSite?.tenant_code, connectorSource, canView]);

  const ingestSampleEvent = async (eventType: "retry" | "dead_letter" | "health") => {
    setBusy(true);
    setError("");
    try {
      await ingestConnectorEvent({
        connector_source: "splunk",
        event_type: eventType,
        status: eventType === "health" ? "degraded" : eventType === "retry" ? "retrying" : "failed",
        tenant_id: selectedSite?.tenant_id || undefined,
        site_id: selectedSite?.site_id || undefined,
        latency_ms: eventType === "health" ? 240 : 480,
        attempt: eventType === "retry" ? 2 : 1,
        payload: { message: `sample_${eventType}_event` },
        error_message: eventType === "dead_letter" ? "destination_api_timeout" : "",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "connector_ingest_failed");
    } finally {
      setBusy(false);
    }
  };

  const saveSlaProfile = async () => {
    if (!selectedSite?.tenant_code) {
      setError("No tenant_code on selected site");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await upsertConnectorSlaProfile({
        tenant_code: selectedSite.tenant_code,
        connector_source: connectorSource,
        min_events: minEvents,
        min_success_rate: minSuccessRate,
        max_dead_letter_count: maxDeadLetter,
        max_average_latency_ms: maxAvgLatencyMs,
        notify_on_breach: notifyOnBreach,
        enabled: true,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "save_sla_profile_failed");
    } finally {
      setBusy(false);
    }
  };

  const runSlaEvaluate = async () => {
    if (!selectedSite?.tenant_code) {
      setError("No tenant_code on selected site");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await evaluateConnectorSla({
        tenant_code: selectedSite.tenant_code,
        connector_source: connectorSource,
        lookback_limit: 1000,
        route_alert: true,
      });
      if (result.breach_detected) {
        setSlaEvalSummary(
          `breach=${result.breach_severity} reasons=${result.breach_reasons.join("|")} route=${result.routing.status}`,
        );
      } else {
        setSlaEvalSummary(`healthy success_rate=${result.metrics.success_rate}% total=${result.metrics.total_events}`);
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "evaluate_sla_failed");
    } finally {
      setBusy(false);
    }
  };

  const saveReplayPolicy = async () => {
    if (!selectedSite?.tenant_code) {
      setError("No tenant_code on selected site");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await upsertConnectorReliabilityPolicy({
        tenant_code: selectedSite.tenant_code,
        connector_source: connectorSource,
        max_replay_per_run: maxReplayPerRun,
        max_attempts: maxReplayAttempts,
        auto_replay_enabled: replayAutoEnabled,
        route_alert: replayRouteAlert,
        schedule_interval_minutes: replayScheduleMinutes,
        enabled: true,
        owner: "security",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "save_replay_policy_failed");
    } finally {
      setBusy(false);
    }
  };

  const runReplay = async (dryRun: boolean) => {
    if (!selectedSite?.tenant_code) {
      setError("No tenant_code on selected site");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await runConnectorReliabilityReplay({
        tenant_code: selectedSite.tenant_code,
        connector_source: connectorSource,
        dry_run: dryRun,
        actor: "dashboard_operator",
      });
      const execution = result.execution;
      if (execution) {
        setReplayRunSummary(
          `${result.status} dry_run=${String(result.dry_run)} selected=${execution.selected_count} replayed=${execution.replayed_count} failed=${execution.failed_count}`,
        );
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "run_replay_failed");
    } finally {
      setBusy(false);
    }
  };

  const runReplaySchedule = async (dryRunOverride: boolean) => {
    setBusy(true);
    setError("");
    try {
      const result = await runConnectorReliabilityScheduler({
        limit: 200,
        dry_run_override: dryRunOverride,
        actor: "connector_replay_scheduler",
      });
      setReplayRunSummary(
        `scheduler executed=${result.executed_count} skipped=${result.skipped_count} policies=${result.scheduled_policy_count}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "run_replay_scheduler_failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Connector Reliability</h2>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={busy || !canApprove}
            onClick={() => void ingestSampleEvent("retry")}
            className="rounded-md border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
          >
            Sample Retry
          </button>
          <button
            type="button"
            disabled={busy || !canApprove}
            onClick={() => void ingestSampleEvent("dead_letter")}
            className="rounded-md border border-danger/60 bg-danger/10 px-2 py-1 text-[11px] text-danger hover:bg-danger/20 disabled:opacity-60"
          >
            Sample DLQ
          </button>
          <button
            type="button"
            disabled={busy || !canApprove}
            onClick={() => void ingestSampleEvent("health")}
            className="rounded-md border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
          >
            Sample Health
          </button>
        </div>
      </div>
      <p className="mt-1 text-xs text-slate-400">Connector health, retries, dead-letter replay orchestration, and federation risk controls.</p>
      <p className="mt-1 text-xs text-slate-500">
        RBAC: viewer={String(canView)} policy_editor={String(canEditPolicy)} approver={String(canApprove)}
      </p>
      {error ? <p className="mt-2 text-sm text-danger">{error}</p> : null}

      {health ? (
        <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2 text-xs">
          <p className="text-slate-200 wrap-anywhere">
            total={health.total_events} success={health.success_count} retry={health.retry_count} dead_letter={health.dead_letter_count}
          </p>
          <p className="mt-1 text-slate-400 wrap-anywhere">
            success_rate={health.success_rate} avg_latency_ms={health.average_latency_ms}
          </p>
        </div>
      ) : null}

      <div className="mt-2 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
        <p className="text-slate-300">Connector SLA</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{slaSummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{breachSummary}</p>
        {slaEvalSummary ? <p className="mt-1 text-slate-300 wrap-anywhere">evaluate={slaEvalSummary}</p> : null}
        <div className="mt-2 grid grid-cols-2 gap-2">
          <label className="text-[11px] text-slate-400">
            Connector Source
            <input
              value={connectorSource}
              onChange={(event) => setConnectorSource(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Min Events
            <input
              type="number"
              value={minEvents}
              onChange={(event) => setMinEvents(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Min Success %
            <input
              type="number"
              value={minSuccessRate}
              onChange={(event) => setMinSuccessRate(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Max DLQ
            <input
              type="number"
              value={maxDeadLetter}
              onChange={(event) => setMaxDeadLetter(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400 col-span-2">
            Max Avg Latency (ms)
            <input
              type="number"
              value={maxAvgLatencyMs}
              onChange={(event) => setMaxAvgLatencyMs(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
        </div>
        <label className="mt-2 flex items-center gap-1 text-[11px] text-slate-300">
          <input type="checkbox" checked={notifyOnBreach} onChange={(event) => setNotifyOnBreach(event.target.checked)} />
          route alert on breach
        </label>
        <div className="mt-2 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!selectedSite || busy || !canEditPolicy}
            onClick={() => void saveSlaProfile()}
            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
          >
            Save SLA Profile
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy || !canApprove}
            onClick={() => void runSlaEvaluate()}
            className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
          >
            Evaluate SLA
          </button>
        </div>
      </div>

      <div className="mt-2 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
        <p className="text-slate-300">Dead-Letter Replay Policy</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{replayPolicySummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{backlogSummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{federationSummary}</p>
        {replayRunSummary ? <p className="mt-1 text-slate-300 wrap-anywhere">run={replayRunSummary}</p> : null}
        <div className="mt-2 grid grid-cols-2 gap-2">
          <label className="text-[11px] text-slate-400">
            Max Replay / Run
            <input
              type="number"
              value={maxReplayPerRun}
              onChange={(event) => setMaxReplayPerRun(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Max Attempts
            <input
              type="number"
              value={maxReplayAttempts}
              onChange={(event) => setMaxReplayAttempts(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400 col-span-2">
            Schedule Interval (minutes)
            <input
              type="number"
              value={replayScheduleMinutes}
              onChange={(event) => setReplayScheduleMinutes(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
        </div>
        <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-300">
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={replayAutoEnabled} onChange={(event) => setReplayAutoEnabled(event.target.checked)} />
            auto replay enabled
          </label>
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={replayRouteAlert} onChange={(event) => setReplayRouteAlert(event.target.checked)} />
            route alert
          </label>
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!selectedSite || busy || !canEditPolicy}
            onClick={() => void saveReplayPolicy()}
            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
          >
            Save Replay Policy
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy || !canApprove}
            onClick={() => void runReplay(true)}
            className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
          >
            Replay Dry Run
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy || !canApprove}
            onClick={() => void runReplay(false)}
            className="rounded border border-danger/60 bg-danger/10 px-2 py-1 text-[11px] text-danger hover:bg-danger/20 disabled:opacity-60"
          >
            Replay Apply
          </button>
          <button
            type="button"
            disabled={busy || !canApprove}
            onClick={() => void runReplaySchedule(true)}
            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
          >
            Run Scheduler
          </button>
        </div>
      </div>

      <div className="mt-3 max-h-36 overflow-auto rounded border border-slate-800 p-2 text-xs">
        <p className="mb-2 text-slate-400">Recent Replay Runs</p>
        {(replayRuns?.rows || []).length === 0 ? <p className="text-slate-500">No replay runs yet.</p> : null}
        {(replayRuns?.rows || []).slice(0, 6).map((row) => (
          <div key={row.run_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">
              [{row.connector_source}] {row.status} risk={row.risk_tier} replayed={row.replayed_count} failed={row.failed_count}
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              backlog={row.backlog_count} selected={row.selected_count} dry_run={String(row.dry_run)}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-3 max-h-44 overflow-auto rounded border border-slate-800 p-2 text-xs">
        <p className="mb-2 text-slate-400">Recent Connector Events</p>
        {(events?.rows || []).length === 0 ? <p className="text-slate-500">No connector events yet.</p> : null}
        {(events?.rows || []).map((row) => (
          <div key={row.event_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">
              [{row.connector_source}] {row.event_type} status={row.status} attempt={row.attempt}
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              latency={row.latency_ms}ms error={row.error_message || "-"}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
