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
      </div>
      <div className="card p-4">
        <p className="text-xs uppercase tracking-widest text-slate-400">Passing</p>
        <p className="mt-2 text-2xl font-bold text-accent">{passing}</p>
      </div>
      <div className="card p-4">
        <p className="text-xs uppercase tracking-widest text-slate-400">Failing</p>
        <p className="mt-2 text-2xl font-bold text-danger">{failing}</p>
      </div>
    </section>
  );
}
