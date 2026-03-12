import { useEffect, useState } from "react";

import {
  applySiteBlueRecommendation,
  applySiteDetectionRule,
  fetchSiteBlueEvents,
  fetchSiteDetectionAutotunePolicy,
  fetchSiteDetectionAutotuneRuns,
  fetchSiteDetectionRules,
  ingestSiteBlueEvent,
  runDetectionAutotuneScheduler,
  runSiteDetectionAutotune,
  runSiteDetectionCopilotTune,
  upsertSiteDetectionAutotunePolicy,
} from "@/lib/api";
import type {
  SiteBlueEventHistoryResponse,
  SiteDetectionAutotuneRunListResponse,
  SiteDetectionCopilotTuneResponse,
  SiteDetectionRulesResponse,
  SiteRow,
} from "@/lib/types";

type Props = {
  selectedSite: SiteRow | null;
  canView: boolean;
  canEditPolicy: boolean;
  canApprove: boolean;
};

type ActionType = "block_ip" | "notify_team" | "limit_user" | "ignore";

type RiskTier = "low" | "medium" | "high" | "critical";

export function BlueTeamPanel({ selectedSite, canView, canEditPolicy, canApprove }: Props) {
  const [history, setHistory] = useState<SiteBlueEventHistoryResponse | null>(null);
  const [detectionRules, setDetectionRules] = useState<SiteDetectionRulesResponse | null>(null);
  const [autotuneRuns, setAutotuneRuns] = useState<SiteDetectionAutotuneRunListResponse | null>(null);
  const [lastTune, setLastTune] = useState<SiteDetectionCopilotTuneResponse | null>(null);

  const [autotunePolicySummary, setAutotunePolicySummary] = useState("No autotune policy loaded");
  const [autotuneRunSummary, setAutotuneRunSummary] = useState("No autotune run yet");

  const [minRiskScore, setMinRiskScore] = useState(60);
  const [minRiskTier, setMinRiskTier] = useState<RiskTier>("high");
  const [targetCoveragePct, setTargetCoveragePct] = useState(90);
  const [maxRulesPerRun, setMaxRulesPerRun] = useState(3);
  const [autoApplyAutotune, setAutoApplyAutotune] = useState(false);
  const [autotuneRouteAlert, setAutotuneRouteAlert] = useState(true);
  const [autotuneScheduleMinutes, setAutotuneScheduleMinutes] = useState(60);

  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    if (!selectedSite) return;
    setLoading(true);
    setError("");
    try {
      const [events, rules] = await Promise.all([
        fetchSiteBlueEvents(selectedSite.site_id, 100),
        fetchSiteDetectionRules(selectedSite.site_id, 30),
      ]);
      setHistory(events);
      setDetectionRules(rules);

      if (canView) {
        const [policy, runs] = await Promise.all([
          fetchSiteDetectionAutotunePolicy(selectedSite.site_id),
          fetchSiteDetectionAutotuneRuns(selectedSite.site_id, 20),
        ]);
        setAutotuneRuns(runs);
        const p = policy.policy;
        setMinRiskScore(p.min_risk_score);
        setMinRiskTier(p.min_risk_tier);
        setTargetCoveragePct(p.target_detection_coverage_pct);
        setMaxRulesPerRun(p.max_rules_per_run);
        setAutoApplyAutotune(Boolean(p.auto_apply));
        setAutotuneRouteAlert(Boolean(p.route_alert));
        setAutotuneScheduleMinutes(p.schedule_interval_minutes);
        setAutotunePolicySummary(
          `risk>=${p.min_risk_score}/${p.min_risk_tier} target_coverage>=${p.target_detection_coverage_pct}% max_rules=${p.max_rules_per_run} auto_apply=${String(p.auto_apply)}`,
        );
        const latestRun = runs.rows?.[0];
        if (latestRun) {
          setAutotuneRunSummary(
            `${latestRun.status} risk=${latestRun.risk_tier}/${latestRun.risk_score} coverage=${latestRun.coverage_before_pct}%->${latestRun.coverage_after_pct}% recs=${latestRun.recommendation_count}`,
          );
        } else {
          setAutotuneRunSummary("No autotune run yet");
        }
      } else {
        setAutotunePolicySummary("No permission to view autotune policy");
        setAutotuneRunSummary("No permission to view autotune runs");
        setAutotuneRuns(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "blue_events_load_failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    if (!selectedSite) return;
    const timer = setInterval(() => void load(), 10000);
    return () => clearInterval(timer);
  }, [selectedSite?.site_id, canView]);

  const ingestSampleLog = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await ingestSiteBlueEvent(selectedSite.site_id, {
        event_type: "waf_http",
        source_ip: "203.0.113.20",
        path: "/admin/login",
        method: "POST",
        status_code: 401,
        message: "possible brute force attempt",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "blue_ingest_failed");
    } finally {
      setBusy(false);
    }
  };

  const applyAction = async (eventId: string, action: ActionType) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await applySiteBlueRecommendation(selectedSite.site_id, eventId, action);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "blue_apply_failed");
    } finally {
      setBusy(false);
    }
  };

  const runDetectionCopilot = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const tune = await runSiteDetectionCopilotTune(selectedSite.site_id, {
        rule_count: 3,
        auto_apply: false,
        dry_run: true,
      });
      setLastTune(tune);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "detection_copilot_failed");
    } finally {
      setBusy(false);
    }
  };

  const saveAutotunePolicy = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await upsertSiteDetectionAutotunePolicy(selectedSite.site_id, {
        min_risk_score: minRiskScore,
        min_risk_tier: minRiskTier,
        target_detection_coverage_pct: targetCoveragePct,
        max_rules_per_run: maxRulesPerRun,
        auto_apply: autoApplyAutotune,
        route_alert: autotuneRouteAlert,
        schedule_interval_minutes: autotuneScheduleMinutes,
        enabled: true,
        owner: "security",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "autotune_policy_save_failed");
    } finally {
      setBusy(false);
    }
  };

  const runAutotune = async (dryRun: boolean, force: boolean) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const result = await runSiteDetectionAutotune(selectedSite.site_id, {
        dry_run: dryRun,
        force,
        actor: "dashboard_operator",
      });
      setAutotuneRunSummary(
        `${result.status} risk=${result.risk.risk_tier}/${result.risk.risk_score} should_tune=${String(result.execution.should_tune)} recs=${result.execution.recommendation_count} applied=${result.execution.applied_count}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "autotune_run_failed");
    } finally {
      setBusy(false);
    }
  };

  const runAutotuneScheduler = async () => {
    setBusy(true);
    setError("");
    try {
      const result = await runDetectionAutotuneScheduler({
        limit: 200,
        dry_run_override: true,
        actor: "dashboard_scheduler",
      });
      setAutotuneRunSummary(
        `scheduler policies=${result.scheduled_policy_count} executed=${result.executed_count} skipped=${result.skipped_count}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "autotune_scheduler_failed");
    } finally {
      setBusy(false);
    }
  };

  const applyRule = async (ruleId: string) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await applySiteDetectionRule(selectedSite.site_id, ruleId, true);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "detection_rule_apply_failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Blue Team Service</h2>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-400"
        >
          Refresh
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-400">AI rates severity and suggests response actions per event log.</p>
      <p className="mt-1 text-xs text-slate-500">
        RBAC: viewer={String(canView)} policy_editor={String(canEditPolicy)} approver={String(canApprove)}
      </p>

      <div className="mt-3">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={!selectedSite || busy}
            onClick={() => void ingestSampleLog()}
            className="rounded-md border border-accent/60 bg-accent/15 px-3 py-1.5 text-xs text-accent hover:bg-accent/25 disabled:opacity-60"
          >
            Ingest Sample Event Log
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy}
            onClick={() => void runDetectionCopilot()}
            className="rounded-md border border-warning/60 bg-warning/10 px-3 py-1.5 text-xs text-warning hover:bg-warning/20 disabled:opacity-60"
          >
            Run Detection Copilot
          </button>
        </div>
      </div>

      {loading ? <p className="mt-3 text-sm text-slate-400">Monitoring logs...</p> : null}
      {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}

      <div className="mt-3 max-h-80 overflow-auto rounded-md border border-slate-800">
        <table className="w-full table-fixed text-left text-xs">
          <thead className="bg-panelAlt/50 text-slate-300">
            <tr>
              <th className="px-2 py-2">Time</th>
              <th className="px-2 py-2">Event</th>
              <th className="px-2 py-2">Severity</th>
              <th className="px-2 py-2">AI Recommendation</th>
              <th className="px-2 py-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {(history?.rows || []).map((event) => (
              <tr key={event.event_id} className="border-t border-slate-800/80">
                <td className="px-2 py-2 text-slate-400 wrap-anywhere">{event.created_at}</td>
                <td className="px-2 py-2 text-slate-200 wrap-anywhere">{event.event_type}</td>
                <td
                  className={
                    "px-2 py-2 " +
                    (event.ai_severity === "high"
                      ? "text-danger"
                      : event.ai_severity === "medium"
                        ? "text-warning"
                        : "text-accent")
                  }
                >
                  {event.ai_severity}
                </td>
                <td className="px-2 py-2 text-slate-300 wrap-anywhere">{event.ai_recommendation}</td>
                <td className="px-2 py-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void applyAction(event.event_id, (event.ai_recommendation as ActionType) || "notify_team")}
                    className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                  >
                    Apply
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(history?.rows?.length || 0) === 0 ? <p className="p-3 text-xs text-slate-500">No blue events yet.</p> : null}
      </div>

      {lastTune ? (
        <div className="mt-3 rounded border border-slate-800 bg-panelAlt/30 p-2 text-xs">
          <p className="text-slate-200 wrap-anywhere">Detection coverage delta: {lastTune.expected_detection_coverage_delta}</p>
          <p className="mt-1 text-slate-400 wrap-anywhere">before: {JSON.stringify(lastTune.before_metrics)}</p>
          <p className="mt-1 text-slate-400 wrap-anywhere">after: {JSON.stringify(lastTune.after_metrics)}</p>
        </div>
      ) : null}

      <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
        <p className="text-slate-300">Detection Autotune Policy</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{autotunePolicySummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{autotuneRunSummary}</p>

        <div className="mt-2 grid grid-cols-2 gap-2">
          <label className="text-[11px] text-slate-400">
            Min Risk Score
            <input
              type="number"
              value={minRiskScore}
              onChange={(event) => setMinRiskScore(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Min Risk Tier
            <select
              value={minRiskTier}
              onChange={(event) => setMinRiskTier(event.target.value as RiskTier)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
              <option value="critical">critical</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400">
            Target Coverage %
            <input
              type="number"
              value={targetCoveragePct}
              onChange={(event) => setTargetCoveragePct(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Max Rules / Run
            <input
              type="number"
              value={maxRulesPerRun}
              onChange={(event) => setMaxRulesPerRun(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400 col-span-2">
            Schedule Interval (minutes)
            <input
              type="number"
              value={autotuneScheduleMinutes}
              onChange={(event) => setAutotuneScheduleMinutes(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
        </div>

        <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-300">
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={autoApplyAutotune} onChange={(event) => setAutoApplyAutotune(event.target.checked)} />
            auto apply rules
          </label>
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={autotuneRouteAlert} onChange={(event) => setAutotuneRouteAlert(event.target.checked)} />
            route alert
          </label>
        </div>

        <div className="mt-2 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!selectedSite || busy || !canEditPolicy}
            onClick={() => void saveAutotunePolicy()}
            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
          >
            Save Autotune Policy
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy || !canApprove}
            onClick={() => void runAutotune(true, false)}
            className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
          >
            Run Autotune Dry Run
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy || !canApprove}
            onClick={() => void runAutotune(false, true)}
            className="rounded border border-danger/60 bg-danger/10 px-2 py-1 text-[11px] text-danger hover:bg-danger/20 disabled:opacity-60"
          >
            Run Autotune Apply
          </button>
          <button
            type="button"
            disabled={busy || !canApprove}
            onClick={() => void runAutotuneScheduler()}
            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
          >
            Run Autotune Scheduler
          </button>
        </div>
      </div>

      <div className="mt-3 max-h-36 overflow-auto rounded border border-slate-800 p-2 text-xs">
        <p className="mb-2 text-slate-400">Detection Autotune Runs</p>
        {(autotuneRuns?.rows || []).length === 0 ? <p className="text-slate-500">No autotune runs yet.</p> : null}
        {(autotuneRuns?.rows || []).slice(0, 6).map((run) => (
          <div key={run.run_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">
              {run.status} risk={run.risk_tier}/{run.risk_score} coverage={run.coverage_before_pct}%{"->"}
              {run.coverage_after_pct}%
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              recommendations={run.recommendation_count} applied={run.applied_count} dry_run={String(run.dry_run)}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-3 max-h-44 overflow-auto rounded border border-slate-800 p-2 text-xs">
        <p className="mb-2 text-slate-400">Detection Copilot Rules</p>
        {(detectionRules?.rows || []).length === 0 ? <p className="text-slate-500">No copilot rules yet.</p> : null}
        {(detectionRules?.rows || []).map((rule) => (
          <div key={rule.rule_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">{rule.rule_name}</p>
            <p className="mt-1 text-slate-400">status={rule.status}</p>
            <button
              type="button"
              disabled={busy || rule.status === "applied"}
              onClick={() => void applyRule(rule.rule_id)}
              className="mt-2 rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
            >
              Apply Rule
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
