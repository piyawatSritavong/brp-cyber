"use client";

const STEPS = [
  {
    num: 1,
    icon: "👁",
    label: "Detection",
    desc: "Guardian spots anomaly",
    example: "Brute force on NAS",
  },
  {
    num: 2,
    icon: "🧠",
    label: "Analysis",
    desc: "Orchestrator evaluates risk",
    example: "IP จาก Tor · Risk 90%",
  },
  {
    num: 3,
    icon: "🤝",
    label: "Co-work",
    desc: "Human confirms via chat",
    example: "ตัดการเชื่อมต่อเลยไหม? [Confirm]",
  },
  {
    num: 4,
    icon: "⚡",
    label: "Execution",
    desc: "AI calls Firewall API",
    example: "Block IP ทันที",
  },
  {
    num: 5,
    icon: "📋",
    label: "Post-incident",
    desc: "Report drafted & sent",
    example: "Incident Report → Email",
  },
] as const;

type Props = {
  activeStep?: number;
};

export function ActionLoopPanel({ activeStep = 0 }: Props) {
  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-xs uppercase tracking-[0.26em] text-accent">Co-pilot to Auto-pilot</p>
          <h3 className="mt-1 text-base font-semibold text-ink">The Action Loop</h3>
        </div>
        <span className="text-xs text-slate-400 bg-slate-100 rounded-full px-3 py-1">
          {activeStep > 0 ? `Step ${activeStep} / 5 Active` : "Monitoring…"}
        </span>
      </div>

      <div className="action-loop-container pb-2">
        {STEPS.map((step) => {
          const isActive = activeStep === step.num;
          const isDone = activeStep > step.num;
          return (
            <div
              key={step.num}
              className={`action-loop-step ${isActive ? "action-loop-step-active" : ""}`}
            >
              <div
                className="action-loop-step-icon"
                style={isDone ? { background: "rgba(23,201,100,0.15)", borderColor: "rgba(23,201,100,0.35)" } : {}}
              >
                {isDone ? "✓" : step.icon}
              </div>
              <p className="action-loop-step-label">{step.label}</p>
              <p className="action-loop-step-desc">{step.desc}</p>
              {isActive && (
                <span className="inline-flex items-center gap-1 mt-1 rounded-full bg-accent px-2 py-0.5 text-[9px] font-semibold text-white">
                  <span className="agent-dot agent-dot-green" style={{ width: 5, height: 5 }} />
                  Live
                </span>
              )}
            </div>
          );
        })}
      </div>

      {activeStep > 0 && activeStep <= STEPS.length && (
        <div className="mt-4 rounded-xl bg-muted-surface border border-[var(--card-border)] p-3 text-xs text-slate-500">
          <span className="font-semibold text-ink">Current: </span>
          {STEPS[activeStep - 1]?.example}
        </div>
      )}
    </div>
  );
}
