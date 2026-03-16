"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { GovernancePanel } from "@/components/GovernancePanel";
import { OverviewStats } from "@/components/OverviewStats";
import { TenantDetailPanel } from "@/components/TenantDetailPanel";
import { TenantTable } from "@/components/TenantTable";
import { RedTeamPanel } from "@/components/RedTeamPanel";
import { BlueTeamPanel } from "@/components/BlueTeamPanel";
import { PurpleReportsPanel } from "@/components/PurpleReportsPanel";
import { FeatureGuidePanel } from "@/components/FeatureGuidePanel";
import { SOARPlaybookPanel } from "@/components/SOARPlaybookPanel";
import { ConnectorReliabilityPanel } from "@/components/ConnectorReliabilityPanel";
import { ActionCenterPanel } from "@/components/ActionCenterPanel";
import { CoworkerDeliveryPanel } from "@/components/CoworkerDeliveryPanel";
import { CoworkerPluginPanel } from "@/components/CoworkerPluginPanel";
import { FederationOpsPanel } from "@/components/FederationOpsPanel";
import { SecOpsDataTierPanel } from "@/components/SecOpsDataTierPanel";
import {
  fetchCompetitiveAuthContext,
  fetchDashboard,
  fetchGovernanceDashboard,
  fetchSites,
  fetchTenantGate,
  fetchTenantHistory,
  fetchTenantRemediation,
} from "@/lib/api";
import type {
  CompetitiveAuthContextResponse,
  DashboardRow,
  DashboardResponse,
  GovernanceDashboardResponse,
  SiteRow,
  TenantGateResponse,
  TenantHistoryResponse,
  TenantRemediation,
} from "@/lib/types";

export type WorkspaceMode = "overview" | "red" | "blue" | "purple" | "redPlugin" | "bluePlugin" | "purplePlugin";

const WORKSPACE_COPY: Record<WorkspaceMode, { eyebrow: string; title: string; description: string }> = {
  overview: {
    eyebrow: "Objective Gate Command Board",
    title: "Run autonomous Red, Blue, and Purple operations from one workspace",
    description:
      "Track enterprise readiness, route AI co-worker actions, and review governance telemetry in a single operator view designed for fast daily execution.",
  },
  red: {
    eyebrow: "Red Service Category",
    title: "Continuous validation and exploit-path testing",
    description:
      "Drive shadow pentest, exploit autopilot, and threat-content refresh from a dedicated Red service page.",
  },
  blue: {
    eyebrow: "Blue Service Category",
    title: "Detection, response, and SecOps automation",
    description:
      "Operate blue triage, detection tuning, SOAR, reliability, and data-tier workflows without scrolling past unrelated sections.",
  },
  purple: {
    eyebrow: "Purple Service Category",
    title: "Correlation, compliance, and executive reporting",
    description:
      "Review Purple analysis, federation posture, and case context on a page dedicated to strategic security operations.",
  },
  redPlugin: {
    eyebrow: "Red Plugin Category",
    title: "Red plugin execution, binding, and delivery",
    description:
      "Operate Exploit Code Generator and Nuclei AI-Template Writer as Red-specific AI co-workers with their own delivery controls.",
  },
  bluePlugin: {
    eyebrow: "Blue Plugin Category",
    title: "Blue plugin execution, binding, and delivery",
    description:
      "Operate Thai alert translation and Auto-Playbook Executor as Blue-specific AI co-workers with their own delivery controls.",
  },
  purplePlugin: {
    eyebrow: "Purple Plugin Category",
    title: "Purple plugin execution, binding, and delivery",
    description:
      "Operate MITRE heatmap and incident-report plugins with Purple-specific binding, run, and delivery workflows.",
  },
};

