"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LangProvider, useLang, type TKey } from "@/contexts/LangContext";
import { fetchSites } from "@/lib/api";

// ─── Types ─────────────────────────────────────────────────────────────────
type MenuItem = {
  labelKey: string;
  href: string;
  icon: ReactNode;
  exact?: boolean;
  showBadge?: boolean;
};

// ─── Menu Groups ────────────────────────────────────────────────────────────
const MENU_GROUPS: Array<{ labelKey: TKey; items: MenuItem[] }> = [
  {
    labelKey: "menu.group.menu",
    items: [
      { labelKey: "page./.title", href: "/", exact: true, icon: <MenuIcon kind="command" /> },
      { labelKey: "page./dashboard.title", href: "/dashboard", exact: true, icon: <MenuIcon kind="grid" /> },
      { labelKey: "page./reports.title", href: "/reports", exact: true, icon: <MenuIcon kind="pulse" /> },
    ],
  },
  {
    labelKey: "menu.group.tools",
    items: [
      { labelKey: "page./plugins.title", href: "/plugins", exact: true, icon: <MenuIcon kind="plug" />, showBadge: true },
      { labelKey: "page./code.title", href: "/code", exact: true, icon: <MenuIcon kind="code" /> },
      { labelKey: "page./n8n-agents.title", href: "/n8n-agents", exact: true, icon: <MenuIcon kind="n8n" /> },
    ],
  },
  {
    labelKey: "menu.group.config",
    items: [
      { labelKey: "page./agents.title", href: "/agents", exact: true, icon: <MenuIcon kind="agents" /> },
      { labelKey: "page./settings.title", href: "/settings", exact: true, icon: <MenuIcon kind="settings" /> },
    ],
  },
];

// ─── Sidebar agent status cycles ───────────────────────────────────────────
const SIDEBAR_AGENT_CYCLES = [
  ["Currently scanning port 443 for Network A", "Monitoring NAS traffic. No anomalies detected"],
  ["Shadow pentest: crawling /api/auth endpoints", "Detected unusual login attempts — investigating"],
  ["Validating CVE-2024-3094 on Vercel deployment", "Log refiner active — filtering 1,240 events"],
  ["Exploit autopilot idle — next sweep in 12 min", "Guardian: All clear ✅ Zero anomalies past 1h"],
];

// ─── Icons ──────────────────────────────────────────────────────────────────
function MenuIcon({
  kind,
}: {
  kind: "grid" | "settings" | "bolt" | "shield" | "pulse" | "plug" | "send" | "command" | "code" | "agents" | "n8n";
}) {
  const paths: Record<typeof kind, ReactNode> = {
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </>
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="3.5" />
        <path d="M12 2.75v2.5M12 18.75v2.5M21.25 12h-2.5M5.25 12h-2.5M18.54 5.46l-1.77 1.77M7.23 16.77l-1.77 1.77M18.54 18.54l-1.77-1.77M7.23 7.23 5.46 5.46" />
      </>
    ),
    bolt: <path d="M13 2 5 13h5l-1 9 8-11h-5l1-9Z" />,
    shield: <path d="M12 3 5 6v5c0 5 2.98 8.67 7 10 4.02-1.33 7-5 7-10V6l-7-3Z" />,
    pulse: <path d="M3 13h4l2.4-5 4.2 10 2.8-5H21" />,
    plug: (
      <>
        <path d="M8 3v6M16 3v6M7 9h10v3a5 5 0 0 1-5 5 5 5 0 0 1-5-5V9Z" />
        <path d="M12 17v4" />
      </>
    ),
    send: <path d="M3 11.5 21 3l-4.8 18-4.23-6.35L3 11.5Z" />,
    command: <path d="M4 17l6-6-6-6M12 19h8" />,
    code: (
      <>
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
      </>
    ),
    agents: (
      <>
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </>
    ),
    n8n: (
      <>
        <circle cx="5" cy="12" r="2.5" />
        <circle cx="19" cy="6" r="2.5" />
        <circle cx="19" cy="18" r="2.5" />
        <path d="M7.5 12h4l2-6M7.5 12l2 6h4" />
      </>
    ),
  };

  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[kind]}
    </svg>
  );
}

function isActive(pathname: string, item: MenuItem) {
  const basePath = item.href.split("#")[0] || "/";
  if (item.exact) return pathname === basePath;
  if (basePath === "/") return pathname === "/";
  return pathname.startsWith(basePath);
}

