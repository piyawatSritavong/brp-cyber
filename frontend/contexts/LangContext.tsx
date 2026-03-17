"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

export type Lang = "th" | "en";

const T = {
  th: {
    "brand.sub": "BRP Cyber",
    "brand.title": "Co-worker",
    "brand.desc": "AI Security Co-worker ที่ทำงานตลอด 24/7 สำหรับองค์กรไทย",
    "menu.group.menu": "เมนู",
    "menu.group.tools": "เครื่องมือ",
    "menu.group.config": "ตั้งค่า",
    "support.title": "AI Orchestrator",
    "support.body": "ระบบอัตโนมัติ, policy gates, และ audit-ready delivery พร้อมใช้งาน",
    "chat.header.eyebrow": "Natural Language",
    "chat.header.title": "Chat with AI",
    "chat.header.sub": "พิมพ์คำสั่งภาษาไทยหรืออังกฤษ เช่น 'สแกน URL นี้' หรือ 'ตรวจ Traffic'",
    "chat.empty.title": "พิมพ์คำสั่งได้เลย",
    "chat.empty.body": "ใช้ภาษาไทยหรืออังกฤษ เช่น 'สแกนเว็บ URL นี้' แล้ว AI จะเริ่มทำงานทันที",
    "chat.placeholder": "พิมพ์คำสั่ง… (Enter ส่ง)",
    "chat.hints": "ลอง: 'สแกน' · 'ตรวจ traffic' · 'รายงาน' · 'status' · 'help'",
    "page./.eyebrow": "AI Command Center",
    "page./.title": "Orchestrator",
    "page./.desc": "ศูนย์บัญชาการ AI agent แบบ real-time พร้อม priority task board และ command interface",
    "page./dashboard.eyebrow": "Security Overview",
    "page./dashboard.title": "Dashboard",
    "page./dashboard.desc": "ภาพรวมความปลอดภัย, objective gates, governance telemetry ขององค์กร",
    "page./reports.eyebrow": "Purple Service",
    "page./reports.title": "Reports",
    "page./reports.desc": "Correlation analysis, compliance mapping, executive scorecard และ ROI",
    "page./plugins.eyebrow": "Plugin Catalog",
    "page./plugins.title": "Plugins",
    "page./plugins.desc": "AI co-workers ที่ติดตั้งและดำเนินการต่อ site",
    "page./code.eyebrow": "Developer Security",
    "page./code.title": "Code Scanner",
    "page./code.desc": "อัปโหลดหรือวางโค้ดเพื่อวิเคราะห์ช่องโหว่ด้วย AI ทันที",
    "page./agents.eyebrow": "Agent Management",
    "page./agents.title": "Agent Roles",
    "page./agents.desc": "ตั้งค่า Scout, Guardian, Architect และ Orchestrator agent behavior",
    "page./settings.eyebrow": "System Configuration",
    "page./settings.title": "Settings",
    "page./settings.desc": "Alert channels, client connections และ system preferences",
    "page./n8n-agents.eyebrow": "Workflow Automation",
    "page./n8n-agents.title": "n8n Agents",
    "page./n8n-agents.desc": "Automation workflow สำหรับแต่ละ Agent — นำเข้า n8n เพื่อรัน automation อัตโนมัติ",
    "notif.tooltip": "การแจ้งเตือน",
  },
  en: {
    "brand.sub": "BRP Cyber",
    "brand.title": "Co-worker",
    "brand.desc": "AI Security Co-worker operating 24/7 for your organization",
    "menu.group.menu": "Menu",
    "menu.group.tools": "Tools",
    "menu.group.config": "Configuration",
    "support.title": "AI Orchestrator",
    "support.body": "Safe-mode automation, policy gates, and audit-ready delivery are enabled.",
    "chat.header.eyebrow": "Natural Language",
    "chat.header.title": "Chat with AI",
    "chat.header.sub": "Type commands in Thai or English, e.g. 'scan this URL' or 'check traffic'",
    "chat.empty.title": "Type a command",
    "chat.empty.body": "Use Thai or English. Try 'scan site URL' — AI will start immediately.",
    "chat.placeholder": "Type a command… (Enter to send)",
    "chat.hints": "Try: 'scan' · 'monitor traffic' · 'report' · 'status' · 'help'",
    "page./.eyebrow": "AI Command Center",
    "page./.title": "Orchestrator",
    "page./.desc": "Live AI agent coordination, priority task board, and natural language command interface.",
    "page./dashboard.eyebrow": "Security Overview",
    "page./dashboard.title": "Dashboard",
    "page./dashboard.desc": "Tenant posture, objective gates, governance telemetry, and enterprise readiness.",
    "page./reports.eyebrow": "Purple Service",
    "page./reports.title": "Reports",
    "page./reports.desc": "Correlation analysis, compliance mapping, executive scorecard, and ROI reporting.",
    "page./plugins.eyebrow": "Plugin Catalog",
    "page./plugins.title": "Plugins",
    "page./plugins.desc": "Role-based AI co-workers installed and operated per site.",
    "page./code.eyebrow": "Developer Security",
    "page./code.title": "Code Scanner",
    "page./code.desc": "Upload or paste code for instant AI vulnerability analysis.",
    "page./agents.eyebrow": "Agent Management",
    "page./agents.title": "Agent Roles",
    "page./agents.desc": "Configure Scout, Guardian, Architect, and Orchestrator agent behavior.",
    "page./settings.eyebrow": "System Configuration",
    "page./settings.title": "Settings",
    "page./settings.desc": "Alert channels, client connections, and system preferences.",
    "page./n8n-agents.eyebrow": "Workflow Automation",
    "page./n8n-agents.title": "n8n Agents",
    "page./n8n-agents.desc": "Per-agent automation workflows — import into n8n and run fully automated security operations.",
    "notif.tooltip": "Notifications",
  },
} as const;

export type TKey = keyof typeof T.th;

type LangContextValue = { lang: Lang; toggle: () => void; t: (key: TKey) => string };

const LangContext = createContext<LangContextValue>({
  lang: "th",
  toggle: () => {},
  t: (key) => key,
});

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>("th");
  const t = (key: TKey): string => T[lang][key];
  return (
    <LangContext.Provider value={{ lang, toggle: () => setLang((l) => (l === "th" ? "en" : "th")), t }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang() {
  return useContext(LangContext);
}
