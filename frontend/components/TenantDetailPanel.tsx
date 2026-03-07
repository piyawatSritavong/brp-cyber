import type { TenantGateResponse, TenantHistoryResponse, TenantRemediation } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

type Props = {
  tenantId: string;
  gate: TenantGateResponse | null;
  history: TenantHistoryResponse | null;
  remediation: TenantRemediation | null;
  loading: boolean;
  error: string;
};

export function TenantDetailPanel({ tenantId, gate, history, remediation, loading, error }: Props) {
  return (
    <aside className="card p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Tenant Detail</h2>
        {gate ? <StatusBadge pass={gate.overall_pass} /> : null}
      </div>

      <p className="mt-3 break-all rounded-md bg-panelAlt/60 px-3 py-2 font-mono text-xs text-slate-200">{tenantId || "Select tenant"}</p>

      {loading ? <p className="mt-4 text-sm text-slate-400">Loading tenant intelligence...</p> : null}
      {error ? <p className="mt-4 text-sm text-danger">{error}</p> : null}

      {gate ? (
        <div className="mt-4">
          <h3 className="text-xs uppercase tracking-widest text-slate-400">Gate Matrix</h3>
          <div className="mt-2 grid gap-2">
            {Object.entries(gate.gates).map(([gateName, state]) => (
              <div key={gateName} className="flex items-center justify-between rounded-md border border-slate-800 bg-panelAlt/40 px-3 py-2">
                <span className="text-xs text-slate-200">{gateName}</span>
                <StatusBadge pass={state.pass} />
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {remediation ? (
        <div className="mt-5">
          <h3 className="text-xs uppercase tracking-widest text-slate-400">Remediation</h3>
          <p className="mt-2 text-xs text-warning">Failed gates: {remediation.remediation.failed_gate_count}</p>
          <div className="mt-2 space-y-2">
            {remediation.remediation.actions.slice(0, 5).map((item, index) => (
              <div key={`${item.gate}-${index}`} className="rounded-md border border-slate-800 bg-panelAlt/40 p-3">
                <p className="text-xs uppercase tracking-wider text-slate-400">{item.gate} / {item.priority}</p>
                <p className="mt-1 text-xs text-slate-200">{item.action}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {history ? (
        <div className="mt-5">
          <h3 className="text-xs uppercase tracking-widest text-slate-400">Recent Snapshots</h3>
          <ul className="mt-2 space-y-1 text-xs">
            {history.rows.slice(0, 8).map((row) => (
              <li key={row.id} className="flex items-center justify-between rounded-md border border-slate-800 bg-panelAlt/30 px-2 py-1.5">
                <span className="font-mono text-slate-400">{row.id}</span>
                <StatusBadge pass={row.overall_pass} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </aside>
  );
}
