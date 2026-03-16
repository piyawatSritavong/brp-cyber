"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { ThemeToggle } from "@/components/ThemeToggle";

type MenuItem = {
  label: string;
  href: string;
  icon: ReactNode;
  exact?: boolean;
};

const PAGE_META: Record<string, { eyebrow: string; title: string; description: string }> = {
  "/": {
    eyebrow: "Cyber AI Co-worker",
    title: "Dashboard",
    description: "Overview of tenant posture, governance signals, and shared operations context.",
  },
  "/configuration": {
    eyebrow: "Control Plane Setup",
    title: "Configuration",
    description: "Manage sites, integration adapters, and objective-scope bootstrap controls.",
  },
  "/red-service": {
    eyebrow: "Red Service Category",
    title: "Red Service",
    description: "Continuous validation, exploit path testing, and autonomous red execution.",
  },
  "/blue-service": {
    eyebrow: "Blue Service Category",
    title: "Blue Service",
    description: "Detection, response, SecOps automation, and reliability operations.",
  },
  "/purple-service": {
    eyebrow: "Purple Service Category",
    title: "Purple Service",
    description: "Correlation, compliance mapping, and executive reporting workflows.",
  },
  "/red-plugin": {
    eyebrow: "Red Plugin Category",
    title: "Red Plugin",
    description: "Template generation, exploit draft output, and Red plugin delivery operations.",
  },
  "/blue-plugin": {
    eyebrow: "Blue Plugin Category",
    title: "Blue Plugin",
    description: "Alert translation, playbook execution plugins, and Blue plugin delivery operations.",
  },
  "/purple-plugin": {
    eyebrow: "Purple Plugin Category",
    title: "Purple Plugin",
    description: "Heatmap/report plugins and Purple plugin delivery operations.",
  },
};

const MENU_GROUPS: Array<{ label: string; items: MenuItem[] }> = [
  {
    label: "Menu",
    items: [
      { label: "Dashboard", href: "/", exact: true, icon: <MenuIcon kind="grid" /> },
      { label: "Configuration", href: "/configuration", exact: true, icon: <MenuIcon kind="settings" /> },
    ],
  },
  {
    label: "Service Categories",
    items: [
      { label: "Red Service", href: "/red-service", exact: true, icon: <MenuIcon kind="bolt" /> },
      { label: "Blue Service", href: "/blue-service", exact: true, icon: <MenuIcon kind="shield" /> },
      { label: "Purple Service", href: "/purple-service", exact: true, icon: <MenuIcon kind="pulse" /> },
    ],
  },
  {
    label: "Plugin Categories",
    items: [
      { label: "Red Plugin", href: "/red-plugin", exact: true, icon: <MenuIcon kind="bolt" /> },
      { label: "Blue Plugin", href: "/blue-plugin", exact: true, icon: <MenuIcon kind="shield" /> },
      { label: "Purple Plugin", href: "/purple-plugin", exact: true, icon: <MenuIcon kind="pulse" /> },
    ],
  },
];

function MenuIcon({ kind }: { kind: "grid" | "settings" | "bolt" | "shield" | "pulse" | "plug" | "send" }) {
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
  };

  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      {paths[kind]}
    </svg>
  );
}

function isActive(pathname: string, item: MenuItem) {
  const basePath = item.href.split("#")[0] || "/";
  if (item.exact) {
    return pathname === basePath;
  }
  if (basePath === "/") {
    return pathname === "/";
  }
  return pathname.startsWith(basePath);
}

export function AppChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const pageMeta = PAGE_META[pathname] || PAGE_META["/"];

  return (
    <div className="app-layout">
      <aside className="app-sidebar">
        <div className="app-brand">
          <div className="brand-mark" aria-hidden="true">
            <span />
            <span />
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.36em] text-[var(--sidebar-muted)]">BRP Cyber</p>
            <h2 className="mt-2 text-[1.7rem] font-semibold tracking-tight text-white">Co-worker</h2>
            <p className="mt-1 text-xs leading-5 text-[var(--sidebar-muted)]">
              Plugin-first security operations for Thai enterprise workflows.
            </p>
          </div>
        </div>

        <nav className="mt-8 space-y-7">
          {MENU_GROUPS.map((group) => (
            <div key={group.label}>
              <p className="sidebar-section-label">{group.label}</p>
              <div className="mt-3 space-y-2">
                {group.items.map((item) => {
                  const active = isActive(pathname, item);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`sidebar-link ${active ? "sidebar-link-active" : ""}`}
                      aria-current={active ? "page" : undefined}
                    >
                      <span className="sidebar-link-icon">{item.icon}</span>
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      <div className="app-page">
        <header className="app-topbar">
          <div>
            <p className="app-topbar-eyebrow">{pageMeta.eyebrow}</p>
            <h1>{pageMeta.title}</h1>
            <p>{pageMeta.description}</p>
          </div>
          <div className="app-topbar-actions">
            <button
              type="button"
              className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-slate-200 bg-white text-[#110B0A] shadow-sm hover:border-[#F76C45]"
              title="Notifications"
            >
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 17h5l-1.4-1.4A2 2 0 0 1 18 14.2V11a6 6 0 1 0-12 0v3.2a2 2 0 0 1-.6 1.4L4 17h5" />
                <path d="M10 17a2 2 0 0 0 4 0" />
              </svg>
            </button>
            <ThemeToggle />
            <div className="app-identity">
              <div className="app-identity-avatar">AI</div>
              <div>
                <p className="app-identity-name">Security Operator</p>
                <p className="app-identity-role">Plugin-first orchestration</p>
              </div>
            </div>
          </div>
        </header>
        <div className="app-content">{children}</div>
      </div>
    </div>
  );
}
