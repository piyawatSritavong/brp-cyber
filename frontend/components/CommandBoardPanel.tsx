"use client";

import { EmptyStateCard } from "@/components/EmptyStateCard";

export type CommandItem = {
  id: string;
  severity: "warning" | "info" | "success" | "danger";
  emoji: string;
  title: string;
  body: string;
  actionLabel?: string;
  actionType?: "red_scan" | "blue_check" | "block_ip" | "report" | null;
  loading?: boolean;
};

type Props = {
  items: CommandItem[];
  onAction: (item: CommandItem) => void;
};

const SEVERITY_LABEL: Record<CommandItem["severity"], string> = {
  warning: "Recommended Action",
  danger: "Alert",
  success: "Health Check",
  info: "Info",
};

const severityClass: Record<CommandItem["severity"], string> = {
  warning: "cmd-item-warning",
  danger: "cmd-item-danger",
  success: "cmd-item-success",
  info: "cmd-item-info",
};

export function CommandBoardPanel({ items, onAction }: Props) {
  if (items.length === 0) {
    return (
      <div className="card h-full">
        <EmptyStateCard
          icon="shield"
          title="All clear"
          body="ไม่มี Priority Task จาก AI ในขณะนี้ ระบบกำลัง Monitor อยู่"
          size="sm"
        />
      </div>
    );
  }

  return (
    <div className="card flex flex-col h-full">
      <div className="px-5 pt-5 pb-3 border-b border-[var(--card-border)]">
        <p className="text-xs uppercase tracking-[0.26em] text-accent">AI Recommendations</p>
        <h3 className="mt-1 text-base font-semibold text-ink">Priority Tasks</h3>
      </div>
      <div className="flex-1 overflow-y-auto space-y-3 p-4">
        {items.map((item) => (
          <div key={item.id} className={`cmd-item ${severityClass[item.severity]}`}>
            <div className="flex items-start gap-2">
              <span className="text-base leading-none mt-0.5 flex-shrink-0">{item.emoji}</span>
              <div className="flex-1 min-w-0">
                <p className="text-[10px] uppercase tracking-wider font-semibold" style={{
                  color: item.severity === "danger" ? "#f31260"
                    : item.severity === "warning" ? "#f5a623"
                    : item.severity === "success" ? "#17c964"
                    : "var(--accent)"
                }}>
                  {SEVERITY_LABEL[item.severity]}
                </p>
                <p className="mt-0.5 text-xs font-semibold text-ink leading-snug">{item.title}</p>
                <p className="mt-1 text-[11px] text-slate-400 leading-relaxed">{item.body}</p>
              </div>
            </div>
            {item.actionLabel && (
              <div className="mt-2 flex justify-end">
                <button
                  type="button"
                  disabled={item.loading}
                  onClick={() => onAction(item)}
                  className="rounded-xl border border-accent bg-accent-soft px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent hover:text-white transition-all disabled:opacity-50"
                >
                  {item.loading ? "Running…" : item.actionLabel}
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
