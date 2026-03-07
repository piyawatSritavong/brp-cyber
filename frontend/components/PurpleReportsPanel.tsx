import { useEffect, useState } from "react";

import { fetchSitePurpleIsoGapTemplate, fetchSitePurpleReports, generateSitePurpleAnalysis } from "@/lib/api";
import type { SitePurpleIsoGapTemplateResponse, SitePurpleReportHistoryResponse, SiteRow } from "@/lib/types";

type Props = {
  selectedSite: SiteRow | null;
};

export function PurpleReportsPanel({ selectedSite }: Props) {
  const [reports, setReports] = useState<SitePurpleReportHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [isoTemplate, setIsoTemplate] = useState<SitePurpleIsoGapTemplateResponse | null>(null);

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

  const latest = reports?.rows?.[0];

  return (
    <section className="card p-4">
      <div className="flex items-center justify-between gap-3">
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
      </div>
      <p className="mt-1 text-xs text-slate-400">AI correlates Red + Blue operations and generates strategic feedback.</p>

      {loading ? <p className="mt-3 text-sm text-slate-400">Analyzing...</p> : null}
      {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}

      {latest ? (
        <div className="mt-3 space-y-2 rounded-md border border-slate-800 bg-panelAlt/30 p-3 text-xs">
          <p className="text-slate-100">{latest.summary}</p>
          <p className="text-slate-300">Metrics: {JSON.stringify(latest.metrics)}</p>
          <p className="text-slate-300">AI: {JSON.stringify(latest.ai_analysis)}</p>
        </div>
      ) : (
        <p className="mt-3 text-xs text-slate-500">No purple report yet.</p>
      )}

      <div className="mt-3 max-h-44 overflow-auto rounded border border-slate-800 p-2">
        {(reports?.rows || []).map((row) => (
          <div key={row.report_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2 text-xs">
            <p className="text-slate-400">{row.created_at}</p>
            <p className="mt-1 text-slate-200">{row.summary}</p>
          </div>
        ))}
      </div>

      {isoTemplate ? (
        <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
          <p className="text-slate-200">
            {isoTemplate.framework} | controls: {isoTemplate.controls.length} | generated: {isoTemplate.summary.generated_at}
          </p>
          <div className="mt-2 space-y-1">
            {isoTemplate.controls.slice(0, 4).map((control) => (
              <p key={control.control_id} className="text-slate-300">
                {control.control_id} [{control.status}] {control.control_name}
              </p>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
