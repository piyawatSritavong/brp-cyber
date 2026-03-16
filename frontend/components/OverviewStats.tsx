type Props = {
  total: number;
  passing: number;
  failing: number;
};

export function OverviewStats({ total, passing, failing }: Props) {
  return (
    <section className="grid gap-4 sm:grid-cols-3">
      <div className="card p-5">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Tenants</p>
          <span className="rounded-full bg-accent/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-accent">
            Total
          </span>
        </div>
        <p className="mt-3 text-3xl font-semibold text-ink">{total}</p>
        <p className="mt-2 text-xs leading-6 text-slate-400">Total organizations currently monitored.</p>
      </div>
      <div className="card p-5">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Passing</p>
          <span className="rounded-full bg-accent/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-accent">
            Ready
          </span>
        </div>
        <p className="mt-3 text-3xl font-semibold text-accent">{passing}</p>
        <p className="mt-2 text-xs leading-6 text-slate-400">Tenants meeting objective-gate criteria.</p>
      </div>
      <div className="card p-5">
        <div className="flex items-center justify-between gap-3">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Failing</p>
          <span className="rounded-full bg-[#110B0A]/6 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-[#110B0A]">
            Needs work
          </span>
        </div>
        <p className="mt-3 text-3xl font-semibold text-danger">{failing}</p>
        <p className="mt-2 text-xs leading-6 text-slate-400">Tenants with unresolved blockers or missing evidence.</p>
      </div>
    </section>
  );
}
