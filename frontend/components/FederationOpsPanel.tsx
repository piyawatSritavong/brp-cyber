import { useEffect, useState } from "react";

import { fetchActionCenterSlaFederation } from "@/lib/api";
import type { FederationActionCenterSlaResponse } from "@/lib/types";

type Props = {
  canView: boolean;
};

export function FederationOpsPanel({ canView }: Props) {
  const [data, setData] = useState<FederationActionCenterSlaResponse | null>(null);
  const [error, setError] = useState("");

  const load = async () => {
    if (!canView) {
      setData(null);
      setError("Viewer permission required");
      return;
    }
    setError("");
    try {
      const response = await fetchActionCenterSlaFederation({ lookback_hours: 24, limit: 200 });
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "federation_load_failed");
    }
  };

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), 30000);
    return () => clearInterval(timer);
  }, [canView]);

  return (
    <section className="card mt-4 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Federation Ops (MSSP)</h2>
        {data ? (
          <p className="text-xs text-slate-400 wrap-anywhere">
            window={data.window_hours}h generated={data.generated_at}
          </p>
        ) : null}
      </div>
      <p className="mt-1 text-xs text-slate-400">Cross-tenant SLA breach + action-center dispatch risk heatmap for enterprise operations.</p>
      {error ? <p className="mt-2 text-sm text-danger">{error}</p> : null}

      {data ? (
        <div className="mt-2 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
          <p className="text-slate-300 wrap-anywhere">
            tenants={data.count} tiers={JSON.stringify(data.tier_counts)}
          </p>
        </div>
      ) : null}

      <div className="mt-3 max-h-52 overflow-auto rounded border border-slate-800 p-2 text-xs">
        <p className="mb-2 text-slate-400">Top Risk Tenants</p>
        {(data?.rows || []).length === 0 ? <p className="text-slate-500">No federation activity in window.</p> : null}
        {(data?.rows || []).map((row) => (
          <div key={row.tenant_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">
              {row.tenant_code} risk={row.risk_tier} score={row.risk_score}
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              breach={row.breach_count} critical={row.critical_breach_count} dispatch={row.dispatch_count} failed_channels={row.failed_channel_count}
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">{row.recommended_action}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
