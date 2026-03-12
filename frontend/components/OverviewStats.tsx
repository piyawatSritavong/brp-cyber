type Props = {
  total: number;
  passing: number;
  failing: number;
};

export function OverviewStats({ total, passing, failing }: Props) {
  return (
    <section className="grid gap-4 sm:grid-cols-3">
      <div className="card p-4">
        <p className="text-xs uppercase tracking-widest text-slate-400">Tenants</p>
        <p className="mt-2 text-2xl font-bold text-ink">{total}</p>
        <p className="mt-1 text-xs text-slate-400">Total organizations currently monitored.</p>
      </div>
      <div className="card p-4">
        <p className="text-xs uppercase tracking-widest text-slate-400">Passing</p>
        <p className="mt-2 text-2xl font-bold text-accent">{passing}</p>
        <p className="mt-1 text-xs text-slate-400">Tenants meeting objective-gate criteria.</p>
      </div>
      <div className="card p-4">
        <p className="text-xs uppercase tracking-widest text-slate-400">Failing</p>
        <p className="mt-2 text-2xl font-bold text-danger">{failing}</p>
        <p className="mt-1 text-xs text-slate-400">Tenants with unresolved blockers or missing evidence.</p>
      </div>
    </section>
  );
}
