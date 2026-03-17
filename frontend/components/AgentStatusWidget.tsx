"use client";

export type AgentStatusData = {
  id: "red" | "blue" | "purple" | "orchestrator";
  label: string;
  shortLabel: string;
  status: "active" | "idle" | "warning";
  currentActivity: string;
  lastUpdated: string;
};

function DotClass(status: AgentStatusData["status"]): string {
  if (status === "active") return "agent-dot agent-dot-green";
  if (status === "warning") return "agent-dot agent-dot-yellow";
  return "agent-dot";
}

function agentColor(id: AgentStatusData["id"]): string {
  if (id === "red") return "#f31260";
  if (id === "blue") return "#006FEE";
  if (id === "purple") return "#9353d3";
  return "var(--accent)";
}

type AgentStatusWidgetProps = {
  agents: AgentStatusData[];
  variant: "sidebar" | "card";
};

export function AgentStatusWidget({ agents, variant }: AgentStatusWidgetProps) {
  if (variant === "sidebar") {
    const visible = agents.filter((a) => a.id === "red" || a.id === "blue");
    return (
      <div className="sidebar-agent-status">
        {visible.map((agent) => (
          <p key={agent.id} className="sidebar-agent-line">
            <span>{agent.shortLabel}:</span> {agent.currentActivity}
          </p>
        ))}
      </div>
    );
  }

  // card variant — 2×2 grid
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {agents.map((agent) => (
        <div key={agent.id} className="agent-card">
          <div className="agent-card-header">
            <span
              className="inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold text-white flex-shrink-0"
              style={{ background: agentColor(agent.id) }}
            >
              {agent.label.charAt(0)}
            </span>
            <span className="text-xs font-semibold text-ink leading-tight flex-1 min-w-0">{agent.label}</span>
            <span className={DotClass(agent.status)} />
          </div>
          <p className="agent-card-activity">{agent.currentActivity}</p>
          <p className="text-[10px] text-slate-400 mt-1">
            {agent.status === "active" ? "● Running" : agent.status === "warning" ? "⚠ Warning" : "○ Idle"}
          </p>
        </div>
      ))}
    </div>
  );
}
