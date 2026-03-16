export function StatusBadge({ pass }: { pass: boolean }) {
  return (
    <span
      className={
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide " +
        (pass
          ? "border border-accent/30 bg-accent/10 text-accent"
          : "border border-[#110B0A]/12 bg-[#110B0A]/5 text-[#110B0A]")
      }
    >
      {pass ? "Pass" : "Fail"}
    </span>
  );
}
