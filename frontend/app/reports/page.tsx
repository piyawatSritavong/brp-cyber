"use client";

import { useCallback, useEffect, useState } from "react";
import { PurpleReportsPanel } from "@/components/PurpleReportsPanel";
import { RedTeamPanel } from "@/components/RedTeamPanel";
import { BlueTeamPanel } from "@/components/BlueTeamPanel";
import { fetchSites } from "@/lib/api";
import type { SiteRow } from "@/lib/types";

type ServiceTab = "purple" | "red" | "blue";

const SERVICE_TABS: { id: ServiceTab; label: string; eyebrow: string; color: string }[] = [
  { id: "purple", label: "Reports & Compliance", eyebrow: "Purple Service", color: "#9353d3" },
  { id: "red", label: "Red Team / Pentest", eyebrow: "Red Service", color: "#f31260" },
  { id: "blue", label: "Blue Team / SOC", eyebrow: "Blue Service", color: "#006FEE" },
];

export default function ReportsPage() {
  const [sites, setSites] = useState<SiteRow[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState("");
  const [activeService, setActiveService] = useState<ServiceTab>("purple");

  const loadSites = useCallback(async () => {
    try {
      const res = await fetchSites("", 300);
      setSites(res.rows || []);
      if (!selectedSiteId && res.rows.length > 0) {
        setSelectedSiteId(res.rows[0].site_id);
      }
    } catch {
      // silent – empty state handled in panel
    }
  }, [selectedSiteId]);

  useEffect(() => {
    void loadSites();
  }, [loadSites]);

  const selectedSite = sites.find((s) => s.site_id === selectedSiteId) ?? null;
  const current = SERVICE_TABS.find((t) => t.id === activeService)!;

  return (
    <main className="space-y-6">
      <section className="card p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.26em]" style={{ color: current.color }}>
              {current.eyebrow}
            </p>
            <h2 className="mt-2 text-[1.9rem] font-semibold leading-tight text-ink">
              {current.label}
            </h2>
            <p className="mt-2 text-sm leading-7 text-slate-500">
              Correlation, compliance, pentest reports, SOC monitoring, and MITRE ATT&amp;CK heatmaps.
            </p>
          </div>
          {sites.length > 0 && (
            <label className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-panelAlt/50 px-3 py-2 text-xs text-slate-500">
              Site
              <select
                value={selectedSiteId}
                onChange={(e) => setSelectedSiteId(e.target.value)}
                className="min-w-[180px] bg-transparent text-sm font-medium text-ink outline-none"
              >
                {sites.map((s) => (
                  <option key={s.site_id} value={s.site_id}>
                    {s.display_name}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>

        {/* Service tab switcher */}
        <div className="mt-4 flex gap-2 flex-wrap">
          {SERVICE_TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setActiveService(t.id)}
              className="settings-tab"
              style={
                activeService === t.id
                  ? { borderColor: t.color, color: t.color, background: `${t.color}15` }
                  : {}
              }
            >
              {t.label}
            </button>
          ))}
        </div>
      </section>

      {activeService === "purple" && <PurpleReportsPanel selectedSite={selectedSite} />}

      {activeService === "red" && (
        <RedTeamPanel
          sites={sites}
          selectedSiteId={selectedSiteId}
          onSelectSite={setSelectedSiteId}
          canView
          canEditPolicy
          canApprove
        />
      )}

      {activeService === "blue" && (
        <BlueTeamPanel
          selectedSite={selectedSite}
          canView
          canEditPolicy
          canApprove
        />
      )}
    </main>
  );
}
