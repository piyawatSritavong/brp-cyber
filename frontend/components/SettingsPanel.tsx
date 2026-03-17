"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchSites, upsertSite, upsertSiteCoworkerDeliveryProfile } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";
import { EmptyStateCard } from "@/components/EmptyStateCard";
import type { SiteRow } from "@/lib/types";

type Tab = "alerts" | "connections" | "integrations" | "system";

// ─── Alert Channels ────────────────────────────────────────────────────────
function AlertChannelsTab({ sites }: { sites: SiteRow[] }) {
  const [selectedSiteId, setSelectedSiteId] = useState(sites[0]?.site_id ?? "");
  const [slackWebhook, setSlackWebhook] = useState("");
  const [lineToken, setLineToken] = useState("");
  const [telegramToken, setTelegramToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  async function handleSave() {
    if (!selectedSiteId) { setError("กรุณาเลือก Site ก่อน"); return; }
    setSaving(true);
    setError("");
    try {
      const promises = [];
      if (slackWebhook) {
        promises.push(
          upsertSiteCoworkerDeliveryProfile(selectedSiteId, {
            channel: "webhook",
            webhook_url: slackWebhook,
            enabled: true,
            include_thai_summary: true,
          })
        );
      }
      if (lineToken || telegramToken) {
        promises.push(
          upsertSiteCoworkerDeliveryProfile(selectedSiteId, {
            channel: lineToken ? "line" : "telegram",
            enabled: true,
            include_thai_summary: true,
          })
        );
      }
      await Promise.all(promises);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "save_failed");
    } finally {
      setSaving(false);
    }
  }

  const inputClass = "w-full rounded-xl border border-[var(--card-border)] bg-[var(--muted-surface)] px-4 py-2.5 text-sm text-ink outline-none focus:border-accent transition-colors";

  return (
    <div className="space-y-5">
      <div className="card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-ink">Alert Channels</h3>
        <p className="text-xs text-slate-400">ตั้งค่าช่องทางรับ Notification จาก AI Agent เมื่อเกิดเหตุการณ์สำคัญ</p>

        {sites.length > 0 && (
          <label className="flex items-center gap-2 rounded-xl border border-[var(--card-border)] bg-[var(--muted-surface)] px-3 py-2 text-xs text-slate-500">
            Site
            <select
              value={selectedSiteId}
              onChange={(e) => setSelectedSiteId(e.target.value)}
              className="min-w-[160px] bg-transparent text-sm font-medium text-ink outline-none"
            >
              {sites.map((s) => (
                <option key={s.site_id} value={s.site_id}>{s.display_name}</option>
              ))}
            </select>
          </label>
        )}

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-ink mb-1.5">
              Slack Webhook URL
            </label>
            <input
              type="url"
              value={slackWebhook}
              onChange={(e) => setSlackWebhook(e.target.value)}
              placeholder="https://hooks.slack.com/services/…"
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-ink mb-1.5">
              LINE Notify Token
            </label>
            <input
              type="text"
              value={lineToken}
              onChange={(e) => setLineToken(e.target.value)}
              placeholder="LINE Notify Token (จาก notify.line.me)"
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-ink mb-1.5">
              Telegram Bot Token
            </label>
            <input
              type="text"
              value={telegramToken}
              onChange={(e) => setTelegramToken(e.target.value)}
              placeholder="1234567890:ABCdefGHI… (จาก @BotFather)"
              className={inputClass}
            />
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-xs text-red-600">{error}</div>
        )}

        <button
          type="button"
          onClick={() => void handleSave()}
          disabled={saving}
          className="rounded-xl bg-accent px-5 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-40 transition-opacity"
        >
          {saving ? "Saving…" : saved ? "✓ Saved!" : "Save Alert Settings"}
        </button>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-semibold text-ink mb-2">Test Notification</h3>
        <p className="text-xs text-slate-400 mb-3">ส่ง Test Notification ผ่านทุกช่องทางที่ตั้งค่าไว้</p>
        <button
          type="button"
          className="rounded-xl border border-accent px-4 py-2 text-xs font-semibold text-accent hover:bg-accent hover:text-white transition-all"
        >
          Send Test Notification
        </button>
      </div>
    </div>
  );
}

