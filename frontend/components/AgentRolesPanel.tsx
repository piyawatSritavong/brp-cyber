"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchSites } from "@/lib/api";
import { EmptyStateCard } from "@/components/EmptyStateCard";
import { useRouter } from "next/navigation";
import type { SiteRow } from "@/lib/types";

type NotifyChannel = "slack" | "line" | "telegram" | "email";

type AgentConfig = {
  id: "red" | "blue" | "purple" | "orchestrator";
  label: string;
  shortRole: string;
  roleColor: string;
  description: string;
  capability: string[];
  enabled: boolean;
  scheduleMinutes: number;
  notifyChannels: NotifyChannel[];
  currentObjective: string;
  status: "active" | "idle" | "warning";
};

const DEFAULT_AGENTS: AgentConfig[] = [
  {
    id: "red",
    label: "Scout Agent",
    shortRole: "Red",
    roleColor: "#f31260",
    description: "คอยสแกนหาช่องโหว่ของตัวเองตลอดเวลา (Continuous Pen-test) ทดสอบ exploit path และ validate CVE ใหม่ๆ",
    capability: ["Shadow Pentest", "CVE Validation", "Exploit Autopilot", "Social Engineering Sim"],
    enabled: true,
    scheduleMinutes: 60,
    notifyChannels: ["slack"],
    currentObjective: "Continuous scan ทุก port ที่เปิดอยู่ใน scope",
    status: "active",
  },
  {
    id: "blue",
    label: "Guardian Agent",
    shortRole: "Blue",
    roleColor: "#006FEE",
    description: "คอย Monitor Log และดักจับพฤติกรรมแปลกๆ ตรวจสอบ Threat Intelligence และ Block Threat อัตโนมัติ",
    capability: ["Log Monitoring", "Threat Detection", "Auto Response", "SOAR Integration"],
    enabled: true,
    scheduleMinutes: 5,
    notifyChannels: ["slack", "line"],
    currentObjective: "Monitor NAS traffic + Auth logs ทุก 5 นาที",
    status: "active",
  },
  {
    id: "purple",
    label: "Architect Agent",
    shortRole: "Purple",
    roleColor: "#9353d3",
    description: "คอยสรุปผลจาก Scout และ Guardian เพื่อเสนอวิธีแก้ปัญหา สร้าง Report และ Compliance mapping",
    capability: ["ISO/NIST Gap Analysis", "ROI Dashboard", "Incident Report", "MITRE ATT&CK Map"],
    enabled: true,
    scheduleMinutes: 1440,
    notifyChannels: ["slack", "email"],
    currentObjective: "รอ weekly report cycle (ทุกวันจันทร์ 09:00)",
    status: "idle",
  },
  {
    id: "orchestrator",
    label: "Orchestrator",
    shortRole: "Manager",
    roleColor: "var(--accent)",
    description: "ตัวหลักที่สั่งการ Agent ตัวอื่นและสรุปรายงานให้ User ประสาน Scout + Guardian + Architect ให้ทำงานร่วมกัน",
    capability: ["Agent Coordination", "Priority Triage", "Approval Workflow", "Auto-pilot Mode"],
    enabled: true,
    scheduleMinutes: 1,
    notifyChannels: ["slack", "line", "telegram"],
    currentObjective: "Coordinate all agents · 2 pending approvals",
    status: "active",
  },
];

const CHANNEL_LABELS: Record<NotifyChannel, string> = {
  slack: "Slack",
  line: "LINE",
  telegram: "Telegram",
  email: "Email",
};

function Toggle({ on, onToggle }: { on: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`toggle-track ${on ? "toggle-track-on" : ""}`}
      aria-label="Toggle agent"
    >
      <span className="toggle-thumb" />
    </button>
  );
}

function DotClass(status: AgentConfig["status"]): string {
  if (status === "active") return "agent-dot agent-dot-green";
  if (status === "warning") return "agent-dot agent-dot-yellow";
  return "agent-dot";
}

