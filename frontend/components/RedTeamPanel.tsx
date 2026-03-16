import { useMemo, useState } from "react";

import {
  fetchSiteExploitPathRuns,
  fetchSiteCoworkerPluginRuns,
  fetchSiteRedExploitAutopilotPolicy,
  fetchSiteRedExploitAutopilotRuns,
  fetchSiteRedShadowPentestAssets,
  fetchSiteRedShadowPentestPolicy,
  fetchSiteRedShadowPentestRuns,
  fetchSiteRedPluginIntelligence,
  fetchSiteRedPluginSafetyPolicy,
  fetchSiteRedPluginSyncRuns,
  fetchSiteRedPluginSyncSources,
  fetchSiteRedSocialPolicy,
  fetchSiteRedSocialRoster,
  fetchSiteRedScans,
  fetchSiteRedSocialSimulatorRuns,
  fetchSiteRedSocialTelemetry,
  fetchSiteRedVulnerabilityFindings,
  fetchSiteRedVulnerabilityRemediationExport,
  fetchSiteRedVulnerabilityValidationRuns,
  fetchThreatContentPipelineFederation,
  fetchThreatContentPipelinePolicy,
  fetchThreatContentPipelineRuns,
  fetchThreatContentPacks,
  exportSiteRedPluginOutput,
  ingestSiteRedSocialProviderCallback,
  importSiteRedPluginIntelligence,
  importSiteRedSocialRoster,
  importSiteRedVulnerabilityFindings,
  killSiteRedSocialCampaign,
  lintSiteRedPluginOutput,
  publishSiteRedTemplateThreatPack,
  reviewSiteRedSocialCampaign,
  runRedExploitAutopilotScheduler,
  runRedPluginSyncScheduler,
  runRedShadowPentestScheduler,
  runSiteCoworkerPlugin,
  runSiteRedPluginSync,
  runSiteRedExploitAutopilot,
  runSiteRedScan,
  runSiteRedShadowPentest,
  runSiteRedSocialSimulator,
  runSiteRedVulnerabilityValidator,
  runThreatContentPipeline,
  runThreatContentPipelineScheduler,
  simulateSiteExploitPath,
  triggerSiteRedShadowPentestDeployEvent,
  upsertSiteCoworkerPluginBinding,
  upsertSiteRedSocialPolicy,
  upsertSiteRedPluginSafetyPolicy,
  upsertSiteRedPluginSyncSource,
  upsertThreatContentPipelinePolicy,
  upsertSiteRedExploitAutopilotPolicy,
  upsertSiteRedShadowPentestPolicy,
} from "@/lib/api";
import type {
  RedPluginIntelligenceRow,
  SiteExploitPathRunsResponse,
  SiteCoworkerPluginRunListResponse,
  SiteRedExploitAutopilotPolicyResponse,
  SiteRedExploitAutopilotRunListResponse,
  SiteRedShadowPentestAssetResponse,
  SiteRedShadowPentestPolicyResponse,
  SiteRedShadowPentestRunListResponse,
  SiteRedPluginExportResponse,
  SiteRedPluginIntelligenceResponse,
  SiteRedPluginLintResponse,
  SiteRedPluginSafetyPolicyResponse,
  SiteRedPluginSyncRunsResponse,
  SiteRedPluginSyncSourcesResponse,
  SiteRedPluginThreatPackPublishResponse,
  SiteRedScanHistoryResponse,
  SiteRedSocialPolicyResponse,
  SiteRedSocialProviderCallbackResponse,
  SiteRedSocialRosterResponse,
  SiteRedSocialSimulatorRunListResponse,
  SiteRedSocialTelemetryResponse,
  SiteRedVulnerabilityFindingListResponse,
  SiteRedVulnerabilityRemediationExportResponse,
  SiteRedVulnerabilityValidationRunListResponse,
  SiteRow,
  ThreatContentPipelineFederationResponse,
  ThreatContentPipelinePolicyResponse,
  ThreatContentPipelineRunListResponse,
  ThreatContentPackRow,
} from "@/lib/types";

type Props = {
  sites: SiteRow[];
  selectedSiteId: string;
  onSelectSite: (siteId: string) => void;
  canView: boolean;
  canEditPolicy: boolean;
  canApprove: boolean;
};

const SCAN_CASES = [
  { key: "baseline_scan", label: "Baseline Web Scan" },
  { key: "vuln_scan", label: "Vulnerability Sweep" },
  { key: "pentest_sim", label: "Pentest Simulation" },
];

const RED_SERVICE_MENUS = [
  {
    title: "24/7 Shadow Pentest",
    fit: "บริษัทที่อัปเดตเว็บหรือแอปบ่อย",
    value: "ตรวจเชิงรุกแบบต่อเนื่องโดยไม่ต้องรอ pentest รายปี",
    status: "live",
    note: "Passive crawl, diff-based drift detection, zero-day pack auto-assignment, and continuous safe schedule policy",
  },
  {
    title: "Social Engineering Simulator",
    fit: "องค์กรใหญ่ที่มีพนักงานจำนวนมาก",
    value: "ทดสอบ phishing ภาษาไทยตามบริบทภัยในไทยเพื่อลด human risk",
    status: "live",
    note: "Thai-language phishing simulation workflow with campaign history and safe dry-run mode",
  },
  {
    title: "Vulnerability Auto-Validator",
    fit: "ทีม IT Security ที่ต้องคัด false positive จำนวนมาก",
    value: "AI ยืนยันว่า finding ไหนเจาะได้จริงก่อนส่งให้ทีมแก้ไข",
    status: "live",
    note: "Mapped to Exploit Path Simulation + validation summaries",
  },
];

type RiskTier = "low" | "medium" | "high" | "critical";
type ValidatorSourceTool = "nessus" | "burp" | "generic";
type SocialConnectorType = "simulated" | "smtp" | "webhook";

const VULN_IMPORT_SAMPLES: Record<ValidatorSourceTool, string> = {
  nessus: JSON.stringify(
    {
      findings: [
        {
          plugin_id: "11219",
          plugin_name: "Web Application Potentially Vulnerable to SQL Injection",
          severity: "high",
          cve: "CVE-2024-12345",
          host: "duck-sec-ai.vercel.app",
          path: "/admin/login",
          description: "Potential SQL injection in admin login parameter.",
          solution: "Sanitize parameters and deploy WAF rule.",
          evidence: "error-based SQL response observed",
        },
      ],
    },
    null,
    2,
  ),
  burp: JSON.stringify(
    {
      issues: [
        {
          issue_id: "burp-01",
          issue_name: "Reflected cross-site scripting",
          severity: "medium",
          url: "https://duck-sec-ai.vercel.app/search?q=test",
          description: "User-controlled parameter is reflected without proper encoding.",
          remediation: "Encode output and add CSP.",
          request: "GET /search?q=<script>alert(1)</script>",
        },
      ],
    },
    null,
    2,
  ),
  generic: JSON.stringify(
    {
      findings: [
        {
          finding_id: "generic-01",
          title: "Exposed admin endpoint without strong protection",
          severity: "medium",
          endpoint: "/admin",
          asset: "duck-sec-ai.vercel.app",
          description: "Administrative panel exposed to public internet.",
          remediation: "Restrict by IP and enforce MFA.",
        },
      ],
    },
    null,
    2,
  ),
};

const SOCIAL_ROSTER_SAMPLE = JSON.stringify(
  {
    entries: [
      {
        employee_code: "EMP-001",
        full_name: "Narisara Chaiyo",
        email: "narisara@duck-sec-ai.vercel.app",
        department: "finance",
        role_title: "Accounting Officer",
        locale: "th",
        risk_level: "high",
        tags: ["finance", "privileged"],
      },
      {
        employee_code: "EMP-002",
        full_name: "Anucha Suksawat",
        email: "anucha@duck-sec-ai.vercel.app",
        department: "hr",
        role_title: "HR Manager",
        locale: "th",
        risk_level: "medium",
        tags: ["hr"],
      },
      {
        employee_code: "EMP-003",
        full_name: "Kornkanok Phet",
        email: "kornkanok@duck-sec-ai.vercel.app",
        department: "it",
        role_title: "IT Support",
        locale: "th",
        risk_level: "medium",
        tags: ["it", "support"],
      },
    ],
  },
  null,
  2,
);

