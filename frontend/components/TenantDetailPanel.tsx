import type { SiteRow, TenantGateResponse, TenantHistoryResponse, TenantRemediation } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

type Props = {
  tenantId: string;
  gate: TenantGateResponse | null;
  history: TenantHistoryResponse | null;
  remediation: TenantRemediation | null;
  tenantSites: SiteRow[];
  loading: boolean;
  error: string;
};

export function TenantDetailPanel({ tenantId, gate, history, remediation, tenantSites, loading, error }: Props) {
  return (
    <aside className="card p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.24em] text-accent">Tenant Detail</p>
          <h2 className="mt-1 text-lg font-semibold text-ink">Tenant intelligence</h2>
        </div>
        {gate ? <StatusBadge pass={gate.overall_pass} /> : null}
      </div>
      <p className="mt-1 text-xs text-slate-400">Shows gate posture, remediation plan, historical snapshots, and linked sites for this tenant.</p>

      <p className="mt-3 wrap-anywhere rounded-xl border border-slate-200 bg-panelAlt/60 px-3 py-2 font-mono text-xs text-ink">{tenantId || "Select tenant"}</p>

      {loading ? <p className="mt-4 text-sm text-slate-400">Loading tenant intelligence...</p> : null}
      {error ? <p className="mt-4 text-sm text-danger">{error}</p> : null}

      {gate ? (
        <div className="mt-4">
          <h3 className="text-xs uppercase tracking-[0.24em] text-slate-400">Gate Matrix</h3>
          <div className="mt-2 grid gap-2">
            {Object.entries(gate.gates).map(([gateName, state]) => (
              <div key={gateName} className="flex items-center justify-between rounded-xl border border-slate-200 bg-panelAlt/40 px-3 py-2">
                <span className="text-xs text-ink">{gateName}</span>
                <StatusBadge pass={state.pass} />
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {!gate && tenantSites.length > 0 ? (
        <div className="mt-4 rounded-xl border border-slate-200 bg-panelAlt/30 p-3 text-xs text-slate-500 wrap-anywhere">
          Objective-gate detail is not generated yet for this tenant. Site-level telemetry is available below and will feed this panel after orchestration cycles run.
        </div>
      ) : null}

      {remediation ? (
        <div className="mt-5">
          <h3 className="text-xs uppercase tracking-[0.24em] text-slate-400">Remediation</h3>
          <p className="mt-2 text-xs text-accent">Failed gates: {remediation.remediation.failed_gate_count}</p>
          <div className="mt-2 space-y-2">
            {remediation.remediation.actions.slice(0, 5).map((item, index) => (
              <div key={`${item.gate}-${index}`} className="rounded-xl border border-slate-200 bg-panelAlt/40 p-3">
                <p className="text-xs uppercase tracking-wider text-slate-400">{item.gate} / {item.priority}</p>
                <p className="mt-1 text-xs text-ink">{item.action}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {history ? (
        <div className="mt-5">
          <h3 className="text-xs uppercase tracking-[0.24em] text-slate-400">Recent Snapshots</h3>
          <ul className="mt-2 space-y-1 text-xs">
            {history.rows.slice(0, 8).map((row) => (
              <li key={row.id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-panelAlt/30 px-2 py-1.5">
                <span className="font-mono text-slate-400">{row.id}</span>
                <StatusBadge pass={row.overall_pass} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {tenantSites.length > 0 ? (
        <div className="mt-5">
          <h3 className="text-xs uppercase tracking-[0.24em] text-slate-400">Linked Sites</h3>
          <div className="mt-2 space-y-2">
            {tenantSites.slice(0, 6).map((site) => (
              <div key={site.site_id} className="rounded-xl border border-slate-200 bg-panelAlt/30 p-2 text-xs">
                <p className="text-ink wrap-anywhere">{site.display_name}</p>
                <p className="mt-1 font-mono text-slate-400 wrap-anywhere">{site.base_url}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