const FEATURE_GUIDES: Record<WorkspaceMode, Array<{ title: string; summary: string; details: string[] }>> = {
  overview: [
    {
      title: "Dashboard",
      summary: "หน้ารวมสำหรับดู tenant readiness, governance posture, และ feature-to-menu map ก่อนลงมือปฏิบัติการ",
      details: ["Objective gate summary", "Tenant status/detail", "Governance dashboard", "Menu-to-feature routing map"],
    },
    {
      title: "Configuration",
      summary: "หน้าตั้งค่าพื้นฐานของไซต์, embedded workflow, vendor preset, activation bundle, และ control-plane bootstrap",
      details: ["Sites", "Adapters", "Embedded endpoints", "Activation bundles", "Automation verification"],
    },
    {
      title: "Service / Plugin Separation",
      summary: "Service pages เน้น operational workflows ส่วน Plugin pages เน้น binding/run/delivery ของ AI co-workers ตามหมวด",
      details: ["Red/Blue/Purple Service pages", "Red Plugin", "Blue Plugin", "Purple Plugin"],
    },
  ],
  red: [
    {
      title: "24/7 Shadow Pentest",
      summary: "งาน continuous passive validation, drift detection, zero-day pack assignment, deploy-trigger, และ asset validation",
      details: ["Policy", "Run history", "Scheduler", "Asset inventory", "Pack validation"],
    },
    {
      title: "Social Engineering Simulator",
      summary: "งาน phishing simulation ภาษาไทย, roster, policy, campaign approval, telemetry, และ provider callback",
      details: ["Roster import", "Policy", "Campaign run/review/kill", "Telemetry", "Provider callback"],
    },
    {
      title: "Vulnerability Auto-Validator",
      summary: "งาน import finding จาก scanner และพิสูจน์ exploitability พร้อม remediation export",
      details: ["Nessus/Burp import", "Exploit-path validation", "False-positive reduction", "Remediation export"],
    },
  ],
  blue: [
    {
      title: "AI Log Refiner",
      summary: "ลด noise, เก็บ KPI/storage saving, callback ingestion, feedback loop, และ schedule policy ต่อ connector",
      details: ["Policy", "Run KPI", "Feedback", "Mapping packs", "Callback ingestion", "Scheduler"],
    },
    {
      title: "Managed AI Responder",
      summary: "ตรวจจับ-ตอบสนอง, approval/rollback/evidence, vendor action confirmation, callback contracts, และ scheduler",
      details: ["Policy", "Dry-run/apply", "Review/rollback", "Evidence verify", "Vendor packs", "Callback history"],
    },
    {
      title: "Threat Intelligence Localizer + SecOps Ops",
      summary: "Thai threat localization, gap promotion, detection/response platform ops, SOAR, reliability, and data-tier governance",
      details: ["Threat feed/adapters", "Routing/promotions", "SOAR marketplace", "Action center", "Connector reliability", "SecOps data tier"],
    },
  ],
  purple: [
    {
      title: "Automated ISO/NIST Gap Analysis",
      summary: "สร้าง compliance mapping, case graph, executive scorecard, และ control-family evidence correlation",
      details: ["ISO gap", "NIST gap", "Case graph", "Executive scorecard", "Control-family map"],
    },
    {
      title: "ROI Security Dashboard",
      summary: "สร้าง snapshot/trend/portfolio/board export และ final release workflow สำหรับรายงานระดับบริหาร",
      details: ["ROI snapshots", "Trends", "Portfolio roll-up", "Board export", "Release approvals"],
    },
    {
      title: "Purple Federation",
      summary: "ดู multi-site posture และ cross-team evidence aggregation ในหน้าเดียว",
      details: ["Federation ops", "Executive federation", "Report history", "Release status"],
    },
  ],
  redPlugin: [
    {
      title: "Exploit Code Generator",
      summary: "สร้าง exploit draft หลายภาษา, bind policy, manual run, lint/export, และ delivery profile ของ Red plugin",
      details: ["Binding", "Dry-run/apply", "Config JSON", "Run history", "Delivery/escalation"],
    },
    {
      title: "Nuclei AI-Template Writer",
      summary: "สร้าง YAML template, bind policy, manual run, lint/export, และ threat-pack publishing support",
      details: ["Binding", "Scheduler", "Run history", "Delivery/escalation", "Threat-pack workflow"],
    },
  ],
  bluePlugin: [
    {
      title: "Thai Alert Translator & Summarizer",
      summary: "แปล alert เป็นภาษาไทย, bind policy, manual run, และ route ออก channel ตาม delivery policy",
      details: ["Binding", "Dry-run/apply", "Run history", "Thai delivery preview", "Approval workflow"],
    },
    {
      title: "Auto-Playbook Executor",
      summary: "สร้าง/dispatch response payload, bind policy, manual run, และ route plugin output ผ่าน delivery/escalation",
      details: ["Binding", "Run history", "Delivery/escalation", "SOAR-oriented outputs"],
    },
  ],
  purplePlugin: [
    {
      title: "MITRE ATT&CK Heatmap Generator",
      summary: "bind/run/export heatmap plugin พร้อมส่งออก markdown/csv/ATT&CK layer/SVG และ route ผ่าน delivery policy",
      details: ["Binding", "Run history", "Heatmap outputs", "Delivery/escalation"],
    },
    {
      title: "Incident Report Ghostwriter",
      summary: "bind/run report-writing plugin พร้อมสร้าง draft ภาษาไทยและ route ผ่าน delivery/review workflow",
      details: ["Binding", "Run history", "Thai report draft", "Delivery/escalation"],
    },
  ],
};

function CategoryHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="section-header-card rounded-[20px] border border-slate-200 bg-white px-5 py-4">
      <p className="text-[11px] uppercase tracking-[0.28em] text-accent">{eyebrow}</p>
      <h2 className="mt-1 text-lg font-semibold text-ink">{title}</h2>
      <p className="mt-1 text-xs text-slate-400 wrap-anywhere">{description}</p>
    </div>
  );
}

function WorkspaceHero({
  copy,
  sitesOnline,
  governanceEvents,
  onRefresh,
}: {
  copy: { eyebrow: string; title: string; description: string };
  sitesOnline: number;
  governanceEvents: number;
  onRefresh: () => void;
}) {
  return (
    <section className="dashboard-hero px-6 py-6 lg:px-7">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-3xl">
          <p className="text-xs uppercase tracking-[0.26em] text-accent">{copy.eyebrow}</p>
          <h2 className="mt-3 text-[2rem] font-semibold leading-tight text-ink sm:text-[2.35rem]">
            Run autonomous <span className="text-accent">Red, Blue, and Purple</span> operations from one workspace
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-500">{copy.description}</p>
          <div className="mt-5 flex flex-wrap gap-3">
            <div className="rounded-2xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500 shadow-sm">
              Sites online: <span className="font-semibold text-ink">{sitesOnline}</span>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500 shadow-sm">
              Governance events: <span className="font-semibold text-ink">{governanceEvents}</span>
            </div>
            <button
              type="button"
              className="rounded-2xl border border-accent bg-accent px-4 py-2 text-sm font-semibold text-white shadow-sm hover:opacity-90"
              onClick={onRefresh}
            >
              Refresh
            </button>
          </div>
        </div>

        <div className="hero-visual">
          <div className="hero-visual-card hero-visual-card-secondary" />
          <div className="hero-visual-card hero-visual-card-primary" />
          <div className="hero-visual-orbit" />
          <span className="hero-visual-dot hero-visual-dot-a" />
          <span className="hero-visual-dot hero-visual-dot-b" />
        </div>
      </div>
    </section>
  );
}

