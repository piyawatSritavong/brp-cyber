export function StatusBadge({ pass }: { pass: boolean }) {
  return (
    <span
      className={
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide " +
        (pass
          ? "bg-accent/20 text-accent border border-accent/50"
          : "bg-danger/20 text-danger border border-danger/50 pulse")
      }
    >
      {pass ? "Pass" : "Fail"}
    </span>
  );
}