export function RedTeamPanel({ sites, selectedSiteId, onSelectSite, canView, canEditPolicy, canApprove }: Props) {
  const [busyKey, setBusyKey] = useState("");
  const [error, setError] = useState("");
  const [historyBySite, setHistoryBySite] = useState<Record<string, SiteRedScanHistoryResponse>>({});
  const [exploitRunsBySite, setExploitRunsBySite] = useState<Record<string, SiteExploitPathRunsResponse>>({});
  const [threatPacks, setThreatPacks] = useState<ThreatContentPackRow[]>([]);
  const [autopilotPolicyBySite, setAutopilotPolicyBySite] = useState<Record<string, SiteRedExploitAutopilotPolicyResponse["policy"]>>({});
  const [autopilotRunsBySite, setAutopilotRunsBySite] = useState<Record<string, SiteRedExploitAutopilotRunListResponse>>({});
  const [socialPolicyBySite, setSocialPolicyBySite] = useState<Record<string, SiteRedSocialPolicyResponse["policy"]>>({});
  const [socialRosterBySite, setSocialRosterBySite] = useState<Record<string, SiteRedSocialRosterResponse>>({});
  const [socialRunsBySite, setSocialRunsBySite] = useState<Record<string, SiteRedSocialSimulatorRunListResponse>>({});
  const [socialTelemetryBySite, setSocialTelemetryBySite] = useState<Record<string, SiteRedSocialTelemetryResponse>>({});
  const [validatorFindingsBySite, setValidatorFindingsBySite] = useState<Record<string, SiteRedVulnerabilityFindingListResponse>>({});
  const [validatorRunsBySite, setValidatorRunsBySite] = useState<Record<string, SiteRedVulnerabilityValidationRunListResponse>>({});
  const [validatorExportBySite, setValidatorExportBySite] = useState<Record<string, SiteRedVulnerabilityRemediationExportResponse>>({});
  const [pluginRunsBySite, setPluginRunsBySite] = useState<Record<string, SiteCoworkerPluginRunListResponse>>({});
  const [shadowPolicyBySite, setShadowPolicyBySite] = useState<Record<string, SiteRedShadowPentestPolicyResponse["policy"]>>({});
  const [shadowRunsBySite, setShadowRunsBySite] = useState<Record<string, SiteRedShadowPentestRunListResponse>>({});
  const [shadowAssetsBySite, setShadowAssetsBySite] = useState<Record<string, SiteRedShadowPentestAssetResponse>>({});
  const [shadowRunSummary, setShadowRunSummary] = useState("No shadow pentest run yet");
  const [autopilotRunSummary, setAutopilotRunSummary] = useState("No autopilot run yet");
  const [validatorSummary, setValidatorSummary] = useState("No validator run yet");
  const [pipelineScope, setPipelineScope] = useState("global");
  const [pipelinePolicySummary, setPipelinePolicySummary] = useState("No threat-content pipeline policy loaded");
  const [pipelineRunSummary, setPipelineRunSummary] = useState("No pipeline run yet");
  const [pipelineRuns, setPipelineRuns] = useState<ThreatContentPipelineRunListResponse | null>(null);
  const [pipelineFederation, setPipelineFederation] = useState<ThreatContentPipelineFederationResponse | null>(null);

  const [pipelineMinRefreshMinutes, setPipelineMinRefreshMinutes] = useState(1440);
  const [pipelinePreferredCategoriesCsv, setPipelinePreferredCategoriesCsv] = useState("identity,ransomware,phishing,web");
  const [pipelineMaxPacksPerRun, setPipelineMaxPacksPerRun] = useState(8);
  const [pipelineAutoActivate, setPipelineAutoActivate] = useState(true);
  const [pipelineEnabled, setPipelineEnabled] = useState(true);

  const [minRiskScore, setMinRiskScore] = useState(50);
  const [minRiskTier, setMinRiskTier] = useState<RiskTier>("medium");
  const [preferredPackCategory, setPreferredPackCategory] = useState("identity");
  const [targetSurface, setTargetSurface] = useState("/admin-login");
  const [simulationDepth, setSimulationDepth] = useState(3);
  const [maxRequestsPerMinute, setMaxRequestsPerMinute] = useState(30);
  const [stopOnCritical, setStopOnCritical] = useState(true);
  const [simulationOnly, setSimulationOnly] = useState(true);
  const [autoRun, setAutoRun] = useState(false);
  const [routeAlert, setRouteAlert] = useState(true);
  const [scheduleMinutes, setScheduleMinutes] = useState(120);
  const [shadowCrawlDepth, setShadowCrawlDepth] = useState(2);
  const [shadowMaxPages, setShadowMaxPages] = useState(12);
  const [shadowChangeThreshold, setShadowChangeThreshold] = useState(2);
  const [shadowScheduleMinutes, setShadowScheduleMinutes] = useState(180);
  const [shadowAutoAssignZeroDayPack, setShadowAutoAssignZeroDayPack] = useState(true);
  const [shadowRouteAlert, setShadowRouteAlert] = useState(true);
  const [shadowEnabled, setShadowEnabled] = useState(true);
  const [shadowDeployId, setShadowDeployId] = useState("deploy-001");
  const [shadowReleaseVersion, setShadowReleaseVersion] = useState("2026.03.15");
  const [shadowChangedPathsCsv, setShadowChangedPathsCsv] = useState("/,/admin,/login");
  const [socialCampaignName, setSocialCampaignName] = useState("thai_phishing_awareness");
  const [socialEmployeeSegment, setSocialEmployeeSegment] = useState("all_staff");
  const [socialEmailCount, setSocialEmailCount] = useState(50);
  const [socialDifficulty, setSocialDifficulty] = useState<"low" | "medium" | "high">("medium");
  const [socialImpersonationBrand, setSocialImpersonationBrand] = useState("");
  const [socialRosterPayload, setSocialRosterPayload] = useState(SOCIAL_ROSTER_SAMPLE);
  const [socialConnectorType, setSocialConnectorType] = useState<SocialConnectorType>("simulated");
  const [socialSenderName, setSocialSenderName] = useState("Security Awareness AI");
  const [socialSenderEmail, setSocialSenderEmail] = useState("security-awareness@example.local");
  const [socialSubjectPrefix, setSocialSubjectPrefix] = useState("[Awareness]");
  const [socialLandingBaseUrl, setSocialLandingBaseUrl] = useState("");
  const [socialReportMailbox, setSocialReportMailbox] = useState("");
  const [socialRequireApproval, setSocialRequireApproval] = useState(true);
  const [socialOpenTracking, setSocialOpenTracking] = useState(true);
  const [socialClickTracking, setSocialClickTracking] = useState(true);
  const [socialMaxEmailsPerRun, setSocialMaxEmailsPerRun] = useState(200);
  const [socialAllowedDomainsCsv, setSocialAllowedDomainsCsv] = useState("");
  const [socialConnectorSimulateDelivery, setSocialConnectorSimulateDelivery] = useState(true);
  const [socialPolicyEnabled, setSocialPolicyEnabled] = useState(true);
  const [socialKillSwitchActive, setSocialKillSwitchActive] = useState(false);
  const [socialProviderEventType, setSocialProviderEventType] = useState("delivered");
  const [socialProviderRecipientEmail, setSocialProviderRecipientEmail] = useState("");
  const [socialProviderOccurredAt, setSocialProviderOccurredAt] = useState("");
  const [socialProviderEventId, setSocialProviderEventId] = useState("provider-event-001");
  const [socialProviderMetadata, setSocialProviderMetadata] = useState('{"provider":"smtp_gateway","message_id":"msg-001"}');
  const [socialCallbackResultBySite, setSocialCallbackResultBySite] = useState<Record<string, SiteRedSocialProviderCallbackResponse>>({});
  const [validatorSourceTool, setValidatorSourceTool] = useState<ValidatorSourceTool>("nessus");
  const [validatorImportPayload, setValidatorImportPayload] = useState(VULN_IMPORT_SAMPLES.nessus);
  const [validatorMaxFindings, setValidatorMaxFindings] = useState(20);
  const [pluginIntelligenceBySite, setPluginIntelligenceBySite] = useState<Record<string, SiteRedPluginIntelligenceResponse>>({});
  const [pluginSafetyPolicyBySite, setPluginSafetyPolicyBySite] = useState<Record<string, SiteRedPluginSafetyPolicyResponse["policy"]>>({});
  const [pluginSyncSourcesBySite, setPluginSyncSourcesBySite] = useState<Record<string, SiteRedPluginSyncSourcesResponse>>({});
  const [pluginSyncRunsBySite, setPluginSyncRunsBySite] = useState<Record<string, SiteRedPluginSyncRunsResponse>>({});
  const [pluginLintBySite, setPluginLintBySite] = useState<Record<string, Record<string, SiteRedPluginLintResponse>>>({});
  const [pluginExportBySite, setPluginExportBySite] = useState<Record<string, Record<string, SiteRedPluginExportResponse>>>({});
  const [pluginPublishBySite, setPluginPublishBySite] = useState<Record<string, SiteRedPluginThreatPackPublishResponse>>({});
  const [pluginIntelSourceType, setPluginIntelSourceType] = useState<"cve" | "news" | "article">("cve");
  const [pluginIntelTitle, setPluginIntelTitle] = useState("CVE-2026-0001 Thai Auth Bypass");
  const [pluginIntelCveId, setPluginIntelCveId] = useState("CVE-2026-0001");
  const [pluginIntelTargetType, setPluginIntelTargetType] = useState("web");
  const [pluginIntelSummary, setPluginIntelSummary] = useState("ช่องโหว่เกี่ยวกับ auth bypass ในหน้า admin-login ที่ควรสร้าง template และ exploit draft เพื่อ validation แบบปลอดภัย");
  const [pluginIntelReference, setPluginIntelReference] = useState("https://example.com/security-advisory");
  const [pluginSyncSourceName, setPluginSyncSourceName] = useState("threat-news-feed");
  const [pluginSyncSourceUrl, setPluginSyncSourceUrl] = useState("https://example.com/feed.json");
  const [pluginSyncParserKind, setPluginSyncParserKind] = useState<"json_feed" | "jsonl">("json_feed");
  const [pluginSyncIntervalMinutes, setPluginSyncIntervalMinutes] = useState(1440);
  const [pluginSyncEnabled, setPluginSyncEnabled] = useState(true);
  const [pluginSyncSummary, setPluginSyncSummary] = useState("");
  const [pluginSafetyTargetType, setPluginSafetyTargetType] = useState("web");
  const [pluginSafetyMaxRequests, setPluginSafetyMaxRequests] = useState(5);
  const [pluginSafetyMaxLines, setPluginSafetyMaxLines] = useState(80);
  const [pluginSafetyAllowNetwork, setPluginSafetyAllowNetwork] = useState(true);
  const [pluginSafetyRequireHeader, setPluginSafetyRequireHeader] = useState(true);
  const [pluginSafetyRequireDisclaimer, setPluginSafetyRequireDisclaimer] = useState(true);
  const [pluginSafetyAllowedModulesCsv, setPluginSafetyAllowedModulesCsv] = useState("requests");
  const [pluginSafetyBlockedModulesCsv, setPluginSafetyBlockedModulesCsv] = useState("subprocess,socket,paramiko");
  const [pluginExportKind, setPluginExportKind] = useState("bundle");

  const selectedSite = useMemo(() => sites.find((site) => site.site_id === selectedSiteId) || null, [sites, selectedSiteId]);

  const applyShadowPolicyForm = (policy: SiteRedShadowPentestPolicyResponse["policy"]) => {
    setShadowCrawlDepth(policy.crawl_depth);
    setShadowMaxPages(policy.max_pages);
    setShadowChangeThreshold(policy.change_threshold);
    setShadowScheduleMinutes(policy.schedule_interval_minutes);
    setShadowAutoAssignZeroDayPack(Boolean(policy.auto_assign_zero_day_pack));
    setShadowRouteAlert(Boolean(policy.route_alert));
    setShadowEnabled(Boolean(policy.enabled));
  };

  const applyPolicyForm = (policy: SiteRedExploitAutopilotPolicyResponse["policy"]) => {
    setMinRiskScore(policy.min_risk_score);
    setMinRiskTier(policy.min_risk_tier);
    setPreferredPackCategory(policy.preferred_pack_category);
    setTargetSurface(policy.target_surface);
    setSimulationDepth(policy.simulation_depth);
    setMaxRequestsPerMinute(policy.max_requests_per_minute);
    setStopOnCritical(Boolean(policy.stop_on_critical));
    setSimulationOnly(Boolean(policy.simulation_only));
    setAutoRun(Boolean(policy.auto_run));
    setRouteAlert(Boolean(policy.route_alert));
    setScheduleMinutes(policy.schedule_interval_minutes);
  };

  const applyPipelinePolicyForm = (policy: ThreatContentPipelinePolicyResponse["policy"]) => {
    setPipelineScope(policy.scope || "global");
    setPipelineMinRefreshMinutes(policy.min_refresh_interval_minutes);
    setPipelinePreferredCategoriesCsv((policy.preferred_categories || []).join(","));
    setPipelineMaxPacksPerRun(policy.max_packs_per_run);
    setPipelineAutoActivate(Boolean(policy.auto_activate));
    setPipelineEnabled(Boolean(policy.enabled));
    setPipelinePolicySummary(
      `scope=${policy.scope} refresh=${policy.min_refresh_interval_minutes}m categories=${(policy.preferred_categories || []).join(",")} max_packs=${policy.max_packs_per_run} auto_activate=${String(policy.auto_activate)}`,
    );
  };

  const applySocialPolicyForm = (policy: SiteRedSocialPolicyResponse["policy"]) => {
    setSocialConnectorType((policy.connector_type as SocialConnectorType) || "simulated");
    setSocialSenderName(policy.sender_name);
    setSocialSenderEmail(policy.sender_email);
    setSocialSubjectPrefix(policy.subject_prefix);
    setSocialLandingBaseUrl(policy.landing_base_url);
    setSocialReportMailbox(policy.report_mailbox);
    setSocialRequireApproval(Boolean(policy.require_approval));
    setSocialOpenTracking(Boolean(policy.enable_open_tracking));
    setSocialClickTracking(Boolean(policy.enable_click_tracking));
    setSocialMaxEmailsPerRun(policy.max_emails_per_run);
    setSocialAllowedDomainsCsv((policy.allowed_domains || []).join(","));
    setSocialConnectorSimulateDelivery(Boolean(policy.connector_config?.simulate_delivery ?? true));
    setSocialPolicyEnabled(Boolean(policy.enabled));
    setSocialKillSwitchActive(Boolean(policy.kill_switch_active));
  };

  const applyPluginSafetyPolicyForm = (policy: SiteRedPluginSafetyPolicyResponse["policy"]) => {
    setPluginSafetyTargetType(policy.target_type || "web");
    setPluginSafetyMaxRequests(policy.max_http_requests_per_run);
    setPluginSafetyMaxLines(policy.max_script_lines);
    setPluginSafetyAllowNetwork(Boolean(policy.allow_network_calls));
    setPluginSafetyRequireHeader(Boolean(policy.require_comment_header));
    setPluginSafetyRequireDisclaimer(Boolean(policy.require_disclaimer));
    setPluginSafetyAllowedModulesCsv((policy.allowed_modules || []).join(","));
    setPluginSafetyBlockedModulesCsv((policy.blocked_modules || []).join(","));
  };

  const loadThreatPacks = async (): Promise<ThreatContentPackRow[]> => {
    try {
      const response = await fetchThreatContentPacks({ active_only: true, limit: 20 });
      setThreatPacks(response.rows || []);
      return response.rows || [];
    } catch {
      return [];
    }
  };

  const loadHistory = async (siteId: string) => {
    try {
      const history = await fetchSiteRedScans(siteId, 10);
      setHistoryBySite((prev) => ({ ...prev, [siteId]: history }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_history_load_failed");
    }
  };

  const loadExploitRuns = async (siteId: string) => {
    try {
      const runs = await fetchSiteExploitPathRuns(siteId, 10);
      setExploitRunsBySite((prev) => ({ ...prev, [siteId]: runs }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "exploit_runs_load_failed");
    }
  };

  const loadShadowPolicy = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedShadowPentestPolicy(siteId);
      setShadowPolicyBySite((prev) => ({ ...prev, [siteId]: response.policy }));
      applyShadowPolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "shadow_policy_load_failed");
    }
  };

  const loadShadowRuns = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedShadowPentestRuns(siteId, 10);
      setShadowRunsBySite((prev) => ({ ...prev, [siteId]: response }));
      const latest = response.rows?.[0];
      if (latest) {
        setShadowRunSummary(
          `${latest.status} changed=${String(latest.site_changed)} pages=${latest.page_count} delta=${latest.new_page_count + latest.changed_page_count + latest.removed_page_count} pack=${latest.assigned_pack_code || "none"}`,
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "shadow_runs_load_failed");
    }
  };

  const loadShadowAssets = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedShadowPentestAssets(siteId, 50);
      setShadowAssetsBySite((prev) => ({ ...prev, [siteId]: response }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "shadow_assets_load_failed");
    }
  };

  const loadAutopilotPolicy = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedExploitAutopilotPolicy(siteId);
      setAutopilotPolicyBySite((prev) => ({ ...prev, [siteId]: response.policy }));
      applyPolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "autopilot_policy_load_failed");
    }
  };

  const loadAutopilotRuns = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedExploitAutopilotRuns(siteId, 10);
      setAutopilotRunsBySite((prev) => ({ ...prev, [siteId]: response }));
      const latest = response.rows?.[0];
      if (latest) {
        setAutopilotRunSummary(
          `${latest.status} risk=${latest.risk_tier}/${latest.risk_score} pack=${latest.threat_pack_code || "none"} executed=${String(latest.executed)}`,
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "autopilot_runs_load_failed");
    }
  };

  const loadSocialPolicy = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedSocialPolicy(siteId);
      setSocialPolicyBySite((prev) => ({ ...prev, [siteId]: response.policy }));
      applySocialPolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "social_policy_load_failed");
    }
  };

  const loadSocialRoster = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedSocialRoster(siteId, { active_only: false, limit: 100 });
      setSocialRosterBySite((prev) => ({ ...prev, [siteId]: response }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "social_roster_load_failed");
    }
  };

  const loadSocialRuns = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedSocialSimulatorRuns(siteId, 10);
      setSocialRunsBySite((prev) => ({ ...prev, [siteId]: response }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "social_runs_load_failed");
    }
  };

  const loadSocialTelemetry = async (siteId: string, runId?: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedSocialTelemetry(siteId, { run_id: runId, limit: 50 });
      setSocialTelemetryBySite((prev) => ({ ...prev, [siteId]: response }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "social_telemetry_load_failed");
    }
  };

  const loadValidatorFindings = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedVulnerabilityFindings(siteId, { limit: 20 });
      setValidatorFindingsBySite((prev) => ({ ...prev, [siteId]: response }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "validator_findings_load_failed");
    }
  };

  const loadValidatorRuns = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedVulnerabilityValidationRuns(siteId, 10);
      setValidatorRunsBySite((prev) => ({ ...prev, [siteId]: response }));
      const latest = response.rows?.[0];
      if (latest) {
        setValidatorSummary(
          `${latest.status} findings=${latest.finding_count} exploitable=${latest.exploitable_count} false_positive=${latest.false_positive_count} review=${latest.needs_review_count}`,
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "validator_runs_load_failed");
    }
  };

  const loadValidatorExport = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedVulnerabilityRemediationExport(siteId, { limit: 20 });
      setValidatorExportBySite((prev) => ({ ...prev, [siteId]: response }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "validator_export_load_failed");
    }
  };

  const loadPluginRuns = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteCoworkerPluginRuns(siteId, { category: "red", limit: 20 });
      setPluginRunsBySite((prev) => ({ ...prev, [siteId]: response }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_plugin_runs_load_failed");
    }
  };

  const loadPluginIntelligence = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedPluginIntelligence(siteId, { limit: 10 });
      setPluginIntelligenceBySite((prev) => ({ ...prev, [siteId]: response }));
      const latest = response.rows?.[0];
      if (latest) {
        setPluginIntelSourceType((latest.source_type as "cve" | "news" | "article") || "article");
        setPluginIntelTitle(latest.title);
        setPluginIntelCveId(latest.cve_id || "");
        setPluginIntelTargetType(latest.target_type || "web");
        setPluginIntelSummary(latest.summary_th || "");
        setPluginIntelReference(latest.references?.[0] || "");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_plugin_intelligence_load_failed");
    }
  };

  const loadPluginSyncSources = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedPluginSyncSources(siteId, { limit: 10 });
      setPluginSyncSourcesBySite((prev) => ({ ...prev, [siteId]: response }));
      const latest = response.rows?.[0];
      if (latest) {
        setPluginSyncSourceName(latest.source_name || "threat-news-feed");
        setPluginSyncSourceUrl(latest.source_url || "https://example.com/feed.json");
        setPluginIntelSourceType((latest.source_type as "cve" | "news" | "article") || "article");
        setPluginIntelTargetType(latest.target_type || "web");
        setPluginSyncParserKind((latest.parser_kind as "json_feed" | "jsonl") || "json_feed");
        setPluginSyncIntervalMinutes(latest.sync_interval_minutes || 1440);
        setPluginSyncEnabled(Boolean(latest.enabled));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_plugin_sync_sources_load_failed");
    }
  };

  const loadPluginSyncRuns = async (siteId: string) => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedPluginSyncRuns(siteId, { limit: 10 });
      setPluginSyncRunsBySite((prev) => ({ ...prev, [siteId]: response }));
      const latest = response.rows?.[0];
      if (latest) {
        setPluginSyncSummary(
          `${latest.status} fetched=${latest.fetched_count} imported=${latest.imported_count} updated=${latest.updated_count}`,
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_plugin_sync_runs_load_failed");
    }
  };

  const loadPluginSafetyPolicy = async (siteId: string, targetType = pluginSafetyTargetType || "web") => {
    if (!canView) return;
    try {
      const response = await fetchSiteRedPluginSafetyPolicy(siteId, targetType);
      setPluginSafetyPolicyBySite((prev) => ({ ...prev, [siteId]: response.policy }));
      applyPluginSafetyPolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_plugin_safety_policy_load_failed");
    }
  };

  const savePluginSyncSource = async (siteId: string) => {
    setError("");
    setBusyKey(`${siteId}:plugin_sync_source`);
    try {
      const response = await upsertSiteRedPluginSyncSource(siteId, {
        source_name: pluginSyncSourceName,
        source_type: pluginIntelSourceType,
        source_url: pluginSyncSourceUrl,
        target_type: pluginIntelTargetType || "web",
        parser_kind: pluginSyncParserKind,
        sync_interval_minutes: pluginSyncIntervalMinutes,
        enabled: pluginSyncEnabled,
        owner: "security",
      });
      setPluginSyncSourcesBySite((prev) => ({
        ...prev,
        [siteId]: { ...(prev[siteId] || { status: "ok", site_id: siteId, count: 0, rows: [] }), ...response },
      }));
      if (response.source) {
        setPluginSyncSummary(
          `${response.status} ${response.source.source_name} every ${response.source.sync_interval_minutes}m enabled=${String(response.source.enabled)}`,
        );
      }
      await loadPluginSyncSources(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_plugin_sync_source_save_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runPluginSync = async (siteId: string, dryRun: boolean) => {
    setError("");
    setBusyKey(`${siteId}:plugin_sync_run`);
    try {
      const response = await runSiteRedPluginSync(siteId, {
        dry_run: dryRun,
        actor: "red_plugin_sync_operator",
      });
      setPluginSyncSummary(
        `${response.status} fetched=${response.fetched_count || 0} imported=${Number((response.import_result || {}).created_count || 0)} updated=${Number((response.import_result || {}).updated_count || 0)}`,
      );
      await loadPluginIntelligence(siteId);
      await loadPluginSyncRuns(siteId);
      await loadPluginSyncSources(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_plugin_sync_run_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runPluginSyncScheduler = async () => {
    setError("");
    setBusyKey("red_plugin_sync_scheduler");
    try {
      const response = await runRedPluginSyncScheduler({
        limit: 100,
        dry_run_override: true,
        actor: "dashboard_scheduler",
      });
      setPluginSyncSummary(
        `scheduler scheduled=${response.scheduled_source_count || 0} executed=${response.executed_count || 0} skipped=${response.skipped_count || 0}`,
      );
      if (selectedSiteId) {
        await loadPluginSyncRuns(selectedSiteId);
        await loadPluginSyncSources(selectedSiteId);
        await loadPluginIntelligence(selectedSiteId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_plugin_sync_scheduler_failed");
    } finally {
      setBusyKey("");
    }
  };

  const loadThreatContentPipelinePolicy = async () => {
    if (!canView) return;
    try {
      const response = await fetchThreatContentPipelinePolicy(pipelineScope || "global");
      applyPipelinePolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_pipeline_policy_load_failed");
    }
  };

  const loadThreatContentPipelineRuns = async () => {
    if (!canView) return;
    try {
      const response = await fetchThreatContentPipelineRuns({ scope: pipelineScope || "global", limit: 10 });
      setPipelineRuns(response);
      const latest = response.rows?.[0];
      if (latest) {
        setPipelineRunSummary(
          `${latest.status} categories=${latest.selected_categories.join(",")} candidate=${latest.candidate_count} created=${latest.created_count} refreshed=${latest.refreshed_count}`,
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_pipeline_runs_load_failed");
    }
  };

  const loadThreatContentPipelineFederation = async () => {
    if (!canView) return;
    try {
      const response = await fetchThreatContentPipelineFederation({ limit: 200, stale_after_hours: 48 });
      setPipelineFederation(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_pipeline_federation_load_failed");
    }
  };

  const runCase = async (siteId: string, scanType: string) => {
    setError("");
    setBusyKey(`${siteId}:${scanType}`);
    try {
      await runSiteRedScan(siteId, { scan_type: scanType });
      await loadHistory(siteId);
      await loadAutopilotPolicy(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_scan_failed");
    } finally {
      setBusyKey("");
    }
  };

  const loadValidatorSample = (sourceTool: ValidatorSourceTool) => {
    setValidatorSourceTool(sourceTool);
    setValidatorImportPayload(VULN_IMPORT_SAMPLES[sourceTool]);
  };

  const importValidatorFindings = async (siteId: string) => {
    setError("");
    setBusyKey(`${siteId}:vuln_import`);
    try {
      const parsedPayload = JSON.parse(validatorImportPayload || "{}") as Record<string, unknown> | Array<Record<string, unknown>>;
      const response = await importSiteRedVulnerabilityFindings(siteId, {
        source_tool: validatorSourceTool,
        payload: parsedPayload,
        actor: "red_service",
      });
      setValidatorSummary(
        `imported=${response.imported_count} deduped=${response.deduped_count} received=${response.received_count} source=${response.source_tool}`,
      );
      await loadValidatorFindings(siteId);
      await loadValidatorExport(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "validator_import_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runValidator = async (siteId: string, dryRun: boolean) => {
    setError("");
    setBusyKey(`${siteId}:vuln_validator`);
    try {
      const response = await runSiteRedVulnerabilityValidator(siteId, {
        max_findings: validatorMaxFindings,
        dry_run: dryRun,
        actor: "red_service",
      });
      setValidatorSummary(
        `${response.status} findings=${response.summary.finding_count} exploitable=${response.summary.exploitable_count} false_positive=${response.summary.false_positive_count} review=${response.summary.needs_review_count}`,
      );
      await loadValidatorFindings(siteId);
      await loadValidatorRuns(siteId);
      await loadValidatorExport(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "validator_run_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runExploitPath = async (siteId: string) => {
    setError("");
    setBusyKey(`${siteId}:exploit_path`);
    try {
      const packs = threatPacks.length > 0 ? threatPacks : await loadThreatPacks();
      await simulateSiteExploitPath(siteId, {
        threat_pack_code: packs[0]?.pack_code || "",
        simulation_depth: 3,
        target_surface: "/admin-login",
        max_requests_per_minute: 20,
        simulation_only: true,
      });
      await loadExploitRuns(siteId);
      await loadAutopilotRuns(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "exploit_path_failed");
    } finally {
      setBusyKey("");
    }
  };

  const saveShadowPolicy = async (siteId: string) => {
    setError("");
    setBusyKey(`${siteId}:shadow_policy`);
    try {
      const response = await upsertSiteRedShadowPentestPolicy(siteId, {
        crawl_depth: shadowCrawlDepth,
        max_pages: shadowMaxPages,
        change_threshold: shadowChangeThreshold,
        schedule_interval_minutes: shadowScheduleMinutes,
        auto_assign_zero_day_pack: shadowAutoAssignZeroDayPack,
        route_alert: shadowRouteAlert,
        enabled: shadowEnabled,
        owner: "security",
      });
      setShadowPolicyBySite((prev) => ({ ...prev, [siteId]: response.policy }));
      applyShadowPolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "shadow_policy_save_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runShadowPentest = async (siteId: string, dryRun: boolean, force: boolean) => {
    setError("");
    setBusyKey(`${siteId}:shadow_run`);
    try {
      const response = await runSiteRedShadowPentest(siteId, {
        dry_run: dryRun,
        force,
        actor: "dashboard_operator",
      });
      setShadowRunSummary(
        `${response.status} changed=${String(response.diff.site_changed)} total_delta=${response.diff.total_change_count} pages=${response.crawl.page_count} pack=${response.pack_assignment.pack_code || "none"} coverage=${response.pack_validation.summary.coverage_pct}% targeted=${response.pack_validation.summary.targeted_assets}`,
      );
      await loadShadowRuns(siteId);
      await loadShadowAssets(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "shadow_run_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runShadowScheduler = async () => {
    setError("");
    setBusyKey("red_shadow_scheduler");
    try {
      const response = await runRedShadowPentestScheduler({
        limit: 100,
        dry_run_override: true,
        actor: "dashboard_scheduler",
      });
      setShadowRunSummary(
        `scheduler policies=${response.scheduled_policy_count} executed=${response.executed_count} skipped=${response.skipped_count}`,
      );
      if (selectedSiteId) {
        await loadShadowRuns(selectedSiteId);
        await loadShadowAssets(selectedSiteId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "shadow_scheduler_failed");
    } finally {
      setBusyKey("");
    }
  };

  const triggerShadowDeployEvent = async (siteId: string) => {
    setError("");
    setBusyKey(`${siteId}:shadow_deploy`);
    try {
      const response = await triggerSiteRedShadowPentestDeployEvent(siteId, {
        deploy_id: shadowDeployId,
        release_version: shadowReleaseVersion,
        changed_paths: shadowChangedPathsCsv
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        actor: "deploy_pipeline",
        dry_run_override: true,
      });
      setShadowRunSummary(
        `deploy=${shadowDeployId} version=${shadowReleaseVersion} status=${response.status} changed=${String(response.diff.site_changed)} assets=${response.asset_inventory.total_assets}`,
      );
      await loadShadowRuns(siteId);
      await loadShadowAssets(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "shadow_deploy_trigger_failed");
    } finally {
      setBusyKey("");
    }
  };

  const saveAutopilotPolicy = async (siteId: string) => {
    setError("");
    setBusyKey(`${siteId}:autopilot_policy`);
    try {
      const response = await upsertSiteRedExploitAutopilotPolicy(siteId, {
        min_risk_score: minRiskScore,
        min_risk_tier: minRiskTier,
        preferred_pack_category: preferredPackCategory,
        target_surface: targetSurface,
        simulation_depth: simulationDepth,
        max_requests_per_minute: maxRequestsPerMinute,
        stop_on_critical: stopOnCritical,
        simulation_only: simulationOnly,
        auto_run: autoRun,
        route_alert: routeAlert,
        schedule_interval_minutes: scheduleMinutes,
        enabled: true,
        owner: "security",
      });
      setAutopilotPolicyBySite((prev) => ({ ...prev, [siteId]: response.policy }));
      applyPolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "autopilot_policy_save_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runAutopilot = async (siteId: string, dryRun: boolean, force: boolean) => {
    setError("");
    setBusyKey(`${siteId}:autopilot_run`);
    try {
      const response = await runSiteRedExploitAutopilot(siteId, {
        dry_run: dryRun,
        force,
        actor: "dashboard_operator",
      });
      setAutopilotRunSummary(
        `${response.status} risk=${response.risk.risk_tier}/${response.risk.risk_score} should_run=${String(response.execution.should_run)} executed=${String(response.execution.executed)}`,
      );
      await loadExploitRuns(siteId);
      await loadAutopilotRuns(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "autopilot_run_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runAutopilotScheduler = async () => {
    setError("");
    setBusyKey("red_autopilot_scheduler");
    try {
      const response = await runRedExploitAutopilotScheduler({
        limit: 200,
        dry_run_override: true,
        actor: "dashboard_scheduler",
      });
      setAutopilotRunSummary(
        `scheduler policies=${response.scheduled_policy_count} executed=${response.executed_count} skipped=${response.skipped_count}`,
      );
      if (selectedSiteId) {
        await loadAutopilotRuns(selectedSiteId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "autopilot_scheduler_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runSocialSimulator = async (siteId: string, dryRun: boolean) => {
    setError("");
    setBusyKey(`${siteId}:social_sim`);
    try {
      const response = await runSiteRedSocialSimulator(siteId, {
        campaign_name: socialCampaignName,
        employee_segment: socialEmployeeSegment,
        email_count: socialEmailCount,
        difficulty: socialDifficulty,
        impersonation_brand: socialImpersonationBrand,
        dry_run: dryRun,
        actor: "dashboard_operator",
      });
      await loadSocialRuns(siteId);
      await loadSocialTelemetry(siteId, response.run.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "social_simulator_failed");
    } finally {
      setBusyKey("");
    }
  };

  const importSocialRoster = async (siteId: string) => {
    setError("");
    setBusyKey(`${siteId}:social_roster`);
    try {
      const parsed = JSON.parse(socialRosterPayload || "{}") as { entries?: Array<Record<string, unknown>> };
      await importSiteRedSocialRoster(siteId, {
        entries: parsed.entries || [],
        actor: "dashboard_operator",
      });
      await loadSocialRoster(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "social_roster_import_failed");
    } finally {
      setBusyKey("");
    }
  };

  const saveSocialPolicy = async (siteId: string) => {
    setError("");
    setBusyKey(`${siteId}:social_policy`);
    try {
      const response = await upsertSiteRedSocialPolicy(siteId, {
        connector_type: socialConnectorType,
        sender_name: socialSenderName,
        sender_email: socialSenderEmail,
        subject_prefix: socialSubjectPrefix,
        landing_base_url: socialLandingBaseUrl,
        report_mailbox: socialReportMailbox,
        require_approval: socialRequireApproval,
        enable_open_tracking: socialOpenTracking,
        enable_click_tracking: socialClickTracking,
        max_emails_per_run: socialMaxEmailsPerRun,
        kill_switch_active: socialKillSwitchActive,
        allowed_domains: socialAllowedDomainsCsv
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        connector_config: {
          simulate_delivery: socialConnectorSimulateDelivery,
        },
        enabled: socialPolicyEnabled,
        owner: "security",
      });
      setSocialPolicyBySite((prev) => ({ ...prev, [siteId]: response.policy }));
      applySocialPolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "social_policy_save_failed");
    } finally {
      setBusyKey("");
    }
  };

  const reviewLatestSocialCampaign = async (siteId: string, approve: boolean) => {
    const latestRun = socialRunsBySite[siteId]?.rows?.[0];
    if (!latestRun) return;
    setError("");
    setBusyKey(`${siteId}:social_review`);
    try {
      const response = await reviewSiteRedSocialCampaign(siteId, latestRun.run_id, {
        approve,
        actor: "security_lead",
        note: approve ? "approved_from_red_service" : "rejected_from_red_service",
      });
      await loadSocialRuns(siteId);
      await loadSocialTelemetry(siteId, response.run.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "social_review_failed");
    } finally {
      setBusyKey("");
    }
  };

  const killLatestSocialCampaign = async (siteId: string) => {
    const latestRun = socialRunsBySite[siteId]?.rows?.[0];
    if (!latestRun) return;
    setError("");
    setBusyKey(`${siteId}:social_kill`);
    try {
      const response = await killSiteRedSocialCampaign(siteId, latestRun.run_id, {
        actor: "security_operator",
        note: "manual_kill_switch_from_red_service",
        activate_site_kill_switch: socialKillSwitchActive,
      });
      await loadSocialPolicy(siteId);
      await loadSocialRuns(siteId);
      await loadSocialTelemetry(siteId, response.run.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "social_kill_failed");
    } finally {
      setBusyKey("");
    }
  };

  const ingestLatestSocialProviderCallback = async (siteId: string) => {
    const latestRun = socialRunsBySite[siteId]?.rows?.[0];
    if (!latestRun) return;
    const recipientEmail =
      socialProviderRecipientEmail.trim() || socialTelemetryBySite[siteId]?.rows?.[0]?.recipient_email || "";
    if (!recipientEmail) {
      setError("social_provider_callback_recipient_required");
      return;
    }
    setError("");
    setBusyKey(`${siteId}:social_callback`);
    try {
      const metadata = JSON.parse(socialProviderMetadata || "{}") as Record<string, unknown>;
      const response = await ingestSiteRedSocialProviderCallback(siteId, {
        run_id: latestRun.run_id,
        connector_type: latestRun.execution.connector_type || socialConnectorType,
        event_type: socialProviderEventType,
        recipient_email: recipientEmail,
        occurred_at: socialProviderOccurredAt.trim(),
        provider_event_id: socialProviderEventId,
        metadata,
        actor: "red_service_callback_sim",
      });
      setSocialCallbackResultBySite((prev) => ({ ...prev, [siteId]: response }));
      await loadSocialRuns(siteId);
      await loadSocialTelemetry(siteId, latestRun.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "social_provider_callback_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runRedPlugin = async (siteId: string, pluginCode: "red_template_writer" | "red_exploit_code_generator", dryRun: boolean) => {
    setError("");
    setBusyKey(`${siteId}:${pluginCode}`);
    try {
      await upsertSiteCoworkerPluginBinding(siteId, {
        plugin_code: pluginCode,
        enabled: true,
        auto_run: false,
        schedule_interval_minutes: 60,
        notify_channels: [],
        config: { target_surface: targetSurface || "/admin-login" },
        owner: "red_service",
      });
      await runSiteCoworkerPlugin(siteId, pluginCode, {
        dry_run: dryRun,
        force: true,
        actor: "red_service",
      });
      await loadPluginRuns(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_plugin_run_failed");
    } finally {
      setBusyKey("");
    }
  };

  const importPluginIntelligence = async (siteId: string) => {
    setError("");
    setBusyKey(`${siteId}:plugin_intelligence_import`);
    try {
      await importSiteRedPluginIntelligence(siteId, {
        actor: "red_service",
        items: [
          {
            source_type: pluginIntelSourceType,
            source_name: pluginIntelSourceType === "cve" ? "cve_manual" : "article_manual",
            source_item_id: pluginIntelCveId || pluginIntelTitle.toLowerCase().replace(/\s+/g, "-"),
            title: pluginIntelTitle,
            summary_th: pluginIntelSummary,
            cve_id: pluginIntelCveId,
            target_surface: targetSurface || "/admin-login",
            target_type: pluginIntelTargetType || "web",
            references: pluginIntelReference ? [pluginIntelReference] : [],
            tags: [pluginIntelSourceType, pluginIntelTargetType || "web"],
            payload: { imported_from: "red_service_ui" },
          },
        ],
      });
      await loadPluginIntelligence(siteId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_plugin_intelligence_import_failed");
    } finally {
      setBusyKey("");
    }
  };

  const savePluginSafetyPolicy = async (siteId: string) => {
    setError("");
    setBusyKey(`${siteId}:plugin_safety_policy`);
    try {
      const response = await upsertSiteRedPluginSafetyPolicy(siteId, {
        target_type: pluginSafetyTargetType || "web",
        max_http_requests_per_run: pluginSafetyMaxRequests,
        max_script_lines: pluginSafetyMaxLines,
        allow_network_calls: pluginSafetyAllowNetwork,
        require_comment_header: pluginSafetyRequireHeader,
        require_disclaimer: pluginSafetyRequireDisclaimer,
        allowed_modules: pluginSafetyAllowedModulesCsv.split(",").map((item) => item.trim()).filter(Boolean),
        blocked_modules: pluginSafetyBlockedModulesCsv.split(",").map((item) => item.trim()).filter(Boolean),
        enabled: true,
        owner: "red_service",
      });
      setPluginSafetyPolicyBySite((prev) => ({ ...prev, [siteId]: response.policy }));
      applyPluginSafetyPolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_plugin_safety_policy_save_failed");
    } finally {
      setBusyKey("");
    }
  };

  const lintRedPluginArtifact = async (siteId: string, pluginCode: "red_template_writer" | "red_exploit_code_generator") => {
    setError("");
    setBusyKey(`${siteId}:${pluginCode}:lint`);
    try {
      const response = await lintSiteRedPluginOutput(siteId, pluginCode, {});
      setPluginLintBySite((prev) => ({
        ...prev,
        [siteId]: {
          ...(prev[siteId] || {}),
          [pluginCode]: response,
        },
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_plugin_lint_failed");
    } finally {
      setBusyKey("");
    }
  };

  const exportRedPluginArtifact = async (siteId: string, pluginCode: "red_template_writer" | "red_exploit_code_generator") => {
    setError("");
    setBusyKey(`${siteId}:${pluginCode}:export`);
    try {
      const response = await exportSiteRedPluginOutput(siteId, pluginCode, {
        export_kind: pluginExportKind,
        title_override: pluginCode === "red_template_writer" ? "Nuclei Threat Content Export" : "Exploit Draft Export",
      });
      setPluginExportBySite((prev) => ({
        ...prev,
        [siteId]: {
          ...(prev[siteId] || {}),
          [pluginCode]: response,
        },
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_plugin_export_failed");
    } finally {
      setBusyKey("");
    }
  };

  const publishTemplateThreatPack = async (siteId: string) => {
    setError("");
    setBusyKey(`${siteId}:template_publish`);
    try {
      const response = await publishSiteRedTemplateThreatPack(siteId, {
        activate: true,
        actor: "red_plugin_publish_operator",
      });
      setPluginPublishBySite((prev) => ({ ...prev, [siteId]: response }));
      setPluginSyncSummary(`published ${response.pack.pack_code} category=${response.pack.category}`);
      await loadThreatPacks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "red_template_publish_failed");
    } finally {
      setBusyKey("");
    }
  };

  const saveThreatContentPipelinePolicy = async () => {
    setError("");
    setBusyKey("threat_pipeline_policy");
    try {
      const preferredCategories = pipelinePreferredCategoriesCsv
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      const response = await upsertThreatContentPipelinePolicy({
        scope: pipelineScope || "global",
        min_refresh_interval_minutes: pipelineMinRefreshMinutes,
        preferred_categories: preferredCategories,
        max_packs_per_run: pipelineMaxPacksPerRun,
        auto_activate: pipelineAutoActivate,
        route_alert: false,
        enabled: pipelineEnabled,
        owner: "security",
      });
      applyPipelinePolicyForm(response.policy);
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_pipeline_policy_save_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runThreatPipeline = async (dryRun: boolean, force: boolean) => {
    setError("");
    setBusyKey("threat_pipeline_run");
    try {
      const response = await runThreatContentPipeline({
        scope: pipelineScope || "global",
        dry_run: dryRun,
        force,
        actor: "dashboard_operator",
      });
      setPipelineRunSummary(
        `${response.status} should_run=${String(response.execution.should_run)} candidate=${response.execution.candidate_count} created=${response.execution.created_count} refreshed=${response.execution.refreshed_count}`,
      );
      await loadThreatContentPipelineRuns();
      await loadThreatContentPipelineFederation();
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_pipeline_run_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runThreatPipelineScheduler = async () => {
    setError("");
    setBusyKey("threat_pipeline_scheduler");
    try {
      const response = await runThreatContentPipelineScheduler({
        limit: 20,
        dry_run_override: true,
        actor: "dashboard_scheduler",
      });
      setPipelineRunSummary(
        `scheduler policies=${response.scheduled_policy_count} executed=${response.executed_count} skipped=${response.skipped_count}`,
      );
      await loadThreatContentPipelineRuns();
      await loadThreatContentPipelineFederation();
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_pipeline_scheduler_failed");
    } finally {
      setBusyKey("");
    }
  };

  return (
    <section className="card p-4">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Red Team Service</h2>
      <p className="mt-1 text-xs text-slate-400">AI-driven authorized simulation scans by site.</p>
      <p className="mt-1 text-xs text-slate-500">
        RBAC: viewer={String(canView)} policy_editor={String(canEditPolicy)} approver={String(canApprove)}
      </p>

      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {RED_SERVICE_MENUS.map((item) => (
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

      {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}

      <div className="mt-3 space-y-2">
        {sites.length === 0 ? <p className="text-xs text-slate-500">No site found. Add site in Configuration menu.</p> : null}
        {sites.map((site) => {
          const expanded = selectedSiteId === site.site_id;
          const history = historyBySite[site.site_id];
          const shadowPolicy = shadowPolicyBySite[site.site_id];
          const shadowRuns = shadowRunsBySite[site.site_id];
          const shadowAssets = shadowAssetsBySite[site.site_id];
          const latestShadowRun = shadowRuns?.rows?.[0];
          const autopilotPolicy = autopilotPolicyBySite[site.site_id];
          const socialPolicy = socialPolicyBySite[site.site_id];
          const socialRoster = socialRosterBySite[site.site_id];
          const socialRuns = socialRunsBySite[site.site_id];
          const socialTelemetry = socialTelemetryBySite[site.site_id];
          const latestSocialRun = socialRuns?.rows?.[0];
          const validatorFindings = validatorFindingsBySite[site.site_id];
          const validatorRuns = validatorRunsBySite[site.site_id];
          const validatorExport = validatorExportBySite[site.site_id];
          const redPluginRuns = pluginRunsBySite[site.site_id];
          const pluginIntel = pluginIntelligenceBySite[site.site_id];
          const pluginSyncSources = pluginSyncSourcesBySite[site.site_id];
          const pluginSyncRuns = pluginSyncRunsBySite[site.site_id];
          const pluginSafetyPolicy = pluginSafetyPolicyBySite[site.site_id];
          const pluginPublish = pluginPublishBySite[site.site_id];
          const latestTemplateRun = (redPluginRuns?.rows || []).find((row) => row.plugin_code === "red_template_writer");
          const latestExploitCodeRun = (redPluginRuns?.rows || []).find((row) => row.plugin_code === "red_exploit_code_generator");
          const templateLint = pluginLintBySite[site.site_id]?.red_template_writer;
          const exploitLint = pluginLintBySite[site.site_id]?.red_exploit_code_generator;
          const templateExport = pluginExportBySite[site.site_id]?.red_template_writer;
          const exploitExport = pluginExportBySite[site.site_id]?.red_exploit_code_generator;
          const latestIntel = pluginIntel?.rows?.[0] as RedPluginIntelligenceRow | undefined;
          const latestPluginSyncRun = pluginSyncRuns?.rows?.[0];
          const latestPluginSyncSource = pluginSyncSources?.rows?.[0];
          return (
            <div key={site.site_id} className="rounded-md border border-slate-800 bg-panelAlt/30 p-3">
              <button
                type="button"
                onClick={() => {
                  onSelectSite(site.site_id);
                  void loadHistory(site.site_id);
                  void loadExploitRuns(site.site_id);
                  void loadThreatPacks();
                  void loadShadowPolicy(site.site_id);
                  void loadShadowRuns(site.site_id);
                  void loadShadowAssets(site.site_id);
                  void loadAutopilotPolicy(site.site_id);
                  void loadAutopilotRuns(site.site_id);
                  void loadSocialPolicy(site.site_id);
                  void loadSocialRoster(site.site_id);
                  void loadSocialRuns(site.site_id);
                  void loadSocialTelemetry(site.site_id);
                  void loadValidatorFindings(site.site_id);
                  void loadValidatorRuns(site.site_id);
                  void loadValidatorExport(site.site_id);
                  void loadPluginRuns(site.site_id);
                  void loadPluginIntelligence(site.site_id);
                  void loadPluginSyncSources(site.site_id);
                  void loadPluginSyncRuns(site.site_id);
                  void loadPluginSafetyPolicy(site.site_id);
                  void loadThreatContentPipelinePolicy();
                  void loadThreatContentPipelineRuns();
                  void loadThreatContentPipelineFederation();
                }}
                className="w-full text-left"
              >
                <p className="text-xs font-semibold text-slate-100 wrap-anywhere">{site.display_name}</p>
                <p className="mt-1 font-mono text-[11px] text-slate-400 wrap-anywhere">{site.base_url}</p>
              </button>

              {expanded ? (
                <div className="mt-3 space-y-2">
                  <div className="grid gap-2 sm:grid-cols-3">
                    {SCAN_CASES.map((scan) => (
                      <button
                        key={scan.key}
                        type="button"
                        onClick={() => void runCase(site.site_id, scan.key)}
                        disabled={busyKey.length > 0}
                        className="rounded-md border border-danger/50 bg-danger/10 px-2 py-2 text-[11px] text-danger hover:bg-danger/20 disabled:opacity-60"
                      >
                        {scan.label}
                      </button>
                    ))}
                  </div>

                  <button
                    type="button"
                    onClick={() => void runExploitPath(site.site_id)}
                    disabled={busyKey.length > 0}
                    className="w-full rounded-md border border-warning/50 bg-warning/10 px-2 py-2 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                  >
                    Exploit Path Simulation (AI)
                  </button>

                  <div className="rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="text-slate-300">Social Engineering Simulator</p>
                        <p className="mt-1 text-slate-500 wrap-anywhere">
                          production path สำหรับ Thai phishing campaign: roster import, connector policy, approval, telemetry, และ kill switch.
                        </p>
                      </div>
                      <p className="text-[11px] text-slate-500 wrap-anywhere">
                        connector={socialPolicy?.connector_type || "simulated"} roster={socialRoster?.count || 0} latest=
                        {latestSocialRun?.execution?.status || "none"}
                      </p>
                    </div>

                    <div className="mt-3 grid gap-2 xl:grid-cols-3">
                      <div className="rounded border border-slate-800 bg-panelAlt/30 p-2 xl:col-span-2">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-medium text-slate-200">Campaign Builder</p>
                          <p className="text-[11px] text-slate-500 wrap-anywhere">
                            approval={String(socialPolicy?.require_approval ?? socialRequireApproval)} kill_switch=
                            {String(socialPolicy?.kill_switch_active ?? socialKillSwitchActive)}
                          </p>
                        </div>
                        <div className="mt-2 grid gap-2 md:grid-cols-2">
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Campaign</span>
                            <input
                              type="text"
                              value={socialCampaignName}
                              onChange={(event) => setSocialCampaignName(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Employee Segment</span>
                            <input
                              type="text"
                              value={socialEmployeeSegment}
                              onChange={(event) => setSocialEmployeeSegment(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Email Count</span>
                            <input
                              type="number"
                              min={1}
                              max={5000}
                              value={socialEmailCount}
                              onChange={(event) => setSocialEmailCount(Number(event.target.value || 50))}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Difficulty</span>
                            <select
                              value={socialDifficulty}
                              onChange={(event) => setSocialDifficulty(event.target.value as "low" | "medium" | "high")}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            >
                              <option value="low">low</option>
                              <option value="medium">medium</option>
                              <option value="high">high</option>
                            </select>
                          </label>
                          <label className="text-slate-400 md:col-span-2">
                            <span className="mb-1 block text-[11px]">Impersonation Brand</span>
                            <input
                              type="text"
                              value={socialImpersonationBrand}
                              onChange={(event) => setSocialImpersonationBrand(event.target.value)}
                              placeholder={site.display_name}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove}
                            onClick={() => void runSocialSimulator(site.site_id, true)}
                            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                          >
                            Run Dry Run
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove}
                            onClick={() => void runSocialSimulator(site.site_id, false)}
                            className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                          >
                            Queue/Run Campaign
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove || latestSocialRun?.execution?.status !== "pending_approval"}
                            onClick={() => void reviewLatestSocialCampaign(site.site_id, true)}
                            className="rounded border border-emerald-500/60 bg-emerald-500/10 px-2 py-1 text-[11px] text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-60"
                          >
                            Approve Latest
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove || latestSocialRun?.execution?.status !== "pending_approval"}
                            onClick={() => void reviewLatestSocialCampaign(site.site_id, false)}
                            className="rounded border border-danger/60 bg-danger/10 px-2 py-1 text-[11px] text-danger hover:bg-danger/20 disabled:opacity-60"
                          >
                            Reject Latest
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove || !latestSocialRun}
                            onClick={() => void killLatestSocialCampaign(site.site_id)}
                            className="rounded border border-danger/60 bg-danger/10 px-2 py-1 text-[11px] text-danger hover:bg-danger/20 disabled:opacity-60"
                          >
                            Kill Latest Campaign
                          </button>
                        </div>
                      </div>

                      <div className="rounded border border-slate-800 bg-panelAlt/30 p-2">
                        <p className="font-medium text-slate-200">Connector Policy</p>
                        <div className="mt-2 grid gap-2">
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Connector</span>
                            <select
                              value={socialConnectorType}
                              onChange={(event) => setSocialConnectorType(event.target.value as SocialConnectorType)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            >
                              <option value="simulated">simulated</option>
                              <option value="smtp">smtp</option>
                              <option value="webhook">webhook</option>
                            </select>
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Sender Name</span>
                            <input
                              type="text"
                              value={socialSenderName}
                              onChange={(event) => setSocialSenderName(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Sender Email</span>
                            <input
                              type="text"
                              value={socialSenderEmail}
                              onChange={(event) => setSocialSenderEmail(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Subject Prefix</span>
                            <input
                              type="text"
                              value={socialSubjectPrefix}
                              onChange={(event) => setSocialSubjectPrefix(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Landing Base URL</span>
                            <input
                              type="text"
                              value={socialLandingBaseUrl}
                              onChange={(event) => setSocialLandingBaseUrl(event.target.value)}
                              placeholder={site.base_url}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Allowed Domains (csv)</span>
                            <input
                              type="text"
                              value={socialAllowedDomainsCsv}
                              onChange={(event) => setSocialAllowedDomainsCsv(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Max Emails / Run</span>
                            <input
                              type="number"
                              min={1}
                              max={5000}
                              value={socialMaxEmailsPerRun}
                              onChange={(event) => setSocialMaxEmailsPerRun(Number(event.target.value || 200))}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="flex items-center gap-2 text-slate-400">
                            <input type="checkbox" checked={socialRequireApproval} onChange={(event) => setSocialRequireApproval(event.target.checked)} />
                            Require approval
                          </label>
                          <label className="flex items-center gap-2 text-slate-400">
                            <input type="checkbox" checked={socialOpenTracking} onChange={(event) => setSocialOpenTracking(event.target.checked)} />
                            Open tracking
                          </label>
                          <label className="flex items-center gap-2 text-slate-400">
                            <input type="checkbox" checked={socialClickTracking} onChange={(event) => setSocialClickTracking(event.target.checked)} />
                            Click tracking
                          </label>
                          <label className="flex items-center gap-2 text-slate-400">
                            <input
                              type="checkbox"
                              checked={socialConnectorSimulateDelivery}
                              onChange={(event) => setSocialConnectorSimulateDelivery(event.target.checked)}
                            />
                            Simulate delivery
                          </label>
                          <label className="flex items-center gap-2 text-slate-400">
                            <input type="checkbox" checked={socialPolicyEnabled} onChange={(event) => setSocialPolicyEnabled(event.target.checked)} />
                            Policy enabled
                          </label>
                          <label className="flex items-center gap-2 text-slate-400">
                            <input type="checkbox" checked={socialKillSwitchActive} onChange={(event) => setSocialKillSwitchActive(event.target.checked)} />
                            Site kill switch
                          </label>
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canEditPolicy}
                            onClick={() => void saveSocialPolicy(site.site_id)}
                            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                          >
                            Save Social Policy
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 grid gap-2 xl:grid-cols-3">
                      <div className="rounded border border-slate-800 bg-panelAlt/30 p-2 xl:col-span-2">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-medium text-slate-200">Employee Roster</p>
                          <p className="text-[11px] text-slate-500">
                            active={socialRoster?.summary.active_count || 0} high_risk={socialRoster?.summary.high_risk_count || 0}
                          </p>
                        </div>
                        <textarea
                          value={socialRosterPayload}
                          onChange={(event) => setSocialRosterPayload(event.target.value)}
                          rows={10}
                          className="mt-2 w-full rounded border border-slate-700 bg-panel px-2 py-2 font-mono text-[11px] text-slate-200"
                        />
                        <div className="mt-2 flex flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove}
                            onClick={() => void importSocialRoster(site.site_id)}
                            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                          >
                            Import Roster
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0}
                            onClick={() => setSocialRosterPayload(SOCIAL_ROSTER_SAMPLE)}
                            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                          >
                            Reload Sample
                          </button>
                        </div>
                        <div className="mt-2 space-y-2">
                          {(socialRoster?.rows || []).slice(0, 5).map((row) => (
                            <div key={row.roster_entry_id} className="rounded border border-slate-800 bg-panel/70 p-2">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="font-medium text-slate-100 wrap-anywhere">{row.full_name || row.email}</p>
                                <p className="text-[11px] uppercase text-slate-500">
                                  {row.department || "-"} | {row.risk_level} | {row.is_active ? "active" : "inactive"}
                                </p>
                              </div>
                              <p className="mt-1 text-slate-400 wrap-anywhere">{row.email}</p>
                              <p className="mt-1 text-slate-500 wrap-anywhere">{row.role_title || "no role title"} tags={(row.tags || []).join(", ") || "-"}</p>
                            </div>
                          ))}
                          {(socialRoster?.rows || []).length === 0 ? <p className="text-slate-500">No employee roster yet.</p> : null}
                        </div>
                      </div>

                      <div className="rounded border border-slate-800 bg-panelAlt/30 p-2">
                        <p className="font-medium text-slate-200">Telemetry + Recent Campaign</p>
                        {latestSocialRun ? (
                          <div className="mt-2 space-y-2">
                            <div className="rounded border border-slate-800 bg-panel/70 p-2">
                              <p className="text-slate-200 wrap-anywhere">{latestSocialRun.summary_th}</p>
                              <p className="mt-1 text-[11px] text-slate-500 wrap-anywhere">
                                status={latestSocialRun.execution.status} connector={latestSocialRun.execution.connector_type} dispatch=
                                {latestSocialRun.execution.dispatch_mode}
                              </p>
                              <p className="mt-1 text-[11px] text-slate-500 wrap-anywhere">
                                risk={latestSocialRun.risk_tier}/{latestSocialRun.risk_score} emails={latestSocialRun.email_count}
                              </p>
                            </div>
                            <div className="rounded border border-slate-800 bg-panel/70 p-2">
                              <p className="text-slate-300">Telemetry Summary</p>
                              <p className="mt-1 text-slate-500 wrap-anywhere">
                                delivered={String(socialTelemetry?.summary.delivered_count || 0)} opened=
                                {String(socialTelemetry?.summary.opened_count || 0)} clicked={String(socialTelemetry?.summary.clicked_count || 0)} reported=
                                {String(socialTelemetry?.summary.reported_count || 0)}
                              </p>
                              <p className="mt-1 text-slate-500 wrap-anywhere">
                                open={String(socialTelemetry?.summary.open_rate_pct || 0)}% click={String(socialTelemetry?.summary.click_rate_pct || 0)}% report=
                                {String(socialTelemetry?.summary.report_rate_pct || 0)}%
                              </p>
                            </div>
                            <div className="rounded border border-slate-800 bg-panel/70 p-2">
                              <div className="flex items-center justify-between gap-2">
                                <p className="text-slate-300">Provider Callback Ingest</p>
                                <p className="text-[11px] text-slate-500 wrap-anywhere">
                                  latest connector={latestSocialRun.execution.connector_type || socialConnectorType}
                                </p>
                              </div>
                              <div className="mt-2 grid gap-2 md:grid-cols-2">
                                <label className="text-slate-400">
                                  <span className="mb-1 block text-[11px]">Event Type</span>
                                  <select
                                    value={socialProviderEventType}
                                    onChange={(event) => setSocialProviderEventType(event.target.value)}
                                    className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                                  >
                                    <option value="delivered">delivered</option>
                                    <option value="opened">opened</option>
                                    <option value="clicked">clicked</option>
                                    <option value="reported">reported</option>
                                    <option value="complained">complained</option>
                                    <option value="bounced">bounced</option>
                                  </select>
                                </label>
                                <label className="text-slate-400">
                                  <span className="mb-1 block text-[11px]">Recipient Email</span>
                                  <input
                                    value={socialProviderRecipientEmail}
                                    onChange={(event) => setSocialProviderRecipientEmail(event.target.value)}
                                    placeholder={socialTelemetry?.rows?.[0]?.recipient_email || "employee@example.com"}
                                    className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                                  />
                                </label>
                                <label className="text-slate-400">
                                  <span className="mb-1 block text-[11px]">Provider Event ID</span>
                                  <input
                                    value={socialProviderEventId}
                                    onChange={(event) => setSocialProviderEventId(event.target.value)}
                                    className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                                  />
                                </label>
                                <label className="text-slate-400">
                                  <span className="mb-1 block text-[11px]">Occurred At</span>
                                  <input
                                    value={socialProviderOccurredAt}
                                    onChange={(event) => setSocialProviderOccurredAt(event.target.value)}
                                    placeholder="2026-03-15T09:00:00+07:00"
                                    className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                                  />
                                </label>
                                <label className="text-slate-400 md:col-span-2">
                                  <span className="mb-1 block text-[11px]">Metadata JSON</span>
                                  <textarea
                                    value={socialProviderMetadata}
                                    onChange={(event) => setSocialProviderMetadata(event.target.value)}
                                    rows={3}
                                    className="w-full rounded border border-slate-700 bg-panel px-2 py-2 font-mono text-[11px] text-slate-200"
                                  />
                                </label>
                              </div>
                              <div className="mt-2 flex flex-wrap gap-2">
                                <button
                                  type="button"
                                  disabled={busyKey.length > 0 || !canApprove}
                                  onClick={() => void ingestLatestSocialProviderCallback(site.site_id)}
                                  className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                                >
                                  Ingest Provider Callback
                                </button>
                                <button
                                  type="button"
                                  disabled={busyKey.length > 0 || (socialTelemetry?.rows || []).length === 0}
                                  onClick={() => setSocialProviderRecipientEmail(socialTelemetry?.rows?.[0]?.recipient_email || "")}
                                  className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                                >
                                  Use Latest Recipient
                                </button>
                              </div>
                              {socialCallbackResultBySite[site.site_id] ? (
                                <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                                  <p className="text-slate-200 wrap-anywhere">
                                    callback={socialCallbackResultBySite[site.site_id].callback.event_type} recipient=
                                    {socialCallbackResultBySite[site.site_id].recipient.recipient_email}
                                  </p>
                                  <p className="mt-1 text-[11px] text-slate-500 wrap-anywhere">
                                    status={socialCallbackResultBySite[site.site_id].status} occurred_at=
                                    {socialCallbackResultBySite[site.site_id].callback.occurred_at} provider_event_id=
                                    {socialCallbackResultBySite[site.site_id].callback.provider_event_id || "-"}
                                  </p>
                                </div>
                              ) : null}
                            </div>
                            {(socialTelemetry?.rows || []).slice(0, 3).map((row) => (
                              <div key={row.recipient_id} className="rounded border border-slate-800 bg-panel/70 p-2">
                                <p className="text-slate-200 wrap-anywhere">{row.recipient_name || row.recipient_email}</p>
                                <p className="mt-1 text-slate-500 wrap-anywhere">
                                  {row.delivery_status} | opened={row.opened_at ? "yes" : "no"} clicked={row.clicked_at ? "yes" : "no"} reported=
                                  {row.reported_at ? "yes" : "no"}
                                </p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="mt-2 text-slate-500">No social campaign yet.</p>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="text-slate-300">Vulnerability Auto-Validator</p>
                        <p className="mt-1 text-slate-500 wrap-anywhere">
                          import finding จาก Nessus/Burp หรือ scanner ภายนอก แล้วให้ AI normalize, dedupe, และตัดสิน verdict ต่อ finding พร้อม remediation export
                        </p>
                      </div>
                      <p className="text-[11px] text-slate-500 wrap-anywhere">{validatorSummary}</p>
                    </div>

                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Source Tool</span>
                        <select
                          value={validatorSourceTool}
                          onChange={(event) => loadValidatorSample(event.target.value as ValidatorSourceTool)}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        >
                          <option value="nessus">nessus</option>
                          <option value="burp">burp</option>
                          <option value="generic">generic</option>
                        </select>
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Max Findings / Run</span>
                        <input
                          type="number"
                          min={1}
                          max={200}
                          value={validatorMaxFindings}
                          onChange={(event) => setValidatorMaxFindings(Number(event.target.value || 20))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400 md:col-span-2">
                        <span className="mb-1 block text-[11px]">Scanner Payload JSON</span>
                        <textarea
                          value={validatorImportPayload}
                          onChange={(event) => setValidatorImportPayload(event.target.value)}
                          rows={10}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-2 font-mono text-[11px] text-slate-200"
                        />
                      </label>
                    </div>

                    <div className="mt-2 flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={busyKey.length > 0 || !canApprove}
                        onClick={() => void importValidatorFindings(site.site_id)}
                        className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                      >
                        Import Findings
                      </button>
                      <button
                        type="button"
                        disabled={busyKey.length > 0 || !canApprove}
                        onClick={() => void runValidator(site.site_id, true)}
                        className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                      >
                        Run Validator Dry Run
                      </button>
                      <button
                        type="button"
                        disabled={busyKey.length > 0 || !canApprove}
                        onClick={() => void runValidator(site.site_id, false)}
                        className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                      >
                        Validate and Score Findings
                      </button>
                      <button
                        type="button"
                        disabled={busyKey.length > 0}
                        onClick={() => loadValidatorSample(validatorSourceTool)}
                        className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                      >
                        Reload Sample
                      </button>
                    </div>

                    <div className="mt-3 grid gap-2 xl:grid-cols-3">
                      <div className="rounded border border-slate-800 bg-panelAlt/30 p-2 xl:col-span-2">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-medium text-slate-200">Imported Findings</p>
                          <p className="text-[11px] text-slate-500">{validatorFindings?.count || 0} rows</p>
                        </div>
                        <div className="mt-2 space-y-2">
                          {(validatorFindings?.rows || []).slice(0, 6).map((finding) => (
                            <div key={finding.finding_id} className="rounded border border-slate-800 bg-panel/70 p-2">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <p className="font-medium text-slate-100 wrap-anywhere">{finding.title}</p>
                                <p className="text-[11px] uppercase text-slate-400">
                                  {finding.source_tool} | {finding.severity} | {finding.verdict}
                                </p>
                              </div>
                              <p className="mt-1 text-slate-400 wrap-anywhere">
                                asset={finding.asset || "-"} endpoint={finding.endpoint || "-"} cve={finding.cve_id || "-"}
                              </p>
                              <p className="mt-1 text-slate-500 wrap-anywhere">{finding.ai_summary || "ยังไม่มี verdict ล่าสุด"}</p>
                              <p className="mt-1 text-[11px] text-slate-500 wrap-anywhere">
                                exploitability={finding.exploitability_score} false_positive={finding.false_positive_score} import_count={finding.import_count}
                              </p>
                            </div>
                          ))}
                          {(validatorFindings?.rows || []).length === 0 ? (
                            <p className="text-slate-500">No imported findings yet.</p>
                          ) : null}
                        </div>
                      </div>

                      <div className="rounded border border-slate-800 bg-panelAlt/30 p-2">
                        <p className="font-medium text-slate-200">Validation Runs</p>
                        <div className="mt-2 space-y-2">
                          {(validatorRuns?.rows || []).slice(0, 4).map((run) => (
                            <div key={run.run_id} className="rounded border border-slate-800 bg-panel/70 p-2">
                              <p className="text-slate-200 wrap-anywhere">{run.summary_th}</p>
                              <p className="mt-1 text-[11px] text-slate-500">
                                {run.status} | findings={run.finding_count} exploitable={run.exploitable_count} fp={run.false_positive_count}
                              </p>
                            </div>
                          ))}
                          {(validatorRuns?.rows || []).length === 0 ? <p className="text-slate-500">No validator runs yet.</p> : null}
                        </div>
                      </div>
                    </div>

                    <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-medium text-slate-200">Remediation Export</p>
                        <p className="text-[11px] text-slate-500">{validatorExport?.count || 0} rows ready</p>
                      </div>
                      <div className="mt-2 space-y-2">
                        {(validatorExport?.rows || []).slice(0, 3).map((row) => (
                          <div key={String(row.finding_id)} className="rounded border border-slate-800 bg-panel/70 p-2">
                            <p className="text-slate-200 wrap-anywhere">
                              {String(row.source_tool).toUpperCase()} to {String(row.scanner_status)}
                            </p>
                            <p className="mt-1 text-slate-400 wrap-anywhere">{String(row.comment || "")}</p>
                            <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap rounded border border-slate-800 bg-panelAlt/30 p-2 text-[11px] text-slate-300">
                              {JSON.stringify(row.payload, null, 2)}
                            </pre>
                          </div>
                        ))}
                        {(validatorExport?.rows || []).length === 0 ? <p className="text-slate-500">No remediation export yet.</p> : null}
                      </div>
                    </div>
                  </div>

                  <div className="rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-slate-300 wrap-anywhere">Red Plugins Category</p>
                      <div className="flex items-center gap-2">
                        <label className="text-[11px] text-slate-500">
                          export
                          <select
                            value={pluginExportKind}
                            onChange={(event) => setPluginExportKind(event.target.value)}
                            className="ml-2 rounded border border-slate-700 bg-panel px-1 py-0.5 text-[11px] text-slate-200"
                          >
                            <option value="bundle">bundle</option>
                            <option value="threat_content_bundle">threat_content_bundle</option>
                          </select>
                        </label>
                        <p className="text-[11px] text-slate-500 wrap-anywhere">uses target surface: {targetSurface}</p>
                      </div>
                    </div>
                    <div className="mt-2 grid gap-2 xl:grid-cols-3">
                      <div className="rounded border border-slate-800 bg-panelAlt/30 p-2">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-medium text-slate-200">Plugin Intelligence Inputs</p>
                          <p className="text-[11px] text-slate-500 wrap-anywhere">
                            latest={latestIntel?.source_type || "none"} {latestIntel?.cve_id || latestIntel?.title || ""}
                          </p>
                        </div>
                        <p className="mt-1 text-slate-500 wrap-anywhere">
                          import CVE/news/article intelligence เพื่อให้ Nuclei template และ exploit draft อ้างอิง threat context จริงแทน finding ภายในอย่างเดียว
                        </p>
                        <div className="mt-2 grid gap-2 md:grid-cols-2">
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Source Type</span>
                            <select
                              value={pluginIntelSourceType}
                              onChange={(event) => setPluginIntelSourceType(event.target.value as "cve" | "news" | "article")}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            >
                              <option value="cve">cve</option>
                              <option value="news">news</option>
                              <option value="article">article</option>
                            </select>
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">CVE ID</span>
                            <input
                              value={pluginIntelCveId}
                              onChange={(event) => setPluginIntelCveId(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400 md:col-span-2">
                            <span className="mb-1 block text-[11px]">Title</span>
                            <input
                              value={pluginIntelTitle}
                              onChange={(event) => setPluginIntelTitle(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Target Type</span>
                            <input
                              value={pluginIntelTargetType}
                              onChange={(event) => setPluginIntelTargetType(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Reference URL</span>
                            <input
                              value={pluginIntelReference}
                              onChange={(event) => setPluginIntelReference(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400 md:col-span-2">
                            <span className="mb-1 block text-[11px]">Summary</span>
                            <textarea
                              value={pluginIntelSummary}
                              onChange={(event) => setPluginIntelSummary(event.target.value)}
                              rows={4}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-2 text-xs text-slate-200"
                            />
                          </label>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canEditPolicy}
                            onClick={() => void importPluginIntelligence(site.site_id)}
                            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                          >
                            Import Intelligence
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0}
                            onClick={() => void loadPluginIntelligence(site.site_id)}
                            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                          >
                            Reload Intelligence
                          </button>
                        </div>
                        <div className="mt-2 space-y-2">
                          {(pluginIntel?.rows || []).slice(0, 3).map((row) => (
                            <div key={row.intel_id} className="rounded border border-slate-800 bg-panel/70 p-2">
                              <p className="text-slate-200 wrap-anywhere">{row.title}</p>
                              <p className="mt-1 text-[11px] text-slate-500 wrap-anywhere">
                                {row.source_type} | {row.cve_id || row.source_item_id} | {row.target_type} | {row.target_surface || "-"}
                              </p>
                              <p className="mt-1 text-slate-400 wrap-anywhere">{row.summary_th}</p>
                            </div>
                          ))}
                          {(pluginIntel?.rows || []).length === 0 ? <p className="text-slate-500">No plugin intelligence imported yet.</p> : null}
                        </div>
                      </div>

                      <div className="rounded border border-slate-800 bg-panelAlt/30 p-2">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-medium text-slate-200">External Intelligence Sync</p>
                          <p className="text-[11px] text-slate-500 wrap-anywhere">
                            {latestPluginSyncSource
                              ? `${latestPluginSyncSource.source_name} / ${latestPluginSyncSource.sync_interval_minutes}m`
                              : "no source"}
                          </p>
                        </div>
                        <p className="mt-1 text-slate-500 wrap-anywhere">
                          auto-sync feed ภายนอกเข้า Red plugin intelligence แล้วส่งต่อเป็น Nuclei template หรือ publish เป็น threat pack ได้ทันที
                        </p>
                        <div className="mt-2 grid gap-2 md:grid-cols-2">
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Source Name</span>
                            <input
                              value={pluginSyncSourceName}
                              onChange={(event) => setPluginSyncSourceName(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Parser</span>
                            <select
                              value={pluginSyncParserKind}
                              onChange={(event) => setPluginSyncParserKind(event.target.value as "json_feed" | "jsonl")}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            >
                              <option value="json_feed">json_feed</option>
                              <option value="jsonl">jsonl</option>
                            </select>
                          </label>
                          <label className="text-slate-400 md:col-span-2">
                            <span className="mb-1 block text-[11px]">Source URL</span>
                            <input
                              value={pluginSyncSourceUrl}
                              onChange={(event) => setPluginSyncSourceUrl(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Interval Minutes</span>
                            <input
                              type="number"
                              min={5}
                              max={10080}
                              value={pluginSyncIntervalMinutes}
                              onChange={(event) => setPluginSyncIntervalMinutes(Number(event.target.value || 1440))}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="flex items-end gap-2 text-slate-300">
                            <input
                              type="checkbox"
                              checked={pluginSyncEnabled}
                              onChange={(event) => setPluginSyncEnabled(event.target.checked)}
                            />
                            enabled
                          </label>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canEditPolicy}
                            onClick={() => void savePluginSyncSource(site.site_id)}
                            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                          >
                            Save Sync Source
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove}
                            onClick={() => void runPluginSync(site.site_id, true)}
                            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                          >
                            Dry Run Sync
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove}
                            onClick={() => void runPluginSync(site.site_id, false)}
                            className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                          >
                            Import Feed
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove}
                            onClick={() => void runPluginSyncScheduler()}
                            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                          >
                            Run Sync Scheduler
                          </button>
                        </div>
                        {pluginSyncSummary ? <p className="mt-2 text-[11px] text-slate-400 wrap-anywhere">{pluginSyncSummary}</p> : null}
                        <div className="mt-2 space-y-2">
                          {latestPluginSyncRun ? (
                            <div className="rounded border border-slate-800 bg-panel/70 p-2">
                              <p className="text-slate-200 wrap-anywhere">
                                {latestPluginSyncRun.status} fetched={latestPluginSyncRun.fetched_count} imported={latestPluginSyncRun.imported_count}
                              </p>
                              <p className="mt-1 text-[11px] text-slate-500 wrap-anywhere">
                                actor={latestPluginSyncRun.actor} at {latestPluginSyncRun.created_at}
                              </p>
                            </div>
                          ) : (
                            <p className="text-slate-500">No sync runs yet.</p>
                          )}
                          {(pluginSyncSources?.rows || []).slice(0, 2).map((row) => (
                            <div key={row.sync_source_id} className="rounded border border-slate-800 bg-panel/70 p-2">
                              <p className="text-slate-200 wrap-anywhere">{row.source_name}</p>
                              <p className="mt-1 text-[11px] text-slate-500 wrap-anywhere">
                                {row.source_type} | {row.parser_kind} | every {row.sync_interval_minutes}m | last={row.last_synced_at || "never"}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="rounded border border-slate-800 bg-panelAlt/30 p-2">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-medium text-slate-200">Exploit Safety Policy</p>
                          <p className="text-[11px] text-slate-500 wrap-anywhere">
                            target_type={pluginSafetyPolicy?.target_type || pluginSafetyTargetType} network={String(pluginSafetyPolicy?.allow_network_calls ?? pluginSafetyAllowNetwork)}
                          </p>
                        </div>
                        <p className="mt-1 text-slate-500 wrap-anywhere">
                          policy นี้ถูกใช้ตอน generate exploit draft และตอน lint/export เพื่อกันโค้ดหลุดขอบเขตจาก authorized validation
                        </p>
                        <div className="mt-2 grid gap-2 md:grid-cols-2">
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Target Type</span>
                            <input
                              value={pluginSafetyTargetType}
                              onChange={(event) => setPluginSafetyTargetType(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Max HTTP Requests / Run</span>
                            <input
                              type="number"
                              min={1}
                              max={50}
                              value={pluginSafetyMaxRequests}
                              onChange={(event) => setPluginSafetyMaxRequests(Number(event.target.value || 5))}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Max Script Lines</span>
                            <input
                              type="number"
                              min={10}
                              max={500}
                              value={pluginSafetyMaxLines}
                              onChange={(event) => setPluginSafetyMaxLines(Number(event.target.value || 80))}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400">
                            <span className="mb-1 block text-[11px]">Allowed Modules CSV</span>
                            <input
                              value={pluginSafetyAllowedModulesCsv}
                              onChange={(event) => setPluginSafetyAllowedModulesCsv(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                          <label className="text-slate-400 md:col-span-2">
                            <span className="mb-1 block text-[11px]">Blocked Modules CSV</span>
                            <input
                              value={pluginSafetyBlockedModulesCsv}
                              onChange={(event) => setPluginSafetyBlockedModulesCsv(event.target.value)}
                              className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                            />
                          </label>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-300">
                          <label className="flex items-center gap-2">
                            <input type="checkbox" checked={pluginSafetyAllowNetwork} onChange={(event) => setPluginSafetyAllowNetwork(event.target.checked)} />
                            allow_network_calls
                          </label>
                          <label className="flex items-center gap-2">
                            <input type="checkbox" checked={pluginSafetyRequireHeader} onChange={(event) => setPluginSafetyRequireHeader(event.target.checked)} />
                            require_comment_header
                          </label>
                          <label className="flex items-center gap-2">
                            <input type="checkbox" checked={pluginSafetyRequireDisclaimer} onChange={(event) => setPluginSafetyRequireDisclaimer(event.target.checked)} />
                            require_disclaimer
                          </label>
                        </div>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canEditPolicy}
                            onClick={() => void savePluginSafetyPolicy(site.site_id)}
                            className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                          >
                            Save Safety Policy
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0}
                            onClick={() => void loadPluginSafetyPolicy(site.site_id, pluginSafetyTargetType)}
                            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                          >
                            Reload Policy
                          </button>
                        </div>
                      </div>
                    </div>
                    <div className="mt-2 grid gap-2 lg:grid-cols-2">
                      <div className="rounded border border-slate-800 bg-panelAlt/30 p-2">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-medium text-slate-200">Nuclei AI-Template Writer</p>
                          <span className="rounded-full border border-accent/50 bg-accent/10 px-2 py-0.5 text-[10px] uppercase text-accent">
                            live
                          </span>
                        </div>
                        <p className="mt-1 text-slate-500 wrap-anywhere">
                          เขียน YAML template จาก finding ล่าสุดเพื่อให้ทีม Red/Blue ใช้ตรวจซ้ำหรือแชร์เป็น threat content ได้ทันที
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove}
                            onClick={() => void runRedPlugin(site.site_id, "red_template_writer", true)}
                            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                          >
                            Generate Template Dry Run
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove}
                            onClick={() => void runRedPlugin(site.site_id, "red_template_writer", false)}
                            className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                          >
                            Generate Nuclei Template
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0}
                            onClick={() => void lintRedPluginArtifact(site.site_id, "red_template_writer")}
                            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                          >
                            Lint Template
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove}
                            onClick={() => void exportRedPluginArtifact(site.site_id, "red_template_writer")}
                            className="rounded border border-accent/50 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                          >
                            Export Template
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove}
                            onClick={() => void publishTemplateThreatPack(site.site_id)}
                            className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                          >
                            Publish as Threat Pack
                          </button>
                        </div>
                        {latestTemplateRun ? (
                          <div className="mt-2 rounded border border-slate-800 bg-panel/70 p-2">
                            <p className="text-slate-200 wrap-anywhere">
                              {String(latestTemplateRun.output_summary.headline || "Template generated")}
                            </p>
                            <p className="mt-1 text-slate-400 wrap-anywhere">
                              {String(latestTemplateRun.output_summary.summary_th || "")}
                            </p>
                            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded border border-slate-800 bg-panelAlt/30 p-2 text-[11px] text-slate-300">
                              {String(latestTemplateRun.output_summary.template_preview || "No template preview yet.")}
                            </pre>
                            <p className="mt-2 text-[11px] text-slate-500 wrap-anywhere">
                              intelligence={(latestTemplateRun.output_summary.source_intelligence as Record<string, unknown> | undefined)?.title
                                ? String((latestTemplateRun.output_summary.source_intelligence as Record<string, unknown>).title)
                                : "none"}
                            </p>
                            {templateLint ? (
                              <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                                <p className="text-slate-300 wrap-anywhere">lint={templateLint.lint.status} lines={templateLint.lint.line_count}</p>
                                <p className="mt-1 text-slate-500 wrap-anywhere">
                                  issues={(templateLint.lint.issues || []).join(" | ") || "none"} warnings={(templateLint.lint.warnings || []).join(" | ") || "none"}
                                </p>
                              </div>
                            ) : null}
                            {templateExport ? (
                              <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                                <p className="text-slate-300 wrap-anywhere">{templateExport.export.filename}</p>
                                <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap rounded border border-slate-800 bg-panel/70 p-2 text-[11px] text-slate-300">
                                  {JSON.stringify(templateExport.export.threat_content_suggestion || templateExport.export.metadata, null, 2)}
                                </pre>
                              </div>
                            ) : null}
                            {pluginPublish ? (
                              <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                                <p className="text-slate-300 wrap-anywhere">
                                  pack={pluginPublish.pack.pack_code} category={pluginPublish.pack.category} active={String(pluginPublish.pack.is_active)}
                                </p>
                                <p className="mt-1 text-slate-500 wrap-anywhere">{pluginPublish.pack.attack_steps.join(" | ")}</p>
                              </div>
                            ) : null}
                          </div>
                        ) : (
                          <p className="mt-2 text-slate-500">No Nuclei template generated yet.</p>
                        )}
                      </div>

                      <div className="rounded border border-slate-800 bg-panelAlt/30 p-2">
                        <div className="flex items-center justify-between gap-2">
                          <p className="font-medium text-slate-200">Exploit Code Generator</p>
                          <span className="rounded-full border border-accent/50 bg-accent/10 px-2 py-0.5 text-[10px] uppercase text-accent">
                            live
                          </span>
                        </div>
                        <p className="mt-1 text-slate-500 wrap-anywhere">
                          แปลง finding ล่าสุดให้เป็น Python proof-of-concept draft สำหรับยืนยัน exploitability แบบปลอดภัย
                        </p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove}
                            onClick={() => void runRedPlugin(site.site_id, "red_exploit_code_generator", true)}
                            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                          >
                            Generate PoC Dry Run
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove}
                            onClick={() => void runRedPlugin(site.site_id, "red_exploit_code_generator", false)}
                            className="rounded border border-danger/60 bg-danger/10 px-2 py-1 text-[11px] text-danger hover:bg-danger/20 disabled:opacity-60"
                          >
                            Generate Exploit Draft
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0}
                            onClick={() => void lintRedPluginArtifact(site.site_id, "red_exploit_code_generator")}
                            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                          >
                            Lint Exploit
                          </button>
                          <button
                            type="button"
                            disabled={busyKey.length > 0 || !canApprove}
                            onClick={() => void exportRedPluginArtifact(site.site_id, "red_exploit_code_generator")}
                            className="rounded border border-accent/50 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                          >
                            Export Exploit
                          </button>
                        </div>
                        {latestExploitCodeRun ? (
                          <div className="mt-2 rounded border border-slate-800 bg-panel/70 p-2">
                            <p className="text-slate-200 wrap-anywhere">
                              {String(latestExploitCodeRun.output_summary.headline || "Exploit draft generated")}
                            </p>
                            <p className="mt-1 text-slate-400 wrap-anywhere">
                              {String(latestExploitCodeRun.output_summary.summary_th || "")}
                            </p>
                            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap rounded border border-slate-800 bg-panelAlt/30 p-2 text-[11px] text-slate-300">
                              {String(latestExploitCodeRun.output_summary.script_preview || "No exploit preview yet.")}
                            </pre>
                            <p className="mt-2 text-[11px] text-slate-500 wrap-anywhere">
                              safety={(latestExploitCodeRun.output_summary.safety_policy as Record<string, unknown> | undefined)?.target_type
                                ? `target=${String((latestExploitCodeRun.output_summary.safety_policy as Record<string, unknown>).target_type)} network=${String((latestExploitCodeRun.output_summary.safety_policy as Record<string, unknown>).allow_network_calls)}`
                                : "default"}
                            </p>
                            {exploitLint ? (
                              <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                                <p className="text-slate-300 wrap-anywhere">lint={exploitLint.lint.status} lines={exploitLint.lint.line_count}</p>
                                <p className="mt-1 text-slate-500 wrap-anywhere">
                                  issues={(exploitLint.lint.issues || []).join(" | ") || "none"} warnings={(exploitLint.lint.warnings || []).join(" | ") || "none"}
                                </p>
                              </div>
                            ) : null}
                            {exploitExport ? (
                              <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                                <p className="text-slate-300 wrap-anywhere">{exploitExport.export.filename}</p>
                                <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap rounded border border-slate-800 bg-panel/70 p-2 text-[11px] text-slate-300">
                                  {JSON.stringify(exploitExport.export.lint || exploitExport.export.metadata, null, 2)}
                                </pre>
                              </div>
                            ) : null}
                          </div>
                        ) : (
                          <p className="mt-2 text-slate-500">No exploit draft generated yet.</p>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className="text-slate-300 wrap-anywhere">24/7 Shadow Pentest</p>
                        <p className="mt-1 text-slate-500 wrap-anywhere">
                          passive crawl + diff-based drift detection เพื่อจับการเปลี่ยนแปลงของไซต์แบบปลอดภัย แล้ว map ไปยัง zero-day threat pack ที่เหมาะกับหน้าที่เปลี่ยน
                        </p>
                      </div>
                      <p className="text-[11px] text-slate-500 wrap-anywhere">
                        latest={latestShadowRun?.status || "none"} changed={String(latestShadowRun?.site_changed || false)} pack=
                        {latestShadowRun?.assigned_pack_code || "none"}
                      </p>
                    </div>
                    {canView ? (
                      <p className="mt-2 text-slate-500 wrap-anywhere">
                        Current: depth={shadowPolicy?.crawl_depth ?? shadowCrawlDepth} max_pages={shadowPolicy?.max_pages ?? shadowMaxPages} threshold=
                        {shadowPolicy?.change_threshold ?? shadowChangeThreshold} schedule=
                        {shadowPolicy?.schedule_interval_minutes ?? shadowScheduleMinutes}m auto_pack=
                        {String(shadowPolicy?.auto_assign_zero_day_pack ?? shadowAutoAssignZeroDayPack)}
                      </p>
                    ) : (
                      <p className="mt-2 text-slate-500">No permission to view shadow policy.</p>
                    )}
                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Crawl Depth</span>
                        <input
                          type="number"
                          min={0}
                          max={4}
                          value={shadowCrawlDepth}
                          onChange={(event) => setShadowCrawlDepth(Number(event.target.value || 2))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Max Pages</span>
                        <input
                          type="number"
                          min={1}
                          max={100}
                          value={shadowMaxPages}
                          onChange={(event) => setShadowMaxPages(Number(event.target.value || 12))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Change Threshold</span>
                        <input
                          type="number"
                          min={1}
                          max={50}
                          value={shadowChangeThreshold}
                          onChange={(event) => setShadowChangeThreshold(Number(event.target.value || 2))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Schedule (minutes)</span>
                        <input
                          type="number"
                          min={5}
                          max={1440}
                          value={shadowScheduleMinutes}
                          onChange={(event) => setShadowScheduleMinutes(Number(event.target.value || 180))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-3 text-slate-300">
                      <label className="flex items-center gap-1 text-[11px]">
                        <input
                          type="checkbox"
                          checked={shadowAutoAssignZeroDayPack}
                          onChange={(event) => setShadowAutoAssignZeroDayPack(event.target.checked)}
                        />
                        auto_assign_zero_day_pack
                      </label>
                      <label className="flex items-center gap-1 text-[11px]">
                        <input type="checkbox" checked={shadowRouteAlert} onChange={(event) => setShadowRouteAlert(event.target.checked)} />
                        route_alert
                      </label>
                      <label className="flex items-center gap-1 text-[11px]">
                        <input type="checkbox" checked={shadowEnabled} onChange={(event) => setShadowEnabled(event.target.checked)} />
                        enabled
                      </label>
                    </div>
                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                      <button
                        type="button"
                        disabled={!canEditPolicy || busyKey.length > 0}
                        onClick={() => void saveShadowPolicy(site.site_id)}
                        className="rounded-md border border-accent/60 bg-accent/10 px-2 py-2 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                      >
                        Save Shadow Policy
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runShadowPentest(site.site_id, true, false)}
                        className="rounded-md border border-slate-600 px-2 py-2 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                      >
                        Run Shadow Dry-Run
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runShadowPentest(site.site_id, false, true)}
                        className="rounded-md border border-warning/50 bg-warning/10 px-2 py-2 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                      >
                        Run Shadow Apply
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runShadowScheduler()}
                        className="rounded-md border border-slate-600 px-2 py-2 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                      >
                        Trigger Shadow Scheduler
                      </button>
                    </div>
                    <div className="mt-3 rounded border border-slate-800 bg-panelAlt/30 p-2">
                      <p className="text-slate-300 wrap-anywhere">Deploy-Event Trigger Mode</p>
                      <p className="mt-1 text-[11px] text-slate-500 wrap-anywhere">
                        ใช้จาก CI/CD หรือ release pipeline เพื่อ force shadow scan หลัง deploy โดยแนบ changed paths มาด้วย
                      </p>
                      <div className="mt-2 grid gap-2 md:grid-cols-2">
                        <label className="text-slate-400">
                          <span className="mb-1 block text-[11px]">Deploy ID</span>
                          <input
                            value={shadowDeployId}
                            onChange={(event) => setShadowDeployId(event.target.value)}
                            className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                          />
                        </label>
                        <label className="text-slate-400">
                          <span className="mb-1 block text-[11px]">Release Version</span>
                          <input
                            value={shadowReleaseVersion}
                            onChange={(event) => setShadowReleaseVersion(event.target.value)}
                            className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                          />
                        </label>
                        <label className="text-slate-400 md:col-span-2">
                          <span className="mb-1 block text-[11px]">Changed Paths CSV</span>
                          <input
                            value={shadowChangedPathsCsv}
                            onChange={(event) => setShadowChangedPathsCsv(event.target.value)}
                            className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                          />
                        </label>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <button
                          type="button"
                          disabled={!canApprove || busyKey.length > 0}
                          onClick={() => void triggerShadowDeployEvent(site.site_id)}
                          className="rounded-md border border-warning/50 bg-warning/10 px-2 py-2 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                        >
                          Trigger Deploy Event
                        </button>
                      </div>
                    </div>
                    <p className="mt-2 text-slate-500 wrap-anywhere">{shadowRunSummary}</p>
                    <div className="mt-2 max-h-32 overflow-auto rounded border border-slate-800 p-2">
                      {(shadowRuns?.rows || []).length === 0 ? <p className="text-slate-500">No shadow pentest runs yet.</p> : null}
                      {(shadowRuns?.rows || []).slice(0, 4).map((run) => (
                        <div key={run.run_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/40 p-2">
                          <p className="text-slate-200 wrap-anywhere">
                            {run.status} changed={String(run.site_changed)} pages={run.page_count} delta=
                            {run.new_page_count + run.changed_page_count + run.removed_page_count}
                          </p>
                          <p className="mt-1 text-slate-400 wrap-anywhere">
                            pack={run.assigned_pack_code || "none"} category={run.assigned_pack_category || "generic"} alert=
                            {String(run.alert_routed)}
                          </p>
                        </div>
                      ))}
                    </div>
                    <div className="mt-2 max-h-40 overflow-auto rounded border border-slate-800 p-2">
                      <p className="text-slate-300 wrap-anywhere">
                        Asset Inventory total={shadowAssets?.summary.total_assets || 0}
                      </p>
                      <p className="mt-1 text-[11px] text-slate-500 wrap-anywhere">
                        kinds={Object.entries(shadowAssets?.summary.kind_counts || {})
                          .map(([key, value]) => `${key}:${String(value)}`)
                          .join(", ") || "none"}
                      </p>
                      {(shadowAssets?.rows || []).length === 0 ? <p className="mt-2 text-slate-500">No asset inventory yet.</p> : null}
                      {(shadowAssets?.rows || []).slice(0, 6).map((asset) => (
                        <div key={`${asset.path}:${asset.url}`} className="mt-2 rounded border border-slate-800 bg-panelAlt/40 p-2">
                          <p className="text-slate-200 wrap-anywhere">
                            {asset.asset_kind} {asset.path}
                          </p>
                          <p className="mt-1 text-slate-400 wrap-anywhere">
                            status={asset.status_code} risk={asset.risk_hint} title={asset.title || "-"}
                          </p>
                        </div>
                      ))}
                    </div>
                    <div className="mt-2 max-h-48 overflow-auto rounded border border-slate-800 p-2">
                      <p className="text-slate-300 wrap-anywhere">
                        Pack-to-Asset Validation pack={shadowAssets?.pack_validation.summary.pack_code || "none"} matched=
                        {shadowAssets?.pack_validation.summary.matched_assets || 0}/{shadowAssets?.pack_validation.summary.total_assets || 0} coverage=
                        {shadowAssets?.pack_validation.summary.coverage_pct || 0}% targeted={shadowAssets?.pack_validation.summary.targeted_assets || 0}
                      </p>
                      <p className="mt-1 text-[11px] text-slate-500 wrap-anywhere">
                        changed_hits={shadowAssets?.pack_validation.summary.changed_asset_hits || 0} attack_steps=
                        {shadowAssets?.pack_validation.summary.attack_step_count || 0} unmatched=
                        {shadowAssets?.pack_validation.summary.unmatched_assets || 0}
                      </p>
                      {(shadowAssets?.pack_validation.rows || []).length === 0 ? <p className="mt-2 text-slate-500">No pack validation yet.</p> : null}
                      {(shadowAssets?.pack_validation.rows || []).slice(0, 6).map((row) => (
                        <div key={`${row.path}:${row.validation_status}`} className="mt-2 rounded border border-slate-800 bg-panelAlt/40 p-2">
                          <p className="text-slate-200 wrap-anywhere">
                            {row.validation_status} priority={row.priority} matched={String(row.matched)} {row.path}
                          </p>
                          <p className="mt-1 text-slate-400 wrap-anywhere">
                            asset={row.asset_kind} candidates={(row.candidate_categories || []).join(", ") || "none"} risk={row.risk_hint}
                          </p>
                          <p className="mt-1 text-[11px] text-slate-500 wrap-anywhere">
                            rationale={row.rationale} steps={(row.validation_steps || []).join(" | ") || "none"}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
                    <p className="text-slate-300 wrap-anywhere">Red Exploit Autopilot Policy</p>
                    {canView ? (
                      <p className="mt-1 text-slate-500 wrap-anywhere">
                        Current: risk&gt;={autopilotPolicy?.min_risk_score ?? minRiskScore}/{autopilotPolicy?.min_risk_tier ?? minRiskTier} category={autopilotPolicy?.preferred_pack_category ?? preferredPackCategory} auto_run={String(autopilotPolicy?.auto_run ?? autoRun)}
                      </p>
                    ) : (
                      <p className="mt-1 text-slate-500">No permission to view policy.</p>
                    )}

                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Min Risk Score</span>
                        <input
                          type="number"
                          min={1}
                          max={100}
                          value={minRiskScore}
                          onChange={(event) => setMinRiskScore(Number(event.target.value || 50))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Min Risk Tier</span>
                        <select
                          value={minRiskTier}
                          onChange={(event) => setMinRiskTier(event.target.value as RiskTier)}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        >
                          <option value="low">low</option>
                          <option value="medium">medium</option>
                          <option value="high">high</option>
                          <option value="critical">critical</option>
                        </select>
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Pack Category</span>
                        <input
                          value={preferredPackCategory}
                          onChange={(event) => setPreferredPackCategory(event.target.value)}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Target Surface</span>
                        <input
                          value={targetSurface}
                          onChange={(event) => setTargetSurface(event.target.value)}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Simulation Depth</span>
                        <input
                          type="number"
                          min={1}
                          max={5}
                          value={simulationDepth}
                          onChange={(event) => setSimulationDepth(Number(event.target.value || 3))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Max RPM</span>
                        <input
                          type="number"
                          min={1}
                          max={500}
                          value={maxRequestsPerMinute}
                          onChange={(event) => setMaxRequestsPerMinute(Number(event.target.value || 30))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Schedule (minutes)</span>
                        <input
                          type="number"
                          min={5}
                          max={1440}
                          value={scheduleMinutes}
                          onChange={(event) => setScheduleMinutes(Number(event.target.value || 120))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                    </div>

                    <div className="mt-2 flex flex-wrap gap-3 text-slate-300">
                      <label className="flex items-center gap-1 text-[11px]">
                        <input type="checkbox" checked={stopOnCritical} onChange={(event) => setStopOnCritical(event.target.checked)} />
                        stop_on_critical
                      </label>
                      <label className="flex items-center gap-1 text-[11px]">
                        <input type="checkbox" checked={simulationOnly} onChange={(event) => setSimulationOnly(event.target.checked)} />
                        simulation_only
                      </label>
                      <label className="flex items-center gap-1 text-[11px]">
                        <input type="checkbox" checked={autoRun} onChange={(event) => setAutoRun(event.target.checked)} />
                        auto_run
                      </label>
                      <label className="flex items-center gap-1 text-[11px]">
                        <input type="checkbox" checked={routeAlert} onChange={(event) => setRouteAlert(event.target.checked)} />
                        route_alert
                      </label>
                    </div>

                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                      <button
                        type="button"
                        disabled={!canEditPolicy || busyKey.length > 0}
                        onClick={() => void saveAutopilotPolicy(site.site_id)}
                        className="rounded-md border border-accent/60 bg-accent/10 px-2 py-2 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                      >
                        Save Red Autopilot Policy
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runAutopilot(site.site_id, true, false)}
                        className="rounded-md border border-slate-600 px-2 py-2 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                      >
                        Run Autopilot Dry-Run
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runAutopilot(site.site_id, false, true)}
                        className="rounded-md border border-warning/50 bg-warning/10 px-2 py-2 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                      >
                        Run Autopilot Apply
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runAutopilotScheduler()}
                        className="rounded-md border border-slate-600 px-2 py-2 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                      >
                        Trigger Autopilot Scheduler
                      </button>
                    </div>

                    <p className="mt-2 text-slate-500 wrap-anywhere">{autopilotRunSummary}</p>
                  </div>

                  <div className="rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
                    <p className="text-slate-300 wrap-anywhere">Threat Content Pipeline (O2)</p>
                    <p className="mt-1 text-slate-500 wrap-anywhere">{pipelinePolicySummary}</p>
                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Scope</span>
                        <input
                          value={pipelineScope}
                          onChange={(event) => setPipelineScope(event.target.value || "global")}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Refresh Interval (minutes)</span>
                        <input
                          type="number"
                          min={5}
                          max={10080}
                          value={pipelineMinRefreshMinutes}
                          onChange={(event) => setPipelineMinRefreshMinutes(Number(event.target.value || 1440))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400 md:col-span-2">
                        <span className="mb-1 block text-[11px]">Preferred Categories (comma-separated)</span>
                        <input
                          value={pipelinePreferredCategoriesCsv}
                          onChange={(event) => setPipelinePreferredCategoriesCsv(event.target.value)}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                      <label className="text-slate-400">
                        <span className="mb-1 block text-[11px]">Max Packs per Run</span>
                        <input
                          type="number"
                          min={1}
                          max={50}
                          value={pipelineMaxPacksPerRun}
                          onChange={(event) => setPipelineMaxPacksPerRun(Number(event.target.value || 8))}
                          className="w-full rounded border border-slate-700 bg-panel px-2 py-1 text-xs text-slate-200"
                        />
                      </label>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-3 text-slate-300">
                      <label className="flex items-center gap-1 text-[11px]">
                        <input
                          type="checkbox"
                          checked={pipelineAutoActivate}
                          onChange={(event) => setPipelineAutoActivate(event.target.checked)}
                        />
                        auto_activate
                      </label>
                      <label className="flex items-center gap-1 text-[11px]">
                        <input type="checkbox" checked={pipelineEnabled} onChange={(event) => setPipelineEnabled(event.target.checked)} />
                        enabled
                      </label>
                    </div>
                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                      <button
                        type="button"
                        disabled={!canEditPolicy || busyKey.length > 0}
                        onClick={() => void saveThreatContentPipelinePolicy()}
                        className="rounded-md border border-accent/60 bg-accent/10 px-2 py-2 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                      >
                        Save Pipeline Policy
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runThreatPipeline(true, false)}
                        className="rounded-md border border-slate-600 px-2 py-2 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                      >
                        Run Pipeline Dry-Run
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runThreatPipeline(false, true)}
                        className="rounded-md border border-warning/50 bg-warning/10 px-2 py-2 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                      >
                        Run Pipeline Apply
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey.length > 0}
                        onClick={() => void runThreatPipelineScheduler()}
                        className="rounded-md border border-slate-600 px-2 py-2 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                      >
                        Trigger Pipeline Scheduler
                      </button>
                    </div>
                    <p className="mt-2 text-slate-500 wrap-anywhere">{pipelineRunSummary}</p>
                    <div className="mt-2 max-h-32 overflow-auto rounded border border-slate-800 p-2">
                      {(pipelineRuns?.rows || []).length === 0 ? <p className="text-slate-500">No pipeline runs yet.</p> : null}
                      {(pipelineRuns?.rows || []).slice(0, 4).map((run) => (
                        <p key={run.run_id} className="text-slate-300 wrap-anywhere">
                          {run.created_at} [{run.status}] candidate={run.candidate_count} created={run.created_count} refreshed=
                          {run.refreshed_count}
                        </p>
                      ))}
                    </div>
                    {pipelineFederation ? (
                      <div className="mt-2 max-h-28 overflow-auto rounded border border-slate-800 p-2">
                        <p className="text-slate-400 wrap-anywhere">
                          federation categories={pipelineFederation.count} stale={pipelineFederation.stale_count}
                        </p>
                        {pipelineFederation.rows.slice(0, 4).map((row) => (
                          <p key={row.category} className="text-slate-300 wrap-anywhere">
                            {row.category}: packs={row.pack_count} mitre={row.unique_mitre_techniques} stale={String(row.is_stale)}
                          </p>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  <div className="max-h-52 overflow-auto rounded border border-slate-800 p-2 text-xs">
                    <p className="mb-2 text-slate-400">Scan Results</p>
                    {history?.rows?.length ? null : <p className="text-slate-500">No scans yet.</p>}
                    {(history?.rows || []).map((row) => (
                      <div key={row.scan_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/40 p-2">
                        <p className="text-slate-200">{row.scan_type}</p>
                        <p className="mt-1 text-slate-400 wrap-anywhere">{row.ai_summary}</p>
                      </div>
                    ))}
                  </div>

                  <div className="max-h-44 overflow-auto rounded border border-slate-800 p-2 text-xs">
                    <p className="mb-2 text-slate-400">Exploit Path Runs</p>
                    {(exploitRunsBySite[site.site_id]?.rows || []).length === 0 ? (
                      <p className="text-slate-500">No exploit-path runs yet.</p>
                    ) : null}
                    {(exploitRunsBySite[site.site_id]?.rows || []).map((run) => (
                      <div key={run.run_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/40 p-2">
                        <p className="text-slate-200">risk_score={run.risk_score}</p>
                        <p className="mt-1 text-slate-400 wrap-anywhere">proof: {JSON.stringify(run.proof)}</p>
                      </div>
                    ))}
                  </div>

                  <div className="max-h-44 overflow-auto rounded border border-slate-800 p-2 text-xs">
                    <p className="mb-2 text-slate-400">Exploit Autopilot Runs</p>
                    {(autopilotRunsBySite[site.site_id]?.rows || []).length === 0 ? (
                      <p className="text-slate-500">No autopilot runs yet.</p>
                    ) : null}
                    {(autopilotRunsBySite[site.site_id]?.rows || []).map((run) => (
                      <div key={run.run_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/40 p-2">
                        <p className="text-slate-200 wrap-anywhere">
                          {run.status} risk={run.risk_tier}/{run.risk_score} executed={String(run.executed)}
                        </p>
                        <p className="mt-1 text-slate-400 wrap-anywhere">
                          pack={run.threat_pack_code || "none"} path={run.path_node_count}n/{run.path_edge_count}e confidence={run.proof_confidence}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      {selectedSite ? (
        <p className="mt-3 text-[11px] text-slate-500">
          Selected site: <span className="font-mono">{selectedSite.site_code}</span>
        </p>
      ) : null}
    </section>
  );
}
