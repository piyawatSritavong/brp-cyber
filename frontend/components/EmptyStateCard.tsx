"use client";

type EmptyStateIcon = "shield" | "scan" | "agent" | "chat" | "code" | "report" | "settings" | "plugin";

type EmptyStateCardProps = {
  icon?: EmptyStateIcon;
  title: string;
  body: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  size?: "sm" | "md" | "lg";
};

function IconSvg({ kind }: { kind: EmptyStateIcon }) {
  const size = 34;
  const props = {
    viewBox: "0 0 24 24",
    width: size,
    height: size,
    fill: "none",
    stroke: "var(--accent)",
    strokeWidth: 1.6,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };

  switch (kind) {
    case "shield":
      return <svg {...props}><path d="M12 3 5 6v5c0 5 2.98 8.67 7 10 4.02-1.33 7-5 7-10V6l-7-3Z" /></svg>;
    case "scan":
      return <svg {...props}><rect x="3" y="3" width="18" height="18" rx="3" /><path d="M7 12h10M12 7v10" /></svg>;
    case "agent":
      return (
        <svg {...props}>
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case "chat":
      return (
        <svg {...props}>
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      );
    case "code":
      return (
        <svg {...props}>
          <polyline points="16 18 22 12 16 6" />
          <polyline points="8 6 2 12 8 18" />
        </svg>
      );
    case "report":
      return (
        <svg {...props}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      );
    case "settings":
      return (
        <svg {...props}>
          <circle cx="12" cy="12" r="3.5" />
          <path d="M12 2.75v2.5M12 18.75v2.5M21.25 12h-2.5M5.25 12h-2.5M18.54 5.46l-1.77 1.77M7.23 16.77l-1.77 1.77M18.54 18.54l-1.77-1.77M7.23 7.23 5.46 5.46" />
        </svg>
      );
    case "plugin":
      return (
        <svg {...props}>
          <path d="M8 3v6M16 3v6M7 9h10v3a5 5 0 0 1-5 5 5 5 0 0 1-5-5V9Z" />
          <path d="M12 17v4" />
        </svg>
      );
  }
}

export function EmptyStateCard({ icon = "shield", title, body, action, size = "md" }: EmptyStateCardProps) {
  const padClass = size === "sm" ? "py-6 px-4" : size === "lg" ? "py-16 px-8" : "py-10 px-6";

  return (
    <div className={`empty-state-card ${padClass}`}>
      <div className="empty-state-blob">
        <IconSvg kind={icon} />
      </div>
      <p className="text-sm font-semibold text-ink mt-1">{title}</p>
      <p className="text-xs leading-6 text-slate-400 max-w-xs">{body}</p>
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="mt-2 rounded-2xl border border-accent bg-accent px-5 py-2 text-sm font-semibold text-white shadow-sm hover:opacity-90 transition-opacity"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
