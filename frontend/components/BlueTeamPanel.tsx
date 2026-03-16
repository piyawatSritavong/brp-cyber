import { useEffect, useState } from "react";

import {
  applySiteBlueRecommendation,
  applySiteDetectionRule,
  fetchBlueLogRefinerMappingPacks,
  fetchSoarConnectorResultContracts,
  fetchSoarConnectorResults,
  fetchSoarMarketplaceOverview,
  fetchSoarMarketplacePacks,
  fetchBlueThreatFeedAdapterTemplates,
  fetchBlueThreatFeedItems,
  fetchBlueThreatSectorProfiles,
  fetchSiteBlueEvents,
  fetchSiteBlueLogRefinerFeedback,
  fetchSiteBlueLogRefinerCallbacks,
  fetchSiteBlueLogRefinerPolicy,
  fetchSiteBlueLogRefinerSchedulePolicy,
  fetchSiteBlueLogRefinerRuns,
  fetchSiteBlueManagedResponderPolicy,
  fetchSiteBlueManagedResponderRuns,
  fetchSiteBlueThreatLocalizerPolicy,
  fetchSiteBlueThreatLocalizerPromotionRuns,
  fetchSiteBlueThreatLocalizerRoutingPolicy,
  reviewSiteBlueManagedResponderRun,
  rollbackSiteBlueManagedResponderRun,
  fetchSiteCoworkerPluginRuns,
  fetchSiteBlueThreatLocalizerRuns,
  fetchSiteDetectionAutotunePolicy,
  fetchSiteDetectionAutotuneRuns,
  fetchSiteDetectionRules,
  fetchSiteSoarExecutions,
  installSoarMarketplacePack,
  ingestSoarConnectorResult,
  verifySoarExecution,
  verifySiteBlueManagedResponderEvidence,
  ingestSiteBlueEvent,
  ingestSiteBlueLogRefinerCallback,
  importBlueThreatFeedItems,
  importBlueThreatFeedAdapter,
  runBlueLogRefinerScheduler,
  runDetectionAutotuneScheduler,
  runBlueThreatLocalizerScheduler,
  runBlueManagedResponderScheduler,
  runSiteCoworkerPlugin,
  runSiteBlueLogRefiner,
  runSiteBlueManagedResponder,
  runSiteBlueThreatLocalizer,
  promoteSiteBlueThreatLocalizerGap,
  runSiteDetectionAutotune,
  runSiteDetectionCopilotTune,
  submitSiteBlueLogRefinerFeedback,
  upsertSiteBlueLogRefinerPolicy,
  upsertSiteBlueLogRefinerSchedulePolicy,
  upsertSiteBlueManagedResponderPolicy,
  upsertSiteBlueThreatLocalizerPolicy,
  upsertSiteBlueThreatLocalizerRoutingPolicy,
  upsertSiteDetectionAutotunePolicy,
} from "@/lib/api";
import type {
  BlueLogRefinerMappingPackResponse,
  BlueThreatFeedListResponse,
  BlueThreatFeedAdapterTemplatesResponse,
  BlueThreatSectorProfilesResponse,
  SiteBlueEventHistoryResponse,
  SiteBlueLogRefinerFeedbackListResponse,
  SiteBlueLogRefinerCallbackListResponse,
  SiteBlueLogRefinerPolicyResponse,
  SiteBlueLogRefinerSchedulePolicyResponse,
  SiteBlueLogRefinerRunListResponse,
  SiteBlueManagedResponderRunListResponse,
  SiteBlueManagedResponderRunResponse,
  SiteBlueManagedResponderEvidenceVerifyResponse,
  SiteBlueThreatLocalizerPolicyResponse,
  SiteBlueThreatLocalizerPromotionRunListResponse,
  SiteBlueThreatLocalizerRoutingPolicyResponse,
  SiteCoworkerPluginRunListResponse,
  SiteBlueThreatLocalizerRunListResponse,
  SiteDetectionAutotuneRunListResponse,
  SiteDetectionCopilotTuneResponse,
  SiteDetectionRulesResponse,
  SiteRow,
  SoarExecutionListResponse,
  SoarConnectorResultContractListResponse,
  SoarConnectorResultListResponse,
  SoarConnectorResultResponse,
  SoarExecutionVerifyResponse,
  SoarMarketplaceOverview,
  SoarMarketplacePackListResponse,
} from "@/lib/types";

type Props = {
  selectedSite: SiteRow | null;
  canView: boolean;
  canEditPolicy: boolean;
  canApprove: boolean;
};

type ActionType = "block_ip" | "notify_team" | "limit_user" | "ignore";
type ActionMode = "ai_recommended" | ActionType;

type RiskTier = "low" | "medium" | "high" | "critical";
type LogRefinerMode = "pre_ingest" | "post_ingest";
type LogRefinerFeedbackType = "keep_signal" | "drop_noise" | "false_positive" | "signal_missed";

const BLUE_SERVICE_MENUS = [
  {
    title: "AI Log Refiner (The Noise Killer)",
    fit: "บริษัทที่ใช้ SIEM/ELK แล้วคนดู log ไม่ไหว",
    value: "ลด alert noise และลดต้นทุนการเก็บข้อมูลในระบบหลัก",
    status: "live",
    note: "Mapped to Blue log triage + plugin-based AI Log Refiner",
  },
  {
    title: "Managed AI Responder",
    fit: "SME หรือองค์กรที่ไม่มีทีม SOC เฝ้ากลางคืน",
    value: "ตอบสนองเหตุการณ์ 24/7 ในต้นทุนต่ำกว่าการเฝ้ากะด้วยคน",
    status: "live",
    note: "Combines AI recommendation apply, Auto-Playbook Executor payload generation, and optional SOAR dry-run dispatch",
  },
  {
    title: "Threat Intelligence Localizer",
    fit: "องค์กรที่ต้องการป้องกันเชิงรุกตามภัยที่ระบาดในไทย",
    value: "สรุปภัยคุกคามเป็นภาษาไทยและเช็กผลกระทบกับระบบเราได้เร็วขึ้น",
    status: "live",
    note: "Localized Thai threat summary with site relevance scoring and recommended actions",
  },
];

const THREAT_FEED_SAMPLE = JSON.stringify(
  [
    {
      source_item_id: "thai-banking-phish-001",
      title: "Thai banking phishing lure targeting finance portals",
      summary_th: "พบแคมเปญ phishing ภาษาไทยปลอมหน้า login ขององค์กรการเงินและหลอกขอ OTP",
      category: "phishing",
      severity: "high",
      focus_region: "thailand",
      sectors: ["finance", "general"],
      iocs: ["login-secure-th.example", "198.51.100.55"],
      references: ["https://example.org/threat/thai-banking-phish-001"],
      published_at: "2026-03-15T09:00:00+07:00",
      payload: {
        family: "credential_phishing",
        tactic: "initial_access",
      },
    },
  ],
  null,
  2,
);

function parseCategoryInput(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}

function parseJsonMap(value: string): Record<string, string[]> {
  if (!value.trim()) return {};
  const parsed = JSON.parse(value) as Record<string, unknown>;
  const out: Record<string, string[]> = {};
  for (const [key, raw] of Object.entries(parsed || {})) {
    const normalizedKey = String(key || "").trim().toLowerCase();
    if (!normalizedKey) continue;
    if (Array.isArray(raw)) {
      out[normalizedKey] = raw.map((item) => String(item || "").trim().toLowerCase()).filter(Boolean);
      continue;
    }
    const single = String(raw || "").trim().toLowerCase();
    out[normalizedKey] = single ? [single] : [];
  }
  return out;
}

function formatThreatLocalizerRunSummary(run: { priority_score: number; risk_tier: string; details: Record<string, unknown> }) {
  const details = run.details || {};
  const siteImpact = Number(details.site_impact_score || 0);
  const feedCount = Number(details.feed_match_count || 0);
  const exploitRisk = Number(details.exploit_risk || 0);
  const detectionGap = (details.detection_gap as { missing_categories?: string[] } | undefined)?.missing_categories?.length || 0;
  return `priority=${run.priority_score} risk=${run.risk_tier} site_impact=${siteImpact} feed_matches=${feedCount} exploit_risk=${exploitRisk} gaps=${detectionGap}`;
}