export function AgentRolesPanel() {
  const router = useRouter();
  const [sites, setSites] = useState<SiteRow[]>([]);
  const [agents, setAgents] = useState<AgentConfig[]>(DEFAULT_AGENTS);
  const [saved, setSaved] = useState(false);

  const loadSites = useCallback(async () => {
    try {
      const res = await fetchSites("", 100);
      setSites(res.rows || []);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => { void loadSites(); }, [loadSites]);

  function toggleAgent(id: AgentConfig["id"]) {
    setAgents((prev) => prev.map((a) => a.id === id ? { ...a, enabled: !a.enabled } : a));
  }

  function setSchedule(id: AgentConfig["id"], minutes: number) {
    setAgents((prev) => prev.map((a) => a.id === id ? { ...a, scheduleMinutes: minutes } : a));
  }

  function toggleChannel(id: AgentConfig["id"], ch: NotifyChannel) {
    setAgents((prev) =>
      prev.map((a) => {
        if (a.id !== id) return a;
        const has = a.notifyChannels.includes(ch);
        return {
          ...a,
          notifyChannels: has ? a.notifyChannels.filter((c) => c !== ch) : [...a.notifyChannels, ch],
        };
      })
    );
  }

  function handleSave() {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <main className="space-y-5">
      <section className="card p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.26em] text-accent">Agent Management</p>
            <h2 className="mt-1 text-[1.85rem] font-semibold text-ink">Agent Roles</h2>
            <p className="mt-1 text-sm text-slate-500">
              กำหนดพฤติกรรม ตาราง และช่องทาง Notify ของ AI Agent แต่ละตัว
            </p>
          </div>
          <button
            type="button"
            onClick={handleSave}
            className="flex-shrink-0 rounded-xl bg-accent px-5 py-2 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
          >
            {saved ? "✓ Saved" : "Save Changes"}
          </button>
        </div>
      </section>

      {sites.length === 0 ? (
        <EmptyStateCard
          icon="agent"
          title="ยังไม่มี Site ที่เชื่อมต่อ"
          body="เพิ่ม Client Site ใน Settings เพื่อเปิดใช้งาน Agent — Agent จะเริ่มทำงานทันทีหลังเพิ่ม Site"
          action={{ label: "ไปที่ Settings", onClick: () => router.push("/settings") }}
        />
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        {agents.map((agent) => (
          <div key={agent.id} className="card p-5 space-y-4">
            {/* Header */}
            <div className="flex items-start gap-3">
              <div
                className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-2xl text-sm font-bold text-white"
                style={{ background: agent.roleColor }}
              >
                {agent.shortRole.charAt(0)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-ink">{agent.label}</span>
                  <span
                    className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full text-white"
                    style={{ background: agent.roleColor }}
                  >
                    {agent.shortRole}
                  </span>
                  <span className={DotClass(agent.status)} />
                  <span className="text-[10px] text-slate-400">
                    {agent.status === "active" ? "Running" : agent.status === "warning" ? "Warning" : "Idle"}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-slate-400 leading-relaxed">{agent.description}</p>
              </div>
              <Toggle on={agent.enabled} onToggle={() => toggleAgent(agent.id)} />
            </div>

            {/* Current Objective */}
            <div className="rounded-xl bg-[var(--muted-surface)] border border-[var(--card-border)] px-3 py-2">
              <p className="text-[10px] uppercase tracking-wider text-slate-400 mb-0.5">Current Objective</p>
              <p className="text-xs text-ink">{agent.currentObjective}</p>
            </div>

            {/* Capabilities */}
            <div>
              <p className="text-[10px] uppercase tracking-wider text-slate-400 mb-1.5">Capabilities</p>
              <div className="flex flex-wrap gap-1.5">
                {agent.capability.map((cap) => (
                  <span
                    key={cap}
                    className="text-[10px] font-medium rounded-full px-2 py-0.5 border"
                    style={{
                      color: agent.roleColor,
                      borderColor: `${agent.roleColor}40`,
                      background: `${agent.roleColor}10`,
                    }}
                  >
                    {cap}
                  </span>
                ))}
              </div>
            </div>

            {/* Schedule */}
            <div className="flex items-center gap-3">
              <label className="text-xs text-slate-500 flex-shrink-0">Run interval</label>
              <input
                type="number"
                min={1}
                max={10080}
                value={agent.scheduleMinutes}
                onChange={(e) => setSchedule(agent.id, Number(e.target.value))}
                disabled={!agent.enabled}
                className="w-20 rounded-xl border border-[var(--card-border)] bg-[var(--muted-surface)] px-3 py-1.5 text-sm text-ink outline-none focus:border-accent disabled:opacity-40"
              />
              <span className="text-xs text-slate-400">minutes</span>
            </div>

            {/* Notify Channels */}
            <div>
              <p className="text-[10px] uppercase tracking-wider text-slate-400 mb-1.5">Notify Channels</p>
              <div className="flex flex-wrap gap-2">
                {(["slack", "line", "telegram", "email"] as NotifyChannel[]).map((ch) => {
                  const active = agent.notifyChannels.includes(ch);
                  return (
                    <button
                      key={ch}
                      type="button"
                      disabled={!agent.enabled}
                      onClick={() => toggleChannel(agent.id, ch)}
                      className="rounded-xl border px-3 py-1 text-xs font-medium transition-all disabled:opacity-40"
                      style={active
                        ? { borderColor: agent.roleColor, background: `${agent.roleColor}15`, color: agent.roleColor }
                        : { borderColor: "var(--card-border)", color: "var(--shell-text)", opacity: 0.5 }
                      }
                    >
                      {CHANNEL_LABELS[ch]}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
