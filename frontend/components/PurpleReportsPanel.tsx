import { useEffect, useState } from "react";

import {
  fetchSiteCaseGraph,
  fetchSitePurpleExecutiveFederation,
  fetchSitePurpleExecutiveScorecard,
  fetchSitePurpleIsoGapTemplate,
  fetchSitePurpleReports,
  generateSitePurpleAnalysis,
} from "@/lib/api";
import type {
  SiteCaseGraphResponse,
  SitePurpleExecutiveFederationResponse,
  SitePurpleExecutiveScorecardResponse,
  SitePurpleIsoGapTemplateResponse,
  SitePurpleReportHistoryResponse,
  SiteRow,
} from "@/lib/types";

type Props = {
  selectedSite: SiteRow | null;
};

export function PurpleReportsPanel({ selectedSite }: Props) {
  const [reports, setReports] = useState<SitePurpleReportHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [isoTemplate, setIsoTemplate] = useState<SitePurpleIsoGapTemplateResponse | null>(null);
  const [caseGraph, setCaseGraph] = useState<SiteCaseGraphResponse | null>(null);
  const [executive, setExecutive] = useState<SitePurpleExecutiveScorecardResponse | null>(null);
  const [federation, setFederation] = useState<SitePurpleExecutiveFederationResponse | null>(null);

  const load = async () => {
    if (!selectedSite) return;
    setLoading(true);
    setError("");
    try {
      setReports(await fetchSitePurpleReports(selectedSite.site_id, 20));
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_reports_load_failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    if (!selectedSite) return;
    const timer = setInterval(() => void load(), 15000);
    return () => clearInterval(timer);
  }, [selectedSite?.site_id]);

  const generate = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await generateSitePurpleAnalysis(selectedSite.site_id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_generate_failed");
    } finally {
      setBusy(false);
    }
  };

  const generateIsoTemplate = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      setIsoTemplate(await fetchSitePurpleIsoGapTemplate(selectedSite.site_id, 200));
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_iso_template_failed");
    } finally {
      setBusy(false);
    }
  };

  const loadCaseGraph = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      setCaseGraph(await fetchSiteCaseGraph(selectedSite.site_id, 50));
    } catch (err) {
      setError(err instanceof Error ? err.message : "case_graph_failed");
    } finally {
      setBusy(false);
    }
  };

  const loadExecutive = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const [siteExecutive, federationExecutive] = await Promise.all([
        fetchSitePurpleExecutiveScorecard(selectedSite.site_id, {
          lookback_runs: 30,
          lookback_events: 500,
          sla_target_seconds: 120,
        }),
        fetchSitePurpleExecutiveFederation({
          limit: 200,
          lookback_runs: 30,
          lookback_events: 500,
          sla_target_seconds: 120,
        }),
      ]);
      setExecutive(siteExecutive);
      setFederation(federationExecutive);
    } catch (err) {
      setError(err instanceof Error ? err.message : "executive_scorecard_failed");
    } finally {
      setBusy(false);
    }
  };

  const latest = reports?.rows?.[0];

  return (
    <section className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Purple Team Service</h2>
        <button
          type="button"
          disabled={!selectedSite || busy}
          onClick={() => void generate()}
          className="rounded-md border border-accent/70 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/25 disabled:opacity-60"
        >
          Run AI Correlation
        </button>
        <button
          type="button"
          disabled={!selectedSite || busy}
          onClick={() => void generateIsoTemplate()}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-400 disabled:opacity-60"
        >
          ISO 27001 Gap
        </button>
        <button
          type="button"
          disabled={!selectedSite || busy}
          onClick={() => void loadCaseGraph()}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-400 disabled:opacity-60"
        >
          Unified Case Graph
        </button>
        <button
          type="button"
          disabled={!selectedSite || busy}
          onClick={() => void loadExecutive()}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-400 disabled:opacity-60"
        >
          Executive Scorecard
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-400">AI correlates Red + Blue operations and generates strategic feedback.</p>

      {loading ? <p className="mt-3 text-sm text-slate-400">Analyzing...</p> : null}
      {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}

      {latest ? (
        <div className="mt-3 space-y-2 rounded-md border border-slate-800 bg-panelAlt/30 p-3 text-xs">
          <p className="text-slate-100 wrap-anywhere">{latest.summary}</p>
          <p className="text-slate-300 wrap-anywhere">Metrics: {JSON.stringify(latest.metrics)}</p>
          <p className="text-slate-300 wrap-anywhere">AI: {JSON.stringify(latest.ai_analysis)}</p>
        </div>
      ) : (
        <p className="mt-3 text-xs text-slate-500">No purple report yet.</p>
      )}

      <div className="mt-3 max-h-44 overflow-auto rounded border border-slate-800 p-2">
        {(reports?.rows || []).map((row) => (
          <div key={row.report_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2 text-xs">
            <p className="text-slate-400 wrap-anywhere">{row.created_at}</p>
            <p className="mt-1 text-slate-200 wrap-anywhere">{row.summary}</p>
          </div>
        ))}
      </div>

      {isoTemplate ? (
        <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
          <p className="text-slate-200 wrap-anywhere">
            {isoTemplate.framework} | controls: {isoTemplate.controls.length} | generated: {isoTemplate.summary.generated_at}
          </p>
          <div className="mt-2 space-y-1">
            {isoTemplate.controls.slice(0, 4).map((control) => (
              <p key={control.control_id} className="text-slate-300 wrap-anywhere">
                {control.control_id} [{control.status}] {control.control_name}
              </p>
            ))}
          </div>
        </div>
      ) : null}

      {caseGraph ? (
        <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
          <p className="text-slate-200 wrap-anywhere">
            Case Graph: nodes={caseGraph.summary.node_count} edges={caseGraph.summary.edge_count} exploit_paths=
            {caseGraph.summary.exploit_paths} blue_events={caseGraph.summary.blue_events} rules={caseGraph.summary.detection_rules}
            soar={caseGraph.summary.soar_executions ?? 0} connector={caseGraph.summary.connector_events ?? 0} replay_runs=
            {caseGraph.summary.connector_replay_runs ?? 0} risk={caseGraph.summary.risk_tier ?? "unknown"}(
            {caseGraph.summary.risk_score ?? 0})
          </p>
          {caseGraph.risk ? (
            <p className="mt-1 text-slate-300 wrap-anywhere">
              Risk details: max_exploit={caseGraph.risk.max_exploit_risk} high_blue={caseGraph.risk.high_blue_events} pending_soar=
              {caseGraph.risk.pending_soar_executions} unresolved_dlq={caseGraph.risk.unresolved_connector_dlq} recommendation=
              {caseGraph.risk.recommendation}
            </p>
          ) : null}
          <div className="mt-2 max-h-28 overflow-auto rounded border border-slate-800 p-2">
            {(caseGraph.timeline || []).length === 0 ? <p className="text-slate-500">No case timeline yet.</p> : null}
            {(caseGraph.timeline || []).slice(0, 6).map((row, index) => (
              <p key={`${row.node_id}-${index}`} className="text-slate-300 wrap-anywhere">
                {row.timestamp} [{row.source}] {row.summary}
              </p>
            ))}
          </div>
        </div>
      ) : null}

      {executive ? (
        <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
          <p className="text-slate-200 wrap-anywhere">
            MITRE coverage={executive.summary.heatmap_coverage} attacked={executive.summary.attacked_techniques} covered=
            {executive.summary.covered_techniques} partial={executive.summary.partial_techniques}
          </p>
          <p className="mt-1 text-slate-300 wrap-anywhere">
            Remediation SLA: status={executive.remediation_sla.sla_status} mttr={executive.remediation_sla.estimated_mttr_seconds}s
            / target={executive.remediation_sla.target_mttr_seconds}s apply_rate={executive.remediation_sla.apply_rate}
          </p>
          <div className="mt-2 max-h-36 overflow-auto rounded border border-slate-800 p-2">
            {executive.heatmap.length === 0 ? <p className="text-slate-500">No MITRE technique evidence yet.</p> : null}
            {executive.heatmap.slice(0, 8).map((row) => (
              <p key={row.technique_id} className="text-slate-300 wrap-anywhere">
                {row.technique_id} [{row.detection_status}] mitigation={row.mitigation_time_seconds ?? "-"}s
              </p>
            ))}
          </div>
        </div>
      ) : null}

      {federation ? (
        <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
          <p className="text-slate-200 wrap-anywhere">
            Federation: sites={federation.count} pass={federation.passing_sites} at_risk={federation.at_risk_sites}
          </p>
          <div className="mt-2 max-h-36 overflow-auto rounded border border-slate-800 p-2">
            {federation.rows.slice(0, 8).map((row) => (
              <p key={row.site_id} className="text-slate-300 wrap-anywhere">
                {row.tenant_code}/{row.site_code} coverage={row.heatmap_coverage} sla={row.sla_status} mttr=
                {row.estimated_mttr_seconds}s
              </p>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
