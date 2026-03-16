"use client";

import { useEffect, useState } from "react";

import {
  createPhaseScopeCheck,
  fetchEmbeddedAutomationFederationReadiness,
  fetchCompetitiveObjectives,
  fetchIntegrationAdapters,
  fetchIntegrationAdapterTemplates,
  fetchSiteEmbeddedActivationBundles,
  fetchSiteEmbeddedAutomationVerify,
  fetchSiteEmbeddedWorkflowEndpoints,
  fetchSiteEmbeddedWorkflowInvokePacks,
  fetchSiteEmbeddedWorkflowInvocations,
  fetchSites,
  ingestIntegrationEvent,
  upsertSiteEmbeddedWorkflowEndpoint,
  upsertSite,
  upsertThreatContentPack,
} from "@/lib/api";
import type {
  CompetitiveObjectivesResponse,
  EmbeddedAutomationFederationReadinessResponse,
  IntegrationAdaptersResponse,
  IntegrationAdapterTemplatesResponse,
  SiteEmbeddedActivationBundleResponse,
  SiteEmbeddedAutomationVerifyResponse,
  SiteEmbeddedInvokePackResponse,
  SiteEmbeddedWorkflowEndpointListResponse,
  SiteEmbeddedWorkflowInvocationListResponse,
  SiteRow,
} from "@/lib/types";

type FormState = {
  tenant_code: string;
  site_code: string;
  display_name: string;
  base_url: string;
  is_active: boolean;
};

const INITIAL_FORM: FormState = {
  tenant_code: "acb",
  site_code: "duck-sec-ai",
  display_name: "Duck Sec AI",
  base_url: "https://duck-sec-ai.vercel.app/",
  is_active: true,
};

const EMBEDDED_PLUGIN_OPTIONS = [
  { code: "blue_thai_alert_translator", label: "Blue: Thai Alert Translator & Summarizer" },
  { code: "blue_auto_playbook_executor", label: "Blue: Auto-Playbook Executor (Webhook)" },
  { code: "blue_log_refiner", label: "Blue: AI Log Refiner" },
  { code: "red_template_writer", label: "Red: Nuclei AI-Template Writer" },
  { code: "red_exploit_code_generator", label: "Red: Exploit Code Generator" },
  { code: "purple_incident_ghostwriter", label: "Purple: Incident Report Ghostwriter" },
  { code: "purple_mitre_heatmap", label: "Purple: MITRE ATT&CK Heatmap Generator" },
];

const EMBEDDED_VENDOR_PRESETS = [
  {
    code: "splunk_thai_alert_translator",
    label: "Splunk -> Blue Thai Alert Translator",
    endpoint_code: "splunk-alert-translator",
    workflow_type: "coworker_plugin" as const,
    plugin_code: "blue_thai_alert_translator",
    playbook_code: "",
    allowed_playbook_codes: [] as string[],
    require_playbook_approval: true,
    connector_source: "splunk",
    default_event_kind: "security_event",
    config: { lookback_limit: 20, summarize_mode: "thai_operator" },
  },
  {
    code: "crowdstrike_managed_responder",
    label: "CrowdStrike -> Managed AI Responder",
    endpoint_code: "crowdstrike-managed-response",
    workflow_type: "soar_playbook" as const,
    plugin_code: "",
    playbook_code: "isolate-host-and-reset-session",
    allowed_playbook_codes: ["isolate-host-and-reset-session", "notify-and-clear-session"],
    require_playbook_approval: true,
    connector_source: "crowdstrike",
    default_event_kind: "endpoint_detection",
    config: { lookback_limit: 10, response_mode: "containment_ready", required_payload_fields: ["severity"] },
  },
  {
    code: "cloudflare_waf_playbook",
    label: "Cloudflare -> Auto-Playbook Executor",
    endpoint_code: "cloudflare-waf-playbook",
    workflow_type: "soar_playbook" as const,
    plugin_code: "",
    playbook_code: "block-ip-and-waf-tighten",
    allowed_playbook_codes: ["block-ip-and-waf-tighten"],
    require_playbook_approval: true,
    connector_source: "cloudflare",
    default_event_kind: "waf_event",
    config: { lookback_limit: 10, action_scope: "waf_tighten", require_webhook_event_id: true },
  },
];

