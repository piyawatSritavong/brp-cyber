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
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-panelAlt/60 text-slate-300">
            <tr>
              <th className="px-4 py-3">Tenant</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Failed Gates</th>
              <th className="px-4 py-3">Blockers</th>
              <th className="px-4 py-3">Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.tenant_id} className="border-t border-slate-800/80">
                <td className="px-4 py-3 font-mono text-xs text-slate-200">{row.tenant_id}</td>
                <td className="px-4 py-3">
                  <StatusBadge pass={row.overall_pass} />
                </td>
                <td className="px-4 py-3 text-warning">{row.failed_gate_count}</td>
                <td className="px-4 py-3 text-xs text-slate-300">
                  {row.blockers.length ? row.blockers.map((b) => b.gate).join(", ") : "none"}
                </td>
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => onSelectTenant(row.tenant_id)}
                    className={
                      "rounded-md border px-3 py-1.5 text-xs font-semibold transition " +
                      (selectedTenantId === row.tenant_id
                        ? "border-accent bg-accent/15 text-accent"
                        : "border-slate-600 text-slate-200 hover:border-slate-400")
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