function WorkspaceIntro({
  copy,
  selectedSiteId,
  sites,
  onSelectSite,
  onRefresh,
  showSitePicker,
}: {
  copy: { eyebrow: string; title: string; description: string };
  selectedSiteId: string;
  sites: SiteRow[];
  onSelectSite: (siteId: string) => void;
  onRefresh: () => void;
  showSitePicker: boolean;
}) {
  return (
    <section className="card p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <p className="text-xs uppercase tracking-[0.26em] text-accent">{copy.eyebrow}</p>
          <h2 className="mt-2 text-[1.95rem] font-semibold leading-tight text-ink">{copy.title}</h2>
          <p className="mt-2 text-sm leading-7 text-slate-500">{copy.description}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {showSitePicker ? (
            <label className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-panelAlt/50 px-3 py-2 text-xs text-slate-500">
              Site
              <select
                value={selectedSiteId}
                onChange={(event) => onSelectSite(event.target.value)}
                className="min-w-[180px] bg-transparent text-sm font-medium text-ink outline-none"
              >
                {sites.map((site) => (
                  <option key={site.site_id} value={site.site_id}>
                    {site.display_name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <button
            type="button"
            className="rounded-2xl border border-accent bg-accent px-4 py-2 text-sm font-semibold text-white shadow-sm hover:opacity-90"
            onClick={onRefresh}
          >
            Refresh
          </button>
        </div>
      </div>
    </section>
  );
}

export function CompetitiveWorkspace({ mode }: { mode: WorkspaceMode }) {
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");
  const [tenantGate, setTenantGate] = useState<TenantGateResponse | null>(null);
  const [tenantHistory, setTenantHistory] = useState<TenantHistoryResponse | null>(null);
  const [tenantRemediation, setTenantRemediation] = useState<TenantRemediation | null>(null);
  const [governance, setGovernance] = useState<GovernanceDashboardResponse | null>(null);
  const [loadingDashboard, setLoadingDashboard] = useState(false);
  const [loadingTenant, setLoadingTenant] = useState(false);
  const [loadingGovernance, setLoadingGovernance] = useState(false);
  const [authContext, setAuthContext] = useState<CompetitiveAuthContextResponse | null>(null);
  const [sites, setSites] = useState<SiteRow[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState("");
  const [error, setError] = useState<string>("");
  const [governanceError, setGovernanceError] = useState<string>("");
  const [siteError, setSiteError] = useState<string>("");

  const fallbackRows = useMemo<DashboardRow[]>(() => {
    const grouped = new Map<string, { total: number; inactive: number }>();
    for (const site of sites) {
      const key = site.tenant_id;
      const entry = grouped.get(key) || { total: 0, inactive: 0 };
      entry.total += 1;
      if (!site.is_active) entry.inactive += 1;
      grouped.set(key, entry);
    }
    return Array.from(grouped.entries()).map(([tenantId, summary]) => {
      const blockers = [{ gate: "objective_snapshot", reason: "No objective-gate snapshot yet. Run orchestration cycle." }];
      if (summary.inactive > 0) {
        blockers.push({ gate: "site_config", reason: `${summary.inactive} inactive site(s)` });
      }
      return {
        tenant_id: tenantId,
        overall_pass: summary.inactive === 0,
        failed_gate_count: summary.inactive > 0 ? 1 : 0,
        blockers,
      };
    });
  }, [sites]);

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
      if (dashboard?.rows?.length) {
        setError(err instanceof Error ? err.message : "tenant_detail_load_failed");
      } else {
        setTenantGate(null);
        setTenantHistory(null);
        setTenantRemediation(null);
      }
    } finally {
      setLoadingTenant(false);
    }
  }, [dashboard?.rows?.length]);

  const loadAuthContext = useCallback(async () => {
    try {
      const data = await fetchCompetitiveAuthContext();
      setAuthContext(data);
    } catch {
      setAuthContext({
        authenticated: false,
        actor: "",
        scopes: [],
        roles: ["viewer"],
        permissions: { can_view: false, can_edit_policy: false, can_approve: false },
      });
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

  const refreshAll = useCallback(() => {
    void loadDashboard();
    void loadGovernance();
    void loadSites();
    void loadAuthContext();
  }, [loadAuthContext, loadDashboard, loadGovernance, loadSites]);

  useEffect(() => {
    refreshAll();
    const timer = setInterval(() => {
      refreshAll();
    }, 15000);
    return () => clearInterval(timer);
  }, [refreshAll]);

  useEffect(() => {
    void loadTenantDetail(selectedTenantId);
  }, [selectedTenantId, loadTenantDetail]);

  const rows = useMemo(() => {
    const objectiveRows = dashboard?.rows || [];
    return objectiveRows.length > 0 ? objectiveRows : fallbackRows;
  }, [dashboard, fallbackRows]);
  const stats = useMemo(() => {
    const passing = rows.filter((row) => row.overall_pass).length;
    return {
      total: rows.length,
      passing,
      failing: Math.max(0, rows.length - passing),
    };
  }, [rows]);
  const selectedSite = useMemo(() => sites.find((site) => site.site_id === selectedSiteId) || null, [sites, selectedSiteId]);
  const selectedTenantSites = useMemo(() => sites.filter((site) => site.tenant_id === selectedTenantId), [sites, selectedTenantId]);
  const canViewCompetitive = Boolean(authContext?.permissions?.can_view);
  const canEditPolicy = Boolean(authContext?.permissions?.can_edit_policy);
  const canApprove = Boolean(authContext?.permissions?.can_approve);
  const copy = WORKSPACE_COPY[mode];

  useEffect(() => {
    if (!selectedTenantId && rows.length > 0) {
      setSelectedTenantId(rows[0].tenant_id);
    }
  }, [rows, selectedTenantId]);

  return (
    <main className="space-y-6">
      {mode === "overview" ? (
        <WorkspaceHero
          copy={copy}
          sitesOnline={sites.filter((site) => site.is_active).length}
          governanceEvents={governance?.summary.events_analyzed ?? 0}
          onRefresh={refreshAll}
        />
      ) : (
        <WorkspaceIntro
          copy={copy}
          selectedSiteId={selectedSiteId}
          sites={sites}
          onSelectSite={setSelectedSiteId}
          onRefresh={refreshAll}
          showSitePicker={mode !== "red"}
        />
      )}

      {loadingDashboard ? <p className="text-sm text-slate-400">Refreshing dashboard stream...</p> : null}
      {error ? <p className="text-sm text-danger">{error}</p> : null}
      {siteError ? <p className="text-sm text-danger">{siteError}</p> : null}

      {mode === "overview" ? (
        <>
          <FeatureGuidePanel
            eyebrow="Menu Coverage"
            title="Feature-to-menu mapping from the implementation docs"
            description="เมนูทั้งหมดด้านซ้ายถูกจัดใหม่ตาม `VIRTUAL_EXPERT_CHECKLIST.md`, `PHASE_CHECKLIST.md`, และ `COMPETITIVE_ENGINE_API.md` เพื่อให้ service workflows กับ plugin workflows แยกกันชัดเจน"
            items={FEATURE_GUIDES.overview}
          />
          <OverviewStats total={stats.total} passing={stats.passing} failing={stats.failing} />

          <p className="text-xs text-slate-500 wrap-anywhere">
            Competitive RBAC roles: {(authContext?.roles || ["viewer"]).join(", ")}
          </p>
          {dashboard?.rows?.length === 0 ? (
            <p className="text-xs text-warning wrap-anywhere">
              No objective-gate snapshots yet. Dashboard is showing site-derived tenant data so operations remain visible.
            </p>
          ) : null}

          <section className="space-y-4">
            <TenantTable rows={rows} selectedTenantId={selectedTenantId} onSelectTenant={setSelectedTenantId} />
            <TenantDetailPanel
              tenantId={selectedTenantId}
              gate={tenantGate}
              history={tenantHistory}
              remediation={tenantRemediation}
              tenantSites={selectedTenantSites}
              loading={loadingTenant}
              error={error}
            />
          </section>

          <GovernancePanel data={governance} loading={loadingGovernance} error={governanceError} />
        </>
      ) : null}

      {mode === "red" ? (
        <>
          <CategoryHeader
            eyebrow="Red Service Category"
            title="Active testing, validation, and threat content"
            description="Red service handles simulated scanning, exploit-path validation, threat-content refresh, and policy-driven autonomous attack validation for the selected site."
          />
          <FeatureGuidePanel
            eyebrow="Feature Coverage"
            title="What belongs in Red Service"
            description="หน้านี้รวมเฉพาะ operational Red workflows ตาม checklist ไม่รวม plugin binding/delivery ซึ่งถูกย้ายไปหน้า Red Plugin"
            items={FEATURE_GUIDES.red}
          />
          <RedTeamPanel
            sites={sites}
            selectedSiteId={selectedSiteId}
            onSelectSite={setSelectedSiteId}
            canView={canViewCompetitive}
            canEditPolicy={canEditPolicy}
            canApprove={canApprove}
          />
        </>
      ) : null}

      {mode === "blue" ? (
        <>
          <CategoryHeader
            eyebrow="Blue Service Category"
            title="Detection, response, routing, and SecOps operations"
            description="Blue service covers event triage, detection autotune, SOAR execution, connector reliability, notification routing, and SecOps data-tier operations."
          />
          <FeatureGuidePanel
            eyebrow="Feature Coverage"
            title="What belongs in Blue Service"
            description="หน้านี้รวม Blue operational workflows และ platform ops ที่ต้องใช้ระหว่าง detection/response จริง ไม่รวม plugin binding/delivery ซึ่งถูกย้ายไปหน้า Blue Plugin"
            items={FEATURE_GUIDES.blue}
          />
          <section className="space-y-4">
            <BlueTeamPanel
              selectedSite={selectedSite}
              canView={canViewCompetitive}
              canEditPolicy={canEditPolicy}
              canApprove={canApprove}
            />
            <SOARPlaybookPanel
              selectedSite={selectedSite}
              canView={canViewCompetitive}
              canEditPolicy={canEditPolicy}
              canApprove={canApprove}
            />
            <ActionCenterPanel
              selectedSite={selectedSite}
              canView={canViewCompetitive}
              canEditPolicy={canEditPolicy}
              canApprove={canApprove}
            />
            <ConnectorReliabilityPanel
              selectedSite={selectedSite}
              canView={canViewCompetitive}
              canEditPolicy={canEditPolicy}
              canApprove={canApprove}
            />
            <SecOpsDataTierPanel
              selectedSite={selectedSite}
              canView={canViewCompetitive}
              canEditPolicy={canEditPolicy}
              canApprove={canApprove}
            />
          </section>
        </>
      ) : null}

      {mode === "purple" ? (
        <>
          <CategoryHeader
            eyebrow="Purple Service Category"
            title="Correlation, compliance, executive reporting, and federation"
            description="Purple service correlates Red and Blue evidence, builds case graphs, generates executive scorecards, and surfaces multi-site federation posture."
          />
          <FeatureGuidePanel
            eyebrow="Feature Coverage"
            title="What belongs in Purple Service"
            description="หน้านี้รวม Purple strategic/compliance/executive workflows ไม่รวม plugin binding/delivery ซึ่งถูกย้ายไปหน้า Purple Plugin"
            items={FEATURE_GUIDES.purple}
          />
          <section className="space-y-4">
            <PurpleReportsPanel selectedSite={selectedSite} />
            <FederationOpsPanel canView={canViewCompetitive} />
          </section>
        </>
      ) : null}

      {mode === "redPlugin" ? (
        <>
          <CategoryHeader
            eyebrow="Red Plugin Category"
            title="Red plugin binding, execution, and delivery"
            description="หน้านี้รวม Red plugin lifecycle ทั้ง binding, run, scheduler, preview, delivery, และ escalation."
          />
          <FeatureGuidePanel
            eyebrow="Feature Coverage"
            title="What belongs in Red Plugin"
            description="เฉพาะ Red AI co-workers และ delivery controls ของ Red plugin เท่านั้น"
            items={FEATURE_GUIDES.redPlugin}
          />
          <CoworkerPluginPanel
            selectedSite={selectedSite}
            canView={canViewCompetitive}
            canEditPolicy={canEditPolicy}
            canApprove={canApprove}
            fixedCategory="red"
          />
          <CoworkerDeliveryPanel
            selectedSite={selectedSite}
            canView={canViewCompetitive}
            canEditPolicy={canEditPolicy}
            canApprove={canApprove}
            pluginCategory="red"
          />
        </>
      ) : null}

      {mode === "bluePlugin" ? (
        <>
          <CategoryHeader
            eyebrow="Blue Plugin Category"
            title="Blue plugin binding, execution, and delivery"
            description="หน้านี้รวม Blue plugin lifecycle ทั้ง binding, run, preview, delivery, approval, และ escalation."
          />
          <FeatureGuidePanel
            eyebrow="Feature Coverage"
            title="What belongs in Blue Plugin"
            description="เฉพาะ Blue AI co-workers และ delivery controls ของ Blue plugin เท่านั้น"
            items={FEATURE_GUIDES.bluePlugin}
          />
          <CoworkerPluginPanel
            selectedSite={selectedSite}
            canView={canViewCompetitive}
            canEditPolicy={canEditPolicy}
            canApprove={canApprove}
            fixedCategory="blue"
          />
          <CoworkerDeliveryPanel
            selectedSite={selectedSite}
            canView={canViewCompetitive}
            canEditPolicy={canEditPolicy}
            canApprove={canApprove}
            pluginCategory="blue"
          />
        </>
      ) : null}

      {mode === "purplePlugin" ? (
        <>
          <CategoryHeader
            eyebrow="Purple Plugin Category"
            title="Purple plugin binding, execution, and delivery"
            description="หน้านี้รวม Purple plugin lifecycle ทั้ง binding, run, export-related delivery, approval, และ escalation."
          />
          <FeatureGuidePanel
            eyebrow="Feature Coverage"
            title="What belongs in Purple Plugin"
            description="เฉพาะ Purple AI co-workers และ delivery controls ของ Purple plugin เท่านั้น"
            items={FEATURE_GUIDES.purplePlugin}
          />
          <CoworkerPluginPanel
            selectedSite={selectedSite}
            canView={canViewCompetitive}
            canEditPolicy={canEditPolicy}
            canApprove={canApprove}
            fixedCategory="purple"
          />
          <CoworkerDeliveryPanel
            selectedSite={selectedSite}
            canView={canViewCompetitive}
            canEditPolicy={canEditPolicy}
            canApprove={canApprove}
            pluginCategory="purple"
          />
        </>
      ) : null}
    </main>
  );
}