export default function ConfigurationPage() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [rows, setRows] = useState<SiteRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [adapters, setAdapters] = useState<IntegrationAdaptersResponse | null>(null);
  const [adapterTemplates, setAdapterTemplates] = useState<IntegrationAdapterTemplatesResponse | null>(null);
  const [objectives, setObjectives] = useState<CompetitiveObjectivesResponse | null>(null);
  const [embeddedSiteId, setEmbeddedSiteId] = useState("");
  const [embeddedPresetCode, setEmbeddedPresetCode] = useState(EMBEDDED_VENDOR_PRESETS[0].code);
  const [embeddedEndpointCode, setEmbeddedEndpointCode] = useState("soc-alert-translator");
  const [embeddedWorkflowType, setEmbeddedWorkflowType] = useState<"coworker_plugin" | "soar_playbook">("coworker_plugin");
  const [embeddedPluginCode, setEmbeddedPluginCode] = useState("blue_thai_alert_translator");
  const [embeddedPlaybookCode, setEmbeddedPlaybookCode] = useState("");
  const [embeddedAllowedPlaybookCodes, setEmbeddedAllowedPlaybookCodes] = useState("");
  const [embeddedRequirePlaybookApproval, setEmbeddedRequirePlaybookApproval] = useState(true);
  const [embeddedConnectorSource, setEmbeddedConnectorSource] = useState("splunk");
  const [embeddedEventKind, setEmbeddedEventKind] = useState("security_event");
  const [embeddedEnabled, setEmbeddedEnabled] = useState(true);
  const [embeddedDryRunDefault, setEmbeddedDryRunDefault] = useState(true);
  const [embeddedRotateSecret, setEmbeddedRotateSecret] = useState(false);
  const [embeddedConfigText, setEmbeddedConfigText] = useState('{"lookback_limit": 20}');
  const [embeddedEndpoints, setEmbeddedEndpoints] = useState<SiteEmbeddedWorkflowEndpointListResponse | null>(null);
  const [embeddedInvocations, setEmbeddedInvocations] = useState<SiteEmbeddedWorkflowInvocationListResponse | null>(null);
  const [embeddedInvokePacks, setEmbeddedInvokePacks] = useState<SiteEmbeddedInvokePackResponse | null>(null);
  const [embeddedActivationBundles, setEmbeddedActivationBundles] = useState<SiteEmbeddedActivationBundleResponse | null>(null);
  const [embeddedAutomationVerify, setEmbeddedAutomationVerify] = useState<SiteEmbeddedAutomationVerifyResponse | null>(null);
  const [embeddedFederationReadiness, setEmbeddedFederationReadiness] = useState<EmbeddedAutomationFederationReadinessResponse | null>(null);
  const [embeddedMessage, setEmbeddedMessage] = useState("");
  const [embeddedError, setEmbeddedError] = useState("");
  const [embeddedToken, setEmbeddedToken] = useState("");
  const [embeddedInvokePath, setEmbeddedInvokePath] = useState("");

  const loadSites = async () => {
    setError("");
    try {
      const response = await fetchSites("", 300);
      setRows(response.rows || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "load_sites_failed");
    }
  };

  useEffect(() => {
    void loadSites();
    void fetchIntegrationAdapters().then(setAdapters).catch(() => undefined);
    void fetchIntegrationAdapterTemplates().then(setAdapterTemplates).catch(() => undefined);
    void fetchCompetitiveObjectives().then(setObjectives).catch(() => undefined);
    void fetchEmbeddedAutomationFederationReadiness({ limit: 200 }).then(setEmbeddedFederationReadiness).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!embeddedSiteId && rows[0]?.site_id) {
      setEmbeddedSiteId(rows[0].site_id);
    }
  }, [rows, embeddedSiteId]);

  const loadEmbeddedWorkflowData = async (siteId: string) => {
    if (!siteId) return;
    setEmbeddedError("");
    try {
      const [endpoints, invocations, invokePacks, activationBundles, automationVerify, federationReadiness] = await Promise.all([
        fetchSiteEmbeddedWorkflowEndpoints(siteId, 100),
        fetchSiteEmbeddedWorkflowInvocations(siteId, { limit: 20 }),
        fetchSiteEmbeddedWorkflowInvokePacks(siteId, { limit: 20 }),
        fetchSiteEmbeddedActivationBundles(siteId, { limit: 20 }),
        fetchSiteEmbeddedAutomationVerify(siteId, { limit: 20 }),
        fetchEmbeddedAutomationFederationReadiness({ limit: 200 }),
      ]);
      setEmbeddedEndpoints(endpoints);
      setEmbeddedInvocations(invocations);
      setEmbeddedInvokePacks(invokePacks);
      setEmbeddedActivationBundles(activationBundles);
      setEmbeddedAutomationVerify(automationVerify);
      setEmbeddedFederationReadiness(federationReadiness);
    } catch (err) {
      setEmbeddedError(err instanceof Error ? err.message : "load_embedded_workflows_failed");
    }
  };

  useEffect(() => {
    if (!embeddedSiteId) return;
    void loadEmbeddedWorkflowData(embeddedSiteId);
  }, [embeddedSiteId]);

  const save = async () => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const response = await upsertSite({
        tenant_code: form.tenant_code.trim(),
        site_code: form.site_code.trim(),
        display_name: form.display_name.trim(),
        base_url: form.base_url.trim(),
        is_active: form.is_active,
        config: { ai_mode: "local_assist", source: "configuration_page" },
      });
      setMessage(`Saved: ${response.site.display_name} (${response.status})`);
      await loadSites();
    } catch (err) {
      setError(err instanceof Error ? err.message : "save_site_failed");
    } finally {
      setBusy(false);
    }
  };

  const ingestSampleWebhook = async () => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const primarySite = rows[0];
      if (!primarySite) {
        setError("No site available. Save configuration first.");
        return;
      }
      const response = await ingestIntegrationEvent({
        source: "cloudflare",
        event_kind: "waf_event",
        site_id: primarySite.site_id,
        payload: {
          ClientIP: "198.51.100.77",
          ClientRequestURI: "/admin-login",
          EdgeResponseStatus: 403,
          message: "WAF challenge triggered",
        },
      });
      setMessage(`Sample webhook ingested: ${response.integration_event_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "ingest_sample_failed");
    } finally {
      setBusy(false);
    }
  };

  const seedThreatPack = async () => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await upsertThreatContentPack({
        pack_code: "weekly-credential-ransomware",
        title: "Weekly Credential + Ransomware Validation Pack",
        category: "ransomware",
        mitre_techniques: ["T1110", "T1078", "T1486"],
        attack_steps: [
          "credential_stuffing_sim",
          "privilege_escalation_sim",
          "ransomware_preimpact_chain_sim",
        ],
        validation_mode: "simulation_safe",
        is_active: true,
      });
      setMessage(`Threat pack ${result.status}: weekly-credential-ransomware`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "seed_threat_pack_failed");
    } finally {
      setBusy(false);
    }
  };

  const recordPhaseScope = async () => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const firstSite = rows[0];
      const result = await createPhaseScopeCheck({
        phase_code: "PHASE64",
        phase_title: "Competitive Engine Foundations",
        objective_ids: ["O1", "O2", "O3", "O6", "O8", "O9"],
        deliverables: [
          "exploit path simulation engine",
          "threat content pack pipeline baseline",
          "detection copilot tuning loop",
          "unified case graph endpoint",
          "purple executive iso gap alignment",
          "connector reliability baseline",
        ],
        site_id: firstSite?.site_id || undefined,
        context: { source: "configuration_page" },
      });
      setMessage(`Phase scope check: ${result.scope_status} (${result.phase_code})`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "phase_scope_check_failed");
    } finally {
      setBusy(false);
    }
  };

  const applyEmbeddedPreset = () => {
    const preset = EMBEDDED_VENDOR_PRESETS.find((row) => row.code === embeddedPresetCode);
    if (!preset) return;
    setEmbeddedEndpointCode(preset.endpoint_code);
    setEmbeddedWorkflowType(preset.workflow_type);
    setEmbeddedPluginCode(preset.plugin_code);
    setEmbeddedPlaybookCode(preset.playbook_code);
    setEmbeddedAllowedPlaybookCodes(preset.allowed_playbook_codes.join(","));
    setEmbeddedRequirePlaybookApproval(preset.require_playbook_approval);
    setEmbeddedConnectorSource(preset.connector_source);
    setEmbeddedEventKind(preset.default_event_kind);
    setEmbeddedConfigText(JSON.stringify(preset.config, null, 2));
    setEmbeddedMessage(`Preset applied: ${preset.label}`);
    setEmbeddedError("");
  };

  const saveEmbeddedEndpoint = async () => {
    if (!embeddedSiteId) {
      setEmbeddedError("Select site first");
      return;
    }
    let config: Record<string, unknown> = {};
    try {
      config = JSON.parse(embeddedConfigText || "{}") as Record<string, unknown>;
    } catch {
      setEmbeddedError("Invalid embedded config JSON");
      return;
    }
    if (embeddedWorkflowType === "soar_playbook") {
      const allowedPlaybookCodes = embeddedAllowedPlaybookCodes
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
      if (embeddedPlaybookCode.trim()) {
        config.playbook_code = embeddedPlaybookCode.trim();
        config.default_playbook_code = embeddedPlaybookCode.trim();
      }
      config.allowed_playbook_codes = Array.from(new Set([
        ...allowedPlaybookCodes,
        ...(embeddedPlaybookCode.trim() ? [embeddedPlaybookCode.trim()] : []),
      ]));
      config.require_playbook_approval = embeddedRequirePlaybookApproval;
    } else {
      delete config.playbook_code;
      delete config.default_playbook_code;
      delete config.allowed_playbook_codes;
      delete config.require_playbook_approval;
    }

    setBusy(true);
    setEmbeddedError("");
    setEmbeddedMessage("");
    try {
      const response = await upsertSiteEmbeddedWorkflowEndpoint(embeddedSiteId, {
        endpoint_code: embeddedEndpointCode,
        workflow_type: embeddedWorkflowType,
        plugin_code: embeddedWorkflowType === "coworker_plugin" ? embeddedPluginCode : "",
        connector_source: embeddedConnectorSource,
        default_event_kind: embeddedEventKind,
        enabled: embeddedEnabled,
        dry_run_default: embeddedDryRunDefault,
        config,
        owner: "configuration_page",
        rotate_secret: embeddedRotateSecret,
      });
      setEmbeddedMessage(`Embedded endpoint ${response.status}: ${response.endpoint.endpoint_code}`);
      setEmbeddedToken(response.token || "");
      setEmbeddedInvokePath(response.invoke_path || "");
      setEmbeddedRotateSecret(false);
      await loadEmbeddedWorkflowData(embeddedSiteId);
    } catch (err) {
      setEmbeddedError(err instanceof Error ? err.message : "save_embedded_endpoint_failed");
    } finally {
      setBusy(false);
    }
  };

  const selectedEmbeddedSite = rows.find((row) => row.site_id === embeddedSiteId) || null;
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const embeddedCurlPayload = {
    source: embeddedConnectorSource,
    event_kind: embeddedEventKind,
    ...(embeddedWorkflowType === "soar_playbook" && embeddedPlaybookCode.trim()
      ? { playbook_code: embeddedPlaybookCode.trim() }
      : {}),
    payload: {
      message: "sample embedded alert",
      severity: "high",
      source_ip: "203.0.113.20",
    },
  };
  const embeddedCurl = embeddedToken && embeddedInvokePath
    ? `curl -X POST ${apiBaseUrl}${embeddedInvokePath} \\
  -H 'Content-Type: application/json' \\
  -H 'X-BRP-Embed-Token: ${embeddedToken}' \\
  -d '${JSON.stringify(embeddedCurlPayload)}'`
    : "";

  return (
    <main className="space-y-6">
      <section className="card p-5">
        <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Configuration</p>
        <h2 className="mt-1 text-2xl font-bold text-ink">Customer Sites Settings</h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Register sites, seed adapters, and record phase-scope checks without leaving the shared control plane shell.
        </p>
      </section>

      <section className="card p-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Tenant Code" value={form.tenant_code} onChange={(value) => setForm((prev) => ({ ...prev, tenant_code: value }))} />
          <Field label="Site Code" value={form.site_code} onChange={(value) => setForm((prev) => ({ ...prev, site_code: value }))} />
          <Field
            label="Display Name"
            value={form.display_name}
            onChange={(value) => setForm((prev) => ({ ...prev, display_name: value }))}
          />
          <Field label="Base URL" value={form.base_url} onChange={(value) => setForm((prev) => ({ ...prev, base_url: value }))} />
        </div>

        <label className="mt-3 flex items-center gap-2 text-xs text-slate-300">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm((prev) => ({ ...prev, is_active: e.target.checked }))}
          />
          Active
        </label>

        <div className="mt-3 flex items-center gap-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => void save()}
            className="rounded-md border border-accent/60 bg-accent/15 px-3 py-2 text-xs font-semibold text-accent hover:bg-accent/25 disabled:opacity-60"
          >
            Save Configuration
          </button>
          <button
            type="button"
            onClick={() => void loadSites()}
            className="rounded-md border border-slate-600 px-3 py-2 text-xs text-slate-200 hover:border-slate-400"
          >
            Reload
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void ingestSampleWebhook()}
            className="rounded-md border border-slate-600 px-3 py-2 text-xs text-slate-200 hover:border-slate-400 disabled:opacity-60"
          >
            Ingest Sample External Event
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void seedThreatPack()}
            className="rounded-md border border-warning/60 bg-warning/10 px-3 py-2 text-xs text-warning hover:bg-warning/20 disabled:opacity-60"
          >
            Seed Threat Pack
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void recordPhaseScope()}
            className="rounded-md border border-slate-600 px-3 py-2 text-xs text-slate-200 hover:border-slate-400 disabled:opacity-60"
          >
            Record Phase Scope Check
          </button>
        </div>

        {message ? <p className="mt-2 text-sm text-accent">{message}</p> : null}
        {error ? <p className="mt-2 text-sm text-danger">{error}</p> : null}
        <p className="mt-3 text-xs text-slate-400">
          Integration adapters:{" "}
          {adapters ? Object.keys(adapters.adapters).join(", ") : "loading..."}
        </p>
        <p className="mt-2 text-xs text-slate-400 wrap-anywhere">
          Competitive objectives top-priority:{" "}
          {objectives ? objectives.top_priority_objective_ids.join(", ") : "loading..."}
        </p>
      </section>

      <section className="card mt-5 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-panelAlt/60 text-slate-300">
              <tr>
                <th className="px-4 py-3">Tenant</th>
                <th className="px-4 py-3">Site</th>
                <th className="px-4 py-3">Base URL</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.site_id} className="border-t border-slate-800/80">
                  <td className="px-4 py-3 text-xs text-slate-300">{row.tenant_code || row.tenant_id}</td>
                  <td className="px-4 py-3 text-xs text-slate-100">{row.display_name}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-300">{row.base_url}</td>
                  <td className="px-4 py-3 text-xs">{row.is_active ? "active" : "inactive"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 ? <p className="p-4 text-xs text-slate-500">No sites found.</p> : null}
        </div>
      </section>

      <section className="card p-4">
        <div className="flex flex-col gap-2">
          <p className="text-xs uppercase tracking-[0.24em] text-accent">Adapter Templates</p>
          <h3 className="text-lg font-semibold text-ink">Embedded invoke payload templates</h3>
          <p className="text-sm text-slate-400">
            Prebuilt request bodies for Splunk, CrowdStrike, and Cloudflare so customer tools can call AI co-workers without inventing a schema first.
          </p>
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-3">
          {(adapterTemplates?.rows || []).map((row) => (
            <div key={row.source} className="rounded-md border border-slate-800 bg-panelAlt/20 p-4 text-xs">
              <p className="font-semibold text-slate-100">{row.display_name}</p>
              <p className="mt-1 text-slate-400">
                source={row.source} event_kind={row.default_event_kind}
              </p>
              <p className="mt-2 text-slate-300 wrap-anywhere">
                plugins: {row.recommended_plugin_codes.join(", ")}
              </p>
              <div className="mt-2 space-y-1">
                {row.notes.map((note) => (
                  <p key={`${row.source}-${note}`} className="text-slate-400 wrap-anywhere">
                    {note}
                  </p>
                ))}
              </div>
              <div className="mt-3 rounded-md border border-slate-800 bg-panelAlt/40 p-3">
                <p className="mb-2 text-slate-300">Field mapping</p>
                <div className="space-y-1">
                  {row.field_mapping.map((mapping) => (
                    <p key={`${row.source}-${mapping.incoming}-${mapping.mapped_to}`} className="text-slate-400 wrap-anywhere">
                      {mapping.incoming} {"->"} {mapping.mapped_to} ({mapping.note})
                    </p>
                  ))}
                </div>
              </div>
              <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap rounded-md border border-slate-800 bg-panelAlt/40 p-3 text-[11px] text-slate-100">
                {JSON.stringify(row.invoke_payload, null, 2)}
              </pre>
            </div>
          ))}
        </div>
        {(adapterTemplates?.rows || []).length === 0 ? (
          <p className="mt-3 text-xs text-slate-500">No adapter templates loaded.</p>
        ) : null}
      </section>

      <section className="card p-4">
        <div className="flex flex-col gap-2">
          <p className="text-xs uppercase tracking-[0.24em] text-accent">Embedded Workflow API</p>
          <h3 className="text-lg font-semibold text-ink">Plugin-first webhook trigger surface</h3>
          <p className="text-sm text-slate-400">
            Create site-level endpoints so customer SIEM, EDR, WAF, or custom tools can invoke AI co-workers directly by shared secret.
          </p>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="text-xs text-slate-300">
            Site
            <select
              value={embeddedSiteId}
              onChange={(event) => setEmbeddedSiteId(event.target.value)}
              className="mt-1 w-full rounded-md border border-slate-700 bg-panelAlt/40 px-2 py-2 text-xs text-slate-100"
            >
              {rows.map((row) => (
                <option key={row.site_id} value={row.site_id}>
                  {row.display_name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-300">
            Vendor Preset
            <select
              value={embeddedPresetCode}
              onChange={(event) => setEmbeddedPresetCode(event.target.value)}
              className="mt-1 w-full rounded-md border border-slate-700 bg-panelAlt/40 px-2 py-2 text-xs text-slate-100"
            >
              {EMBEDDED_VENDOR_PRESETS.map((preset) => (
                <option key={preset.code} value={preset.code}>
                  {preset.label}
                </option>
              ))}
            </select>
          </label>
          <Field label="Endpoint Code" value={embeddedEndpointCode} onChange={setEmbeddedEndpointCode} />
          <label className="text-xs text-slate-300">
            Workflow Type
            <select
              value={embeddedWorkflowType}
              onChange={(event) => setEmbeddedWorkflowType(event.target.value as "coworker_plugin" | "soar_playbook")}
              className="mt-1 w-full rounded-md border border-slate-700 bg-panelAlt/40 px-2 py-2 text-xs text-slate-100"
            >
              <option value="coworker_plugin">coworker_plugin</option>
              <option value="soar_playbook">soar_playbook</option>
            </select>
          </label>
          <Field label="Connector Source" value={embeddedConnectorSource} onChange={setEmbeddedConnectorSource} />
          <Field label="Default Event Kind" value={embeddedEventKind} onChange={setEmbeddedEventKind} />
        </div>

        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {embeddedWorkflowType === "coworker_plugin" ? (
            <label className="text-xs text-slate-300">
              Plugin
              <select
                value={embeddedPluginCode}
                onChange={(event) => setEmbeddedPluginCode(event.target.value)}
                className="mt-1 w-full rounded-md border border-slate-700 bg-panelAlt/40 px-2 py-2 text-xs text-slate-100"
              >
                {EMBEDDED_PLUGIN_OPTIONS.map((option) => (
                  <option key={option.code} value={option.code}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <>
              <Field label="Default Playbook" value={embeddedPlaybookCode} onChange={setEmbeddedPlaybookCode} />
              <Field label="Allowed Playbooks" value={embeddedAllowedPlaybookCodes} onChange={setEmbeddedAllowedPlaybookCodes} />
              <label className="mt-5 flex items-center gap-2 text-xs text-slate-300">
                <input
                  type="checkbox"
                  checked={embeddedRequirePlaybookApproval}
                  onChange={(event) => setEmbeddedRequirePlaybookApproval(event.target.checked)}
                />
                require playbook approval
              </label>
            </>
          )}
        </div>

        <label className="mt-3 block text-xs text-slate-300">
          Endpoint Config JSON
          <textarea
            value={embeddedConfigText}
            onChange={(event) => setEmbeddedConfigText(event.target.value)}
            className="mt-1 h-28 w-full rounded-md border border-slate-700 bg-panelAlt/40 px-2 py-2 font-mono text-xs text-slate-100"
          />
        </label>

        <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-300">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={embeddedEnabled} onChange={(event) => setEmbeddedEnabled(event.target.checked)} />
            enabled
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={embeddedDryRunDefault}
              onChange={(event) => setEmbeddedDryRunDefault(event.target.checked)}
            />
            dry-run default
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={embeddedRotateSecret}
              onChange={(event) => setEmbeddedRotateSecret(event.target.checked)}
            />
            rotate secret on save
          </label>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={applyEmbeddedPreset}
            className="rounded-md border border-warning/60 bg-warning/10 px-3 py-2 text-xs text-warning hover:bg-warning/20"
          >
            Apply Vendor Preset
          </button>
          <button
            type="button"
            disabled={busy || !embeddedSiteId}
            onClick={() => void saveEmbeddedEndpoint()}
            className="rounded-md border border-accent/60 bg-accent/15 px-3 py-2 text-xs font-semibold text-accent hover:bg-accent/25 disabled:opacity-60"
          >
            Save Embedded Endpoint
          </button>
          <button
            type="button"
            disabled={!embeddedSiteId}
            onClick={() => void loadEmbeddedWorkflowData(embeddedSiteId)}
            className="rounded-md border border-slate-600 px-3 py-2 text-xs text-slate-200 hover:border-slate-400 disabled:opacity-60"
          >
            Reload Embedded Data
          </button>
        </div>

        {embeddedMessage ? <p className="mt-2 text-sm text-accent">{embeddedMessage}</p> : null}
        {embeddedError ? <p className="mt-2 text-sm text-danger">{embeddedError}</p> : null}

        {embeddedFederationReadiness ? (
          <div className="mt-4 rounded-md border border-slate-800 bg-panelAlt/20 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-100">Federation Readiness Snapshot</p>
                <p className="mt-1 text-xs text-slate-400 wrap-anywhere">
                  Cross-site posture for embedded automation bundles. Use this to see which customer sites are ready for vendor-native activation.
                </p>
              </div>
              <p className="text-xs text-slate-500 wrap-anywhere">generated_at={embeddedFederationReadiness.generated_at}</p>
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-4">
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Ready Sites</p>
                <p className="mt-1 text-lg font-semibold text-accent">{embeddedFederationReadiness.summary.ready_sites}</p>
              </div>
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Warning Sites</p>
                <p className="mt-1 text-lg font-semibold text-warning">{embeddedFederationReadiness.summary.warning_sites}</p>
              </div>
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Error Sites</p>
                <p className="mt-1 text-lg font-semibold text-danger">{embeddedFederationReadiness.summary.error_sites}</p>
              </div>
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Not Configured</p>
                <p className="mt-1 text-lg font-semibold text-slate-100">{embeddedFederationReadiness.summary.not_configured_sites}</p>
              </div>
            </div>
            <div className="mt-3 space-y-2">
              {(embeddedFederationReadiness.rows || []).slice(0, 8).map((row) => (
                <div key={`${row.site_id}-federation`} className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-slate-100">{row.site_code}</p>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] ${
                        row.status === "ready"
                          ? "bg-accent/15 text-accent"
                          : row.status === "warning"
                            ? "bg-warning/15 text-warning"
                            : row.status === "error"
                              ? "bg-danger/15 text-danger"
                              : "bg-slate-700/40 text-slate-300"
                      }`}
                    >
                      {row.status}
                    </span>
                  </div>
                  <p className="mt-1 text-slate-400 wrap-anywhere">
                    tenant={row.tenant_code || "-"} endpoints={row.endpoint_count} ready={row.ready_endpoint_count} warnings=
                    {row.warning_endpoint_count} errors={row.error_endpoint_count} approvals={row.approval_required_count}
                  </p>
                  <p className="mt-1 text-slate-500 wrap-anywhere">{row.recommended_action}</p>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {embeddedToken ? (
          <div className="mt-3 rounded-md border border-accent/30 bg-accent/10 p-3">
            <p className="text-xs font-semibold text-accent">Store token now. It is only shown on create/rotate.</p>
            <p className="mt-2 font-mono text-xs text-slate-100 wrap-anywhere">{embeddedToken}</p>
            <p className="mt-2 text-xs text-slate-400 wrap-anywhere">
              Invoke path: {apiBaseUrl}
              {embeddedInvokePath}
            </p>
            {selectedEmbeddedSite ? (
              <pre className="mt-3 overflow-auto whitespace-pre-wrap rounded-md border border-slate-800 bg-panelAlt/40 p-3 text-[11px] text-slate-100">
                {embeddedCurl}
              </pre>
            ) : null}
          </div>
        ) : null}

        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="rounded-md border border-slate-800 overflow-hidden">
            <div className="border-b border-slate-800 bg-panelAlt/60 px-4 py-3">
              <p className="text-sm font-semibold text-slate-100">Configured Endpoints</p>
            </div>
            <div className="max-h-80 overflow-auto">
              {(embeddedEndpoints?.rows || []).map((row) => (
                <div key={row.endpoint_id} className="border-b border-slate-800/80 px-4 py-3 text-xs">
                  <p className="font-semibold text-slate-100 wrap-anywhere">
                    {row.endpoint_code} <span className="text-slate-500">({row.workflow_type})</span>
                  </p>
                  <p className="mt-1 text-slate-400 wrap-anywhere">
                    source={row.connector_source} event_kind={row.default_event_kind} enabled={String(row.enabled)} dry_run_default=
                    {String(row.dry_run_default)}
                  </p>
                  <p className="mt-1 text-slate-500 wrap-anywhere">
                    {row.workflow_type === "coworker_plugin"
                      ? `plugin=${row.plugin_code || "-"}`
                      : `playbook=${String(row.config.playbook_code || row.config.default_playbook_code || "-")}`}
                  </p>
                </div>
              ))}
              {(embeddedEndpoints?.rows || []).length === 0 ? <p className="p-4 text-xs text-slate-500">No embedded endpoints yet.</p> : null}
            </div>
          </div>

          <div className="rounded-md border border-slate-800 overflow-hidden">
            <div className="border-b border-slate-800 bg-panelAlt/60 px-4 py-3">
              <p className="text-sm font-semibold text-slate-100">Recent Invocations</p>
            </div>
            <div className="max-h-80 overflow-auto">
              {(embeddedInvocations?.rows || []).map((row) => (
                <div key={row.invocation_id} className="border-b border-slate-800/80 px-4 py-3 text-xs">
                  <p className="font-semibold text-slate-100 wrap-anywhere">
                    {row.endpoint_code} [{row.status}] source={row.source}
                  </p>
                  <p className="mt-1 text-slate-400 wrap-anywhere">
                    plugin={row.plugin_code} dry_run={String(row.dry_run)} at {row.created_at}
                  </p>
                </div>
              ))}
              {(embeddedInvocations?.rows || []).length === 0 ? <p className="p-4 text-xs text-slate-500">No embedded invocations yet.</p> : null}
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-md border border-slate-800 overflow-hidden">
          <div className="border-b border-slate-800 bg-panelAlt/60 px-4 py-3">
            <p className="text-sm font-semibold text-slate-100">Vendor Activation Bundles</p>
            <p className="mt-1 text-xs text-slate-400">
              Bundle everything an operator needs to hand over to the customer tool owner: invoke template, activation steps, checklist, and readiness status.
            </p>
          </div>
          <div className="p-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Ready</p>
                <p className="mt-1 text-lg font-semibold text-accent">{embeddedActivationBundles?.ready_count ?? 0}</p>
              </div>
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Needs Attention</p>
                <p className="mt-1 text-lg font-semibold text-warning">{embeddedActivationBundles?.needs_attention_count ?? 0}</p>
              </div>
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Blocked</p>
                <p className="mt-1 text-lg font-semibold text-danger">{embeddedActivationBundles?.blocked_count ?? 0}</p>
              </div>
            </div>
            <div className="mt-4 space-y-4">
              {(embeddedActivationBundles?.rows || []).map((row) => (
                <div key={`${row.endpoint.endpoint_id}-bundle`} className="rounded-md border border-slate-800 bg-panelAlt/20 p-4 text-xs">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-slate-100 wrap-anywhere">{row.endpoint.endpoint_code}</p>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] ${
                        row.handoff.status === "ready"
                          ? "bg-accent/15 text-accent"
                          : row.handoff.status === "needs_attention"
                            ? "bg-warning/15 text-warning"
                            : "bg-danger/15 text-danger"
                      }`}
                    >
                      {row.handoff.status}
                    </span>
                  </div>
                  <p className="mt-1 text-slate-400 wrap-anywhere">
                    {row.activation_bundle.display_name} preset={row.activation_bundle.vendor_preset_code} workflow=
                    {row.activation_bundle.automation_pack.workflow_type}
                  </p>
                  <p className="mt-1 text-slate-500 wrap-anywhere">{row.handoff.summary}</p>
                  <div className="mt-3 grid gap-3 lg:grid-cols-2">
                    <div className="rounded-md border border-slate-800 bg-panelAlt/30 p-3">
                      <p className="text-slate-300">Operator Checklist</p>
                      <div className="mt-2 space-y-1">
                        {row.activation_bundle.operator_checklist.map((item) => (
                          <p key={`${row.endpoint.endpoint_id}-${item}`} className="text-slate-400 wrap-anywhere">
                            {item}
                          </p>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-md border border-slate-800 bg-panelAlt/30 p-3">
                      <p className="text-slate-300">Missing Items</p>
                      {(row.handoff.missing_items || []).length > 0 ? (
                        <div className="mt-2 space-y-1">
                          {row.handoff.missing_items.map((item) => (
                            <p key={`${row.endpoint.endpoint_id}-${item}`} className="text-warning wrap-anywhere">
                              {item}
                            </p>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-2 text-accent">No missing items detected.</p>
                      )}
                    </div>
                  </div>
                  <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-md border border-slate-800 bg-panelAlt/40 p-3 text-[11px] text-slate-100">
                    {row.activation_bundle.curl_example}
                  </pre>
                </div>
              ))}
              {(embeddedActivationBundles?.rows || []).length === 0 ? (
                <p className="text-xs text-slate-500">No activation bundles yet. Save an embedded endpoint first.</p>
              ) : null}
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-md border border-slate-800 overflow-hidden">
          <div className="border-b border-slate-800 bg-panelAlt/60 px-4 py-3">
            <p className="text-sm font-semibold text-slate-100">Connector-specific Invoke Packs</p>
          </div>
          <div className="max-h-[32rem] overflow-auto p-4">
            {(embeddedInvokePacks?.rows || []).length === 0 ? (
              <p className="text-xs text-slate-500">No invoke packs yet. Save an embedded endpoint first.</p>
            ) : null}
            <div className="space-y-4">
              {(embeddedInvokePacks?.rows || []).map((row) => (
                <div key={`${row.endpoint.endpoint_id}-pack`} className="rounded-md border border-slate-800 bg-panelAlt/20 p-4 text-xs">
                  <p className="font-semibold text-slate-100 wrap-anywhere">
                    {row.endpoint.endpoint_code} <span className="text-slate-500">({row.endpoint.connector_source})</span>
                  </p>
                  <p className="mt-1 text-slate-400 wrap-anywhere">{row.invoke_pack.display_name}</p>
                  <p className="mt-1 text-slate-400 wrap-anywhere">preset={row.invoke_pack.vendor_preset_code}</p>
                  <p className="mt-2 text-slate-300 wrap-anywhere">
                    workflow={row.invoke_pack.automation_pack.workflow_type} invoke_path={apiBaseUrl}
                    {row.invoke_pack.invoke_path}
                  </p>
                  {row.invoke_pack.automation_pack.default_playbook_code ? (
                    <p className="mt-1 text-slate-400 wrap-anywhere">
                      default_playbook={row.invoke_pack.automation_pack.default_playbook_code} allowed=
                      {row.invoke_pack.automation_pack.allowed_playbook_codes.join(", ") || "-"}
                    </p>
                  ) : null}
                  <div className="mt-2 rounded-md border border-slate-800 bg-panelAlt/40 p-3">
                    <p className="text-slate-300">Guardrails</p>
                    <p className="mt-1 text-slate-400 wrap-anywhere">
                      rate_limit/min={row.invoke_pack.guardrails.rate_limit_per_minute} replay_window_seconds=
                      {row.invoke_pack.guardrails.replay_window_seconds} require_webhook_event_id=
                      {String(row.invoke_pack.guardrails.require_webhook_event_id)}
                    </p>
                  </div>
                  <div className="mt-2 space-y-1">
                    {row.invoke_pack.notes.map((note) => (
                      <p key={`${row.endpoint.endpoint_id}-${note}`} className="text-slate-400 wrap-anywhere">
                        {note}
                      </p>
                    ))}
                  </div>
                  <div className="mt-2 rounded-md border border-slate-800 bg-panelAlt/40 p-3">
                    <p className="text-slate-300">Activation Steps</p>
                    <div className="mt-1 space-y-1">
                      {row.invoke_pack.activation_steps.map((step) => (
                        <p key={`${row.endpoint.endpoint_id}-${step}`} className="text-slate-400 wrap-anywhere">
                          {step}
                        </p>
                      ))}
                    </div>
                  </div>
                  <pre className="mt-3 max-h-48 overflow-auto whitespace-pre-wrap rounded-md border border-slate-800 bg-panelAlt/40 p-3 text-[11px] text-slate-100">
                    {row.invoke_pack.curl_example}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-md border border-slate-800 overflow-hidden">
          <div className="border-b border-slate-800 bg-panelAlt/60 px-4 py-3">
            <p className="text-sm font-semibold text-slate-100">Automation Pack Verification</p>
            <p className="mt-1 text-xs text-slate-400">
              Checks whether the saved endpoint is actually runnable against its plugin/playbook and tenant policy.
            </p>
          </div>
          <div className="p-4">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">OK</p>
                <p className="mt-1 text-lg font-semibold text-accent">{embeddedAutomationVerify?.ok_count ?? 0}</p>
              </div>
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Warnings</p>
                <p className="mt-1 text-lg font-semibold text-warning">{embeddedAutomationVerify?.warning_count ?? 0}</p>
              </div>
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Errors</p>
                <p className="mt-1 text-lg font-semibold text-danger">{embeddedAutomationVerify?.error_count ?? 0}</p>
              </div>
            </div>
            <div className="mt-4 space-y-3">
              {(embeddedAutomationVerify?.rows || []).map((row) => (
                <div key={`${row.endpoint.endpoint_id}-verify`} className="rounded-md border border-slate-800 bg-panelAlt/20 p-4 text-xs">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-slate-100">{row.endpoint.endpoint_code}</p>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] ${
                        row.verification.status === "ok"
                          ? "bg-accent/15 text-accent"
                          : row.verification.status === "warning"
                            ? "bg-warning/15 text-warning"
                            : "bg-danger/15 text-danger"
                      }`}
                    >
                      {row.verification.status}
                    </span>
                  </div>
                  <p className="mt-1 text-slate-400 wrap-anywhere">
                    workflow={row.verification.workflow_type} playbook={row.verification.playbook_code || "-"} approval_required=
                    {String(row.verification.effective_approval_required)}
                  </p>
                  {(row.verification.issues || []).length > 0 ? (
                    <div className="mt-2 space-y-1">
                      {row.verification.issues.map((issue) => (
                        <p
                          key={`${row.endpoint.endpoint_id}-${issue.code}`}
                          className={issue.level === "error" ? "text-danger wrap-anywhere" : "text-warning wrap-anywhere"}
                        >
                          {issue.code}: {issue.message}
                        </p>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-2 text-accent">No blocking issues detected.</p>
                  )}
                  {(row.verification.recommendations || []).length > 0 ? (
                    <div className="mt-2 space-y-1">
                      {row.verification.recommendations.map((recommendation) => (
                        <p key={`${row.endpoint.endpoint_id}-${recommendation}`} className="text-slate-400 wrap-anywhere">
                          {recommendation}
                        </p>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
              {(embeddedAutomationVerify?.rows || []).length === 0 ? (
                <p className="text-xs text-slate-500">No automation packs to verify yet.</p>
              ) : null}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="text-xs text-slate-300">
      {label}
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-slate-700 bg-panelAlt/40 px-2 py-2 text-xs text-slate-100"
      />
    </label>
  );
}