export function BlueTeamPanel({ selectedSite, canView, canEditPolicy, canApprove }: Props) {
  const [history, setHistory] = useState<SiteBlueEventHistoryResponse | null>(null);
  const [detectionRules, setDetectionRules] = useState<SiteDetectionRulesResponse | null>(null);
  const [autotuneRuns, setAutotuneRuns] = useState<SiteDetectionAutotuneRunListResponse | null>(null);
  const [localizerRuns, setLocalizerRuns] = useState<SiteBlueThreatLocalizerRunListResponse | null>(null);
  const [localizerPolicy, setLocalizerPolicy] = useState<SiteBlueThreatLocalizerPolicyResponse | null>(null);
  const [localizerRoutingPolicy, setLocalizerRoutingPolicy] = useState<SiteBlueThreatLocalizerRoutingPolicyResponse | null>(null);
  const [localizerPromotionRuns, setLocalizerPromotionRuns] = useState<SiteBlueThreatLocalizerPromotionRunListResponse | null>(null);
  const [localizerFeeds, setLocalizerFeeds] = useState<BlueThreatFeedListResponse | null>(null);
  const [localizerFeedAdapters, setLocalizerFeedAdapters] = useState<BlueThreatFeedAdapterTemplatesResponse | null>(null);
  const [localizerProfiles, setLocalizerProfiles] = useState<BlueThreatSectorProfilesResponse | null>(null);
  const [logRefinerPolicy, setLogRefinerPolicy] = useState<SiteBlueLogRefinerPolicyResponse | null>(null);
  const [logRefinerSchedulePolicy, setLogRefinerSchedulePolicy] = useState<SiteBlueLogRefinerSchedulePolicyResponse | null>(null);
  const [logRefinerRuns, setLogRefinerRuns] = useState<SiteBlueLogRefinerRunListResponse | null>(null);
  const [logRefinerFeedback, setLogRefinerFeedback] = useState<SiteBlueLogRefinerFeedbackListResponse | null>(null);
  const [logRefinerCallbacks, setLogRefinerCallbacks] = useState<SiteBlueLogRefinerCallbackListResponse | null>(null);
  const [logRefinerMappingPacks, setLogRefinerMappingPacks] = useState<BlueLogRefinerMappingPackResponse | null>(null);
  const [pluginRuns, setPluginRuns] = useState<SiteCoworkerPluginRunListResponse | null>(null);
  const [soarExecutions, setSoarExecutions] = useState<SoarExecutionListResponse | null>(null);
  const [soarConnectorContracts, setSoarConnectorContracts] = useState<SoarConnectorResultContractListResponse | null>(null);
  const [soarConnectorResults, setSoarConnectorResults] = useState<SoarConnectorResultListResponse | null>(null);
  const [soarMarketplaceOverview, setSoarMarketplaceOverview] = useState<SoarMarketplaceOverview | null>(null);
  const [soarMarketplacePacks, setSoarMarketplacePacks] = useState<SoarMarketplacePackListResponse | null>(null);
  const [soarVerificationByExecution, setSoarVerificationByExecution] = useState<Record<string, SoarExecutionVerifyResponse>>({});
  const [soarConnectorCallbackSummary, setSoarConnectorCallbackSummary] = useState("No connector callback yet");
  const [lastTune, setLastTune] = useState<SiteDetectionCopilotTuneResponse | null>(null);
  const [managedRuns, setManagedRuns] = useState<SiteBlueManagedResponderRunListResponse | null>(null);
  const [managedEvidence, setManagedEvidence] = useState<SiteBlueManagedResponderEvidenceVerifyResponse | null>(null);

  const [autotunePolicySummary, setAutotunePolicySummary] = useState("No autotune policy loaded");
  const [autotuneRunSummary, setAutotuneRunSummary] = useState("No autotune run yet");
  const [managedPolicySummary, setManagedPolicySummary] = useState("No managed responder policy loaded");
  const [managedRunSummary, setManagedRunSummary] = useState("No managed responder run yet");
  const [managedSchedulerSummary, setManagedSchedulerSummary] = useState("No managed responder scheduler run yet");
  const [managedEvidenceSummary, setManagedEvidenceSummary] = useState("No evidence chain verification yet");
  const [soarMarketplaceSummary, setSoarMarketplaceSummary] = useState("No marketplace data loaded");
  const [localizerPolicySummary, setLocalizerPolicySummary] = useState("No threat localizer policy loaded");
  const [localizerRunSummary, setLocalizerRunSummary] = useState("No threat localizer run yet");
  const [localizerFeedSummary, setLocalizerFeedSummary] = useState("No external threat feed imported yet");
  const [localizerSchedulerSummary, setLocalizerSchedulerSummary] = useState("No threat localizer scheduler run yet");
  const [localizerRoutingSummary, setLocalizerRoutingSummary] = useState("No routing pack policy loaded");
  const [localizerPromotionSummary, setLocalizerPromotionSummary] = useState("No gap promotion run yet");
  const [logRefinerPolicySummary, setLogRefinerPolicySummary] = useState("No log refiner policy loaded");
  const [logRefinerScheduleSummary, setLogRefinerScheduleSummary] = useState("No log refiner scheduler policy loaded");
  const [logRefinerRunSummary, setLogRefinerRunSummary] = useState("No log refiner run yet");
  const [logRefinerFeedbackSummary, setLogRefinerFeedbackSummary] = useState("No operator feedback yet");
  const [logRefinerCallbackSummary, setLogRefinerCallbackSummary] = useState("No source SIEM callback yet");

  const [minRiskScore, setMinRiskScore] = useState(60);
  const [minRiskTier, setMinRiskTier] = useState<RiskTier>("high");
  const [targetCoveragePct, setTargetCoveragePct] = useState(90);
  const [maxRulesPerRun, setMaxRulesPerRun] = useState(3);
  const [autoApplyAutotune, setAutoApplyAutotune] = useState(false);
  const [autotuneRouteAlert, setAutotuneRouteAlert] = useState(true);
  const [autotuneScheduleMinutes, setAutotuneScheduleMinutes] = useState(60);
  const [focusRegion, setFocusRegion] = useState("thailand");
  const [sector, setSector] = useState("general");
  const [localizerCategoriesText, setLocalizerCategoriesText] = useState("identity, phishing, ransomware, web");
  const [localizerRecurringDigestEnabled, setLocalizerRecurringDigestEnabled] = useState(true);
  const [localizerScheduleMinutes, setLocalizerScheduleMinutes] = useState(240);
  const [localizerMinFeedPriority, setLocalizerMinFeedPriority] = useState<RiskTier>("medium");
  const [localizerEnabled, setLocalizerEnabled] = useState(true);
  const [localizerStakeholderGroupsText, setLocalizerStakeholderGroupsText] = useState("soc_l1, threat_hunting, security_lead");
  const [localizerGroupChannelMapText, setLocalizerGroupChannelMapText] = useState(
    JSON.stringify({ soc_l1: ["telegram"], threat_hunting: ["teams"], security_lead: ["line"] }, null, 2),
  );
  const [localizerCategoryGroupMapText, setLocalizerCategoryGroupMapText] = useState(
    JSON.stringify({ phishing: ["soc_l1", "security_lead"], web: ["threat_hunting", "soc_l1"] }, null, 2),
  );
  const [localizerRoutingMinPriority, setLocalizerRoutingMinPriority] = useState(60);
  const [localizerRoutingMinRiskTier, setLocalizerRoutingMinRiskTier] = useState<RiskTier>("high");
  const [localizerAutoPromoteOnGap, setLocalizerAutoPromoteOnGap] = useState(true);
  const [localizerAutoApplyAutotune, setLocalizerAutoApplyAutotune] = useState(false);
  const [localizerDispatchActionCenter, setLocalizerDispatchActionCenter] = useState(true);
  const [localizerPlaybookPromotionEnabled, setLocalizerPlaybookPromotionEnabled] = useState(true);
  const [localizerFeedSource, setLocalizerFeedSource] = useState("manual");
  const [localizerAdapterSource, setLocalizerAdapterSource] = useState("generic");
  const [localizerFeedPayload, setLocalizerFeedPayload] = useState(THREAT_FEED_SAMPLE);
  const [logRefinerConnectorSource, setLogRefinerConnectorSource] = useState("splunk");
  const [logRefinerExecutionMode, setLogRefinerExecutionMode] = useState<LogRefinerMode>("pre_ingest");
  const [logRefinerLookbackLimit, setLogRefinerLookbackLimit] = useState(200);
  const [logRefinerMinKeepSeverity, setLogRefinerMinKeepSeverity] = useState<RiskTier>("medium");
  const [logRefinerDropRecommendationsText, setLogRefinerDropRecommendationsText] = useState("ignore");
  const [logRefinerTargetNoiseReductionPct, setLogRefinerTargetNoiseReductionPct] = useState(80);
  const [logRefinerAverageEventSizeKb, setLogRefinerAverageEventSizeKb] = useState(4);
  const [logRefinerEnabled, setLogRefinerEnabled] = useState(true);
  const [logRefinerScheduleMinutes, setLogRefinerScheduleMinutes] = useState(60);
  const [logRefinerScheduleDryRun, setLogRefinerScheduleDryRun] = useState(true);
  const [logRefinerCallbackEnabled, setLogRefinerCallbackEnabled] = useState(true);
  const [logRefinerScheduleEnabled, setLogRefinerScheduleEnabled] = useState(true);
  const [logRefinerFeedbackType, setLogRefinerFeedbackType] = useState<LogRefinerFeedbackType>("keep_signal");
  const [logRefinerFeedbackEventType, setLogRefinerFeedbackEventType] = useState("waf_http");
  const [logRefinerFeedbackRecommendation, setLogRefinerFeedbackRecommendation] = useState("ignore");
  const [logRefinerFeedbackNote, setLogRefinerFeedbackNote] = useState("");
  const [logRefinerCallbackType, setLogRefinerCallbackType] = useState<"stream_result" | "storage_report" | "delivery_receipt">("stream_result");
  const [logRefinerCallbackSourceSystem, setLogRefinerCallbackSourceSystem] = useState("splunk");
  const [logRefinerCallbackExternalRef, setLogRefinerCallbackExternalRef] = useState("siem-batch-001");
  const [logRefinerCallbackEventId, setLogRefinerCallbackEventId] = useState("");
  const [logRefinerCallbackTotal, setLogRefinerCallbackTotal] = useState(120);
  const [logRefinerCallbackKept, setLogRefinerCallbackKept] = useState(28);
  const [logRefinerCallbackDropped, setLogRefinerCallbackDropped] = useState(92);
  const [logRefinerCallbackSavedKb, setLogRefinerCallbackSavedKb] = useState(368);
  const [responderMinSeverity, setResponderMinSeverity] = useState<RiskTier>("medium");
  const [responderAction, setResponderAction] = useState<ActionMode>("ai_recommended");
  const [responderPlaybookCode, setResponderPlaybookCode] = useState("block-ip-and-waf-tighten");
  const [responderDispatchPlaybook, setResponderDispatchPlaybook] = useState(true);
  const [responderRequireApproval, setResponderRequireApproval] = useState(true);
  const [responderDryRun, setResponderDryRun] = useState(true);
  const [responderEnabled, setResponderEnabled] = useState(true);
  const [soarContractSource, setSoarContractSource] = useState("cloudflare");
  const [soarContractCode, setSoarContractCode] = useState("cloudflare_block_result_v1");
  const [soarExternalActionRef, setSoarExternalActionRef] = useState("edge-action-001");
  const [soarWebhookEventId, setSoarWebhookEventId] = useState("vendor-callback-001");
  const [soarConnectorResultStatus, setSoarConnectorResultStatus] = useState("confirmed");
  const [soarConnectorPayloadText, setSoarConnectorPayloadText] = useState(
    JSON.stringify({ result: { blocked_ip: "203.0.113.10", rule_mode: "strict", edge_status: "confirmed" } }, null, 2),
  );

  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const selectedThreatAdapter = (localizerFeedAdapters?.rows || []).find((row) => row.source === localizerAdapterSource) || null;

  const load = async () => {
    if (!selectedSite) return;
    setLoading(true);
    setError("");
    try {
      const [events, rules] = await Promise.all([
        fetchSiteBlueEvents(selectedSite.site_id, 100),
        fetchSiteDetectionRules(selectedSite.site_id, 30),
      ]);
      setHistory(events);
      setDetectionRules(rules);

      if (canView) {
        const [
          policy,
          runs,
          threatRuns,
          threatPolicy,
          threatRoutingPolicy,
          threatPromotionRuns,
          threatFeeds,
          threatAdapters,
          threatProfiles,
          refinerPolicy,
          refinerSchedulePolicy,
          refinerRuns,
          refinerFeedbackRows,
          refinerCallbackRows,
          refinerMappingRows,
          bluePluginRuns,
          soarRunHistory,
          soarContracts,
          marketplaceOverview,
          marketplacePacks,
          responderPolicy,
          responderRunHistory,
          responderEvidence,
        ] = await Promise.all([
          fetchSiteDetectionAutotunePolicy(selectedSite.site_id),
          fetchSiteDetectionAutotuneRuns(selectedSite.site_id, 20),
          fetchSiteBlueThreatLocalizerRuns(selectedSite.site_id, 10),
          fetchSiteBlueThreatLocalizerPolicy(selectedSite.site_id),
          fetchSiteBlueThreatLocalizerRoutingPolicy(selectedSite.site_id),
          fetchSiteBlueThreatLocalizerPromotionRuns(selectedSite.site_id, 10),
          fetchBlueThreatFeedItems({ focus_region: focusRegion, sector, limit: 20 }),
          fetchBlueThreatFeedAdapterTemplates(localizerAdapterSource),
          fetchBlueThreatSectorProfiles(),
          fetchSiteBlueLogRefinerPolicy(selectedSite.site_id, logRefinerConnectorSource),
          fetchSiteBlueLogRefinerSchedulePolicy(selectedSite.site_id, logRefinerConnectorSource),
          fetchSiteBlueLogRefinerRuns(selectedSite.site_id, { connector_source: logRefinerConnectorSource, limit: 10 }),
          fetchSiteBlueLogRefinerFeedback(selectedSite.site_id, { connector_source: logRefinerConnectorSource, limit: 10 }),
          fetchSiteBlueLogRefinerCallbacks(selectedSite.site_id, { connector_source: logRefinerConnectorSource, limit: 10 }),
          fetchBlueLogRefinerMappingPacks(logRefinerConnectorSource),
          fetchSiteCoworkerPluginRuns(selectedSite.site_id, { category: "blue", limit: 10 }),
          fetchSiteSoarExecutions(selectedSite.site_id, { limit: 10 }),
          fetchSoarConnectorResultContracts({ connector_source: soarContractSource }),
          fetchSoarMarketplaceOverview(200),
          fetchSoarMarketplacePacks({ limit: 20 }),
          fetchSiteBlueManagedResponderPolicy(selectedSite.site_id),
          fetchSiteBlueManagedResponderRuns(selectedSite.site_id, 10),
          verifySiteBlueManagedResponderEvidence(selectedSite.site_id, 20),
        ]);
        setAutotuneRuns(runs);
        setLocalizerRuns(threatRuns);
        setLocalizerPolicy(threatPolicy);
        setLocalizerRoutingPolicy(threatRoutingPolicy);
        setLocalizerPromotionRuns(threatPromotionRuns);
        setLocalizerFeeds(threatFeeds);
        setLocalizerFeedAdapters(threatAdapters);
        setLocalizerProfiles(threatProfiles);
        setLogRefinerPolicy(refinerPolicy);
        setLogRefinerSchedulePolicy(refinerSchedulePolicy);
        setLogRefinerRuns(refinerRuns);
        setLogRefinerFeedback(refinerFeedbackRows);
        setLogRefinerCallbacks(refinerCallbackRows);
        setLogRefinerMappingPacks(refinerMappingRows);
        setPluginRuns(bluePluginRuns);
        setSoarExecutions(soarRunHistory);
        setSoarConnectorContracts(soarContracts);
        setSoarMarketplaceOverview(marketplaceOverview);
        setSoarMarketplacePacks(marketplacePacks);
        setManagedRuns(responderRunHistory);
        setManagedEvidence(responderEvidence);
        setSoarMarketplaceSummary(
          `packs=${marketplacePacks.count} playbooks=${marketplaceOverview.total_playbooks} active=${marketplaceOverview.active_playbooks} pack_catalog=${marketplaceOverview.marketplace_pack_count}`,
        );
        const latestExecution = soarRunHistory.rows?.[0];
        if (latestExecution) {
          const connectorRows = await fetchSoarConnectorResults(selectedSite.site_id, latestExecution.execution_id, 10);
          setSoarConnectorResults(connectorRows);
          const latestConnectorCallback = connectorRows.rows?.[0];
          if (latestConnectorCallback) {
            setSoarConnectorCallbackSummary(
              `${latestConnectorCallback.connector_source}/${latestConnectorCallback.contract_code} status=${latestConnectorCallback.status} ref=${latestConnectorCallback.external_action_ref || "none"}`,
            );
          } else {
            setSoarConnectorCallbackSummary("No connector callback yet");
          }
        } else {
          setSoarConnectorResults(null);
          setSoarConnectorCallbackSummary("No connector callback yet");
        }
        const p = policy.policy;
        setMinRiskScore(p.min_risk_score);
        setMinRiskTier(p.min_risk_tier);
        setTargetCoveragePct(p.target_detection_coverage_pct);
        setMaxRulesPerRun(p.max_rules_per_run);
        setAutoApplyAutotune(Boolean(p.auto_apply));
        setAutotuneRouteAlert(Boolean(p.route_alert));
        setAutotuneScheduleMinutes(p.schedule_interval_minutes);
        setAutotunePolicySummary(
          `risk>=${p.min_risk_score}/${p.min_risk_tier} target_coverage>=${p.target_detection_coverage_pct}% max_rules=${p.max_rules_per_run} auto_apply=${String(p.auto_apply)}`,
        );
        const latestRun = runs.rows?.[0];
        if (latestRun) {
          setAutotuneRunSummary(
            `${latestRun.status} risk=${latestRun.risk_tier}/${latestRun.risk_score} coverage=${latestRun.coverage_before_pct}%->${latestRun.coverage_after_pct}% recs=${latestRun.recommendation_count}`,
          );
        } else {
          setAutotuneRunSummary("No autotune run yet");
        }

        const localizer = threatPolicy.policy;
        setFocusRegion(localizer.focus_region);
        setSector(localizer.sector);
        setLocalizerCategoriesText(localizer.subscribed_categories.join(", "));
        setLocalizerRecurringDigestEnabled(Boolean(localizer.recurring_digest_enabled));
        setLocalizerScheduleMinutes(localizer.schedule_interval_minutes);
        setLocalizerMinFeedPriority(localizer.min_feed_priority as RiskTier);
        setLocalizerEnabled(Boolean(localizer.enabled));
        setLocalizerPolicySummary(
          `region=${localizer.focus_region} sector=${localizer.sector} categories=${localizer.subscribed_categories.join("/")} min_feed=${localizer.min_feed_priority} digest=${String(localizer.recurring_digest_enabled)} every=${localizer.schedule_interval_minutes}m enabled=${String(localizer.enabled)}`,
        );
        const routing = threatRoutingPolicy.policy;
        setLocalizerStakeholderGroupsText(routing.stakeholder_groups.join(", "));
        setLocalizerGroupChannelMapText(JSON.stringify(routing.group_channel_map, null, 2));
        setLocalizerCategoryGroupMapText(JSON.stringify(routing.category_group_map, null, 2));
        setLocalizerRoutingMinPriority(routing.min_priority_score);
        setLocalizerRoutingMinRiskTier(routing.min_risk_tier as RiskTier);
        setLocalizerAutoPromoteOnGap(Boolean(routing.auto_promote_on_gap));
        setLocalizerAutoApplyAutotune(Boolean(routing.auto_apply_autotune));
        setLocalizerDispatchActionCenter(Boolean(routing.dispatch_via_action_center));
        setLocalizerPlaybookPromotionEnabled(Boolean(routing.playbook_promotion_enabled));
        setLocalizerRoutingSummary(
          `groups=${routing.stakeholder_groups.join("/")} min_priority=${routing.min_priority_score} min_risk=${routing.min_risk_tier} auto_promote=${String(routing.auto_promote_on_gap)} autotune=${String(routing.auto_apply_autotune)} playbook=${String(routing.playbook_promotion_enabled)}`,
        );
        const latestThreatRun = threatRuns.rows?.[0];
        if (latestThreatRun) {
          setLocalizerRunSummary(formatThreatLocalizerRunSummary(latestThreatRun));
        } else {
          setLocalizerRunSummary("No threat localizer run yet");
        }
        const latestPromotion = threatPromotionRuns.rows?.[0];
        if (latestPromotion) {
          setLocalizerPromotionSummary(
            `${latestPromotion.status} categories=${latestPromotion.promoted_categories.join(", ") || "none"} groups=${latestPromotion.routed_groups.join(", ") || "none"} playbooks=${latestPromotion.playbook_codes.join(", ") || "none"}`,
          );
        } else {
          setLocalizerPromotionSummary("No gap promotion run yet");
        }
        setLocalizerFeedSummary(
          `feeds=${threatFeeds.count} adapters=${threatAdapters.count} profiles=${threatProfiles.count} top_region=${localizer.focus_region} top_sector=${localizer.sector}`,
        );

        const refiner = refinerPolicy.policy;
        setLogRefinerConnectorSource(refiner.connector_source);
        setLogRefinerExecutionMode(refiner.execution_mode);
        setLogRefinerLookbackLimit(refiner.lookback_limit);
        setLogRefinerMinKeepSeverity(refiner.min_keep_severity);
        setLogRefinerDropRecommendationsText(refiner.drop_recommendation_codes.join(", "));
        setLogRefinerTargetNoiseReductionPct(refiner.target_noise_reduction_pct);
        setLogRefinerAverageEventSizeKb(refiner.average_event_size_kb);
        setLogRefinerEnabled(Boolean(refiner.enabled));
        setLogRefinerCallbackSourceSystem(refiner.connector_source);
        setLogRefinerPolicySummary(
          `connector=${refiner.connector_source} mode=${refiner.execution_mode} keep>=${refiner.min_keep_severity} target_noise=${refiner.target_noise_reduction_pct}% avg_kb=${refiner.average_event_size_kb} enabled=${String(refiner.enabled)}`,
        );
        const refinerSchedule = refinerSchedulePolicy.policy;
        setLogRefinerScheduleMinutes(refinerSchedule.schedule_interval_minutes);
        setLogRefinerScheduleDryRun(Boolean(refinerSchedule.dry_run_default));
        setLogRefinerCallbackEnabled(Boolean(refinerSchedule.callback_ingest_enabled));
        setLogRefinerScheduleEnabled(Boolean(refinerSchedule.enabled));
        setLogRefinerScheduleSummary(
          `every=${refinerSchedule.schedule_interval_minutes}m dry_run_default=${String(refinerSchedule.dry_run_default)} callback_ingest=${String(refinerSchedule.callback_ingest_enabled)} enabled=${String(refinerSchedule.enabled)}`,
        );
        const latestRefinerRun = refinerRuns.rows?.[0];
        if (latestRefinerRun) {
          setLogRefinerRunSummary(
            `${latestRefinerRun.status} total=${latestRefinerRun.total_events} kept=${latestRefinerRun.kept_events} dropped=${latestRefinerRun.dropped_events} noise=${latestRefinerRun.noise_reduction_pct}% saved=${latestRefinerRun.estimated_storage_saved_kb}KB adjusted=${latestRefinerRun.feedback_adjusted_events}`,
          );
        } else {
          setLogRefinerRunSummary("No log refiner run yet");
        }
        const latestRefinerFeedback = refinerFeedbackRows.rows?.[0];
        if (latestRefinerFeedback) {
          setLogRefinerFeedbackSummary(
            `${latestRefinerFeedback.feedback_type} ${latestRefinerFeedback.event_type || "generic"} -> ${latestRefinerFeedback.recommendation_code || "n/a"} by ${latestRefinerFeedback.actor}`,
          );
        } else {
          setLogRefinerFeedbackSummary("No operator feedback yet");
        }
        const latestRefinerCallback = refinerCallbackRows.rows?.[0];
        if (latestRefinerCallback) {
          setLogRefinerCallbackSummary(
            `${latestRefinerCallback.status} ${latestRefinerCallback.source_system || latestRefinerCallback.connector_source} total=${latestRefinerCallback.total_events} kept=${latestRefinerCallback.kept_events} dropped=${latestRefinerCallback.dropped_events} noise=${latestRefinerCallback.noise_reduction_pct}% matched_run=${latestRefinerCallback.run_id || "none"}`,
          );
          setLogRefinerCallbackExternalRef(latestRefinerCallback.external_run_ref || "siem-batch-001");
          setLogRefinerCallbackEventId(latestRefinerCallback.webhook_event_id || "");
          setLogRefinerCallbackTotal(latestRefinerCallback.total_events || 0);
          setLogRefinerCallbackKept(latestRefinerCallback.kept_events || 0);
          setLogRefinerCallbackDropped(latestRefinerCallback.dropped_events || 0);
          setLogRefinerCallbackSavedKb(latestRefinerCallback.estimated_storage_saved_kb || 0);
        } else {
          setLogRefinerCallbackSummary("No source SIEM callback yet");
        }

        const responder = responderPolicy.policy;
        setResponderMinSeverity(responder.min_severity);
        setResponderAction(responder.action_mode);
        setResponderPlaybookCode(responder.playbook_code);
        setResponderDispatchPlaybook(Boolean(responder.dispatch_playbook));
        setResponderRequireApproval(Boolean(responder.require_approval));
        setResponderDryRun(Boolean(responder.dry_run_default));
        setResponderEnabled(Boolean(responder.enabled));
        setManagedPolicySummary(
          `severity>=${responder.min_severity} action=${responder.action_mode} playbook=${responder.playbook_code || "none"} dispatch=${String(responder.dispatch_playbook)} enabled=${String(responder.enabled)}`,
        );
        const latestManagedRun = responderRunHistory.rows?.[0];
        if (latestManagedRun) {
          setManagedRunSummary(
            `${latestManagedRun.status} action=${latestManagedRun.selected_action} severity=${latestManagedRun.selected_severity} connector=${latestManagedRun.connector_source || "generic"} confirmation=${latestManagedRun.connector_confirmation_status || "n/a"} playbook=${latestManagedRun.playbook_code || "none"} applied=${String(latestManagedRun.action_applied)}`,
          );
        } else {
          setManagedRunSummary("No managed responder run yet");
        }
        setManagedEvidenceSummary(
          `evidence_chain valid=${String(responderEvidence.valid)} rows=${responderEvidence.count} latest_signature=${responderEvidence.rows?.[0]?.signature || "none"}`,
        );
      } else {
        setAutotunePolicySummary("No permission to view autotune policy");
        setAutotuneRunSummary("No permission to view autotune runs");
        setManagedPolicySummary("No permission to view managed responder policy");
        setManagedRunSummary("No permission to view managed responder runs");
        setManagedEvidenceSummary("No permission to verify responder evidence");
        setSoarMarketplaceSummary("No permission to view SOAR marketplace");
        setSoarConnectorCallbackSummary("No permission to view connector callbacks");
        setLocalizerPolicySummary("No permission to view threat localizer policy");
        setLocalizerRunSummary("No permission to view threat localizer runs");
        setLocalizerFeedSummary("No permission to view external threat feed");
        setLocalizerSchedulerSummary("No permission to run threat localizer scheduler");
        setLocalizerRoutingSummary("No permission to view routing pack policy");
        setLocalizerPromotionSummary("No permission to view promotion runs");
        setLogRefinerPolicySummary("No permission to view log refiner policy");
        setLogRefinerScheduleSummary("No permission to view log refiner scheduler");
        setLogRefinerRunSummary("No permission to view log refiner runs");
        setLogRefinerFeedbackSummary("No permission to view log refiner feedback");
        setLogRefinerCallbackSummary("No permission to view log refiner callbacks");
        setAutotuneRuns(null);
        setLocalizerRuns(null);
        setLocalizerPolicy(null);
        setLocalizerRoutingPolicy(null);
        setLocalizerPromotionRuns(null);
        setLocalizerFeeds(null);
        setLocalizerProfiles(null);
        setLocalizerFeedAdapters(null);
        setLogRefinerPolicy(null);
        setLogRefinerSchedulePolicy(null);
        setLogRefinerRuns(null);
        setLogRefinerFeedback(null);
        setLogRefinerCallbacks(null);
        setLogRefinerMappingPacks(null);
        setPluginRuns(null);
        setSoarExecutions(null);
        setSoarConnectorContracts(null);
        setSoarConnectorResults(null);
        setSoarMarketplaceOverview(null);
        setSoarMarketplacePacks(null);
        setManagedRuns(null);
        setManagedEvidence(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "blue_events_load_failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    if (!selectedSite) return;
    const timer = setInterval(() => void load(), 10000);
    return () => clearInterval(timer);
  }, [selectedSite?.site_id, canView]);

  useEffect(() => {
    if (!canView) return;
    let active = true;
    fetchBlueThreatFeedAdapterTemplates(localizerAdapterSource)
      .then((response) => {
        if (active) {
          setLocalizerFeedAdapters(response);
          const adapter = (response.rows || []).find((row) => row.source === localizerAdapterSource) || response.rows?.[0];
          if (adapter?.sample_payload) {
            setLocalizerFeedPayload((current) => {
              if (current.trim() && current.trim() !== THREAT_FEED_SAMPLE.trim()) {
                return current;
              }
              return JSON.stringify(adapter.sample_payload, null, 2);
            });
          }
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : "threat_feed_adapter_load_failed");
        }
      });
    return () => {
      active = false;
    };
  }, [canView, localizerAdapterSource]);

  useEffect(() => {
    const contract = (soarConnectorContracts?.rows || []).find((row) => row.contract_code === soarContractCode) || soarConnectorContracts?.rows?.[0];
    if (!contract) return;
    setSoarContractCode(contract.contract_code);
    setSoarConnectorPayloadText(JSON.stringify(contract.sample_payload || {}, null, 2));
  }, [soarConnectorContracts, soarContractCode]);

  useEffect(() => {
    if (!canView) return;
    let active = true;
    fetchSoarConnectorResultContracts({ connector_source: soarContractSource })
      .then((response) => {
        if (active) {
          setSoarConnectorContracts(response);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : "soar_contracts_load_failed");
        }
      });
    return () => {
      active = false;
    };
  }, [canView, soarContractSource]);

  const ingestSampleLog = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await ingestSiteBlueEvent(selectedSite.site_id, {
        event_type: "waf_http",
        source_ip: "203.0.113.20",
        path: "/admin/login",
        method: "POST",
        status_code: 401,
        message: "possible brute force attempt",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "blue_ingest_failed");
    } finally {
      setBusy(false);
    }
  };

  const applyAction = async (eventId: string, action: ActionType) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await applySiteBlueRecommendation(selectedSite.site_id, eventId, action);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "blue_apply_failed");
    } finally {
      setBusy(false);
    }
  };

  const runDetectionCopilot = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const tune = await runSiteDetectionCopilotTune(selectedSite.site_id, {
        rule_count: 3,
        auto_apply: false,
        dry_run: true,
      });
      setLastTune(tune);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "detection_copilot_failed");
    } finally {
      setBusy(false);
    }
  };

  const saveAutotunePolicy = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await upsertSiteDetectionAutotunePolicy(selectedSite.site_id, {
        min_risk_score: minRiskScore,
        min_risk_tier: minRiskTier,
        target_detection_coverage_pct: targetCoveragePct,
        max_rules_per_run: maxRulesPerRun,
        auto_apply: autoApplyAutotune,
        route_alert: autotuneRouteAlert,
        schedule_interval_minutes: autotuneScheduleMinutes,
        enabled: true,
        owner: "security",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "autotune_policy_save_failed");
    } finally {
      setBusy(false);
    }
  };

  const runAutotune = async (dryRun: boolean, force: boolean) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const result = await runSiteDetectionAutotune(selectedSite.site_id, {
        dry_run: dryRun,
        force,
        actor: "dashboard_operator",
      });
      setAutotuneRunSummary(
        `${result.status} risk=${result.risk.risk_tier}/${result.risk.risk_score} should_tune=${String(result.execution.should_tune)} recs=${result.execution.recommendation_count} applied=${result.execution.applied_count}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "autotune_run_failed");
    } finally {
      setBusy(false);
    }
  };

  const runAutotuneScheduler = async () => {
    setBusy(true);
    setError("");
    try {
      const result = await runDetectionAutotuneScheduler({
        limit: 200,
        dry_run_override: true,
        actor: "dashboard_scheduler",
      });
      setAutotuneRunSummary(
        `scheduler policies=${result.scheduled_policy_count} executed=${result.executed_count} skipped=${result.skipped_count}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "autotune_scheduler_failed");
    } finally {
      setBusy(false);
    }
  };

  const saveManagedResponderPolicy = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await upsertSiteBlueManagedResponderPolicy(selectedSite.site_id, {
        min_severity: responderMinSeverity,
        action_mode: responderAction,
        dispatch_playbook: responderDispatchPlaybook,
        playbook_code: responderPlaybookCode,
        require_approval: responderRequireApproval,
        dry_run_default: responderDryRun,
        enabled: responderEnabled,
        owner: "security",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "managed_responder_policy_save_failed");
    } finally {
      setBusy(false);
    }
  };

  const saveLogRefinerPolicy = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await upsertSiteBlueLogRefinerPolicy(selectedSite.site_id, {
        connector_source: logRefinerConnectorSource,
        execution_mode: logRefinerExecutionMode,
        lookback_limit: logRefinerLookbackLimit,
        min_keep_severity: logRefinerMinKeepSeverity,
        drop_recommendation_codes: parseCategoryInput(logRefinerDropRecommendationsText),
        target_noise_reduction_pct: logRefinerTargetNoiseReductionPct,
        average_event_size_kb: logRefinerAverageEventSizeKb,
        enabled: logRefinerEnabled,
        owner: "security",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "log_refiner_policy_save_failed");
    } finally {
      setBusy(false);
    }
  };

  const saveLogRefinerSchedulePolicy = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await upsertSiteBlueLogRefinerSchedulePolicy(selectedSite.site_id, {
        connector_source: logRefinerConnectorSource,
        schedule_interval_minutes: logRefinerScheduleMinutes,
        dry_run_default: logRefinerScheduleDryRun,
        callback_ingest_enabled: logRefinerCallbackEnabled,
        enabled: logRefinerScheduleEnabled,
        owner: "security",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "log_refiner_schedule_save_failed");
    } finally {
      setBusy(false);
    }
  };

  const runLogRefiner = async (dryRun: boolean) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const result = await runSiteBlueLogRefiner(selectedSite.site_id, {
        connector_source: logRefinerConnectorSource,
        dry_run: dryRun,
        actor: "dashboard_operator",
      });
      setLogRefinerRunSummary(
        `${result.status} total=${result.run.total_events} kept=${result.run.kept_events} dropped=${result.run.dropped_events} noise=${result.run.noise_reduction_pct}% saved=${result.run.estimated_storage_saved_kb}KB`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "log_refiner_run_failed");
    } finally {
      setBusy(false);
    }
  };

  const runLogRefinerSchedulerNow = async (dryRunOverride: boolean) => {
    setBusy(true);
    setError("");
    try {
      const result = await runBlueLogRefinerScheduler({
        limit: 200,
        dry_run_override: dryRunOverride,
        actor: "dashboard_scheduler",
      });
      setLogRefinerScheduleSummary(
        `scheduler policies=${result.scheduled_policy_count} executed=${result.executed_count} skipped=${result.skipped_count} dry_run_override=${String(dryRunOverride)}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "log_refiner_scheduler_failed");
    } finally {
      setBusy(false);
    }
  };

  const submitLogRefinerFeedback = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const result = await submitSiteBlueLogRefinerFeedback(selectedSite.site_id, {
        connector_source: logRefinerConnectorSource,
        feedback_type: logRefinerFeedbackType,
        event_type: logRefinerFeedbackEventType,
        recommendation_code: logRefinerFeedbackRecommendation,
        note: logRefinerFeedbackNote,
        actor: "blue_operator",
        run_id: logRefinerRuns?.rows?.[0]?.run_id || null,
      });
      setLogRefinerFeedbackSummary(
        `${result.feedback.feedback_type} ${result.feedback.event_type || "generic"} -> ${result.feedback.recommendation_code || "n/a"} by ${result.feedback.actor}`,
      );
      setLogRefinerFeedbackNote("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "log_refiner_feedback_failed");
    } finally {
      setBusy(false);
    }
  };

  const ingestLogRefinerCallback = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const result = await ingestSiteBlueLogRefinerCallback(selectedSite.site_id, {
        connector_source: logRefinerConnectorSource,
        callback_type: logRefinerCallbackType,
        source_system: logRefinerCallbackSourceSystem,
        external_run_ref: logRefinerCallbackExternalRef,
        webhook_event_id: logRefinerCallbackEventId,
        run_id: logRefinerRuns?.rows?.[0]?.run_id || null,
        total_events: logRefinerCallbackTotal,
        kept_events: logRefinerCallbackKept,
        dropped_events: logRefinerCallbackDropped,
        estimated_storage_saved_kb: logRefinerCallbackSavedKb,
        payload: {
          note: "source_siem_callback",
          schedule_policy_id: logRefinerSchedulePolicy?.policy.schedule_policy_id || "",
        },
        actor: "dashboard_siem_callback",
      });
      setLogRefinerCallbackSummary(
        `${result.status} ${result.callback.source_system || result.callback.connector_source} total=${result.callback.total_events} kept=${result.callback.kept_events} dropped=${result.callback.dropped_events} noise=${result.callback.noise_reduction_pct}% matched_run=${result.callback.run_id || "none"}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "log_refiner_callback_failed");
    } finally {
      setBusy(false);
    }
  };

  const runThreatLocalizer = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const result = await runSiteBlueThreatLocalizer(selectedSite.site_id, {
        focus_region: focusRegion,
        sector,
        dry_run: true,
        actor: "dashboard_operator",
      });
      setLocalizerRunSummary(formatThreatLocalizerRunSummary(result.run));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_localizer_failed");
    } finally {
      setBusy(false);
    }
  };

  const saveThreatLocalizerPolicy = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await upsertSiteBlueThreatLocalizerPolicy(selectedSite.site_id, {
        focus_region: focusRegion,
        sector,
        subscribed_categories: parseCategoryInput(localizerCategoriesText),
        recurring_digest_enabled: localizerRecurringDigestEnabled,
        schedule_interval_minutes: localizerScheduleMinutes,
        min_feed_priority: localizerMinFeedPriority,
        enabled: localizerEnabled,
        owner: "security",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_localizer_policy_save_failed");
    } finally {
      setBusy(false);
    }
  };

  const saveThreatLocalizerRoutingPolicy = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await upsertSiteBlueThreatLocalizerRoutingPolicy(selectedSite.site_id, {
        stakeholder_groups: parseCategoryInput(localizerStakeholderGroupsText),
        group_channel_map: parseJsonMap(localizerGroupChannelMapText),
        category_group_map: parseJsonMap(localizerCategoryGroupMapText),
        min_priority_score: localizerRoutingMinPriority,
        min_risk_tier: localizerRoutingMinRiskTier,
        auto_promote_on_gap: localizerAutoPromoteOnGap,
        auto_apply_autotune: localizerAutoApplyAutotune,
        dispatch_via_action_center: localizerDispatchActionCenter,
        playbook_promotion_enabled: localizerPlaybookPromotionEnabled,
        owner: "security",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_localizer_routing_policy_save_failed");
    } finally {
      setBusy(false);
    }
  };

  const promoteThreatLocalizerGap = async (autoApplyOverride: boolean | null, playbookOverride: boolean | null) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const result = await promoteSiteBlueThreatLocalizerGap(selectedSite.site_id, {
        localizer_run_id: localizerRuns?.rows?.[0]?.run_id || null,
        auto_apply_override: autoApplyOverride,
        playbook_promotion_override: playbookOverride,
        actor: "dashboard_localizer_promotion",
      });
      setLocalizerPromotionSummary(
        `${result.status} categories=${result.promotion.promoted_categories.join(", ") || "none"} groups=${result.promotion.routed_groups.join(", ") || "none"} playbooks=${result.promotion.playbook_codes.join(", ") || "none"}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_localizer_promote_gap_failed");
    } finally {
      setBusy(false);
    }
  };

  const importThreatFeed = async () => {
    setBusy(true);
    setError("");
    try {
      const items = JSON.parse(localizerFeedPayload);
      if (!Array.isArray(items)) {
        throw new Error("threat_feed_items_must_be_array");
      }
      const result = await importBlueThreatFeedItems({
        source_name: localizerFeedSource,
        items,
        actor: "dashboard_threat_feed_editor",
      });
      setLocalizerFeedSummary(
        `source=${result.source_name} imported=${result.imported_count} updated=${result.updated_count} received=${result.received_count}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_feed_import_failed");
    } finally {
      setBusy(false);
    }
  };

  const importThreatFeedWithAdapter = async () => {
    setBusy(true);
    setError("");
    try {
      const payload = JSON.parse(localizerFeedPayload);
      const result = await importBlueThreatFeedAdapter({
        source: localizerAdapterSource,
        payload,
        actor: "dashboard_threat_feed_adapter",
      });
      setLocalizerFeedSummary(
        `adapter=${result.adapter_source} normalized=${result.normalized_count} imported=${result.imported_count} updated=${result.updated_count}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_feed_adapter_import_failed");
    } finally {
      setBusy(false);
    }
  };

  const runThreatLocalizerScheduler = async (dryRun: boolean) => {
    setBusy(true);
    setError("");
    try {
      const result = await runBlueThreatLocalizerScheduler({
        limit: 200,
        dry_run_override: dryRun,
        actor: "dashboard_scheduler",
      });
      setLocalizerSchedulerSummary(
        `scheduler policies=${result.scheduled_policy_count} executed=${result.executed_count} skipped=${result.skipped_count} dry_run_override=${String(dryRun)}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "threat_localizer_scheduler_failed");
    } finally {
      setBusy(false);
    }
  };

  const runAutoPlaybookExecutor = async () => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await runSiteCoworkerPlugin(selectedSite.site_id, "blue_auto_playbook_executor", {
        dry_run: true,
        force: true,
        actor: "managed_ai_responder",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "auto_playbook_executor_failed");
    } finally {
      setBusy(false);
    }
  };

  const installMarketplacePack = async (packCode: string, scopeOverride: "" | "community" | "partner" | "private" = "") => {
    setBusy(true);
    setError("");
    try {
      const result = await installSoarMarketplacePack(packCode, {
        actor: "blue_service_marketplace",
        scope_override: scopeOverride,
      });
      setSoarMarketplaceSummary(
        `installed pack=${String((result.pack as { pack_code?: string }).pack_code || packCode)} playbooks=${result.installed_count}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "soar_marketplace_install_failed");
    } finally {
      setBusy(false);
    }
  };

  const verifyExecution = async (executionId: string) => {
    setBusy(true);
    setError("");
    try {
      const result = await verifySoarExecution(executionId, { actor: "blue_service_verifier" });
      setSoarVerificationByExecution((prev) => ({ ...prev, [executionId]: result }));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "soar_execution_verify_failed");
    } finally {
      setBusy(false);
    }
  };

  const ingestSoarConnectorCallback = async () => {
    if (!selectedSite) return;
    const executionId = soarExecutions?.rows?.[0]?.execution_id;
    if (!executionId) return;
    setBusy(true);
    setError("");
    try {
      const payload = JSON.parse(soarConnectorPayloadText) as Record<string, unknown>;
      const result: SoarConnectorResultResponse = await ingestSoarConnectorResult(selectedSite.site_id, executionId, {
        connector_source: soarContractSource,
        contract_code: soarContractCode,
        external_action_ref: soarExternalActionRef,
        webhook_event_id: soarWebhookEventId,
        status: soarConnectorResultStatus,
        payload,
        actor: "blue_service_vendor_callback",
      });
      setSoarConnectorCallbackSummary(
        `${result.connector_result.connector_source}/${result.connector_result.contract_code} status=${result.connector_result.status} ref=${result.connector_result.external_action_ref || "none"}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "soar_connector_callback_failed");
    } finally {
      setBusy(false);
    }
  };

  const runManagedResponder = async (dryRun: boolean) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const result = await runSiteBlueManagedResponder(selectedSite.site_id, {
        dry_run: dryRun,
        force: false,
        actor: "dashboard_operator",
      });
      setManagedRunSummary(describeManagedResponderResult(result));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "managed_responder_failed");
    } finally {
      setBusy(false);
    }
  };

  const runManagedResponderScheduler = async () => {
    setBusy(true);
    setError("");
    try {
      const result = await runBlueManagedResponderScheduler({
        limit: 200,
        dry_run_override: responderDryRun,
        actor: "dashboard_scheduler",
      });
      setManagedSchedulerSummary(
        `scheduler policies=${result.scheduled_policy_count} executed=${result.executed_count} skipped=${result.skipped_count} dry_run_override=${String(responderDryRun)}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "managed_responder_scheduler_failed");
    } finally {
      setBusy(false);
    }
  };

  const reviewManagedResponder = async (runId: string, approve: boolean) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const result = await reviewSiteBlueManagedResponderRun(selectedSite.site_id, runId, {
        approve,
        approver: "security_lead",
        note: approve ? "approved_from_blue_service" : "rejected_from_blue_service",
      });
      setManagedRunSummary(describeManagedResponderResult(result));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "managed_responder_review_failed");
    } finally {
      setBusy(false);
    }
  };

  const rollbackManagedResponder = async (runId: string) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      const result = await rollbackSiteBlueManagedResponderRun(selectedSite.site_id, runId, {
        actor: "security_operator",
        note: "rollback_from_blue_service",
      });
      setManagedRunSummary(describeManagedResponderResult(result));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "managed_responder_rollback_failed");
    } finally {
      setBusy(false);
    }
  };

  const applyRule = async (ruleId: string) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await applySiteDetectionRule(selectedSite.site_id, ruleId, true);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "detection_rule_apply_failed");
    } finally {
      setBusy(false);
    }
  };

  const latestAutoPlaybook = pluginRuns?.rows?.find((row) => row.plugin_code === "blue_auto_playbook_executor") || null;
  const latestRiskEvent =
    history?.rows?.find((event) => event.ai_severity === "high" || event.ai_severity === "medium") || history?.rows?.[0] || null;
  const selectedSoarContract =
    (soarConnectorContracts?.rows || []).find((row) => row.contract_code === soarContractCode) || soarConnectorContracts?.rows?.[0] || null;

  return (
    <section className="card p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Blue Team Service</h2>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-md border border-slate-600 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-400"
        >
          Refresh
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-400">AI rates severity and suggests response actions per event log.</p>
      <p className="mt-1 text-xs text-slate-500">
        RBAC: viewer={String(canView)} policy_editor={String(canEditPolicy)} approver={String(canApprove)}
      </p>

      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {BLUE_SERVICE_MENUS.map((item) => (
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

      <div className="mt-3">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={!selectedSite || busy}
            onClick={() => void ingestSampleLog()}
            className="rounded-md border border-accent/60 bg-accent/15 px-3 py-1.5 text-xs text-accent hover:bg-accent/25 disabled:opacity-60"
          >
            Ingest Sample Event Log
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy}
            onClick={() => void runDetectionCopilot()}
            className="rounded-md border border-warning/60 bg-warning/10 px-3 py-1.5 text-xs text-warning hover:bg-warning/20 disabled:opacity-60"
          >
            Run Detection Copilot
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy || !canApprove}
            onClick={() => void runThreatLocalizer()}
            className="rounded-md border border-accent/60 bg-accent/15 px-3 py-1.5 text-xs text-accent hover:bg-accent/25 disabled:opacity-60"
          >
            Run Threat Intelligence Localizer
          </button>
        </div>
      </div>

      {loading ? <p className="mt-3 text-sm text-slate-400">Monitoring logs...</p> : null}
      {error ? <p className="mt-3 text-sm text-danger">{error}</p> : null}

      <div className="mt-3 max-h-80 overflow-auto rounded-md border border-slate-800">
        <table className="w-full table-fixed text-left text-xs">
          <thead className="bg-panelAlt/50 text-slate-300">
            <tr>
              <th className="px-2 py-2">Time</th>
              <th className="px-2 py-2">Event</th>
              <th className="px-2 py-2">Severity</th>
              <th className="px-2 py-2">AI Recommendation</th>
              <th className="px-2 py-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {(history?.rows || []).map((event) => (
              <tr key={event.event_id} className="border-t border-slate-800/80">
                <td className="px-2 py-2 text-slate-400 wrap-anywhere">{event.created_at}</td>
                <td className="px-2 py-2 text-slate-200 wrap-anywhere">{event.event_type}</td>
                <td
                  className={
                    "px-2 py-2 " +
                    (event.ai_severity === "high"
                      ? "text-danger"
                      : event.ai_severity === "medium"
                        ? "text-warning"
                        : "text-accent")
                  }
                >
                  {event.ai_severity}
                </td>
                <td className="px-2 py-2 text-slate-300 wrap-anywhere">{event.ai_recommendation}</td>
                <td className="px-2 py-2">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void applyAction(event.event_id, (event.ai_recommendation as ActionType) || "notify_team")}
                    className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
                  >
                    Apply
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(history?.rows?.length || 0) === 0 ? <p className="p-3 text-xs text-slate-500">No blue events yet.</p> : null}
      </div>

      {lastTune ? (
        <div className="mt-3 rounded border border-slate-800 bg-panelAlt/30 p-2 text-xs">
          <p className="text-slate-200 wrap-anywhere">Detection coverage delta: {lastTune.expected_detection_coverage_delta}</p>
          <p className="mt-1 text-slate-400 wrap-anywhere">before: {JSON.stringify(lastTune.before_metrics)}</p>
          <p className="mt-1 text-slate-400 wrap-anywhere">after: {JSON.stringify(lastTune.after_metrics)}</p>
        </div>
      ) : null}

      <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
        <div className="flex items-center justify-between gap-2">
          <p className="text-slate-300">AI Log Refiner (The Noise Killer)</p>
          <span className="rounded-full border border-accent/50 bg-accent/10 px-2 py-0.5 text-[10px] uppercase text-accent">
            live
          </span>
        </div>
        <p className="mt-1 text-slate-500 wrap-anywhere">
          วัด pre-ingest/post-ingest noise reduction, ประมาณการ storage savings, และรับ feedback จาก operator เพื่อกด false positive ต่อ source SIEM
        </p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{logRefinerPolicySummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{logRefinerScheduleSummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{logRefinerRunSummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{logRefinerFeedbackSummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{logRefinerCallbackSummary}</p>

        <div className="mt-2 grid gap-2 md:grid-cols-3">
          <label className="text-[11px] text-slate-400">
            Connector Source
            <select
              value={logRefinerConnectorSource}
              onChange={(event) => setLogRefinerConnectorSource(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              <option value="splunk">splunk</option>
              <option value="elk">elk</option>
              <option value="cloudflare">cloudflare</option>
              <option value="crowdstrike">crowdstrike</option>
              <option value="generic">generic</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400">
            Execution Mode
            <select
              value={logRefinerExecutionMode}
              onChange={(event) => setLogRefinerExecutionMode(event.target.value as LogRefinerMode)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              <option value="pre_ingest">pre_ingest</option>
              <option value="post_ingest">post_ingest</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400">
            Keep Severity
            <select
              value={logRefinerMinKeepSeverity}
              onChange={(event) => setLogRefinerMinKeepSeverity(event.target.value as RiskTier)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
              <option value="critical">critical</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400">
            Lookback Limit
            <input
              type="number"
              value={logRefinerLookbackLimit}
              onChange={(event) => setLogRefinerLookbackLimit(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Target Noise Reduction %
            <input
              type="number"
              value={logRefinerTargetNoiseReductionPct}
              onChange={(event) => setLogRefinerTargetNoiseReductionPct(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Avg Event Size KB
            <input
              type="number"
              value={logRefinerAverageEventSizeKb}
              onChange={(event) => setLogRefinerAverageEventSizeKb(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400 md:col-span-3">
            Drop Recommendation Codes
            <input
              type="text"
              value={logRefinerDropRecommendationsText}
              onChange={(event) => setLogRefinerDropRecommendationsText(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
        </div>

        <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-300">
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={logRefinerEnabled} onChange={(event) => setLogRefinerEnabled(event.target.checked)} />
            enabled
          </label>
        </div>

        <div className="mt-2 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!selectedSite || busy || !canEditPolicy}
            onClick={() => void saveLogRefinerPolicy()}
            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
          >
            Save Log Refiner Policy
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy || !canApprove}
            onClick={() => void runLogRefiner(true)}
            className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
          >
            Run Refiner Dry Run
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy || !canApprove}
            onClick={() => void runLogRefiner(false)}
            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
          >
            Run Refiner Apply
          </button>
        </div>

        <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
          <p className="text-slate-300">Continuous Scheduler</p>
          <div className="mt-2 grid gap-2 md:grid-cols-3">
            <label className="text-[11px] text-slate-400">
              Schedule Interval (minutes)
              <input
                type="number"
                value={logRefinerScheduleMinutes}
                onChange={(event) => setLogRefinerScheduleMinutes(Number(event.target.value))}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="flex items-center gap-2 text-[11px] text-slate-300 md:mt-6">
              <input type="checkbox" checked={logRefinerScheduleDryRun} onChange={(event) => setLogRefinerScheduleDryRun(event.target.checked)} />
              scheduler dry-run default
            </label>
            <label className="flex items-center gap-2 text-[11px] text-slate-300 md:mt-6">
              <input type="checkbox" checked={logRefinerCallbackEnabled} onChange={(event) => setLogRefinerCallbackEnabled(event.target.checked)} />
              source callback ingestion enabled
            </label>
            <label className="flex items-center gap-2 text-[11px] text-slate-300 md:mt-6">
              <input type="checkbox" checked={logRefinerScheduleEnabled} onChange={(event) => setLogRefinerScheduleEnabled(event.target.checked)} />
              scheduler enabled
            </label>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!selectedSite || busy || !canEditPolicy}
              onClick={() => void saveLogRefinerSchedulePolicy()}
              className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
            >
              Save Scheduler Policy
            </button>
            <button
              type="button"
              disabled={busy || !canApprove}
              onClick={() => void runLogRefinerSchedulerNow(true)}
              className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
            >
              Run Scheduler Dry Run
            </button>
            <button
              type="button"
              disabled={busy || !canApprove}
              onClick={() => void runLogRefinerSchedulerNow(false)}
              className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
            >
              Run Scheduler Apply
            </button>
          </div>
        </div>

        <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
          <p className="text-slate-300">Vendor Mapping Packs</p>
          {(logRefinerMappingPacks?.rows || []).length === 0 ? <p className="mt-1 text-slate-500">No mapping pack loaded.</p> : null}
          {(logRefinerMappingPacks?.rows || []).slice(0, 1).map((pack) => (
            <div key={pack.source} className="mt-2">
              <p className="text-slate-200 wrap-anywhere">
                {pack.display_name} mode={pack.execution_mode}
              </p>
              {pack.notes.map((note, index) => (
                <p key={`${pack.source}-note-${index}`} className="mt-1 text-slate-400 wrap-anywhere">
                  {note}
                </p>
              ))}
              <div className="mt-2 max-h-24 overflow-auto rounded border border-slate-800 p-2">
                {pack.field_mapping.map((field, index) => (
                  <p key={`${pack.source}-${index}`} className="text-slate-400 wrap-anywhere">
                    {field.incoming} → {field.mapped_to}
                  </p>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
          <p className="text-slate-300">Operator Feedback Loop</p>
          <div className="mt-2 grid gap-2 md:grid-cols-2">
            <label className="text-[11px] text-slate-400">
              Feedback Type
              <select
                value={logRefinerFeedbackType}
                onChange={(event) => setLogRefinerFeedbackType(event.target.value as LogRefinerFeedbackType)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              >
                <option value="keep_signal">keep_signal</option>
                <option value="drop_noise">drop_noise</option>
                <option value="false_positive">false_positive</option>
                <option value="signal_missed">signal_missed</option>
              </select>
            </label>
            <label className="text-[11px] text-slate-400">
              Event Type
              <input
                type="text"
                value={logRefinerFeedbackEventType}
                onChange={(event) => setLogRefinerFeedbackEventType(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Recommendation Code
              <input
                type="text"
                value={logRefinerFeedbackRecommendation}
                onChange={(event) => setLogRefinerFeedbackRecommendation(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Note
              <input
                type="text"
                value={logRefinerFeedbackNote}
                onChange={(event) => setLogRefinerFeedbackNote(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!selectedSite || busy || !canApprove}
              onClick={() => void submitLogRefinerFeedback()}
              className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
            >
              Submit Feedback
            </button>
          </div>
          <div className="mt-2 max-h-28 overflow-auto rounded border border-slate-800 p-2">
            {(logRefinerFeedback?.rows || []).length === 0 ? <p className="text-slate-500">No feedback rows yet.</p> : null}
            {(logRefinerFeedback?.rows || []).slice(0, 4).map((row) => (
              <p key={row.feedback_id} className="mb-1 text-slate-400 wrap-anywhere">
                {row.feedback_type} {row.event_type || "generic"} {"->"} {row.recommendation_code || "n/a"} by {row.actor}
              </p>
            ))}
          </div>
        </div>

        <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
          <p className="text-slate-300">Direct SIEM Callback</p>
          <p className="mt-1 text-slate-500 wrap-anywhere">
            ingest stream-result callback จาก source SIEM เพื่อเทียบ refined KPI จริงกับ baseline run และปิด loop สำหรับ source-side refinement
          </p>
          <div className="mt-2 grid gap-2 md:grid-cols-3">
            <label className="text-[11px] text-slate-400">
              Callback Type
              <select
                value={logRefinerCallbackType}
                onChange={(event) => setLogRefinerCallbackType(event.target.value as "stream_result" | "storage_report" | "delivery_receipt")}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              >
                <option value="stream_result">stream_result</option>
                <option value="storage_report">storage_report</option>
                <option value="delivery_receipt">delivery_receipt</option>
              </select>
            </label>
            <label className="text-[11px] text-slate-400">
              Source System
              <input
                type="text"
                value={logRefinerCallbackSourceSystem}
                onChange={(event) => setLogRefinerCallbackSourceSystem(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              External Run Ref
              <input
                type="text"
                value={logRefinerCallbackExternalRef}
                onChange={(event) => setLogRefinerCallbackExternalRef(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400 md:col-span-3">
              Webhook Event ID
              <input
                type="text"
                value={logRefinerCallbackEventId}
                onChange={(event) => setLogRefinerCallbackEventId(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Total Events
              <input
                type="number"
                value={logRefinerCallbackTotal}
                onChange={(event) => setLogRefinerCallbackTotal(Number(event.target.value))}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Kept Events
              <input
                type="number"
                value={logRefinerCallbackKept}
                onChange={(event) => setLogRefinerCallbackKept(Number(event.target.value))}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Dropped Events
              <input
                type="number"
                value={logRefinerCallbackDropped}
                onChange={(event) => setLogRefinerCallbackDropped(Number(event.target.value))}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Estimated Saved KB
              <input
                type="number"
                value={logRefinerCallbackSavedKb}
                onChange={(event) => setLogRefinerCallbackSavedKb(Number(event.target.value))}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!selectedSite || busy || !canApprove}
              onClick={() => void ingestLogRefinerCallback()}
              className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
            >
              Ingest SIEM Callback
            </button>
          </div>
          <div className="mt-2 max-h-28 overflow-auto rounded border border-slate-800 p-2">
            {(logRefinerCallbacks?.rows || []).length === 0 ? <p className="text-slate-500">No callback rows yet.</p> : null}
            {(logRefinerCallbacks?.rows || []).slice(0, 4).map((row) => (
              <p key={row.callback_id} className="mb-1 text-slate-400 wrap-anywhere">
                {row.status} {row.source_system || row.connector_source} total={row.total_events} kept={row.kept_events} dropped={row.dropped_events} noise={row.noise_reduction_pct}% run={row.run_id || "none"}
              </p>
            ))}
          </div>
        </div>

        <div className="mt-2 max-h-32 overflow-auto rounded border border-slate-800 p-2">
          <p className="mb-2 text-slate-400">Recent Log Refiner Runs</p>
          {(logRefinerRuns?.rows || []).length === 0 ? <p className="text-slate-500">No log refiner runs yet.</p> : null}
          {(logRefinerRuns?.rows || []).slice(0, 4).map((run) => (
            <div key={run.run_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
              <p className="text-slate-200 wrap-anywhere">
                {run.status} connector={run.connector_source} mode={run.execution_mode}
              </p>
              <p className="mt-1 text-slate-400 wrap-anywhere">
                total={run.total_events} kept={run.kept_events} dropped={run.dropped_events} noise={run.noise_reduction_pct}% saved=
                {run.estimated_storage_saved_kb}KB
              </p>
              <p className="mt-1 text-slate-500 wrap-anywhere">
                feedback_adjusted={run.feedback_adjusted_events} dry_run={String(run.dry_run)} at {run.created_at}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
        <div className="flex items-center justify-between gap-2">
          <p className="text-slate-300">Managed AI Responder</p>
          <span className="rounded-full border border-accent/50 bg-accent/10 px-2 py-0.5 text-[10px] uppercase text-accent">
            live
          </span>
        </div>
        <p className="mt-1 text-slate-500 wrap-anywhere">
          ใช้ policy ที่เก็บใน DB เพื่อคัด event ตาม severity, ตัดสิน action, และ dispatch SOAR playbook อัตโนมัติจากหน้า Blue โดยตรง
        </p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{managedPolicySummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{managedRunSummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{managedSchedulerSummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{managedEvidenceSummary}</p>
        {latestRiskEvent ? (
          <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">
              candidate={latestRiskEvent.event_type} severity={latestRiskEvent.ai_severity} source_ip={latestRiskEvent.source_ip}
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              ai_recommendation={latestRiskEvent.ai_recommendation} status={latestRiskEvent.status}
            </p>
          </div>
        ) : (
          <p className="mt-2 text-slate-500">No event candidate yet. Ingest sample or wait for telemetry.</p>
        )}

        <div className="mt-2 grid gap-2 md:grid-cols-2">
          <label className="text-[11px] text-slate-400">
            Min Severity
            <select
              value={responderMinSeverity}
              onChange={(event) => setResponderMinSeverity(event.target.value as RiskTier)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
              <option value="critical">critical</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400">
            Response Action
            <select
              value={responderAction}
              onChange={(event) => setResponderAction(event.target.value as ActionMode)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              <option value="ai_recommended">ai_recommended</option>
              <option value="block_ip">block_ip</option>
              <option value="notify_team">notify_team</option>
              <option value="limit_user">limit_user</option>
              <option value="ignore">ignore</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400">
            SOAR Playbook Code
            <input
              type="text"
              value={responderPlaybookCode}
              onChange={(event) => setResponderPlaybookCode(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
        </div>

        <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-300">
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={responderEnabled} onChange={(event) => setResponderEnabled(event.target.checked)} />
            enabled
          </label>
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={responderDispatchPlaybook}
              onChange={(event) => setResponderDispatchPlaybook(event.target.checked)}
            />
            dispatch playbook
          </label>
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={responderRequireApproval} onChange={(event) => setResponderRequireApproval(event.target.checked)} />
            require approval
          </label>
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={responderDryRun} onChange={(event) => setResponderDryRun(event.target.checked)} />
            default dry run
          </label>
        </div>

        <div className="mt-2 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!selectedSite || busy || !canEditPolicy}
            onClick={() => void saveManagedResponderPolicy()}
            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
          >
            Save Responder Policy
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy || !canApprove}
            onClick={() => void runAutoPlaybookExecutor()}
            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
          >
            Run Auto-Playbook Executor
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy || !canApprove}
            onClick={() => void runManagedResponder(true)}
            className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
          >
            Run Managed Response Dry Run
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy || !canApprove}
            onClick={() => void runManagedResponder(false)}
            className="rounded border border-danger/60 bg-danger/10 px-2 py-1 text-[11px] text-danger hover:bg-danger/20 disabled:opacity-60"
          >
            Run Managed Response Apply
          </button>
          <button
            type="button"
            disabled={busy || !canApprove}
            onClick={() => void runManagedResponderScheduler()}
            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
          >
            Run Responder Scheduler
          </button>
        </div>

        {latestAutoPlaybook ? (
          <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">
              {String(latestAutoPlaybook.output_summary.headline || "Auto-Playbook payload ready")}
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              {String(latestAutoPlaybook.output_summary.summary_th || "")}
            </p>
            <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded border border-slate-800 bg-panelAlt/40 p-2 text-[11px] text-slate-300">
              {JSON.stringify(latestAutoPlaybook.output_summary.webhook_payload || {}, null, 2)}
            </pre>
          </div>
        ) : (
          <p className="mt-2 text-slate-500">No Auto-Playbook payload generated yet.</p>
        )}

        <div className="mt-2 max-h-32 overflow-auto rounded border border-slate-800 p-2">
          <p className="mb-2 text-slate-400">Recent Managed Responder Runs</p>
          {(managedRuns?.rows || []).length === 0 ? <p className="text-slate-500">No managed responder runs yet.</p> : null}
          {(managedRuns?.rows || []).slice(0, 4).map((run) => (
            <div key={run.run_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
              <p className="text-slate-200 wrap-anywhere">
                {run.status} action={run.selected_action} severity={run.selected_severity}
              </p>
              <p className="mt-1 text-slate-400 wrap-anywhere">
                dry_run={String(run.dry_run)} playbook={run.playbook_code || "none"} at {run.created_at}
              </p>
              <p className="mt-1 text-slate-500 wrap-anywhere">
                approval_required={String(run.approval_required)} rollback_supported={String(run.rollback_supported)} evidence_seq=
                {run.evidence_sequence}
              </p>
              <p className="mt-1 text-slate-500 wrap-anywhere">
                connector={run.connector_source || "generic"} action_status={run.connector_action_status || "n/a"} confirmation=
                {run.connector_confirmation_status || "n/a"} rollback={run.connector_rollback_status || "n/a"}
              </p>
              {typeof run.details?.guardrails === "object" && run.details?.guardrails ? (
                <p className="mt-1 text-slate-500 wrap-anywhere">
                  guardrail={String((run.details.guardrails as Record<string, unknown>).reason || "none")}
                </p>
              ) : null}
              {typeof run.details?.connector_action_result === "object" && run.details?.connector_action_result ? (
                <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap rounded border border-slate-800 bg-panelAlt/40 p-2 text-[11px] text-slate-300">
                  {JSON.stringify(run.details.connector_action_result, null, 2)}
                </pre>
              ) : null}
              <div className="mt-2 flex flex-wrap gap-2">
                {run.status === "pending_approval" ? (
                  <>
                    <button
                      type="button"
                      disabled={busy || !canApprove}
                      onClick={() => void reviewManagedResponder(run.run_id, true)}
                      className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      disabled={busy || !canApprove}
                      onClick={() => void reviewManagedResponder(run.run_id, false)}
                      className="rounded border border-danger/60 bg-danger/10 px-2 py-1 text-[11px] text-danger hover:bg-danger/20 disabled:opacity-60"
                    >
                      Reject
                    </button>
                  </>
                ) : null}
                {run.rollback_supported && ["applied", "partial", "approved_no_action", "pending_approval"].includes(run.status) ? (
                  <button
                    type="button"
                    disabled={busy || !canApprove}
                    onClick={() => void rollbackManagedResponder(run.run_id)}
                    className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                  >
                    Rollback
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-2 max-h-32 overflow-auto rounded border border-slate-800 p-2">
          <p className="mb-2 text-slate-400">Responder Evidence Chain</p>
          {(managedEvidence?.rows || []).length === 0 ? <p className="text-slate-500">No evidence rows yet.</p> : null}
          {(managedEvidence?.rows || []).slice(0, 4).map((row) => (
            <div key={row.run_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
              <p className="text-slate-200 wrap-anywhere">
                seq={row.sequence} valid={String(row.valid)} status={row.status}
              </p>
              <p className="mt-1 text-slate-400 wrap-anywhere">
                signature={row.signature || "none"} at {row.created_at}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-2 max-h-40 overflow-auto rounded border border-slate-800 p-2">
          <p className="mb-2 text-slate-400">SOAR Marketplace Packs</p>
          <p className="mb-2 text-[11px] text-slate-500 wrap-anywhere">{soarMarketplaceSummary}</p>
          {(soarMarketplacePacks?.rows || []).length === 0 ? <p className="text-slate-500">No marketplace packs loaded.</p> : null}
          {(soarMarketplacePacks?.rows || []).slice(0, 3).map((pack) => (
            <div key={pack.pack_code} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-slate-200 wrap-anywhere">{pack.title}</p>
                <button
                  type="button"
                  disabled={busy || !canEditPolicy}
                  onClick={() => void installMarketplacePack(pack.pack_code, pack.scope)}
                  className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                >
                  Install Pack
                </button>
              </div>
              <p className="mt-1 text-slate-400 wrap-anywhere">
                audience={pack.audience} scope={pack.scope} playbooks={pack.playbook_count}
              </p>
              <p className="mt-1 text-slate-500 wrap-anywhere">{pack.description}</p>
            </div>
          ))}
        </div>

        <div className="mt-2 max-h-32 overflow-auto rounded border border-slate-800 p-2">
          <p className="mb-2 text-slate-400">Recent SOAR Executions</p>
          {(soarExecutions?.rows || []).length === 0 ? <p className="text-slate-500">No SOAR executions yet.</p> : null}
          {(soarExecutions?.rows || []).slice(0, 4).map((run) => (
            <div key={run.execution_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
              <p className="text-slate-200 wrap-anywhere">
                {run.status} approval_required={String(run.approval_required)}
              </p>
              <p className="mt-1 text-slate-400 wrap-anywhere">
                requested_by={run.requested_by || "unknown"} updated_at={run.updated_at}
              </p>
              {run.result?.post_action_verification ? (
                <p className="mt-1 text-slate-500 wrap-anywhere">
                  verify={String((run.result.post_action_verification as { status?: string }).status || "unknown")} action_reflected=
                  {String((run.result.post_action_verification as { action_reflected?: boolean }).action_reflected ?? false)}
                </p>
              ) : null}
              {soarVerificationByExecution[run.execution_id] ? (
                <p className="mt-1 text-[11px] text-accent wrap-anywhere">
                  latest_verify={soarVerificationByExecution[run.execution_id].verification.status} by{" "}
                  {soarVerificationByExecution[run.execution_id].verification.verified_by}
                </p>
              ) : null}
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy || !canApprove}
                  onClick={() => void verifyExecution(run.execution_id)}
                  className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
                >
                  Verify Action
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-2 rounded border border-slate-800 p-2">
          <p className="mb-2 text-slate-400">Connector Result Contracts</p>
          <p className="mb-2 text-[11px] text-slate-500 wrap-anywhere">{soarConnectorCallbackSummary}</p>
          <div className="grid gap-2 md:grid-cols-2">
            <label className="text-[11px] text-slate-400">
              Connector Source
              <select
                value={soarContractSource}
                onChange={(event) => setSoarContractSource(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              >
                <option value="cloudflare">cloudflare</option>
                <option value="crowdstrike">crowdstrike</option>
                <option value="splunk">splunk</option>
                <option value="generic">generic</option>
              </select>
            </label>
            <label className="text-[11px] text-slate-400">
              Contract Code
              <select
                value={soarContractCode}
                onChange={(event) => setSoarContractCode(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              >
                {(soarConnectorContracts?.rows || []).map((row) => (
                  <option key={row.contract_code} value={row.contract_code}>
                    {row.contract_code}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-[11px] text-slate-400">
              External Action Ref
              <input
                type="text"
                value={soarExternalActionRef}
                onChange={(event) => setSoarExternalActionRef(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Webhook Event ID
              <input
                type="text"
                value={soarWebhookEventId}
                onChange={(event) => setSoarWebhookEventId(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Callback Status
              <input
                type="text"
                value={soarConnectorResultStatus}
                onChange={(event) => setSoarConnectorResultStatus(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
          </div>
          <label className="mt-2 block text-[11px] text-slate-400">
            Contract Payload JSON
            <textarea
              value={soarConnectorPayloadText}
              onChange={(event) => setSoarConnectorPayloadText(event.target.value)}
              className="mt-1 h-24 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 font-mono text-[11px] text-slate-100"
            />
          </label>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!selectedSite || busy || !canApprove || !(soarExecutions?.rows || []).length}
              onClick={() => void ingestSoarConnectorCallback()}
              className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
            >
              Ingest Vendor Callback
            </button>
          </div>
          {selectedSoarContract ? (
            <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
              <p className="text-slate-200 wrap-anywhere">
                required_fields={(selectedSoarContract.required_fields || []).join(", ") || "none"}
              </p>
              <p className="mt-1 text-slate-500 wrap-anywhere">{selectedSoarContract.description}</p>
            </div>
          ) : null}
          <div className="mt-2 max-h-28 overflow-auto rounded border border-slate-800 bg-panelAlt/20 p-2">
            {(soarConnectorResults?.rows || []).length === 0 ? <p className="text-slate-500">No connector result callbacks yet.</p> : null}
            {(soarConnectorResults?.rows || []).slice(0, 4).map((row) => (
              <div key={row.connector_result_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {row.connector_source}/{row.contract_code} status={row.status}
                </p>
                <p className="mt-1 text-slate-500 wrap-anywhere">
                  ref={row.external_action_ref || "none"} event={row.webhook_event_id || "none"} at {row.created_at}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
        <p className="text-slate-300">Threat Intelligence Localizer</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{localizerPolicySummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{localizerRunSummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{localizerFeedSummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{localizerSchedulerSummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{localizerRoutingSummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{localizerPromotionSummary}</p>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <label className="text-[11px] text-slate-400">
            Focus Region
            <input
              type="text"
              value={focusRegion}
              onChange={(event) => setFocusRegion(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Sector
            <input
              type="text"
              value={sector}
              onChange={(event) => setSector(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400 col-span-2">
            Subscribed Categories
            <input
              type="text"
              value={localizerCategoriesText}
              onChange={(event) => setLocalizerCategoriesText(event.target.value)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Min Feed Priority
            <select
              value={localizerMinFeedPriority}
              onChange={(event) => setLocalizerMinFeedPriority(event.target.value as RiskTier)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
              <option value="critical">critical</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400">
            Digest Interval (minutes)
            <input
              type="number"
              value={localizerScheduleMinutes}
              onChange={(event) => setLocalizerScheduleMinutes(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
        </div>
        <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-300">
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={localizerRecurringDigestEnabled}
              onChange={(event) => setLocalizerRecurringDigestEnabled(event.target.checked)}
            />
            recurring digest
          </label>
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={localizerEnabled} onChange={(event) => setLocalizerEnabled(event.target.checked)} />
            enabled
          </label>
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!selectedSite || busy || !canEditPolicy}
            onClick={() => void saveThreatLocalizerPolicy()}
            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
          >
            Save Localizer Policy
          </button>
          <button
            type="button"
            disabled={busy || !canApprove}
            onClick={() => void runThreatLocalizerScheduler(true)}
            className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
          >
            Run Digest Scheduler Dry Run
          </button>
          <button
            type="button"
            disabled={busy || !canApprove}
            onClick={() => void runThreatLocalizerScheduler(false)}
            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
          >
            Run Digest Scheduler Apply
          </button>
        </div>
        <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
          <p className="text-slate-300">Stakeholder Routing Pack</p>
          <div className="mt-2 grid gap-2 md:grid-cols-2">
            <label className="text-[11px] text-slate-400">
              Stakeholder Groups
              <input
                type="text"
                value={localizerStakeholderGroupsText}
                onChange={(event) => setLocalizerStakeholderGroupsText(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Min Priority Score
              <input
                type="number"
                value={localizerRoutingMinPriority}
                onChange={(event) => setLocalizerRoutingMinPriority(Number(event.target.value))}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400">
              Min Risk Tier
              <select
                value={localizerRoutingMinRiskTier}
                onChange={(event) => setLocalizerRoutingMinRiskTier(event.target.value as RiskTier)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              >
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
                <option value="critical">critical</option>
              </select>
            </label>
            <label className="text-[11px] text-slate-400 col-span-2">
              Group Channel Map JSON
              <textarea
                value={localizerGroupChannelMapText}
                onChange={(event) => setLocalizerGroupChannelMapText(event.target.value)}
                className="mt-1 h-24 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 font-mono text-[11px] text-slate-100"
              />
            </label>
            <label className="text-[11px] text-slate-400 col-span-2">
              Category Group Map JSON
              <textarea
                value={localizerCategoryGroupMapText}
                onChange={(event) => setLocalizerCategoryGroupMapText(event.target.value)}
                className="mt-1 h-24 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 font-mono text-[11px] text-slate-100"
              />
            </label>
          </div>
          <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-300">
            <label className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={localizerAutoPromoteOnGap}
                onChange={(event) => setLocalizerAutoPromoteOnGap(event.target.checked)}
              />
              auto promote on gap
            </label>
            <label className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={localizerAutoApplyAutotune}
                onChange={(event) => setLocalizerAutoApplyAutotune(event.target.checked)}
              />
              auto apply autotune
            </label>
            <label className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={localizerDispatchActionCenter}
                onChange={(event) => setLocalizerDispatchActionCenter(event.target.checked)}
              />
              dispatch via action center
            </label>
            <label className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={localizerPlaybookPromotionEnabled}
                onChange={(event) => setLocalizerPlaybookPromotionEnabled(event.target.checked)}
              />
              promote playbook
            </label>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!selectedSite || busy || !canEditPolicy}
              onClick={() => void saveThreatLocalizerRoutingPolicy()}
              className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
            >
              Save Routing Pack
            </button>
            <button
              type="button"
              disabled={!selectedSite || busy || !canApprove}
              onClick={() => void promoteThreatLocalizerGap(false, true)}
              className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
            >
              Promote Gap Dry Run
            </button>
            <button
              type="button"
              disabled={!selectedSite || busy || !canApprove}
              onClick={() => void promoteThreatLocalizerGap(true, true)}
              className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
            >
              Promote Gap Apply
            </button>
          </div>
        </div>
        {(localizerRuns?.rows || []).length > 0 ? (
          <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">{localizerRuns?.rows[0].summary_th}</p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              priority={localizerRuns?.rows[0].priority_score} risk={localizerRuns?.rows[0].risk_tier}
            </p>
            <p className="mt-1 text-slate-500 wrap-anywhere">
              site_impact={String(localizerRuns?.rows[0].details?.site_impact_score || 0)} feed_matches=
              {String(localizerRuns?.rows[0].details?.feed_match_count || 0)} digest={String(localizerRuns?.rows[0].details?.digest_mode || false)}
            </p>
            <p className="mt-1 text-slate-500 wrap-anywhere">
              detection_gap=
              {String(
                (localizerRuns?.rows[0].details?.detection_gap as { correlation_status?: string } | undefined)?.correlation_status || "unknown",
              )} missing=
              {String(
                (
                  (localizerRuns?.rows[0].details?.detection_gap as { missing_categories?: string[] } | undefined)?.missing_categories || []
                ).join(", ") || "none",
              )}
            </p>
            <div className="mt-2 space-y-1">
              {(((localizerRuns?.rows[0].details?.headline_rows as Array<{ headline_th: string }>) || []).slice(0, 2)).map((item, index) => (
                <p key={`headline-${index}`} className="text-slate-400 wrap-anywhere">
                  {item.headline_th}
                </p>
              ))}
            </div>
            <div className="mt-2 space-y-1">
              {((((localizerRuns?.rows[0].details?.detection_gap as { coverage_rows?: Array<{ category: string; status: string; matched_rule_count: number; connector_sources: string[] }> } | undefined)
                ?.coverage_rows) || []).slice(0, 3)).map((item, index) => (
                <p key={`gap-${index}`} className="text-slate-500 wrap-anywhere">
                  {item.category}: {item.status} rules={item.matched_rule_count} connectors={(item.connector_sources || []).join(", ") || "none"}
                </p>
              ))}
            </div>
            <div className="mt-2 space-y-1">
              {(((localizerRuns?.rows[0].details?.priority_actions_th as Array<string>) || []).slice(0, 3)).map((item, index) => (
                <p key={`action-${index}`} className="text-slate-500 wrap-anywhere">
                  - {item}
                </p>
              ))}
            </div>
          </div>
        ) : (
          <p className="mt-2 text-slate-500">No localized threat brief yet.</p>
        )}
        <div className="mt-2 grid gap-2 md:grid-cols-2">
          <div className="rounded border border-slate-800 bg-panelAlt/30 p-2">
            <div className="flex items-center justify-between gap-2">
              <p className="text-slate-300">External Feed Import</p>
              <span className="text-[11px] text-slate-500">ไทย/SEA + vendor-native adapters</span>
            </div>
            <label className="mt-2 block text-[11px] text-slate-400">
              Source Name
              <input
                type="text"
                value={localizerFeedSource}
                onChange={(event) => setLocalizerFeedSource(event.target.value)}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              />
            </label>
            <label className="mt-2 block text-[11px] text-slate-400">
              Adapter Source
              <select
                value={localizerAdapterSource}
                onChange={(event) => {
                  const source = event.target.value;
                  setLocalizerAdapterSource(source);
                  const adapter = (localizerFeedAdapters?.rows || []).find((row) => row.source === source);
                  if (adapter?.sample_payload) {
                    setLocalizerFeedPayload(JSON.stringify(adapter.sample_payload, null, 2));
                  }
                }}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
              >
                <option value="generic">generic</option>
                <option value="splunk">splunk</option>
                <option value="crowdstrike">crowdstrike</option>
                <option value="cloudflare">cloudflare</option>
              </select>
            </label>
            <label className="mt-2 block text-[11px] text-slate-400">
              Feed / Adapter Payload JSON
              <textarea
                value={localizerFeedPayload}
                onChange={(event) => setLocalizerFeedPayload(event.target.value)}
                className="mt-1 h-40 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 font-mono text-[11px] text-slate-100"
              />
            </label>
            <div className="mt-2 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busy || !canApprove}
                onClick={() => void importThreatFeed()}
                className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
              >
                Import External Threat Feed
              </button>
              <button
                type="button"
                disabled={busy || !canApprove}
                onClick={() => void importThreatFeedWithAdapter()}
                className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
              >
                Import Via Adapter
              </button>
            </div>
            {selectedThreatAdapter ? (
              <div className="mt-2 rounded border border-slate-800 bg-panelAlt/40 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {selectedThreatAdapter.display_name} categories={selectedThreatAdapter.categories_supported.join(", ")}
                </p>
                <p className="mt-1 text-slate-500 wrap-anywhere">{selectedThreatAdapter.description}</p>
                <p className="mt-1 text-slate-500 wrap-anywhere">
                  mapping={(selectedThreatAdapter.field_mapping || [])
                    .map((item) => `${item.incoming}->${item.mapped_to}`)
                    .join(" | ")}
                </p>
              </div>
            ) : null}
          </div>
          <div className="rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-300">Sector Profiles</p>
            <div className="mt-2 max-h-56 space-y-2 overflow-auto">
              {(localizerProfiles?.rows || []).map((profile) => (
                <div key={profile.sector} className="rounded border border-slate-800 bg-panelAlt/40 p-2">
                  <p className="text-slate-200 wrap-anywhere">
                    {profile.sector} / {profile.label_th}
                  </p>
                  <p className="mt-1 text-slate-400 wrap-anywhere">
                    priority={profile.priority_categories.join(", ")} bias={profile.risk_bias}
                  </p>
                  <p className="mt-1 text-slate-500 wrap-anywhere">{profile.keywords.join(", ")}</p>
                </div>
              ))}
              {(localizerProfiles?.rows || []).length === 0 ? <p className="text-slate-500">No sector profiles loaded.</p> : null}
            </div>
          </div>
        </div>
        <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
          <p className="text-slate-300">Recent Feed Matches</p>
          <div className="mt-2 max-h-48 space-y-2 overflow-auto">
            {(localizerFeeds?.rows || []).slice(0, 6).map((feed) => (
              <div key={feed.feed_item_id} className="rounded border border-slate-800 bg-panelAlt/40 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {feed.severity} / {feed.category} / {feed.focus_region}
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">{feed.title}</p>
                <p className="mt-1 text-slate-500 wrap-anywhere">{feed.summary_th}</p>
              </div>
            ))}
            {(localizerFeeds?.rows || []).length === 0 ? <p className="text-slate-500">No feed rows loaded yet.</p> : null}
          </div>
        </div>
        <div className="mt-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
          <p className="text-slate-300">Routing Promotions</p>
          <div className="mt-2 max-h-48 space-y-2 overflow-auto">
            {(localizerPromotionRuns?.rows || []).slice(0, 6).map((row) => (
              <div key={row.promotion_run_id} className="rounded border border-slate-800 bg-panelAlt/40 p-2">
                <p className="text-slate-200 wrap-anywhere">
                  {row.status} groups={row.routed_groups.join(", ") || "none"} playbooks={row.playbook_codes.join(", ") || "none"}
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">
                  categories={row.promoted_categories.join(", ") || "none"} autotune={row.autotune_run_id || "none"}
                </p>
                <p className="mt-1 text-slate-500 wrap-anywhere">{row.created_at}</p>
              </div>
            ))}
            {(localizerPromotionRuns?.rows || []).length === 0 ? <p className="text-slate-500">No routing promotions yet.</p> : null}
          </div>
        </div>
      </div>

      <div className="mt-3 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
        <p className="text-slate-300">Detection Autotune Policy</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{autotunePolicySummary}</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{autotuneRunSummary}</p>

        <div className="mt-2 grid grid-cols-2 gap-2">
          <label className="text-[11px] text-slate-400">
            Min Risk Score
            <input
              type="number"
              value={minRiskScore}
              onChange={(event) => setMinRiskScore(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Min Risk Tier
            <select
              value={minRiskTier}
              onChange={(event) => setMinRiskTier(event.target.value as RiskTier)}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            >
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
              <option value="critical">critical</option>
            </select>
          </label>
          <label className="text-[11px] text-slate-400">
            Target Coverage %
            <input
              type="number"
              value={targetCoveragePct}
              onChange={(event) => setTargetCoveragePct(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400">
            Max Rules / Run
            <input
              type="number"
              value={maxRulesPerRun}
              onChange={(event) => setMaxRulesPerRun(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
          <label className="text-[11px] text-slate-400 col-span-2">
            Schedule Interval (minutes)
            <input
              type="number"
              value={autotuneScheduleMinutes}
              onChange={(event) => setAutotuneScheduleMinutes(Number(event.target.value))}
              className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
            />
          </label>
        </div>

        <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-slate-300">
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={autoApplyAutotune} onChange={(event) => setAutoApplyAutotune(event.target.checked)} />
            auto apply rules
          </label>
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={autotuneRouteAlert} onChange={(event) => setAutotuneRouteAlert(event.target.checked)} />
            route alert
          </label>
        </div>

        <div className="mt-2 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!selectedSite || busy || !canEditPolicy}
            onClick={() => void saveAutotunePolicy()}
            className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
          >
            Save Autotune Policy
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy || !canApprove}
            onClick={() => void runAutotune(true, false)}
            className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
          >
            Run Autotune Dry Run
          </button>
          <button
            type="button"
            disabled={!selectedSite || busy || !canApprove}
            onClick={() => void runAutotune(false, true)}
            className="rounded border border-danger/60 bg-danger/10 px-2 py-1 text-[11px] text-danger hover:bg-danger/20 disabled:opacity-60"
          >
            Run Autotune Apply
          </button>
          <button
            type="button"
            disabled={busy || !canApprove}
            onClick={() => void runAutotuneScheduler()}
            className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
          >
            Run Autotune Scheduler
          </button>
        </div>
      </div>

      <div className="mt-3 max-h-36 overflow-auto rounded border border-slate-800 p-2 text-xs">
        <p className="mb-2 text-slate-400">Detection Autotune Runs</p>
        {(autotuneRuns?.rows || []).length === 0 ? <p className="text-slate-500">No autotune runs yet.</p> : null}
        {(autotuneRuns?.rows || []).slice(0, 6).map((run) => (
          <div key={run.run_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">
              {run.status} risk={run.risk_tier}/{run.risk_score} coverage={run.coverage_before_pct}%{"->"}
              {run.coverage_after_pct}%
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              recommendations={run.recommendation_count} applied={run.applied_count} dry_run={String(run.dry_run)}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-3 max-h-44 overflow-auto rounded border border-slate-800 p-2 text-xs">
        <p className="mb-2 text-slate-400">Detection Copilot Rules</p>
        {(detectionRules?.rows || []).length === 0 ? <p className="text-slate-500">No copilot rules yet.</p> : null}
        {(detectionRules?.rows || []).map((rule) => (
          <div key={rule.rule_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">{rule.rule_name}</p>
            <p className="mt-1 text-slate-400">status={rule.status}</p>
            <button
              type="button"
              disabled={busy || rule.status === "applied"}
              onClick={() => void applyRule(rule.rule_id)}
              className="mt-2 rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
            >
              Apply Rule
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}

function describeManagedResponderResult(result: SiteBlueManagedResponderRunResponse): string {
  if (result.status === "no_candidate") {
    return "No responder candidate matched the current severity policy";
  }
  if (result.status === "disabled") {
    return "Managed responder policy is disabled";
  }
  if (result.status === "guardrail_blocked") {
    return `Managed responder blocked by guardrail: ${String((result.guardrails as Record<string, unknown> | undefined)?.reason || "unknown")}`;
  }
  if (result.status === "rolled_back") {
    return `Managed responder rolled back for run=${result.run?.run_id || "unknown"}`;
  }
  if (!result.run) {
    return `Managed responder status=${result.status}`;
  }
  return `${result.run.status} action=${result.run.selected_action} severity=${result.run.selected_severity} playbook=${result.run.playbook_code || "none"} applied=${String(result.run.action_applied)}`;
}
