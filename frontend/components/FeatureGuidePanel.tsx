"use client";

type FeatureGuideItem = {
  title: string;
  summary: string;
  details: string[];
};

export function FeatureGuidePanel({
  eyebrow,
  title,
  description,
  items,
}: {
  eyebrow: string;
  title: string;
  description: string;
  items: FeatureGuideItem[];
}) {
  return (
    <section className="card p-5">
      <p className="text-xs uppercase tracking-[0.26em] text-accent">{eyebrow}</p>
      <h2 className="mt-2 text-2xl font-semibold text-ink">{title}</h2>
      <p className="mt-2 text-sm leading-7 text-slate-500">{description}</p>

      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <article key={item.title} className="rounded-2xl border border-slate-200 bg-panelAlt/55 p-4">
            <h3 className="text-sm font-semibold text-ink wrap-anywhere">{item.title}</h3>
            <p className="mt-1 text-xs text-slate-500 wrap-anywhere">{item.summary}</p>
            <div className="mt-3 space-y-1">
              {item.details.map((detail) => (
                <p key={detail} className="text-xs text-slate-700 wrap-anywhere">
                  - {detail}
                </p>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
