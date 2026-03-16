import type { GovernanceDashboardResponse } from "@/lib/types";

type Props = {
  data: GovernanceDashboardResponse | null;
  loading: boolean;
  error: string;
};

export function GovernancePanel({ data, loading, error }: Props) {
  return (
    <section className="card p-5">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.24em] text-accent">Governance</p>
          <h2 className="mt-1 text-lg font-semibold text-ink">Control plane governance</h2>
        </div>
        <span
          className={
            "rounded-full border px-3 py-1 text-[11px] uppercase tracking-wide " +
            (data?.policy.mode === "enforce"
              ? "border-accent/30 bg-accent/10 text-accent"
              : "border-slate-200 bg-panelAlt/60 text-slate-500")
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
            <StatCard label="Events" value={data.summary.events_analyzed} tone="text-ink" />
            <StatCard label="Warnings" value={data.summary.policy_warnings} tone="text-warning" />
            <StatCard label="Denies" value={data.summary.policy_denies} tone="text-danger" />
            <StatCard label="Overrides" value={data.summary.override_actions} tone="text-ink" />
            <StatCard label="Promotions" value={data.summary.production_promotions} tone="text-accent" />
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <div className="rounded-[18px] border border-slate-200 bg-panelAlt/30 p-4">
              <h3 className="text-xs uppercase tracking-wider text-slate-400">Top Actions</h3>
              <ul className="mt-2 space-y-1 text-xs text-ink">
                {data.top_actions.length === 0 ? <li className="text-slate-400">no actions</li> : null}
                {data.top_actions.slice(0, 8).map((item, idx) => (
                  <li key={`${item[0]}-${idx}`} className="flex items-center justify-between border-b border-slate-200 py-1">
                    <span className="wrap-anywhere pr-2">{item[0]}</span>
                    <span className="font-semibold text-accent">{item[1]}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-[18px] border border-slate-200 bg-panelAlt/30 p-4">
              <h3 className="text-xs uppercase tracking-wider text-slate-400">Risky Actors</h3>
              <ul className="mt-2 space-y-1 text-xs text-ink">
                {data.risky_actors.length === 0 ? <li className="text-slate-400">no risky actors</li> : null}
                {data.risky_actors.slice(0, 8).map((item) => (
                  <li key={item.actor} className="flex items-center justify-between border-b border-slate-200 py-1">
                    <span className="wrap-anywhere pr-2">{item.actor}</span>
                    <span className="font-semibold text-accent">{item.risk_score}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </>
      ) : (
        <div className="mt-3 rounded-[18px] border border-slate-200 bg-panelAlt/30 p-3 text-xs text-slate-500 wrap-anywhere">
          No governance snapshot returned yet. This panel tracks control-plane policy events, risky actors, and override activity.
        </div>
      )}
    </section>
  );
}

function StatCard({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="rounded-[18px] border border-slate-200 bg-panelAlt/40 p-4">
      <p className="text-[11px] uppercase tracking-[0.22em] text-slate-400">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${tone}`}>{value}</p>
    </div>
  );
}
