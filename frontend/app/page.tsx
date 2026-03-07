"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { GovernancePanel } from "@/components/GovernancePanel";
import { OverviewStats } from "@/components/OverviewStats";
import { TenantDetailPanel } from "@/components/TenantDetailPanel";
import { TenantTable } from "@/components/TenantTable";
import { RedTeamPanel } from "@/components/RedTeamPanel";
import { BlueTeamPanel } from "@/components/BlueTeamPanel";
import { PurpleReportsPanel } from "@/components/PurpleReportsPanel";
import { fetchDashboard, fetchGovernanceDashboard, fetchSites, fetchTenantGate, fetchTenantHistory, fetchTenantRemediation } from "@/lib/api";
import type {
  DashboardResponse,
  GovernanceDashboardResponse,
  SiteRow,
  TenantGateResponse,
  TenantHistoryResponse,
  TenantRemediation,
} from "@/lib/types";

export default function HomePage() {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");
  const [tenantGate, setTenantGate] = useState<TenantGateResponse | null>(null);
  const [tenantHistory, setTenantHistory] = useState<TenantHistoryResponse | null>(null);
  const [tenantRemediation, setTenantRemediation] = useState<TenantRemediation | null>(null);
  const [governance, setGovernance] = useState<GovernanceDashboardResponse | null>(null);
  const [loadingDashboard, setLoadingDashboard] = useState(false);
  const [loadingTenant, setLoadingTenant] = useState(false);
  const [loadingGovernance, setLoadingGovernance] = useState(false);
  const [sites, setSites] = useState<SiteRow[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState("");
  const [error, setError] = useState<string>("");
  const [governanceError, setGovernanceError] = useState<string>("");
  const [siteError, setSiteError] = useState<string>("");

  const loadDashboard = useCallback(async () => {
    setLoadingDashboard(true);
    setError("");
    try {
      const data = await fetchDashboard(200);
      setDashboard(data);
      if (!selectedTenantId && data.rows.length > 0) {
        setSelectedTenantId(data.rows[0].tenant_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "dashboard_load_failed");
    } finally {
      setLoadingDashboard(false);
    }
  }, [selectedTenantId]);

  const loadGovernance = useCallback(async () => {
    setLoadingGovernance(true);
    setGovernanceError("");
    try {
      const data = await fetchGovernanceDashboard(3000);
      setGovernance(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : "governance_load_failed";
      if (message.includes("403")) {
        setGovernanceError("Governance token invalid/expired. Generate new token and update frontend .env, then restart frontend.");
      } else {
        setGovernanceError(message);
      }
    } finally {
      setLoadingGovernance(false);
    }
  }, []);

  const loadTenantDetail = useCallback(async (tenantId: string) => {
    if (!tenantId) {
      return;
    }
    setLoadingTenant(true);
    setError("");
    try {
      const [gate, history, remediation] = await Promise.all([
        fetchTenantGate(tenantId),
        fetchTenantHistory(tenantId, 20),
        fetchTenantRemediation(tenantId),
      ]);
      setTenantGate(gate);
      setTenantHistory(history);
      setTenantRemediation(remediation);
    } catch (err) {
      setError(err instanceof Error ? err.message : "tenant_detail_load_failed");
    } finally {
      setLoadingTenant(false);
    }
  }, []);

  const loadSites = useCallback(async () => {
    setSiteError("");
    try {
      const response = await fetchSites("", 300);
      setSites(response.rows || []);
      if (!selectedSiteId && response.rows.length > 0) {
        setSelectedSiteId(response.rows[0].site_id);
      }
    } catch (err) {
      setSiteError(err instanceof Error ? err.message : "sites_load_failed");
    }
  }, [selectedSiteId]);

  useEffect(() => {
    void loadDashboard();
    void loadGovernance();
    void loadSites();
    const timer = setInterval(() => {
      void loadDashboard();
      void loadGovernance();
      void loadSites();
    }, 15000);
    return () => clearInterval(timer);
  }, [loadDashboard, loadGovernance, loadSites]);

  useEffect(() => {
    void loadTenantDetail(selectedTenantId);
  }, [selectedTenantId, loadTenantDetail]);

  const rows = useMemo(() => dashboard?.rows || [], [dashboard]);
  const selectedSite = useMemo(() => sites.find((site) => site.site_id === selectedSiteId) || null, [sites, selectedSiteId]);

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">BRP Cyber</p>
          <h1 className="mt-1 text-2xl font-bold text-ink sm:text-3xl">Objective Gate Command Board</h1>
          <p className="mt-2 text-sm text-slate-400">
            Red/Blue/Purple orchestration readiness with enterprise blocker intelligence.
          </p>
        </div>
        <button
          type="button"
          className="rounded-md border border-accent/60 bg-accent/15 px-4 py-2 text-sm font-semibold text-accent hover:bg-accent/25"
          onClick={() => void loadDashboard()}
        >
          Refresh
        </button>
      </header>

      <OverviewStats
        total={dashboard?.total_tenants || 0}
        passing={dashboard?.passing_tenants || 0}
        failing={dashboard?.failing_tenants || 0}
      />

      {loadingDashboard ? <p className="mt-3 text-sm text-slate-400">Refreshing dashboard stream...</p> : null}
      {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}

      <section className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <TenantTable rows={rows} selectedTenantId={selectedTenantId} onSelectTenant={setSelectedTenantId} />
        <TenantDetailPanel
          tenantId={selectedTenantId}
          gate={tenantGate}
          history={tenantHistory}
          remediation={tenantRemediation}
          loading={loadingTenant}
          error={error}
        />
      </section>

      <GovernancePanel data={governance} loading={loadingGovernance} error={governanceError} />

      <section className="mt-6 grid gap-4 xl:grid-cols-3">
        <RedTeamPanel sites={sites} selectedSiteId={selectedSiteId} onSelectSite={setSelectedSiteId} />
        <BlueTeamPanel selectedSite={selectedSite} />
        <PurpleReportsPanel selectedSite={selectedSite} />
      </section>
      {siteError ? <p className="mt-2 text-sm text-danger">{siteError}</p> : null}
    </main>
  );
}
