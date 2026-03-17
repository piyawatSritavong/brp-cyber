"use client";

import { useEffect, useState } from "react";
import { AgentStatusWidget, type AgentStatusData } from "@/components/AgentStatusWidget";
import { CommandBoardPanel, type CommandItem } from "@/components/CommandBoardPanel";
import { ChatInteractivePanel } from "@/components/ChatInteractivePanel";
import { N8nWorkflowsSection } from "@/components/N8nWorkflowsSection";
import { runSiteRedScan } from "@/lib/api";

// ─── Mock Agent Status Cycles ─────────────────────────────────────────────────
const AGENT_CYCLES: AgentStatusData[][] = [
  [
    { id: "red", label: "Scout Agent (Red)", shortLabel: "Red Agent", status: "active", currentActivity: "Currently scanning port 443 for Network A vulnerabilities", lastUpdated: new Date().toISOString() },
    { id: "blue", label: "Guardian Agent (Blue)", shortLabel: "Blue Agent", status: "active", currentActivity: "Monitoring NAS traffic. No anomalies detected", lastUpdated: new Date().toISOString() },
    { id: "purple", label: "Architect Agent (Purple)", shortLabel: "Purple Agent", status: "idle", currentActivity: "Awaiting next report cycle (next: 06:00)", lastUpdated: new Date().toISOString() },
    { id: "orchestrator", label: "Orchestrator", shortLabel: "Orchestrator", status: "active", currentActivity: "Coordinating agents. 2 priority actions pending", lastUpdated: new Date().toISOString() },
  ],
  [
    { id: "red", label: "Scout Agent (Red)", shortLabel: "Red Agent", status: "active", currentActivity: "Shadow pentest: crawling /api/auth endpoints", lastUpdated: new Date().toISOString() },
    { id: "blue", label: "Guardian Agent (Blue)", shortLabel: "Blue Agent", status: "warning", currentActivity: "Detected 3 unusual login attempts from 192.168.x.x", lastUpdated: new Date().toISOString() },
    { id: "purple", label: "Architect Agent (Purple)", shortLabel: "Purple Agent", status: "active", currentActivity: "Correlating Red/Blue data for threat brief", lastUpdated: new Date().toISOString() },
    { id: "orchestrator", label: "Orchestrator", shortLabel: "Orchestrator", status: "active", currentActivity: "Guardian flagged anomaly — analysis in progress", lastUpdated: new Date().toISOString() },
  ],
  [
    { id: "red", label: "Scout Agent (Red)", shortLabel: "Red Agent", status: "active", currentActivity: "Validating CVE-2024-xxxx on Vercel deployment", lastUpdated: new Date().toISOString() },
    { id: "blue", label: "Guardian Agent (Blue)", shortLabel: "Blue Agent", status: "active", currentActivity: "Log refiner active — filtering 1,240 noise events", lastUpdated: new Date().toISOString() },
    { id: "purple", label: "Architect Agent (Purple)", shortLabel: "Purple Agent", status: "active", currentActivity: "Drafting weekly ISO 27001 gap summary", lastUpdated: new Date().toISOString() },
    { id: "orchestrator", label: "Orchestrator", shortLabel: "Orchestrator", status: "active", currentActivity: "All agents nominal. Scheduled next sweep: 15 min", lastUpdated: new Date().toISOString() },
  ],
];

