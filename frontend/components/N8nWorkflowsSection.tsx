"use client";

import Link from "next/link";
import { DEFAULT_WORKFLOWS, AGENT_META, type AgentId } from "@/lib/workflowPlugins";

const AGENTS: AgentId[] = ["red", "blue", "purple", "orchestrator"];

function WorkflowCard({ agentId }: { agentId: AgentId }) {
  const meta = AGENT_META[agentId];
  const wf = DEFAULT_WORKFLOWS[agentId];
  // Show first 4 nodes as mini flow
  const preview = wf.nodes.slice(0, 4);

  return (
    <div
      className="rounded-2xl border bg-white p-4 flex flex-col gap-3"
      style={{ borderColor: `${meta.color}33`, borderTopWidth: 3, borderTopColor: meta.color }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="inline-flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-sm font-bold text-white"
            style={{ background: meta.color }}
          >
            {meta.icon}
          </span>
          <div className="min-w-0">
            <p className="text-xs font-semibold text-ink leading-tight truncate">{wf.name}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">{wf.nodes.length} nodes · Canvas Workflow</p>
          </div>
        </div>
        <span className="flex-shrink-0 inline-flex items-center gap-1 rounded-full text-[9px] font-semibold px-2 py-0.5 bg-green-50 text-green-700 border border-green-200">
          <span className="agent-dot agent-dot-green" style={{ width: 5, height: 5 }} />
          Active
        </span>
      </div>

      {/* Mini node preview */}
      <div className="flex items-center gap-1 flex-wrap">
        {preview.map((node, i) => (
          <span key={node.id} className="flex items-center gap-1">
            <span
              className="inline-flex items-center gap-1 rounded-lg px-1.5 py-0.5 text-[9px] font-semibold border"
              style={{
                background: `${node.color}14`,
                borderColor: `${node.color}33`,
                color: node.color,
              }}
            >
              {node.icon} {node.label}
            </span>
            {i < preview.length - 1 && (
              <svg viewBox="0 0 10 10" style={{ width: 8, height: 8, color: "#cbd5e1", flexShrink: 0 }}>
                <path d="M1 5h8M6 2l3 3-3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
              </svg>
            )}
          </span>
        ))}
        {wf.nodes.length > 4 && (
          <span className="text-[9px] text-slate-400">+{wf.nodes.length - 4}</span>
        )}
      </div>

      {/* Open Canvas button */}
      <Link
        href={`/n8n-agents?agent=${agentId}`}
        className="flex items-center justify-center gap-1.5 text-[10px] font-semibold rounded-xl py-1.5 text-white transition-opacity hover:opacity-90 border-t border-slate-100 pt-2 mt-0"
        style={{ background: meta.color, marginTop: "auto" }}
      >
        <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
          <path d="M14 17.5h7M17.5 14v7" />
        </svg>
        Open Canvas
      </Link>
    </div>
  );
}

export function N8nWorkflowsSection() {
  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.26em] text-accent">Agent Workflows</p>
          <p className="text-[11px] text-slate-400 mt-0.5">Drag-and-drop workflow builder สำหรับแต่ละ Agent — ใช้ BRP plugins เป็น nodes</p>
        </div>
        <Link
          href="/n8n-agents"
          className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 hover:border-accent hover:text-accent transition-colors shadow-sm"
        >
          <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="5" cy="12" r="2.5" />
            <circle cx="19" cy="6" r="2.5" />
            <circle cx="19" cy="18" r="2.5" />
            <path d="M7.5 12h4l2-6M7.5 12l2 6h4" />
          </svg>
          Workflow Builder
        </Link>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {AGENTS.map((id) => (
          <WorkflowCard key={id} agentId={id} />
        ))}
      </div>
    </section>
  );
}
