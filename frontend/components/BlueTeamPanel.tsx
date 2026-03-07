import { useEffect, useState } from "react";

import { applySiteBlueRecommendation, fetchSiteBlueEvents, ingestSiteBlueEvent } from "@/lib/api";
import type { SiteRow, SiteBlueEventHistoryResponse } from "@/lib/types";

type Props = {
  selectedSite: SiteRow | null;
};

type ActionType = "block_ip" | "notify_team" | "limit_user" | "ignore";

export function BlueTeamPanel({ selectedSite }: Props) {
  const [history, setHistory] = useState<SiteBlueEventHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    if (!selectedSite) return;
    setLoading(true);
    setError("");
    try {
      setHistory(await fetchSiteBlueEvents(selectedSite.site_id, 100));
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
  }, [selectedSite?.site_id]);

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

      <div className="mt-3">
        <button
          type="button"
          disabled={!selectedSite || busy}
          onClick={() => void ingestSampleLog()}
          className="rounded-md border border-accent/60 bg-accent/15 px-3 py-1.5 text-xs text-accent hover:bg-accent/25 disabled:opacity-60"
        >
          Ingest Sample Event Log
        </button>
      </div>

      {loading ? <p className="mt-3 text-sm text-slate-400">Monitoring logs...</p> : null}
      {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}

      <div className="mt-3 max-h-80 overflow-auto rounded-md border border-slate-800">
        <table className="w-full text-left text-xs">
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
                <td className="px-2 py-2 text-slate-400">{event.created_at}</td>
                <td className="px-2 py-2 text-slate-200">{event.event_type}</td>
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
                <td className="px-2 py-2 text-slate-300">{event.ai_recommendation}</td>
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
    </section>
  );
}

