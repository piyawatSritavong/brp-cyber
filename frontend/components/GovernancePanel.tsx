import type { GovernanceDashboardResponse } from "@/lib/types";

type Props = {
  data: GovernanceDashboardResponse | null;
  loading: boolean;
  error: string;
};

export function GovernancePanel({ data, loading, error }: Props) {
  return (
    <section className="card mt-6 p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Control Plane Governance</h2>
        <span
          className={
            "rounded-full border px-2 py-1 text-[11px] uppercase tracking-wide " +
            (data?.policy.mode === "enforce"
              ? "border-warning/60 bg-warning/15 text-warning"
              : "border-slate-500 bg-slate-500/10 text-slate-300")
          }
        >
          policy: {data?.policy.mode || "unknown"}
        </span>
      </div>
      <p className="mt-1 text-xs text-slate-400">Central policy engine and audit telemetry across onboarding, auth, overrides, and production promotions.</p>

      {loading ? <p className="mt-3 text-sm text-slate-400">Refreshing governance telemetry...</p> : null}
      {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}

      {data ? (
        <>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard label="Events" value={data.summary.events_analyzed} tone="text-slate-200" />
            <StatCard label="Warnings" value={data.summary.policy_warnings} tone="text-warning" />
            <StatCard label="Denies" value={data.summary.policy_denies} tone="text-danger" />
            <StatCard label="Overrides" value={data.summary.override_actions} tone="text-slate-200" />
            <StatCard label="Promotions" value={data.summary.production_promotions} tone="text-accent" />
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <div className="rounded-md border border-slate-800 bg-panelAlt/30 p-3">
              <h3 className="text-xs uppercase tracking-wider text-slate-400">Top Actions</h3>
              <ul className="mt-2 space-y-1 text-xs text-slate-200">
                {data.top_actions.length === 0 ? <li className="text-slate-400">no actions</li> : null}
                {data.top_actions.slice(0, 8).map((item, idx) => (
                  <li key={`${item[0]}-${idx}`} className="flex items-center justify-between border-b border-slate-800/80 py-1">
                    <span className="wrap-anywhere pr-2">{item[0]}</span>
                    <span className="font-semibold text-slate-300">{item[1]}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-md border border-slate-800 bg-panelAlt/30 p-3">
              <h3 className="text-xs uppercase tracking-wider text-slate-400">Risky Actors</h3>
              <ul className="mt-2 space-y-1 text-xs text-slate-200">
                {data.risky_actors.length === 0 ? <li className="text-slate-400">no risky actors</li> : null}
                {data.risky_actors.slice(0, 8).map((item) => (
                  <li key={item.actor} className="flex items-center justify-between border-b border-slate-800/80 py-1">
                    <span className="wrap-anywhere pr-2">{item.actor}</span>
                    <span className="font-semibold text-danger">{item.risk_score}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </>
      ) : (
        <div className="mt-3 rounded-md border border-slate-800 bg-panelAlt/30 p-3 text-xs text-slate-300 wrap-anywhere">
          No governance snapshot returned yet. This panel tracks control-plane policy events, risky actors, and override activity.
        </div>
      )}
    </section>
  );
}

function StatCard({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-md border border-slate-800 bg-panelAlt/40 p-3">
      <p className="text-[11px] uppercase tracking-wider text-slate-400">{label}</p>
      <p className={`mt-1 text-xl font-bold ${tone}`}>{value}</p>
    </div>
  );
}