// ─── Connections ───────────────────────────────────────────────────────────
function ConnectionsTab({ sites, onRefresh }: { sites: SiteRow[]; onRefresh: () => void }) {
  const [showForm, setShowForm] = useState(false);
  const [tenantCode, setTenantCode] = useState("tenant-01");
  const [siteCode, setSiteCode] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleAdd() {
    if (!siteCode || !displayName || !baseUrl) { setError("กรุณากรอกข้อมูลให้ครบ"); return; }
    setSaving(true);
    setError("");
    try {
      await upsertSite({ tenant_code: tenantCode, site_code: siteCode, display_name: displayName, base_url: baseUrl, is_active: true });
      setShowForm(false);
      setSiteCode("");
      setDisplayName("");
      setBaseUrl("");
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "add_failed");
    } finally {
      setSaving(false);
    }
  }

  const inputClass = "w-full rounded-xl border border-[var(--card-border)] bg-[var(--muted-surface)] px-4 py-2.5 text-sm text-ink outline-none focus:border-accent transition-colors";

  return (
    <div className="space-y-4">
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-ink">Client Connections</h3>
            <p className="text-xs text-slate-400 mt-0.5">เว็บไซต์และระบบของลูกค้าที่เชื่อมต่ออยู่</p>
          </div>
          <button
            type="button"
            onClick={() => setShowForm(!showForm)}
            className="rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-white hover:opacity-90"
          >
            + Add Site
          </button>
        </div>

        {showForm && (
          <div className="mb-4 rounded-xl border border-[var(--card-border)] bg-[var(--muted-surface)] p-4 space-y-3">
            <p className="text-xs font-semibold text-ink">New Site Connection</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <input type="text" value={tenantCode} onChange={(e) => setTenantCode(e.target.value)} placeholder="Tenant Code" className={inputClass} />
              <input type="text" value={siteCode} onChange={(e) => setSiteCode(e.target.value)} placeholder="Site Code (e.g. site-01)" className={inputClass} />
              <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Display Name" className={inputClass} />
              <input type="url" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="Base URL (https://…)" className={inputClass} />
            </div>
            {error && <p className="text-xs text-red-500">{error}</p>}
            <div className="flex gap-2">
              <button type="button" onClick={() => void handleAdd()} disabled={saving} className="rounded-xl bg-accent px-4 py-2 text-xs font-semibold text-white disabled:opacity-40">
                {saving ? "Adding…" : "Add Connection"}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="rounded-xl border border-[var(--card-border)] px-4 py-2 text-xs font-medium text-slate-500">
                Cancel
              </button>
            </div>
          </div>
        )}

        {sites.length === 0 ? (
          <EmptyStateCard icon="settings" title="ยังไม่มี Site" body="กด '+ Add Site' เพื่อเพิ่มเว็บไซต์ลูกค้าตัวแรก" size="sm" />
        ) : (
          <div className="space-y-2">
            {sites.map((s) => (
              <div key={s.site_id} className="flex items-center gap-3 rounded-xl border border-[var(--card-border)] bg-[var(--muted-surface)] px-4 py-3">
                <span className={`agent-dot ${s.is_active ? "agent-dot-green" : ""}`} style={!s.is_active ? { background: "#94a3b8" } : {}} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-ink truncate">{s.display_name}</p>
                  <p className="text-xs text-slate-400 truncate">{s.base_url} · {s.site_code}</p>
                </div>
                <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${s.is_active ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                  {s.is_active ? "Active" : "Inactive"}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Integrations ──────────────────────────────────────────────────────────
const PLUGIN_CATALOG = [
  { code: "blue_thai_alert_translator", label: "Thai Alert Translator", color: "#006FEE", tag: "Blue", desc: "แปล Alert จาก CrowdStrike/SentinelOne เป็นภาษาไทย" },
  { code: "blue_auto_playbook_executor", label: "Auto-Playbook Executor", color: "#006FEE", tag: "Blue", desc: "Block Firewall / Clear Session อัตโนมัติจาก SIEM webhook" },
  { code: "blue_log_refiner", label: "AI Log Refiner", color: "#006FEE", tag: "Blue", desc: "กรอง Log ขยะ 95% เหลือเฉพาะ Alert ที่เสี่ยงจริง" },
  { code: "red_template_writer", label: "Nuclei AI-Template Writer", color: "#f31260", tag: "Red", desc: "เขียน Nuclei YAML template จากข่าวช่องโหว่ภายใน 1 ชั่วโมง" },
  { code: "red_exploit_code_generator", label: "Exploit Code Generator", color: "#f31260", tag: "Red", desc: "แปลง CVE เป็น Python exploit script สำหรับทดสอบ" },
  { code: "purple_incident_ghostwriter", label: "Incident Report Ghostwriter", color: "#9353d3", tag: "Purple", desc: "ร่าง Incident Report ตามฟอร์แมต สกมช. โดยอัตโนมัติ" },
  { code: "purple_mitre_heatmap", label: "MITRE ATT&CK Heatmap", color: "#9353d3", tag: "Purple", desc: "สร้าง Heatmap จาก Log เพื่อแสดง Blind Spot ขององค์กร" },
];

function IntegrationsTab({ sites }: { sites: SiteRow[] }) {
  const [selectedSiteId, setSelectedSiteId] = useState(sites[0]?.site_id ?? "");
  const [enabled, setEnabled] = useState<Record<string, boolean>>({
    blue_thai_alert_translator: true,
    blue_log_refiner: true,
  });
  const [saved, setSaved] = useState(false);

  function togglePlugin(code: string) {
    setEnabled((prev) => ({ ...prev, [code]: !prev[code] }));
  }

  function handleSave() {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="space-y-4">
      <div className="card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-ink">Plugin Activation</h3>
        <p className="text-xs text-slate-400">เปิด/ปิด Plugin แต่ละตัวสำหรับ Site ที่เลือก</p>

        {sites.length > 0 && (
          <label className="flex items-center gap-2 rounded-xl border border-[var(--card-border)] bg-[var(--muted-surface)] px-3 py-2 text-xs text-slate-500">
            Site
            <select
              value={selectedSiteId}
              onChange={(e) => setSelectedSiteId(e.target.value)}
              className="min-w-[160px] bg-transparent text-sm font-medium text-ink outline-none"
            >
              {sites.map((s) => (
                <option key={s.site_id} value={s.site_id}>{s.display_name}</option>
              ))}
            </select>
          </label>
        )}

        <div className="space-y-2">
          {PLUGIN_CATALOG.map((p) => {
            const on = enabled[p.code] ?? false;
            return (
              <div key={p.code} className="flex items-center gap-3 rounded-xl border border-[var(--card-border)] bg-[var(--muted-surface)] px-4 py-3">
                <span
                  className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full text-white flex-shrink-0"
                  style={{ background: p.color }}
                >
                  {p.tag}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-ink">{p.label}</p>
                  <p className="text-xs text-slate-400 truncate">{p.desc}</p>
                </div>
                <button
                  type="button"
                  onClick={() => togglePlugin(p.code)}
                  className={`toggle-track flex-shrink-0 ${on ? "toggle-track-on" : ""}`}
                  aria-label={`Toggle ${p.label}`}
                >
                  <span className="toggle-thumb" />
                </button>
              </div>
            );
          })}
        </div>

        <button
          type="button"
          onClick={handleSave}
          className="rounded-xl bg-accent px-5 py-2 text-sm font-semibold text-white hover:opacity-90 transition-opacity"
        >
          {saved ? "✓ Saved!" : "Save Plugin Settings"}
        </button>
      </div>

      <div className="card p-5 space-y-3">
        <h3 className="text-sm font-semibold text-ink">External Integrations</h3>
        <p className="text-xs text-slate-400">เชื่อมต่อกับเครื่องมือ Security ภายนอก</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {[
            { name: "Splunk", desc: "SIEM log forwarding", status: "available" },
            { name: "CrowdStrike", desc: "EDR alert sync", status: "available" },
            { name: "SentinelOne", desc: "Endpoint detection", status: "available" },
            { name: "Slack / LINE", desc: "Alert notifications", status: "active" },
          ].map((i) => (
            <div key={i.name} className="flex items-center gap-3 rounded-xl border border-[var(--card-border)] bg-[var(--muted-surface)] px-4 py-3">
              <span className={`agent-dot ${i.status === "active" ? "agent-dot-green" : ""}`} style={i.status !== "active" ? { background: "#94a3b8" } : {}} />
              <div>
                <p className="text-sm font-semibold text-ink">{i.name}</p>
                <p className="text-xs text-slate-400">{i.desc}</p>
              </div>
              <span className={`ml-auto text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${i.status === "active" ? "bg-green-100 text-green-700" : "bg-slate-100 text-slate-500"}`}>
                {i.status === "active" ? "Active" : "Setup"}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── System ────────────────────────────────────────────────────────────────
function SystemTab() {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "demo">("checking");

  useEffect(() => {
    fetch(`${apiBase}/sites?limit=1`, { cache: "no-store" })
      .then((r) => setApiStatus(r.ok ? "online" : "demo"))
      .catch(() => setApiStatus("demo"));
  }, [apiBase]);

  return (
    <div className="space-y-4">
      <div className="card p-5 space-y-4">
        <h3 className="text-sm font-semibold text-ink">System Preferences</h3>

        <div className="flex items-center justify-between py-3 border-b border-[var(--card-border)]">
          <div>
            <p className="text-sm font-medium text-ink">Theme</p>
            <p className="text-xs text-slate-400">สลับระหว่าง Light / Dark mode</p>
          </div>
          <ThemeToggle />
        </div>

        <div className="flex items-center justify-between py-3 border-b border-[var(--card-border)]">
          <div>
            <p className="text-sm font-medium text-ink">Backend API</p>
            <p className="text-xs text-slate-400 font-mono">{apiBase}</p>
          </div>
          {apiStatus === "checking" && (
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 bg-slate-100 border border-slate-200 rounded-full px-3 py-1">
              <span className="agent-dot agent-dot-yellow" style={{ width: 6, height: 6 }} />
              Checking…
            </span>
          )}
          {apiStatus === "online" && (
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-green-700 bg-green-50 border border-green-200 rounded-full px-3 py-1">
              <span className="agent-dot agent-dot-green" style={{ width: 6, height: 6 }} />
              Connected
            </span>
          )}
          {apiStatus === "demo" && (
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-full px-3 py-1">
              <span className="agent-dot" style={{ width: 6, height: 6, background: "#006FEE" }} />
              Demo Mode
            </span>
          )}
        </div>

        <div className="flex items-center justify-between py-3">
          <div>
            <p className="text-sm font-medium text-ink">Platform Version</p>
            <p className="text-xs text-slate-400">BRP Cyber Co-worker · Phase 114</p>
          </div>
          <span className="text-xs text-slate-400 bg-slate-100 rounded-full px-3 py-1">v1.14.0</span>
        </div>
      </div>

      <div className="card p-5 space-y-3">
        <h3 className="text-sm font-semibold text-ink">Control Plane</h3>
        <p className="text-xs text-slate-400">
          Governance token, audit logs, และ policy controls จัดการผ่าน Settings → Integrations
        </p>
      </div>
    </div>
  );
}

// ─── Main Settings Panel ───────────────────────────────────────────────────
export function SettingsPanel() {
  const [activeTab, setActiveTab] = useState<Tab>("alerts");
  const [sites, setSites] = useState<SiteRow[]>([]);

  const loadSites = useCallback(async () => {
    try {
      const res = await fetchSites("", 300);
      setSites(res.rows || []);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => { void loadSites(); }, [loadSites]);

  const TABS: { id: Tab; label: string }[] = [
    { id: "alerts", label: "Alert Channels" },
    { id: "connections", label: "Connections" },
    { id: "integrations", label: "Integrations" },
    { id: "system", label: "System" },
  ];

  return (
    <main className="space-y-5">
      <section className="card p-5">
        <p className="text-xs uppercase tracking-[0.26em] text-accent">System Configuration</p>
        <h2 className="mt-1 text-[1.85rem] font-semibold text-ink">Settings</h2>
        <p className="mt-1 text-sm text-slate-500">Alert channels, client connections, and system preferences</p>
      </section>

      <div className="flex gap-2 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setActiveTab(t.id)}
            className={`settings-tab ${activeTab === t.id ? "settings-tab-active" : ""}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === "alerts" && <AlertChannelsTab sites={sites} />}
      {activeTab === "connections" && <ConnectionsTab sites={sites} onRefresh={loadSites} />}
      {activeTab === "integrations" && <IntegrationsTab sites={sites} />}
      {activeTab === "system" && <SystemTab />}
    </main>
  );
}