// ─── Inner shell (uses lang context) ────────────────────────────────────────
function AppChromeShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { lang, toggle, t } = useLang();

  // Page metadata using translations
  const pageMeta = {
    eyebrow: t((`page.${pathname}.eyebrow` as TKey) in Object.keys({}) ? (`page.${pathname}.eyebrow` as TKey) : "page./.eyebrow"),
    title: t((`page.${pathname}.title` as TKey) in Object.keys({}) ? (`page.${pathname}.title` as TKey) : "page./.title"),
    description: t((`page.${pathname}.desc` as TKey) in Object.keys({}) ? (`page.${pathname}.desc` as TKey) : "page./.desc"),
  };

  // Use a lookup for page meta
  const pageMetaLookup: Record<string, { eyebrow: string; title: string; description: string }> = {
    "/": { eyebrow: t("page./.eyebrow"), title: t("page./.title"), description: t("page./.desc") },
    "/dashboard": { eyebrow: t("page./dashboard.eyebrow"), title: t("page./dashboard.title"), description: t("page./dashboard.desc") },
    "/reports": { eyebrow: t("page./reports.eyebrow"), title: t("page./reports.title"), description: t("page./reports.desc") },
    "/plugins": { eyebrow: t("page./plugins.eyebrow"), title: t("page./plugins.title"), description: t("page./plugins.desc") },
    "/code": { eyebrow: t("page./code.eyebrow"), title: t("page./code.title"), description: t("page./code.desc") },
    "/agents": { eyebrow: t("page./agents.eyebrow"), title: t("page./agents.title"), description: t("page./agents.desc") },
    "/settings": { eyebrow: t("page./settings.eyebrow"), title: t("page./settings.title"), description: t("page./settings.desc") },
    "/n8n-agents": { eyebrow: t("page./n8n-agents.eyebrow"), title: t("page./n8n-agents.title"), description: t("page./n8n-agents.desc") },
  };
  const currentMeta = pageMetaLookup[pathname] ?? pageMetaLookup["/"];
  void pageMeta; // suppress unused variable

  // Live agent status cycling
  const [agentCycleIdx, setAgentCycleIdx] = useState(0);
  const [pluginCount, setPluginCount] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setAgentCycleIdx((i) => (i + 1) % SIDEBAR_AGENT_CYCLES.length);
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    fetchSites("", 50)
      .then((res) => {
        setPluginCount(res.rows.filter((s) => s.is_active).length);
      })
      .catch(() => setPluginCount(3));
  }, []);

  const agentLines = SIDEBAR_AGENT_CYCLES[agentCycleIdx] ?? SIDEBAR_AGENT_CYCLES[0];

  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <div className="app-brand">
          <div className="brand-mark" aria-hidden="true">
            <span />
            <span />
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.36em] text-[var(--sidebar-muted)]">{t("brand.sub")}</p>
            <h2 className="mt-2 text-[1.7rem] font-semibold tracking-tight text-white">{t("brand.title")}</h2>
            <p className="mt-1 text-xs leading-5 text-[var(--sidebar-muted)]">{t("brand.desc")}</p>
          </div>
        </div>

        <nav className="mt-8 space-y-7">
          {MENU_GROUPS.map((group) => (
            <div key={group.labelKey}>
              <p className="sidebar-section-label">{t(group.labelKey)}</p>
              <div className="mt-3 space-y-1">
                {group.items.map((item) => {
                  const active = isActive(pathname, item);
                  const isOrchestrator = item.href === "/";
                  return (
                    <div key={item.href}>
                      <Link
                        href={item.href}
                        className={`sidebar-link ${active ? "sidebar-link-active" : ""}`}
                        aria-current={active ? "page" : undefined}
                      >
                        <span className="sidebar-link-icon">{item.icon}</span>
                        <span className="flex-1">{t(item.labelKey as TKey)}</span>
                        {item.showBadge && pluginCount > 0 && (
                          <span className="agent-badge-active">
                            <span className="agent-dot agent-dot-green" style={{ width: 6, height: 6 }} />
                            {pluginCount}
                          </span>
                        )}
                      </Link>

                      {isOrchestrator && (
                        <div className="sidebar-agent-status">
                          <p className="sidebar-agent-line">
                            <span>Red Agent:</span> {agentLines[0]}
                          </p>
                          <p className="sidebar-agent-line">
                            <span>Blue Agent:</span> {agentLines[1]}
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="app-sidebar-footer">
          <p className="sidebar-section-label">Support</p>
          <div className="mt-3 mx-4 rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="flex items-center gap-2 mb-1">
              <span className="agent-dot agent-dot-green" />
              <p className="text-sm font-medium text-white">{t("support.title")}</p>
            </div>
            <p className="text-xs leading-5 text-[var(--sidebar-muted)]">{t("support.body")}</p>
          </div>
        </div>
      </aside>

      <div className="app-page">
        <header className="app-topbar">
          <div>
            <p className="app-topbar-eyebrow">{currentMeta.eyebrow}</p>
            <h1>{currentMeta.title}</h1>
            <p>{currentMeta.description}</p>
          </div>
          <div className="app-topbar-actions">
            {/* Language Toggle */}
            <button
              type="button"
              onClick={toggle}
              title="Switch language"
              className="inline-flex h-11 items-center justify-center rounded-2xl border border-slate-200 bg-white px-3.5 text-xs font-bold tracking-widest text-[#110B0A] shadow-sm hover:border-[#F76C45] hover:text-[#F76C45] transition-colors gap-1"
            >
              <span className={lang === "th" ? "text-accent" : "text-slate-400"}>TH</span>
              <span className="text-slate-300">/</span>
              <span className={lang === "en" ? "text-accent" : "text-slate-400"}>EN</span>
            </button>

            {/* Bell notification */}
            <button
              type="button"
              className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-[#110B0A] shadow-sm hover:border-[#F76C45]"
              title={t("notif.tooltip")}
            >
              <svg
                viewBox="0 0 24 24"
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 1 0-12 0v3.2a2 2 0 0 1-.6 1.4L4 17h5" />
                <path d="M10 17a2 2 0 0 0 4 0" />
              </svg>
            </button>
          </div>
        </header>
        <div className="app-content">{children}</div>
      </div>
    </div>
  );
}

// ─── AppChrome (public export wraps with LangProvider) ─────────────────────
export function AppChrome({ children }: { children: ReactNode }) {
  return (
    <LangProvider>
      <AppChromeShell>{children}</AppChromeShell>
    </LangProvider>
  );
}
