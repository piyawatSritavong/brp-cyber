import type { DashboardRow } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

type Props = {
  rows: DashboardRow[];
  selectedTenantId: string;
  onSelectTenant: (tenantId: string) => void;
};

export function TenantTable({ rows, selectedTenantId, onSelectTenant }: Props) {
  return (
    <section className="card overflow-hidden">
      <div className="border-b border-slate-200 px-5 py-4">
        <p className="text-xs uppercase tracking-[0.24em] text-accent">Tenants</p>
        <h3 className="mt-1 text-lg font-semibold text-ink">Tenant posture matrix</h3>
        <p className="mt-1 text-xs text-slate-400">Failed gates and blockers requiring operator action.</p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] table-fixed text-left text-sm">
          <thead className="bg-panelAlt/60 text-slate-500">
            <tr>
              <th className="px-4 py-3">Tenant</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Failed Gates</th>
              <th className="px-4 py-3">Blockers</th>
              <th className="px-4 py-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr className="border-t border-slate-200">
                <td colSpan={5} className="px-4 py-4 text-xs text-slate-400">
                  No tenants found. Add site records in Configuration first.
                </td>
              </tr>
            ) : null}
            {rows.map((row) => (
              <tr
                key={row.tenant_id}
                className={
                  "border-t border-slate-200 transition-colors " +
                  (selectedTenantId === row.tenant_id ? "bg-accent/5" : "bg-transparent")
                }
              >
                <td className="px-4 py-3 font-mono text-xs text-ink wrap-anywhere">{row.tenant_id}</td>
                <td className="px-4 py-3">
                  <StatusBadge pass={row.overall_pass} />
                </td>
                <td className="px-4 py-3 font-semibold text-danger">{row.failed_gate_count}</td>
                <td className="px-4 py-3 text-xs text-slate-500 wrap-anywhere">
                  {row.blockers.length ? row.blockers.map((b) => b.gate).join(", ") : "none"}
                </td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => onSelectTenant(row.tenant_id)}
                    className={
                      "rounded-md border px-3 py-1.5 text-xs font-semibold transition " +
                      (selectedTenantId === row.tenant_id
                        ? "border-accent bg-accent text-white"
                        : "border-slate-200 bg-white text-ink hover:border-accent hover:text-accent")
                    }
                  >
                    Inspect
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
