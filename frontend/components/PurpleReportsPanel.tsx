import { useEffect, useState } from "react";

import {
  exportSitePurpleIncidentReport,
  exportSitePurpleAttackLayerGraphic,
  exportSitePurpleAttackLayerWorkspace,
  exportSitePurpleControlFamilyMap,
  exportSitePurpleMitreHeatmap,
  exportSitePurpleRegulatedReport,
  exportSitePurpleRoiBoardPack,
  fetchPurpleExportTemplatePacks,
  fetchPurpleRoiPortfolioRollup,
  fetchPurpleRoiTemplatePacks,
  fetchSiteCaseGraph,
  fetchSitePurpleExecutiveFederation,
  fetchSitePurpleExecutiveScorecard,
  fetchSitePurpleAttackLayerWorkspaces,
  fetchSitePurpleControlFamilyMap,
  fetchSitePurpleIsoGapTemplate,
  fetchSitePurpleNistGapTemplate,
  fetchSitePurpleRoiDashboardSnapshots,
  fetchSitePurpleRoiDashboardTrends,
  fetchSitePurpleReportReleases,
  fetchSitePurpleReports,
  generateSitePurpleRoiDashboard,
  generateSitePurpleAnalysis,
  importSitePurpleAttackLayerWorkspace,
  requestSitePurpleReportRelease,
  reviewPurpleReportRelease,
  updateSitePurpleAttackLayerWorkspace,
} from "@/lib/api";
import type {
  PurpleExportTemplatePackResponse,
  PurpleRoiPortfolioRollupResponse,
  PurpleRoiTemplatePackResponse,
  SiteCaseGraphResponse,
  SitePurpleIncidentReportExportResponse,
  SitePurpleMitreHeatmapExportResponse,
  SitePurpleRegulatedReportExportResponse,
  SitePurpleRoiBoardExportResponse,
  SitePurpleExecutiveFederationResponse,
  SitePurpleExecutiveScorecardResponse,
  SitePurpleIsoGapTemplateResponse,
  SitePurpleAttackLayerExportResponse,
  SitePurpleAttackLayerWorkspaceListResponse,
  SitePurpleControlFamilyMapExportResponse,
  SitePurpleControlFamilyMapResponse,
  SitePurpleReportReleaseListResponse,
  SitePurpleRoiDashboardSnapshotListResponse,
  SitePurpleRoiDashboardTrendResponse,
  SitePurpleReportHistoryResponse,
  SiteRow,
} from "@/lib/types";

type Props = {
  selectedSite: SiteRow | null;
};

const PURPLE_SERVICE_MENUS = [
  {
    title: "Automated ISO/NIST Gap Analysis",
    fit: "บริษัทที่ต้องทำ compliance หรือเตรียม audit",
    value: "ลดเวลาทำเอกสารจากหลายสัปดาห์เหลือระดับนาที และพร้อมส่งตรวจได้เร็วขึ้น",
    status: "live",
    note: "Mapped to ISO 27001 + NIST CSF gap templates with unified evidence correlation",
  },
  {
    title: "ROI Security Dashboard",
    fit: "CISO หรือผู้บริหารที่ต้องสื่อสารความคุ้มค่าของงบ security",
    value: "สรุปผลลัพธ์ของเครื่องมือความปลอดภัยเป็นตัวเลขที่ผู้บริหารเข้าใจได้ทันที",
    status: "live",
    note: "Board-ready ROI snapshot with quantified noise reduction, automation coverage, and effort saved",
  },
];

function parseJsonObject(text: string, fallback: Record<string, unknown> = {}): Record<string, unknown> {
  try {
    const parsed = JSON.parse(text || "{}");
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : fallback;
  } catch {
    return fallback;
  }
}

function parseJsonArray(text: string): Array<Record<string, unknown>> {
  try {
    const parsed = JSON.parse(text || "[]");
    return Array.isArray(parsed) ? parsed.filter((row): row is Record<string, unknown> => !!row && typeof row === "object") : [];
  } catch {
    return [];
  }
}

