"use client";

import { useEffect, useRef, useState } from "react";
import { runSiteRedScan, fetchSiteBlueEvents } from "@/lib/api";
import { AIEyes } from "@/components/AIEyes";
import { useLang } from "@/contexts/LangContext";

export type ChatMessage = {
  id: string;
  role: "user" | "agent";
  text: string;
  timestamp: string;
};

type Props = {
  siteId: string;
};

// ─── Action routing (triggers real API calls) ──────────────────────────────
function detectActionIntent(text: string): "scan" | "monitor" | null {
  const lower = text.toLowerCase();
  if (/scan|สแกน|ทดสอบ|pentest|vuln/.test(lower)) return "scan";
  if (/monitor|traffic|ตรวจ log|ดู log|blue|refine log/.test(lower)) return "monitor";
  return null;
}

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function ChatInteractivePanel({ siteId }: Props) {
  const { t } = useLang();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function appendMsg(msg: ChatMessage) {
    setMessages((prev) => [...prev, msg]);
  }

  // ─── Ollama streaming call ────────────────────────────────────────────────
  async function callOllama(userText: string, history: ChatMessage[]) {
    const agentId = uid();
    // Add empty agent message first so streaming fills it in
    setMessages((prev) => [
      ...prev,
      { id: agentId, role: "agent", text: "", timestamp: new Date().toISOString() },
    ]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText, history }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: "ไม่สามารถเชื่อมต่อ Ollama ได้" }));
        setMessages((prev) =>
          prev.map((m) =>
            m.id === agentId
              ? { ...m, text: `⚠️ ${String(err.error || "Ollama error")}` }
              : m
          )
        );
        return;
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        setMessages((prev) =>
          prev.map((m) =>
            m.id === agentId ? { ...m, text: m.text + chunk } : m
          )
        );
      }
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === agentId
            ? { ...m, text: "⚠️ Ollama ไม่พร้อมใช้งาน กรุณารัน `ollama serve` แล้วลองใหม่" }
            : m
        )
      );
    }
  }

  // ─── Submit ───────────────────────────────────────────────────────────────
  async function handleSubmit() {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");

    const userMsg: ChatMessage = { id: uid(), role: "user", text, timestamp: new Date().toISOString() };
    const prevMessages = [...messages];
    appendMsg(userMsg);

    const intent = detectActionIntent(text);

    if (intent === "scan") {
      // Real API action
      setLoading(true);
      try {
        const targetId = siteId || "demo-duck-sec-ai-01";
        const res = await runSiteRedScan(targetId, { scan_type: "full" });
        appendMsg({
          id: uid(),
          role: "agent",
          text: `Scout Agent เริ่ม Scan แล้วค่ะ 🔍\n\nScan ID: ${res.scan_id}\nStatus: ${res.status}\n\n${res.ai_summary ?? "กำลังวิเคราะห์ผล..."}`,
          timestamp: new Date().toISOString(),
        });
      } catch {
        appendMsg({ id: uid(), role: "agent", text: "⚠️ Scout Agent ไม่สามารถเริ่ม Scan ได้ในขณะนี้", timestamp: new Date().toISOString() });
      } finally {
        setLoading(false);
      }
    } else if (intent === "monitor") {
      // Real API action
      setLoading(true);
      try {
        const targetId = siteId || "demo-duck-sec-ai-01";
        const res = await fetchSiteBlueEvents(targetId, 10);
        const count = res.count ?? 0;
        const top = res.rows?.[0];
        appendMsg({
          id: uid(),
          role: "agent",
          text: `Guardian Agent ตรวจพบ Event ล่าสุด ${count} รายการ 👁️${
            top
              ? `\n\nEvent ล่าสุด: ${top.event_type}\nSource IP: ${top.source_ip}\nAI Severity: ${top.ai_severity}\nคำแนะนำ: ${top.ai_recommendation}`
              : "\n\nไม่พบ Event ผิดปกติ ✅"
          }`,
          timestamp: new Date().toISOString(),
        });
      } catch {
        appendMsg({ id: uid(), role: "agent", text: "⚠️ Guardian Agent ไม่สามารถดึงข้อมูล Event ได้", timestamp: new Date().toISOString() });
      } finally {
        setLoading(false);
      }
    } else {
      // General question → Ollama with system context
      setLoading(true);
      await callOllama(text, prevMessages);
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <div className="card flex flex-col" style={{ height: "100%" }}>
      <div className="px-5 pt-5 pb-3 border-b border-[var(--card-border)]">
        <p className="text-xs uppercase tracking-[0.26em] text-accent">{t("chat.header.eyebrow")}</p>
        <h3 className="mt-1 text-base font-semibold text-ink">{t("chat.header.title")}</h3>
        <p className="mt-0.5 text-[11px] text-slate-400">{t("chat.header.sub")}</p>
      </div>

      {/* Message / Eyes area */}
      <div className="flex-1 overflow-y-auto px-4 flex flex-col" style={{ minHeight: 0 }}>
        {messages.length === 0 && !loading ? (
          <div className="ai-eyes-chat-empty flex-1">
            <AIEyes />
            <p className="ai-eyes-hint">{t("chat.empty.title")}</p>
            <p className="ai-eyes-hint-sub">{t("chat.empty.body")}</p>
          </div>
        ) : (
          <div className="chat-messages py-3">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={msg.role === "user" ? "chat-bubble-user" : "chat-bubble-agent"}
                style={{ whiteSpace: "pre-wrap" }}
              >
                {msg.text || (
                  // Empty agent message = streaming in progress
                  <div className="chat-typing">
                    <span /><span /><span />
                  </div>
                )}
              </div>
            ))}
            {/* Loading indicator for action intents */}
            {loading && messages[messages.length - 1]?.role === "user" && (
              <div className="chat-bubble-agent">
                <div className="chat-typing">
                  <span /><span /><span />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      {/* Single-line input */}
      <div className="px-4 pb-4 pt-3 border-t border-[var(--card-border)]">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t("chat.placeholder")}
            disabled={loading}
            className="flex-1 rounded-2xl border border-[var(--card-border)] bg-[var(--muted-surface)] px-4 py-2.5 text-sm text-ink outline-none focus:border-accent transition-colors disabled:opacity-50"
          />
          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={loading || !input.trim()}
            className="flex-shrink-0 h-10 w-10 rounded-2xl bg-accent text-white flex items-center justify-center hover:opacity-90 disabled:opacity-40 transition-opacity"
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 2 11 13M22 2 15 22l-4-9-9-4 20-7Z" />
            </svg>
          </button>
        </div>
        <p className="mt-1.5 text-[10px] text-slate-400">{t("chat.hints")}</p>
      </div>
    </div>
  );
}
