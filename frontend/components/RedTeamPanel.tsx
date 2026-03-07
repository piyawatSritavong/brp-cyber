import { useMemo, useState } from "react";

import { fetchSiteRedScans, runSiteRedScan } from "@/lib/api";
import type { SiteRow, SiteRedScanHistoryResponse } from "@/lib/types";

type Props = {
  sites: SiteRow[];
  selectedSiteId: string;
  onSelectSite: (siteId: string) => void;
};

const SCAN_CASES = [
  { key: "baseline_scan", label: "Baseline Web Scan" },
  { key: "vuln_scan", label: "Vulnerability Sweep" },
  { key: "pentest_sim", label: "Pentest Simulation" },
];

export function RedTeamPanel({ sites, selectedSiteId, onSelectSite }: Props) {
  const [busyKey, setBusyKey] = useState("");
  const [error, setError] = useState("");
  const [historyBySite, setHistoryBySite] = useState<Record<string, SiteRedScanHistoryResponse>>({});

  const selectedSite = useMemo(() => sites.find((site) => site.site_id === selectedSiteId) || null, [sites, selectedSiteId]);

  const loadHistory = async (siteId: string) => {
    try {
      const history = await fetchSiteRedScans(siteId, 10);
      setHistoryBySite((prev) => ({ ...prev, [siteId]: history }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_history_load_failed");
    }
  };

  const runCase = async (siteId: string, scanType: string) => {
    setError("");
    setBusyKey(`${siteId}:${scanType}`);
    try {
      await runSiteRedScan(siteId, { scan_type: scanType });
      await loadHistory(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_scan_failed");
    } finally {
      setBusyKey("");
    }
  };

  return (
    <section className="card p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Red Team Service</h2>
      <p className="mt-1 text-xs text-slate-400">AI-driven authorized simulation scans by site.</p>

      {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}

      <div className="mt-3 space-y-2">
        {sites.length === 0 ? <p className="text-xs text-slate-500">No site found. Add site in Configuration menu.</p> : null}
        {sites.map((site) => {
          const expanded = selectedSiteId === site.site_id;
          const history = historyBySite[site.site_id];
          return (
            <div key={site.site_id} className="rounded-md border border-slate-800 bg-panelAlt/30 p-3">
              <button
                type="button"
                onClick={() => {
                  onSelectSite(site.site_id);
                  void loadHistory(site.site_id);
                }}
                className="w-full text-left"
              >
                <p className="text-xs font-semibold text-slate-100">{site.display_name}</p>
                <p className="mt-1 font-mono text-[11px] text-slate-400">{site.base_url}</p>
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

                  <div className="max-h-52 overflow-auto rounded border border-slate-800 p-2 text-xs">
                    <p className="mb-2 text-slate-400">Scan Results</p>
                    {history?.rows?.length ? null : <p className="text-slate-500">No scans yet.</p>}
                    {(history?.rows || []).map((row) => (
                      <div key={row.scan_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/40 p-2">
                        <p className="text-slate-200">{row.scan_type}</p>
                        <p className="mt-1 text-slate-400">{row.ai_summary}</p>
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