// ─── Initial Command Board Items ───────────────────────────────────────────────
const INITIAL_ITEMS: CommandItem[] = [
  {
    id: "c1",
    severity: "warning",
    emoji: "⚠️",
    title: "พบช่องโหว่ใหม่ใน Vercel Deployment",
    body: "Scout Agent ตรวจพบ CVE-2024-3094 บน edge function ของคุณ ต้องการให้ Red Agent ทดสอบเจาะเพื่อยืนยันไหม?",
    actionLabel: "Run Test",
    actionType: "red_scan",
  },
  {
    id: "c2",
    severity: "success",
    emoji: "✅",
    title: "ระบบ NAS ปลอดภัยดี",
    body: "Guardian Agent ตรวจสอบล่าสุดเมื่อ 2 ชั่วโมงที่แล้ว ไม่พบ Anomaly การสำรองข้อมูลเสร็จสิ้นแล้ว",
  },
  {
    id: "c3",
    severity: "danger",
    emoji: "🔴",
    title: "ตรวจพบ Login ผิดปกติ 47 ครั้ง",
    body: "IP: 185.220.x.x (Tor Exit Node) พยายาม Brute Force เข้า Admin Panel ต้องการบล็อกทันทีไหม?",
    actionLabel: "Block IP",
    actionType: "block_ip",
  },
  {
    id: "c4",
    severity: "info",
    emoji: "ℹ️",
    title: "รายงานประจำสัปดาห์พร้อมแล้ว",
    body: "Architect Agent ร่าง Executive Summary และ ISO 27001 Gap Analysis เสร็จแล้ว ต้องการดูหรือส่ง Email?",
    actionLabel: "View Report",
    actionType: "report",
  },
];

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function OrchestratorPanel() {
  const [agentCycleIdx, setAgentCycleIdx] = useState(0);
  const [commandItems, setCommandItems] = useState<CommandItem[]>(INITIAL_ITEMS);

  useEffect(() => {
    const agentTimer = setInterval(() => {
      setAgentCycleIdx((i) => (i + 1) % AGENT_CYCLES.length);
    }, 8000);
    return () => clearInterval(agentTimer);
  }, []);

  const currentAgents = AGENT_CYCLES[agentCycleIdx] ?? AGENT_CYCLES[0];

  async function handleCommandAction(item: CommandItem) {
    setCommandItems((prev) =>
      prev.map((i) => (i.id === item.id ? { ...i, loading: true } : i))
    );

    try {
      if (item.actionType === "red_scan") {
        const res = await runSiteRedScan("demo-duck-sec-ai-01", { scan_type: "full" });
        setCommandItems((prev) =>
          prev.map((i) =>
            i.id === item.id
              ? { ...i, loading: false, emoji: "🔍", severity: "info" as const, title: "Scan เสร็จสิ้น", body: res.ai_summary || `Scan ID: ${res.scan_id} · Status: ${res.status}`, actionLabel: undefined, actionType: null }
              : i
          )
        );
      } else if (item.actionType === "block_ip") {
        await new Promise((r) => setTimeout(r, 1200));
        setCommandItems((prev) =>
          prev.map((i) =>
            i.id === item.id
              ? { ...i, loading: false, emoji: "🛡️", severity: "success" as const, title: "IP ถูก Block แล้ว", body: "Guardian Agent สั่ง Firewall API Block IP 185.220.x.x เรียบร้อยแล้ว Incident Report กำลังร่าง…", actionLabel: undefined, actionType: null }
              : i
          )
        );
        setCommandItems((prev) => [
          ...prev,
          { id: uid(), severity: "info" as const, emoji: "📋", title: "Incident Report พร้อมส่ง", body: "Architect Agent ร่างรายงานเหตุการณ์ Brute Force เสร็จแล้ว ต้องการส่ง Email ถึงทีมไหม?", actionLabel: "Send Report", actionType: "report" },
        ]);
      } else if (item.actionType === "report") {
        await new Promise((r) => setTimeout(r, 800));
        setCommandItems((prev) =>
          prev.map((i) =>
            i.id === item.id
              ? { ...i, loading: false, emoji: "✅", severity: "success" as const, title: "Report ส่งแล้ว", body: "Incident Report ถูกส่ง Email ให้ทีมแล้ว และบันทึกใน Audit Log เรียบร้อย", actionLabel: undefined, actionType: null }
              : i
          )
        );
      } else {
        setCommandItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, loading: false } : i)));
      }
    } catch {
      setCommandItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, loading: false } : i)));
    }
  }

  return (
    <main className="space-y-5">
      {/* Agent status chips */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <p className="text-xs uppercase tracking-[0.26em] text-accent">Live Agent Status</p>
          <span className="flex items-center gap-1.5 text-xs text-slate-400">
            <span className="agent-dot agent-dot-green" style={{ width: 6, height: 6 }} />
            Auto-updating
          </span>
        </div>
        <AgentStatusWidget agents={currentAgents} variant="card" />
      </section>

      {/* n8n Workflow cards — aligned under each agent */}
      <N8nWorkflowsSection />

      {/* Command Board + Chat side by side */}
      <section className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-2 flex flex-col" style={{ minHeight: 360 }}>
          <CommandBoardPanel items={commandItems} onAction={handleCommandAction} />
        </div>
        <div className="lg:col-span-3 flex flex-col" style={{ minHeight: 360 }}>
          <ChatInteractivePanel siteId="" />
        </div>
      </section>
    </main>
  );
}
