import { useEffect, useState } from "react";

import {
  dispatchActionCenterAlert,
  fetchActionCenterEvents,
  fetchActionCenterPolicy,
  upsertActionCenterPolicy,
} from "@/lib/api";
import type { ActionCenterEventListResponse, ActionCenterPolicyResponse, SiteRow } from "@/lib/types";

type Props = {
  selectedSite: SiteRow | null;
  canView: boolean;
  canEditPolicy: boolean;
  canApprove: boolean;
};

export function ActionCenterPanel({ selectedSite, canView, canEditPolicy, canApprove }: Props) {
  const [policy, setPolicy] = useState<ActionCenterPolicyResponse | null>(null);
  const [events, setEvents] = useState<ActionCenterEventListResponse | null>(null);
  const [minSeverity, setMinSeverity] = useState<"low" | "medium" | "high" | "critical">("high");
  const [telegramEnabled, setTelegramEnabled] = useState(true);
  const [lineEnabled, setLineEnabled] = useState(false);
  const [routingTags, setRoutingTags] = useState("soc,phase66");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    setError("");
    if (!canView || !selectedSite?.tenant_code) {
      setPolicy(null);
      setEvents({ count: 0, rows: [] });
      if (!canView) {
        setError("Viewer permission required");
      }
      return;
    }
    try {
      const [policyData, eventData] = await Promise.all([
        fetchActionCenterPolicy(selectedSite.tenant_code),
        fetchActionCenterEvents({ tenant_code: selectedSite.tenant_code, limit: 40 }),
      ]);
      setPolicy(policyData);
      setEvents(eventData);
      setMinSeverity(policyData.policy.min_severity);
      setTelegramEnabled(Boolean(policyData.policy.telegram_enabled));
      setLineEnabled(Boolean(policyData.policy.line_enabled));
      setRoutingTags((policyData.policy.routing_tags || []).join(","));
    } catch (err) {
      setError(err instanceof Error ? err.message : "action_center_load_failed");
    }
  };

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), 15000);
    return () => clearInterval(timer);
  }, [selectedSite?.tenant_code, canView]);

  const savePolicy = async () => {
    if (!selectedSite?.tenant_code) {
      setError("No tenant_code on selected site");
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await upsertActionCenterPolicy({
        tenant_code: selectedSite.tenant_code,
        policy_version: "1.1",
        owner: "phase66",
        telegram_enabled: telegramEnabled,
        line_enabled: lineEnabled,
        min_severity: minSeverity,
        routing_tags: routingTags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
      });
      setMessage("Action center policy saved");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "save_action_center_policy_failed");
    } finally {
      setBusy(false);
    }
  };

  const sendTestAlert = async () => {
    if (!selectedSite?.tenant_code) {
      setError("No tenant_code on selected site");
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await dispatchActionCenterAlert({
        tenant_code: selectedSite.tenant_code,
        site_code: selectedSite.site_code,
        source: "manual_console",
        severity: "high",
        title: `Manual test alert: ${selectedSite.display_name}`,
        message: "Operator validation for connector SLA breach routing",
        payload: { panel: "action_center", site_id: selectedSite.site_id },
      });
      setMessage(
        `dispatch=${response.routing.status} telegram=${response.routing.telegram_status} line=${response.routing.line_status}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "dispatch_action_center_failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Action Center</h2>
        <button
          type="button"
          disabled={!selectedSite || busy || !canApprove}
          onClick={() => void sendTestAlert()}
          className="rounded-md border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
        >
          Send Test Alert
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-400">Telegram/LINE routing control and dispatch history for autonomous governance events.</p>
      <p className="mt-1 text-xs text-slate-500">
        RBAC: viewer={String(canView)} policy_editor={String(canEditPolicy)} approver={String(canApprove)}
      </p>
      {error ? <p className="mt-2 text-sm text-danger">{error}</p> : null}
      {message ? <p className="mt-2 text-xs text-accent wrap-anywhere">{message}</p> : null}

      <div className="mt-2 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
        <p className="text-slate-300">
          policy={policy?.policy.policy_version || "default"} owner={policy?.policy.owner || "system"}
        </p>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <label className="text-[11px] text-slate-400">
            Min Severity
            <select
              value={minSeverity}
              onChange={(event) => setMinSeverity(event.target.value as "low" | "medium" | "high" | "critical")}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
              <option value="critical">critical</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400">
            Routing Tags
            <input
              value={routingTags}
              onChange={(event) => setRoutingTags(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-slate-300">
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={telegramEnabled} onChange={(event) => setTelegramEnabled(event.target.checked)} />
            telegram
          </label>
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={lineEnabled} onChange={(event) => setLineEnabled(event.target.checked)} />
            line
          </label>
          <button
            type="button"
            disabled={!selectedSite || busy || !canEditPolicy}
            onClick={() => void savePolicy()}
            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
          >
            Save Routing Policy
          </button>
        </div>
      </div>

      <div className="mt-3 max-h-44 overflow-auto rounded border border-slate-800 p-2 text-xs">
        <p className="mb-2 text-slate-400">Recent Dispatch Events</p>
        {(events?.rows || []).length === 0 ? <p className="text-slate-500">No action center events yet.</p> : null}
        {(events?.rows || []).map((row) => (
          <div key={row.event_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">
              [{row.severity}] {row.title}
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              tg={row.telegram_status} line={row.line_status} source={row.source}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