export function PurpleReportsPanel({ selectedSite }: Props) {
  const [reports, setReports] = useState<SitePurpleReportHistoryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [isoTemplate, setIsoTemplate] = useState<SitePurpleIsoGapTemplateResponse | null>(null);
  const [caseGraph, setCaseGraph] = useState<SiteCaseGraphResponse | null>(null);
  const [executive, setExecutive] = useState<SitePurpleExecutiveScorecardResponse | null>(null);
  const [federation, setFederation] = useState<SitePurpleExecutiveFederationResponse | null>(null);
  const [roiSnapshots, setRoiSnapshots] = useState<SitePurpleRoiDashboardSnapshotListResponse | null>(null);
  const [roiTrends, setRoiTrends] = useState<SitePurpleRoiDashboardTrendResponse | null>(null);
  const [roiPortfolio, setRoiPortfolio] = useState<PurpleRoiPortfolioRollupResponse | null>(null);
  const [roiTemplatePacks, setRoiTemplatePacks] = useState<PurpleRoiTemplatePackResponse | null>(null);
  const [roiExport, setRoiExport] = useState<SitePurpleRoiBoardExportResponse | null>(null);
  const [purpleTemplatePacks, setPurpleTemplatePacks] = useState<PurpleExportTemplatePackResponse | null>(null);
  const [mitreExport, setMitreExport] = useState<SitePurpleMitreHeatmapExportResponse | null>(null);
  const [controlFamilyMap, setControlFamilyMap] = useState<SitePurpleControlFamilyMapResponse | null>(null);
  const [controlFamilyExport, setControlFamilyExport] = useState<SitePurpleControlFamilyMapExportResponse | null>(null);
  const [attackLayerWorkspaces, setAttackLayerWorkspaces] = useState<SitePurpleAttackLayerWorkspaceListResponse | null>(null);
  const [attackLayerExport, setAttackLayerExport] = useState<SitePurpleAttackLayerExportResponse | null>(null);
  const [attackLayerGraphicExport, setAttackLayerGraphicExport] = useState<SitePurpleAttackLayerExportResponse | null>(null);
  const [incidentExport, setIncidentExport] = useState<SitePurpleIncidentReportExportResponse | null>(null);
  const [regulatedExport, setRegulatedExport] = useState<SitePurpleRegulatedReportExportResponse | null>(null);
  const [reportReleases, setReportReleases] = useState<SitePurpleReportReleaseListResponse | null>(null);
  const [roiLookbackDays, setRoiLookbackDays] = useState(30);
  const [roiHourlyCost, setRoiHourlyCost] = useState(18);
  const [roiMinutesPerAlert, setRoiMinutesPerAlert] = useState(12);
  const [roiExportFormat, setRoiExportFormat] = useState<"pdf" | "ppt">("pdf");
  const [roiTemplatePack, setRoiTemplatePack] = useState("roi_board_minimal");
  const [roiExportTitle, setRoiExportTitle] = useState("");
  const [roiIncludePortfolio, setRoiIncludePortfolio] = useState(true);
  const [roiTrendMetricFocus, setRoiTrendMetricFocus] = useState("");
  const [roiTrendMinAutomationCoveragePct, setRoiTrendMinAutomationCoveragePct] = useState(0);
  const [roiTrendMinNoiseReductionPct, setRoiTrendMinNoiseReductionPct] = useState(0);
  const [roiPortfolioSiteCodeFilter, setRoiPortfolioSiteCodeFilter] = useState("");
  const [roiPortfolioStatusFilter, setRoiPortfolioStatusFilter] = useState("");
  const [roiPortfolioMinAutomationCoveragePct, setRoiPortfolioMinAutomationCoveragePct] = useState(0);
  const [roiPortfolioMinNoiseReductionPct, setRoiPortfolioMinNoiseReductionPct] = useState(0);
  const [roiPortfolioSortBy, setRoiPortfolioSortBy] = useState("estimated_manual_effort_saved_usd");
  const [purpleMitreExportFormat, setPurpleMitreExportFormat] = useState<"markdown" | "csv" | "attack_layer_json" | "svg">("markdown");
  const [purpleMitreIncludeRecommendations, setPurpleMitreIncludeRecommendations] = useState(true);
  const [purpleIncidentTemplatePack, setPurpleIncidentTemplatePack] = useState("incident_company_standard");
  const [purpleIncidentExportFormat, setPurpleIncidentExportFormat] = useState<"markdown" | "json" | "pdf" | "docx">("markdown");
  const [purpleRegulatedTemplatePack, setPurpleRegulatedTemplatePack] = useState("regulated_nca_th");
  const [purpleRegulatedExportFormat, setPurpleRegulatedExportFormat] = useState<"markdown" | "json" | "pdf" | "docx">("markdown");
  const [controlFamilyFramework, setControlFamilyFramework] = useState<"combined" | "iso27001" | "nist_csf">("combined");
  const [controlFamilyExportFormat, setControlFamilyExportFormat] = useState<"markdown" | "csv" | "json">("markdown");
  const [attackLayerImportName, setAttackLayerImportName] = useState("CyberWitcher Imported Layer");
  const [attackLayerImportNotes, setAttackLayerImportNotes] = useState("");
  const [attackLayerImportJson, setAttackLayerImportJson] = useState(
    '{\n  "name": "CyberWitcher Imported Layer",\n  "domain": "enterprise-attack",\n  "techniques": [\n    {"techniqueID": "T1110", "score": 80, "comment": "Brute force coverage", "enabled": true}\n  ]\n}',
  );
  const [attackLayerOverrideJson, setAttackLayerOverrideJson] = useState(
    '[\n  {"techniqueID": "T1110", "score": 95, "color": "#F76C45", "comment": "Validated by purple team"}\n]',
  );
  const [attackLayerExportFormat, setAttackLayerExportFormat] = useState<"attack_layer_json" | "svg">("attack_layer_json");

  const load = async () => {
    if (!selectedSite) return;
    setLoading(true);
    setError("");
    try {
      const [reportRows, roiRows, trendRows, portfolioRows, templatePacks, roiPackRows, releaseRows, controlRows, layerRows] = await Promise.all([
        fetchSitePurpleReports(selectedSite.site_id, 20),
        fetchSitePurpleRoiDashboardSnapshots(selectedSite.site_id, 10),
        fetchSitePurpleRoiDashboardTrends(selectedSite.site_id, {
          limit: 12,
          metric_focus: roiTrendMetricFocus,
          min_automation_coverage_pct: roiTrendMinAutomationCoveragePct,
          min_noise_reduction_pct: roiTrendMinNoiseReductionPct,
        }),
        fetchPurpleRoiPortfolioRollup({
          tenant_code: selectedSite.tenant_code,
          site_code: roiPortfolioSiteCodeFilter,
          status: roiPortfolioStatusFilter,
          min_automation_coverage_pct: roiPortfolioMinAutomationCoveragePct,
          min_noise_reduction_pct: roiPortfolioMinNoiseReductionPct,
          sort_by: roiPortfolioSortBy,
          limit: 100,
        }),
        fetchPurpleExportTemplatePacks(),
        fetchPurpleRoiTemplatePacks(),
        fetchSitePurpleReportReleases(selectedSite.site_id, 10),
        fetchSitePurpleControlFamilyMap(selectedSite.site_id, controlFamilyFramework),
        fetchSitePurpleAttackLayerWorkspaces(selectedSite.site_id, 20),
      ]);
      setReports(reportRows);
      setRoiSnapshots(roiRows);
      setRoiTrends(trendRows);
      setRoiPortfolio(portfolioRows);
      setPurpleTemplatePacks(templatePacks);
      setRoiTemplatePacks(roiPackRows);
      setReportReleases(releaseRows);
      setControlFamilyMap(controlRows);
      setAttackLayerWorkspaces(layerRows);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "purple_reports_load_failed";
      if (msg.includes("fetch") || msg.includes("network") || msg.toLowerCase().includes("failed to fetch")) {
        setError("ยังไม่มีการเชื่อมต่อ Backend · ระบบอยู่ใน Demo Mode — เพิ่ม Site ใน Settings เพื่อเริ่มใช้งานจริง");
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    if (!selectedSite) return;
    const timer = setInterval(() => void load(), 15000);
    return () => clearInterval(timer);
  }, [
    selectedSite?.site_id,
    roiTrendMetricFocus,
    roiTrendMinAutomationCoveragePct,
    roiTrendMinNoiseReductionPct,
    roiPortfolioSiteCodeFilter,
    roiPortfolioStatusFilter,
    roiPortfolioMinAutomationCoveragePct,
    roiPortfolioMinNoiseReductionPct,
    roiPortfolioSortBy,
    controlFamilyFramework,
  ]);

  const generate = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await generateSitePurpleAnalysis(selectedSite.site_id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_generate_failed");
    } finally {
      setBusy(false);
    }
  };

  const generateIsoTemplate = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      setIsoTemplate(await fetchSitePurpleIsoGapTemplate(selectedSite.site_id, 200));
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_iso_template_failed");
    } finally {
      setBusy(false);
    }
  };

  const generateNistTemplate = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      setIsoTemplate(await fetchSitePurpleNistGapTemplate(selectedSite.site_id, 200));
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_nist_template_failed");
    } finally {
      setBusy(false);
    }
  };

  const loadCaseGraph = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      setCaseGraph(await fetchSiteCaseGraph(selectedSite.site_id, 50));
    } catch (err) {
      setError(err instanceof Error ? err.message : "case_graph_failed");
    } finally {
      setBusy(false);
    }
  };

  const loadExecutive = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const [siteExecutive, federationExecutive] = await Promise.all([
        fetchSitePurpleExecutiveScorecard(selectedSite.site_id, {
          lookback_runs: 30,
          lookback_events: 500,
          sla_target_seconds: 120,
        }),
        fetchSitePurpleExecutiveFederation({
          limit: 200,
          lookback_runs: 30,
          lookback_events: 500,
          sla_target_seconds: 120,
        }),
      ]);
      setExecutive(siteExecutive);
      setFederation(federationExecutive);
    } catch (err) {
      setError(err instanceof Error ? err.message : "executive_scorecard_failed");
    } finally {
      setBusy(false);
    }
  };

  const generateRoiDashboard = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await generateSitePurpleRoiDashboard(selectedSite.site_id, {
        lookback_days: roiLookbackDays,
        analyst_hourly_cost_usd: roiHourlyCost,
        analyst_minutes_per_alert: roiMinutesPerAlert,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "roi_dashboard_failed");
    } finally {
      setBusy(false);
    }
  };

  const exportRoiBoardPack = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      setRoiExport(
        await exportSitePurpleRoiBoardPack(selectedSite.site_id, {
          export_format: roiExportFormat,
          template_pack: roiTemplatePack,
          title_override: roiExportTitle,
          include_portfolio: roiIncludePortfolio,
          tenant_code: selectedSite.tenant_code,
          site_limit: 100,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "roi_export_failed");
    } finally {
      setBusy(false);
    }
  };

  const exportMitreHeatmap = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      setMitreExport(
        await exportSitePurpleMitreHeatmap(selectedSite.site_id, {
          export_format: purpleMitreExportFormat,
          include_recommendations: purpleMitreIncludeRecommendations,
          lookback_runs: 30,
          lookback_events: 500,
          sla_target_seconds: 120,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_mitre_export_failed");
    } finally {
      setBusy(false);
    }
  };

  const exportIncidentReport = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      setIncidentExport(
        await exportSitePurpleIncidentReport(selectedSite.site_id, {
          template_pack: purpleIncidentTemplatePack,
          export_format: purpleIncidentExportFormat,
          include_regulatory_mapping: true,
          blue_event_limit: 20,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_incident_export_failed");
    } finally {
      setBusy(false);
    }
  };

  const exportRegulatedReport = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      setRegulatedExport(
        await exportSitePurpleRegulatedReport(selectedSite.site_id, {
          template_pack: purpleRegulatedTemplatePack,
          export_format: purpleRegulatedExportFormat,
          include_incident_context: true,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_regulated_export_failed");
    } finally {
      setBusy(false);
    }
  };

  const exportControlFamilyMap = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const [mapResult, exportResult] = await Promise.all([
        fetchSitePurpleControlFamilyMap(selectedSite.site_id, controlFamilyFramework),
        exportSitePurpleControlFamilyMap(selectedSite.site_id, {
          framework: controlFamilyFramework,
          export_format: controlFamilyExportFormat,
        }),
      ]);
      setControlFamilyMap(mapResult);
      setControlFamilyExport(exportResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_control_family_export_failed");
    } finally {
      setBusy(false);
    }
  };

  const importAttackLayer = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await importSitePurpleAttackLayerWorkspace(selectedSite.site_id, {
        layer_name: attackLayerImportName,
        layer_document: parseJsonObject(attackLayerImportJson, {}),
        notes: attackLayerImportNotes,
        actor: "purple_operator",
      });
      setAttackLayerWorkspaces(await fetchSitePurpleAttackLayerWorkspaces(selectedSite.site_id, 20));
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_attack_layer_import_failed");
    } finally {
      setBusy(false);
    }
  };

  const updateAttackLayer = async (layerId: string) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await updateSitePurpleAttackLayerWorkspace(selectedSite.site_id, layerId, {
        layer_name: attackLayerImportName,
        notes: attackLayerImportNotes,
        technique_overrides: parseJsonArray(attackLayerOverrideJson),
        actor: "purple_operator",
      });
      setAttackLayerWorkspaces(await fetchSitePurpleAttackLayerWorkspaces(selectedSite.site_id, 20));
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_attack_layer_update_failed");
    } finally {
      setBusy(false);
    }
  };

  const exportAttackLayer = async (layerId: string) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      setAttackLayerExport(
        await exportSitePurpleAttackLayerWorkspace(selectedSite.site_id, layerId, { export_format: attackLayerExportFormat }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_attack_layer_export_failed");
    } finally {
      setBusy(false);
    }
  };

  const exportAttackGraphic = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      setAttackLayerGraphicExport(
        await exportSitePurpleAttackLayerGraphic(selectedSite.site_id, {
          export_format: attackLayerExportFormat === "svg" ? "svg" : "attack_layer_json",
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_attack_layer_graphic_failed");
    } finally {
      setBusy(false);
    }
  };

  const requestRelease = async (reportKind: "incident_report" | "regulated_report") => {
    if (!selectedSite) return;
    const activeExport = reportKind === "incident_report" ? incidentExport?.export : regulatedExport?.export;
    if (!activeExport) return;
    setBusy(true);
    setError("");
    try {
      await requestSitePurpleReportRelease(selectedSite.site_id, {
        report_kind: reportKind,
        export_format: activeExport.export_format as "markdown" | "json" | "pdf" | "docx",
        title: activeExport.title,
        filename: activeExport.filename,
        payload: {
          template_pack: activeExport.template_pack,
          generated_at: activeExport.generated_at,
          byte_size: activeExport.byte_size || 0,
          renderer: activeExport.renderer || "text",
        },
        requester: "purple_service_operator",
        note: "requested_from_purple_dashboard",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_release_request_failed");
    } finally {
      setBusy(false);
    }
  };

  const reviewRelease = async (releaseId: string, approve: boolean) => {
    setBusy(true);
    setError("");
    try {
      await reviewPurpleReportRelease(releaseId, {
        approve,
        approver: "security_lead",
        note: approve ? "approved_from_purple_dashboard" : "rejected_from_purple_dashboard",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "purple_release_review_failed");
    } finally {
      setBusy(false);
    }
  };

  const latest = reports?.rows?.[0];
  const incidentTemplatePacks = (purpleTemplatePacks?.rows || []).filter((row) => row.kind === "incident_report");
  const regulatedTemplatePacks = (purpleTemplatePacks?.rows || []).filter((row) => row.kind === "regulated_report");
  const selectedRoiTemplate = (roiTemplatePacks?.rows || []).find((row) => row.pack_code === roiTemplatePack) || null;
  const latestRelease = reportReleases?.rows?.[0] || null;
  const latestAttackLayer = attackLayerWorkspaces?.rows?.[0] || null;

  return (
    <section className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Purple Team Service</h2>
        <button
          type="button"
          disabled={!selectedSite || busy}
          onClick={() => void generate()}
          className="rounded-md border border-accent/70 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/25 disabled:opacity-60"
        >
          Run AI Correlation
        </button>
        <button
          type="button"
          disabled={!selectedSite || busy}
          onClick={() => void generateIsoTemplate()}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-400 disabled:opacity-60"
        >
          ISO 27001 Gap
        </button>
        <button
          type="button"
          disabled={!selectedSite || busy}
          onClick={() => void generateNistTemplate()}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-400 disabled:opacity-60"
        >
          NIST CSF Gap
        </button>
        <button
          type="button"
          disabled={!selectedSite || busy}
          onClick={() => void loadCaseGraph()}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-400 disabled:opacity-60"
        >
          Unified Case Graph
        </button>
        <button
          type="button"
          disabled={!selectedSite || busy}
          onClick={() => void loadExecutive()}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-400 disabled:opacity-60"
        >
          Executive Scorecard
        </button>
        <button
          type="button"
          disabled={!selectedSite || busy}
          onClick={() => void generateRoiDashboard()}
          className="rounded-md border border-accent/70 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/25 disabled:opacity-60"
        >
          Generate ROI Dashboard
        </button>
        <button
          type="button"
          disabled={!selectedSite || busy}
          onClick={() => void exportRoiBoardPack()}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-400 disabled:opacity-60"
        >
          Build ROI Board Pack
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-400">AI correlates Red + Blue operations and generates strategic feedback.</p>

      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {PURPLE_SERVICE_MENUS.map((item) => (
          <div key={item.title} className="rounded-md border border-slate-800 bg-panelAlt/20 p-3 text-xs">
            <div className="flex items-center justify-between gap-2">
              <p className="font-semibold text-slate-100 wrap-anywhere">{item.title}</p>
              <span
                className={
                  "rounded-full border px-2 py-0.5 text-[10px] uppercase " +
                  (item.status === "live"
                    ? "border-accent/60 bg-accent/10 text-accent"
                    : "border-warning/60 bg-warning/10 text-warning")
                }
              >
                {item.status}
              </span>
            </div>
            <p className="mt-2 text-slate-300 wrap-anywhere">เหมาะกับ: {item.fit}</p>
            <p className="mt-1 text-slate-300 wrap-anywhere">Value: {item.value}</p>
            <p className="mt-2 text-[11px] text-slate-500 wrap-anywhere">{item.note}</p>
          </div>
        ))}
      </div>

      {loading ? <p className="mt-3 text-sm text-slate-400">Analyzing...</p> : null}
      {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}

      {latest ? (
        <div className="mt-3 space-y-2 rounded-md border border-slate-800 bg-panelAlt/30 p-3 text-xs">
          <p className="text-slate-100 wrap-anywhere">{latest.summary}</p>
          <p className="text-slate-300 wrap-anywhere">Metrics: {JSON.stringify(latest.metrics)}</p>
          <p className="text-slate-300 wrap-anywhere">AI: {JSON.stringify(latest.ai_analysis)}</p>
        </div>
      ) : (
        <p className="mt-3 text-xs text-slate-500">No purple report yet.</p>
      )}

      <div className="mt-3 max-h-44 overflow-auto rounded border border-slate-800 p-2">
        {(reports?.rows || []).map((row) => (
          <div key={row.report_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2 text-xs">
            <p className="text-slate-400 wrap-anywhere">{row.created_at}</p>
            <p className="mt-1 text-slate-200 wrap-anywhere">{row.summary}</p>
          </div>
        ))}
      </div>

      <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
        <p className="text-slate-300">ROI Security Dashboard</p>
        <div className="mt-2 grid grid-cols-3 gap-2">
          <label className="text-[11px] text-slate-400">
            Lookback Days
            <input
              type="number"
              min={1}
              max={365}
              value={roiLookbackDays}
              onChange={(event) => setRoiLookbackDays(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Analyst $/hour
            <input
              type="number"
              min={1}
              max={1000}
              value={roiHourlyCost}
              onChange={(event) => setRoiHourlyCost(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Minutes / alert
            <input
              type="number"
              min={1}
              max={240}
              value={roiMinutesPerAlert}
              onChange={(event) => setRoiMinutesPerAlert(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
        </div>
        <div className="mt-2 grid grid-cols-3 gap-2">
          <label className="text-[11px] text-slate-400">
            Export Format
            <select
              value={roiExportFormat}
              onChange={(event) => setRoiExportFormat(event.target.value as "pdf" | "ppt")}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              <option value="pdf">pdf</option>
              <option value="ppt">ppt</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400">
            Template Pack
            <select
              value={roiTemplatePack}
              onChange={(event) => setRoiTemplatePack(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              {(roiTemplatePacks?.rows || []).map((pack) => (
                <option key={pack.pack_code} value={pack.pack_code}>
                  {pack.display_name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-[11px] text-slate-400 col-span-2">
            Export Title Override
            <input
              type="text"
              value={roiExportTitle}
              onChange={(event) => setRoiExportTitle(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
        </div>
        {selectedRoiTemplate ? (
          <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">
              {selectedRoiTemplate.display_name} [{selectedRoiTemplate.audience}] accent=#{selectedRoiTemplate.accent_hex}
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">{selectedRoiTemplate.description}</p>
            <p className="mt-1 text-slate-500 wrap-anywhere">
              layout={selectedRoiTemplate.layout_style} cover={selectedRoiTemplate.cover_label} footer={selectedRoiTemplate.footer_label}
            </p>
            <p className="mt-1 text-slate-500 wrap-anywhere">sections={selectedRoiTemplate.section_order.join(" -> ")}</p>
          </div>
        ) : null}
        <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-300">
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={roiIncludePortfolio}
              onChange={(event) => setRoiIncludePortfolio(event.target.checked)}
            />
            include tenant portfolio roll-up
          </label>
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-3">
          <label className="text-[11px] text-slate-400">
            Trend Metric Focus
            <select
              value={roiTrendMetricFocus}
              onChange={(event) => setRoiTrendMetricFocus(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              <option value="">latest_first</option>
              <option value="validated_findings">validated_findings</option>
              <option value="automation_coverage_pct">automation_coverage_pct</option>
              <option value="noise_reduction_pct">noise_reduction_pct</option>
              <option value="estimated_manual_effort_saved_usd">estimated_manual_effort_saved_usd</option>
              <option value="high_risk_findings">high_risk_findings</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400">
            Trend Min Automation %
            <input
              type="number"
              min={0}
              max={100}
              value={roiTrendMinAutomationCoveragePct}
              onChange={(event) => setRoiTrendMinAutomationCoveragePct(Number(event.target.value || 0))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Trend Min Noise %
            <input
              type="number"
              min={0}
              max={100}
              value={roiTrendMinNoiseReductionPct}
              onChange={(event) => setRoiTrendMinNoiseReductionPct(Number(event.target.value || 0))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Portfolio Site Filter
            <input
              type="text"
              value={roiPortfolioSiteCodeFilter}
              onChange={(event) => setRoiPortfolioSiteCodeFilter(event.target.value)}
              placeholder="site_code"
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Portfolio Status
            <select
              value={roiPortfolioStatusFilter}
              onChange={(event) => setRoiPortfolioStatusFilter(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              <option value="">all</option>
              <option value="completed">completed</option>
              <option value="no_snapshot">no_snapshot</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400">
            Portfolio Sort By
            <select
              value={roiPortfolioSortBy}
              onChange={(event) => setRoiPortfolioSortBy(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              <option value="estimated_manual_effort_saved_usd">estimated_manual_effort_saved_usd</option>
              <option value="validated_findings">validated_findings</option>
              <option value="automation_coverage_pct">automation_coverage_pct</option>
              <option value="noise_reduction_pct">noise_reduction_pct</option>
              <option value="high_risk_findings">high_risk_findings</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400">
            Portfolio Min Automation %
            <input
              type="number"
              min={0}
              max={100}
              value={roiPortfolioMinAutomationCoveragePct}
              onChange={(event) => setRoiPortfolioMinAutomationCoveragePct(Number(event.target.value || 0))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Portfolio Min Noise %
            <input
              type="number"
              min={0}
              max={100}
              value={roiPortfolioMinNoiseReductionPct}
              onChange={(event) => setRoiPortfolioMinNoiseReductionPct(Number(event.target.value || 0))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <div className="flex items-end">
            <button
              type="button"
              disabled={loading}
              onClick={() => void load()}
              className="rounded-md border border-slate-600 px-3 py-1.5 text-[11px] text-slate-100 hover:border-slate-400 disabled:opacity-60"
            >
              Reload ROI Slice
            </button>
          </div>
        </div>
        {(roiSnapshots?.rows || []).length > 0 ? (
          <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">{String(roiSnapshots?.rows[0].summary?.headline_th || "")}</p>
            <p className="mt-1 text-slate-400 wrap-anywhere">{String(roiSnapshots?.rows[0].summary?.board_statement_th || "")}</p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              validated_findings=
              {String((roiSnapshots?.rows[0].summary?.board_metrics as Record<string, unknown> | undefined)?.validated_findings ?? 0)}
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              automation_coverage_pct=
              {String((roiSnapshots?.rows[0].summary?.board_metrics as Record<string, unknown> | undefined)?.automation_coverage_pct ?? 0)}
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              estimated_manual_effort_saved_usd=
              {String((roiSnapshots?.rows[0].summary?.board_metrics as Record<string, unknown> | undefined)?.estimated_manual_effort_saved_usd ?? 0)}
            </p>
          </div>
        ) : (
          <p className="mt-2 text-slate-500">No ROI snapshot yet.</p>
        )}
        {roiTrends ? (
          <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-300">
              Trend: points={roiTrends.summary.trend_points} direction={roiTrends.summary.direction} latest={roiTrends.summary.latest_created_at || "n/a"}
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              delta validated={roiTrends.summary.validated_findings_delta} automation={roiTrends.summary.automation_coverage_delta_pct}
              noise={roiTrends.summary.noise_reduction_delta_pct} saved_usd={roiTrends.summary.estimated_manual_effort_saved_delta_usd}
            </p>
            <p className="mt-1 text-slate-500 wrap-anywhere">
              focus={roiTrends.summary.metric_focus || "latest_first"} filtered_out={roiTrends.summary.filtered_out_count}
              filters={JSON.stringify(roiTrends.summary.applied_filters)}
            </p>
            <div className="mt-2 max-h-32 overflow-auto rounded border border-slate-800 p-2">
              {(roiTrends.rows || []).slice(0, 6).map((row) => (
                <p key={row.snapshot_id} className="text-slate-300 wrap-anywhere">
                  {row.created_at} findings={row.validated_findings} auto={row.automation_coverage_pct}% noise={row.noise_reduction_pct}% saved=${row.estimated_manual_effort_saved_usd}
                </p>
              ))}
            </div>
          </div>
        ) : null}
        {roiPortfolio ? (
          <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-300">
              Portfolio: tenant={roiPortfolio.summary.tenant_code || selectedSite?.tenant_code || "all"} sites={roiPortfolio.summary.total_sites}
              snapshots={roiPortfolio.summary.sites_with_snapshots} avg_auto={roiPortfolio.summary.average_automation_coverage_pct}%
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              total_validated={roiPortfolio.summary.total_validated_findings} total_saved_usd={roiPortfolio.summary.total_estimated_manual_effort_saved_usd}
              top_site={roiPortfolio.summary.highest_value_site_code || "n/a"}
            </p>
            <p className="mt-1 text-slate-500 wrap-anywhere">
              sort_by={roiPortfolio.summary.sort_by} filtered_total={roiPortfolio.summary.total_sites} from={roiPortfolio.summary.total_sites_before_filter}
              filters={JSON.stringify(roiPortfolio.summary.applied_filters)}
            </p>
            <div className="mt-2 max-h-36 overflow-auto rounded border border-slate-800 p-2">
              {(roiPortfolio.rows || []).slice(0, 6).map((row) => (
                <p key={row.site_id} className="text-slate-300 wrap-anywhere">
                  {row.tenant_code}/{row.site_code} [{row.status}] findings={row.validated_findings} auto={row.automation_coverage_pct}% noise={row.noise_reduction_pct}% saved=${row.estimated_manual_effort_saved_usd}
                </p>
              ))}
            </div>
          </div>
        ) : null}
        {roiExport ? (
          <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">
              Export Pack: {roiExport.export.title} {"->"} {roiExport.export.filename}
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              format={roiExport.export.export_format} renderer={roiExport.export.renderer} mime={roiExport.export.mime_type} size={roiExport.export.byte_size}B
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              template={roiExport.export.template_pack.display_name} includes_portfolio={String(roiExport.export.includes_portfolio)} generated={roiExport.export.generated_at}
            </p>
            <a
              href={`data:${roiExport.export.mime_type};base64,${roiExport.export.content_base64}`}
              download={roiExport.export.filename}
              className="mt-2 inline-flex rounded-md border border-accent/70 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/25"
            >
              Download Native {roiExport.export.export_format === "ppt" ? "PPTX" : "PDF"}
            </a>
            <div className="mt-2 max-h-36 overflow-auto rounded border border-slate-800 p-2">
              {roiExport.export.sections.map((section) => (
                <div key={section.section} className="mb-2">
                  <p className="text-slate-200 wrap-anywhere">{section.section}</p>
                  {section.content.map((line, index) => (
                    <p key={`${section.section}-${index}`} className="text-slate-400 wrap-anywhere">
                      {line}
                    </p>
                  ))}
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-3 text-xs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-slate-200">Purple Plugin Export Layer</p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              Export MITRE heatmap, incident packs, และ regulatory outputs จาก evidence ล่าสุดของ Red/Blue/Purple
            </p>
          </div>
          <p className="text-[11px] text-slate-500">
            packs={purpleTemplatePacks?.count ?? 0} incident={incidentTemplatePacks.length} regulated={regulatedTemplatePacks.length}
          </p>
        </div>

        {(purpleTemplatePacks?.rows || []).length > 0 ? (
          <div className="mt-2 max-h-32 overflow-auto rounded border border-slate-800 bg-panelAlt/30 p-2">
            {purpleTemplatePacks?.rows.map((pack) => (
              <div key={pack.pack_code} className="mb-2 rounded border border-slate-800 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {pack.display_name} [{pack.kind}] audience={pack.audience}
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">{pack.description}</p>
                <p className="mt-1 text-slate-500 wrap-anywhere">sections: {pack.sections.join(", ")}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-2 text-slate-500">No export template packs loaded.</p>
        )}

        <div className="mt-3 grid gap-3 xl:grid-cols-3">
          <div className="rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-300">MITRE Heatmap Export</p>
            <div className="mt-2 grid gap-2">
              <label className="text-[11px] text-slate-400">
                Format
                <select
                  value={purpleMitreExportFormat}
                  onChange={(event) =>
                    setPurpleMitreExportFormat(event.target.value as "markdown" | "csv" | "attack_layer_json" | "svg")
                  }
                  className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
                >
                  <option value="markdown">markdown</option>
                  <option value="csv">csv</option>
                  <option value="attack_layer_json">attack_layer_json</option>
                  <option value="svg">svg</option>
                </select>
              </label>
              <label className="flex items-center gap-2 text-[11px] text-slate-300">
                <input
                  type="checkbox"
                  checked={purpleMitreIncludeRecommendations}
                  onChange={(event) => setPurpleMitreIncludeRecommendations(event.target.checked)}
                />
                include recommendations
              </label>
              <button
                type="button"
                disabled={!selectedSite || busy}
                onClick={() => void exportMitreHeatmap()}
                className="rounded-md border border-accent/70 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/25 disabled:opacity-60"
              >
                Export MITRE Heatmap
              </button>
            </div>
            {mitreExport ? (
              <div className="mt-2 rounded border border-slate-800 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {mitreExport.export.filename} [{mitreExport.export.export_format}]
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">
                  attacked={String(mitreExport.export.summary.attacked_techniques ?? 0)} covered=
                  {String(mitreExport.export.summary.covered_techniques ?? 0)} sla=
                  {String(mitreExport.export.remediation_sla.sla_status ?? "unknown")}
                </p>
                <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words text-[11px] text-slate-400">
                  {mitreExport.export.content}
                </pre>
              </div>
            ) : null}
          </div>

          <div className="rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-300">Incident Report Export</p>
            <div className="mt-2 grid gap-2">
              <label className="text-[11px] text-slate-400">
                Template Pack
                <select
                  value={purpleIncidentTemplatePack}
                  onChange={(event) => setPurpleIncidentTemplatePack(event.target.value)}
                  className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
                >
                  {incidentTemplatePacks.map((pack) => (
                    <option key={pack.pack_code} value={pack.pack_code}>
                      {pack.display_name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-[11px] text-slate-400">
                Format
                <select
                  value={purpleIncidentExportFormat}
                  onChange={(event) => setPurpleIncidentExportFormat(event.target.value as "markdown" | "json" | "pdf" | "docx")}
                  className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
                >
                  <option value="markdown">markdown</option>
                  <option value="json">json</option>
                  <option value="pdf">pdf</option>
                  <option value="docx">docx</option>
                </select>
              </label>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={!selectedSite || busy}
                  onClick={() => void exportIncidentReport()}
                  className="rounded-md border border-accent/70 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/25 disabled:opacity-60"
                >
                  Export Incident Report
                </button>
                <button
                  type="button"
                  disabled={!selectedSite || busy || !incidentExport}
                  onClick={() => void requestRelease("incident_report")}
                  className="rounded-md border border-warning/60 bg-warning/10 px-3 py-1.5 text-xs font-semibold text-warning hover:bg-warning/20 disabled:opacity-60"
                >
                  Request Final Release
                </button>
              </div>
            </div>
            {incidentExport ? (
              <div className="mt-2 rounded border border-slate-800 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {incidentExport.export.filename} [{incidentExport.export.export_format}]
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">
                  renderer={incidentExport.export.renderer || "text"} mime={incidentExport.export.mime_type || "text/plain"} size=
                  {String(incidentExport.export.byte_size || 0)}B
                </p>
                {incidentExport.export.content_base64 ? (
                  <a
                    href={`data:${incidentExport.export.mime_type || "application/octet-stream"};base64,${incidentExport.export.content_base64}`}
                    download={incidentExport.export.filename}
                    className="mt-2 inline-flex rounded-md border border-accent/70 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/25"
                  >
                    Download Native {incidentExport.export.export_format.toUpperCase()}
                  </a>
                ) : null}
                <div className="mt-2 max-h-40 overflow-auto rounded border border-slate-800 p-2">
                  {incidentExport.export.sections.map((section) => (
                    <div key={section.section} className="mb-2">
                      <p className="text-slate-200 wrap-anywhere">{section.section}</p>
                      {section.content.map((line, index) => (
                        <p key={`${section.section}-${index}`} className="text-slate-400 wrap-anywhere">
                          {line}
                        </p>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>

          <div className="rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-300">Regulated Report Export</p>
            <div className="mt-2 grid gap-2">
              <label className="text-[11px] text-slate-400">
                Template Pack
                <select
                  value={purpleRegulatedTemplatePack}
                  onChange={(event) => setPurpleRegulatedTemplatePack(event.target.value)}
                  className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
                >
                  {regulatedTemplatePacks.map((pack) => (
                    <option key={pack.pack_code} value={pack.pack_code}>
                      {pack.display_name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-[11px] text-slate-400">
                Format
                <select
                  value={purpleRegulatedExportFormat}
                  onChange={(event) => setPurpleRegulatedExportFormat(event.target.value as "markdown" | "json" | "pdf" | "docx")}
                  className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
                >
                  <option value="markdown">markdown</option>
                  <option value="json">json</option>
                  <option value="pdf">pdf</option>
                  <option value="docx">docx</option>
                </select>
              </label>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={!selectedSite || busy}
                  onClick={() => void exportRegulatedReport()}
                  className="rounded-md border border-accent/70 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/25 disabled:opacity-60"
                >
                  Export Regulated Report
                </button>
                <button
                  type="button"
                  disabled={!selectedSite || busy || !regulatedExport}
                  onClick={() => void requestRelease("regulated_report")}
                  className="rounded-md border border-warning/60 bg-warning/10 px-3 py-1.5 text-xs font-semibold text-warning hover:bg-warning/20 disabled:opacity-60"
                >
                  Request Final Release
                </button>
              </div>
            </div>
            {regulatedExport ? (
              <div className="mt-2 rounded border border-slate-800 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {regulatedExport.export.filename} [{regulatedExport.export.export_format}]
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">
                  renderer={regulatedExport.export.renderer || "text"} mime={regulatedExport.export.mime_type || "text/plain"} size=
                  {String(regulatedExport.export.byte_size || 0)}B
                </p>
                {regulatedExport.export.content_base64 ? (
                  <a
                    href={`data:${regulatedExport.export.mime_type || "application/octet-stream"};base64,${regulatedExport.export.content_base64}`}
                    download={regulatedExport.export.filename}
                    className="mt-2 inline-flex rounded-md border border-accent/70 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/25"
                  >
                    Download Native {regulatedExport.export.export_format.toUpperCase()}
                  </a>
                ) : null}
                <div className="mt-2 max-h-40 overflow-auto rounded border border-slate-800 p-2">
                  {regulatedExport.export.sections.map((section) => (
                    <div key={section.section} className="mb-2">
                      <p className="text-slate-200 wrap-anywhere">{section.section}</p>
                      {section.content.map((line, index) => (
                        <p key={`${section.section}-${index}`} className="text-slate-400 wrap-anywhere">
                          {line}
                        </p>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-2">
        <div className="rounded border border-slate-800 bg-panelAlt/20 p-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-slate-200">Policy / Evidence Control Family Map</p>
              <p className="mt-1 text-slate-400 wrap-anywhere">
                Map Red/Blue/Purple evidence ลง ISO 27001 และ NIST CSF control families พร้อม export
              </p>
            </div>
            <button
              type="button"
              disabled={!selectedSite || busy}
              onClick={() => void exportControlFamilyMap()}
              className="rounded-md border border-accent/70 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/25 disabled:opacity-60"
            >
              Build Control Map
            </button>
          </div>
          <div className="mt-2 grid gap-2 md:grid-cols-2">
            <label className="text-[11px] text-slate-400">
              Framework
              <select
                value={controlFamilyFramework}
                onChange={(event) => setControlFamilyFramework(event.target.value as "combined" | "iso27001" | "nist_csf")}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              >
                <option value="combined">combined</option>
                <option value="iso27001">iso27001</option>
                <option value="nist_csf">nist_csf</option>
              </select>
            </label>
            <label className="text-[11px] text-slate-400">
              Export Format
              <select
                value={controlFamilyExportFormat}
                onChange={(event) => setControlFamilyExportFormat(event.target.value as "markdown" | "csv" | "json")}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              >
                <option value="markdown">markdown</option>
                <option value="csv">csv</option>
                <option value="json">json</option>
              </select>
            </label>
          </div>
          {controlFamilyMap ? (
            <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
              <p className="text-slate-300">
                families={controlFamilyMap.summary.family_count} implemented={controlFamilyMap.summary.implemented_family_count} partial=
                {controlFamilyMap.summary.partial_family_count} gap={controlFamilyMap.summary.gap_family_count}
              </p>
              <div className="mt-2 max-h-40 overflow-auto rounded border border-slate-800 p-2">
                {controlFamilyMap.rows.slice(0, 8).map((row) => (
                  <div key={`${row.framework}-${row.family_code}`} className="mb-2">
                    <p className="text-slate-200 wrap-anywhere">
                      {row.framework} {row.family_code} [{row.coverage_status}] coverage={row.coverage_pct}
                    </p>
                    <p className="text-slate-400 wrap-anywhere">
                      policies={row.policy_refs.join(", ") || "-"} evidence={row.evidence_refs.join(", ") || "-"}
                    </p>
                    <p className="text-slate-500 wrap-anywhere">top_gaps={row.top_gaps.join(", ") || "-"}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {controlFamilyExport ? (
            <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
              <p className="text-slate-200 wrap-anywhere">
                {controlFamilyExport.export.filename} [{controlFamilyExport.export.export_format}]
              </p>
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words text-[11px] text-slate-400">
                {controlFamilyExport.export.content}
              </pre>
            </div>
          ) : null}
        </div>

        <div className="rounded border border-slate-800 bg-panelAlt/20 p-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-slate-200">ATT&CK Layer Import / Edit / Graphical Export</p>
              <p className="mt-1 text-slate-400 wrap-anywhere">
                Import ATT&CK layer JSON, apply technique overrides, export workspace or live graphical layer
              </p>
            </div>
            <button
              type="button"
              disabled={!selectedSite || busy}
              onClick={() => void exportAttackGraphic()}
              className="rounded-md border border-accent/70 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/25 disabled:opacity-60"
            >
              Export Live Layer
            </button>
          </div>
          <div className="mt-2 grid gap-2">
            <label className="text-[11px] text-slate-400">
              Layer Name
              <input
                type="text"
                value={attackLayerImportName}
                onChange={(event) => setAttackLayerImportName(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Notes
              <input
                type="text"
                value={attackLayerImportNotes}
                onChange={(event) => setAttackLayerImportNotes(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Import Layer JSON
              <textarea
                value={attackLayerImportJson}
                onChange={(event) => setAttackLayerImportJson(event.target.value)}
                rows={7}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 font-mono text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Technique Overrides JSON
              <textarea
                value={attackLayerOverrideJson}
                onChange={(event) => setAttackLayerOverrideJson(event.target.value)}
                rows={5}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 font-mono text-[11px] text-slate-100"
              />
            </label>
            <div className="grid gap-2 md:grid-cols-[1fr_auto_auto]">
              <label className="text-[11px] text-slate-400">
                Export Format
                <select
                  value={attackLayerExportFormat}
                  onChange={(event) => setAttackLayerExportFormat(event.target.value as "attack_layer_json" | "svg")}
                  className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
                >
                  <option value="attack_layer_json">attack_layer_json</option>
                  <option value="svg">svg</option>
                </select>
              </label>
              <button
                type="button"
                disabled={!selectedSite || busy}
                onClick={() => void importAttackLayer()}
                className="self-end rounded-md border border-accent/70 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/25 disabled:opacity-60"
              >
                Import Layer
              </button>
              <button
                type="button"
                disabled={!selectedSite || busy || !latestAttackLayer}
                onClick={() => (latestAttackLayer ? void updateAttackLayer(latestAttackLayer.workspace_id) : undefined)}
                className="self-end rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-100 hover:border-slate-400 disabled:opacity-60"
              >
                Apply Overrides
              </button>
            </div>
          </div>
          <div className="mt-2 max-h-44 overflow-auto rounded border border-slate-800 bg-panelAlt/30 p-2">
            {(attackLayerWorkspaces?.rows || []).length === 0 ? <p className="text-slate-500">No imported attack layers yet.</p> : null}
            {(attackLayerWorkspaces?.rows || []).map((row) => (
              <div key={row.workspace_id} className="mb-2 rounded border border-slate-800 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {row.layer_name} [{row.source_kind}] techniques={String(row.summary.technique_count ?? 0)}
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">{row.notes || "no notes"}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void exportAttackLayer(row.workspace_id)}
                    className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-100 hover:border-slate-400 disabled:opacity-60"
                  >
                    Export Workspace
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      setAttackLayerImportName(row.layer_name);
                      setAttackLayerImportNotes(row.notes || "");
                      setAttackLayerImportJson(JSON.stringify(row.layer, null, 2));
                    }}
                    className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-100 hover:border-slate-400 disabled:opacity-60"
                  >
                    Load Into Editor
                  </button>
                </div>
              </div>
            ))}
          </div>
          {attackLayerExport ? (
            <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
              <p className="text-slate-200 wrap-anywhere">
                {attackLayerExport.export.filename} [{attackLayerExport.export.export_format}]
              </p>
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words text-[11px] text-slate-400">
                {attackLayerExport.export.content}
              </pre>
            </div>
          ) : null}
          {attackLayerGraphicExport ? (
            <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
              <p className="text-slate-200 wrap-anywhere">
                {attackLayerGraphicExport.export.filename} [{attackLayerGraphicExport.export.export_format}]
              </p>
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words text-[11px] text-slate-400">
                {attackLayerGraphicExport.export.content}
              </pre>
            </div>
          ) : null}
        </div>
      </div>

      <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-3 text-xs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-slate-200">Final Report Release Approval</p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              ใช้ workflow นี้เพื่อขออนุมัติ report ขั้นสุดท้ายหลัง export เป็น markdown/json/pdf/docx แล้ว
            </p>
          </div>
          <p className="text-[11px] text-slate-500">
            latest={latestRelease?.status || "none"} count={reportReleases?.count ?? 0}
          </p>
        </div>
        <div className="mt-2 max-h-48 overflow-auto rounded border border-slate-800 bg-panelAlt/30 p-2">
          {(reportReleases?.rows || []).map((row) => (
            <div key={row.release_id} className="mb-2 rounded border border-slate-800 p-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-slate-200 wrap-anywhere">
                  {row.report_kind} [{row.export_format}] {row.filename}
                </p>
                <span
                  className={
                    "rounded-full border px-2 py-0.5 text-[10px] uppercase " +
                    (row.status === "approved"
                      ? "border-accent/60 bg-accent/10 text-accent"
                      : row.status === "rejected"
                        ? "border-danger/60 bg-danger/10 text-danger"
                        : "border-warning/60 bg-warning/10 text-warning")
                  }
                >
                  {row.status}
                </span>
              </div>
              <p className="mt-1 text-slate-400 wrap-anywhere">
                requested_by={row.requested_by} approved_by={row.approved_by || "-"} created={row.created_at}
              </p>
              <p className="mt-1 text-slate-500 wrap-anywhere">{row.note || "no note"}</p>
              <p className="mt-1 text-slate-500 wrap-anywhere">
                renderer={String(row.payload.renderer || "text")} size={String(row.payload.byte_size || 0)} generated=
                {String(row.payload.generated_at || "-")}
              </p>
              {row.status === "pending_approval" ? (
                <div className="mt-2 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void reviewRelease(row.release_id, true)}
                    className="rounded-md border border-accent/70 bg-accent/15 px-3 py-1.5 text-xs font-semibold text-accent hover:bg-accent/25 disabled:opacity-60"
                  >
                    Approve Release
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void reviewRelease(row.release_id, false)}
                    className="rounded-md border border-danger/60 bg-danger/10 px-3 py-1.5 text-xs font-semibold text-danger hover:bg-danger/20 disabled:opacity-60"
                  >
                    Reject Release
                  </button>
                </div>
              ) : null}
            </div>
          ))}
          {(reportReleases?.rows || []).length === 0 ? <p className="text-slate-500">No report releases requested yet.</p> : null}
        </div>
      </div>

      {isoTemplate ? (
        <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
          <p className="text-slate-200 wrap-anywhere">
            {isoTemplate.framework} | controls: {isoTemplate.controls.length} | generated: {isoTemplate.summary.generated_at}
          </p>
          <div className="mt-2 space-y-1">
            {isoTemplate.controls.slice(0, 4).map((control) => (
              <p key={control.control_id} className="text-slate-300 wrap-anywhere">
                {control.control_id} [{control.status}] {control.control_name}
              </p>
            ))}
          </div>
        </div>
      ) : null}

      {caseGraph ? (
        <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
          <p className="text-slate-200 wrap-anywhere">
            Case Graph: nodes={caseGraph.summary.node_count} edges={caseGraph.summary.edge_count} exploit_paths=
            {caseGraph.summary.exploit_paths} blue_events={caseGraph.summary.blue_events} rules={caseGraph.summary.detection_rules}
            soar={caseGraph.summary.soar_executions ?? 0} connector={caseGraph.summary.connector_events ?? 0} replay_runs=
            {caseGraph.summary.connector_replay_runs ?? 0} risk={caseGraph.summary.risk_tier ?? "unknown"}(
            {caseGraph.summary.risk_score ?? 0})
          </p>
          {caseGraph.risk ? (
            <p className="mt-1 text-slate-300 wrap-anywhere">
              Risk details: max_exploit={caseGraph.risk.max_exploit_risk} high_blue={caseGraph.risk.high_blue_events} pending_soar=
              {caseGraph.risk.pending_soar_executions} unresolved_dlq={caseGraph.risk.unresolved_connector_dlq} recommendation=
              {caseGraph.risk.recommendation}
            </p>
          ) : null}
          <div className="mt-2 max-h-28 overflow-auto rounded border border-slate-800 p-2">
            {(caseGraph.timeline || []).length === 0 ? <p className="text-slate-500">No case timeline yet.</p> : null}
            {(caseGraph.timeline || []).slice(0, 6).map((row, index) => (
              <p key={`${row.node_id}-${index}`} className="text-slate-300 wrap-anywhere">
                {row.timestamp} [{row.source}] {row.summary}
              </p>
            ))}
          </div>
        </div>
      ) : null}

      {executive ? (
        <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
          <p className="text-slate-200 wrap-anywhere">
            MITRE coverage={executive.summary.heatmap_coverage} attacked={executive.summary.attacked_techniques} covered=
            {executive.summary.covered_techniques} partial={executive.summary.partial_techniques}
          </p>
          <p className="mt-1 text-slate-300 wrap-anywhere">
            Remediation SLA: status={executive.remediation_sla.sla_status} mttr={executive.remediation_sla.estimated_mttr_seconds}s
            / target={executive.remediation_sla.target_mttr_seconds}s apply_rate={executive.remediation_sla.apply_rate}
          </p>
          <div className="mt-2 max-h-36 overflow-auto rounded border border-slate-800 p-2">
            {executive.heatmap.length === 0 ? <p className="text-slate-500">No MITRE technique evidence yet.</p> : null}
            {executive.heatmap.slice(0, 8).map((row) => (
              <p key={row.technique_id} className="text-slate-300 wrap-anywhere">
                {row.technique_id} [{row.detection_status}] mitigation={row.mitigation_time_seconds ?? "-"}s
              </p>
            ))}
          </div>
        </div>
      ) : null}

      {federation ? (
        <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
          <p className="text-slate-200 wrap-anywhere">
            Federation: sites={federation.count} pass={federation.passing_sites} at_risk={federation.at_risk_sites}
          </p>
          <div className="mt-2 max-h-36 overflow-auto rounded border border-slate-800 p-2">
            {federation.rows.slice(0, 8).map((row) => (
              <p key={row.site_id} className="text-slate-300 wrap-anywhere">
                {row.tenant_code}/{row.site_code} coverage={row.heatmap_coverage} sla={row.sla_status} mttr=
                {row.estimated_mttr_seconds}s
              </p>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
