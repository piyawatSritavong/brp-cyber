"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { Suspense } from "react";
import { WorkflowCanvas } from "@/components/WorkflowCanvas";
import { AGENT_META, type AgentId } from "@/lib/workflowPlugins";

const AGENTS: { id: AgentId; label: string; color: string; icon: string }[] = [
  { id: "red", label: "Scout Agent", color: "#f31260", icon: "🔍" },
  { id: "blue", label: "Guardian Agent", color: "#006FEE", icon: "🛡️" },
  { id: "purple", label: "Architect Agent", color: "#9353d3", icon: "📐" },
  { id: "orchestrator", label: "Orchestrator", color: "#F76C45", icon: "⚡" },
];

function N8nPageInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const agentParam = searchParams.get("agent") as AgentId | null;
  const activeId: AgentId = agentParam && AGENT_META[agentParam] ? agentParam : "red";

  function switchAgent(id: AgentId) {
    router.push(`/n8n-agents?agent=${id}`);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 120px)", overflow: "hidden" }}>
      {/* Agent tabs */}
      <div
        style={{
          display: "flex",
          gap: 6,
          padding: "0 0 12px",
          flexShrink: 0,
          flexWrap: "wrap",
        }}
      >
        {AGENTS.map((a) => {
          const active = a.id === activeId;
          return (
            <button
              key={a.id}
              type="button"
              onClick={() => switchAgent(a.id)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 7,
                borderRadius: 12,
                border: `1.5px solid ${active ? a.color : "#e2e8f0"}`,
                background: active ? a.color : "#fff",
                color: active ? "#fff" : "#374151",
                padding: "7px 16px",
                fontSize: 13,
                fontWeight: 700,
                cursor: "pointer",
                transition: "all 0.15s",
              }}
            >
              <span>{a.icon}</span>
              {a.label}
            </button>
          );
        })}

        <div style={{ flex: 1 }} />
        <span style={{ alignSelf: "center", fontSize: 11, color: "#94a3b8" }}>
          Drag plugins from the right panel to build your workflow
        </span>
      </div>

      {/* Canvas — fills remaining height */}
      <div style={{ flex: 1, borderRadius: 16, overflow: "hidden", border: "1px solid #2d2d45" }}>
        <WorkflowCanvas key={activeId} agentId={activeId} />
      </div>
    </div>
  );
}

export default function N8nAgentsPage() {
  return (
    <Suspense fallback={<div style={{ padding: 40, color: "#6b7280" }}>Loading…</div>}>
      <N8nPageInner />
    </Suspense>
  );
}
