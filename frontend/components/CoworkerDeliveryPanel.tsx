import { useEffect, useMemo, useState } from "react";

import {
  dispatchSiteCoworkerDelivery,
  fetchCoworkerDeliveryEscalationFederation,
  fetchSiteCoworkerDeliveryEscalationPolicy,
  fetchSiteCoworkerDeliveryEvents,
  fetchSiteCoworkerDeliveryProfiles,
  fetchSiteCoworkerDeliverySla,
  fetchSiteCoworkerPlugins,
  previewSiteCoworkerDelivery,
  reviewSiteCoworkerDeliveryEvent,
  runCoworkerDeliveryEscalationScheduler,
  runSiteCoworkerDeliveryEscalation,
  upsertSiteCoworkerDeliveryEscalationPolicy,
  upsertSiteCoworkerDeliveryProfile,
} from "@/lib/api";
import type {
  SiteCoworkerDeliveryEscalationPolicyResponse,
  SiteCoworkerDeliveryEscalationFederationResponse,
  SiteCoworkerDeliveryEscalationRunResponse,
  SiteCoworkerDeliveryEscalationSchedulerResponse,
  SiteCoworkerDeliveryEventsResponse,
  SiteCoworkerDeliveryPreviewResponse,
  SiteCoworkerDeliveryProfileRow,
  SiteCoworkerDeliverySlaResponse,
  SiteCoworkerPluginListResponse,
  SiteRow,
} from "@/lib/types";

type Props = {
  selectedSite: SiteRow | null;
  canView: boolean;
  canEditPolicy: boolean;
  canApprove: boolean;
};

type ChannelFormState = {
  enabled: boolean;
  min_severity: "low" | "medium" | "high" | "critical";
  delivery_mode: "manual" | "auto";
  require_approval: boolean;
  include_thai_summary: boolean;
  webhook_url: string;
  owner: string;
};

type EscalationFormState = {
  enabled: boolean;
  escalate_after_minutes: number;
  max_escalation_count: number;
  fallback_channels: string;
  escalate_on_statuses: string;
  owner: string;
};

const CHANNELS: Array<"telegram" | "line" | "teams" | "webhook"> = ["telegram", "line", "teams", "webhook"];

function buildChannelForm(profile: SiteCoworkerDeliveryProfileRow): ChannelFormState {
  return {
    enabled: profile.enabled,
    min_severity: profile.min_severity,
    delivery_mode: profile.delivery_mode,
    require_approval: profile.require_approval,
    include_thai_summary: profile.include_thai_summary,
    webhook_url: profile.webhook_url,
    owner: profile.owner,
  };
}

export function CoworkerDeliveryPanel({ selectedSite, canView, canEditPolicy, canApprove }: Props) {
  const [plugins, setPlugins] = useState<SiteCoworkerPluginListResponse | null>(null);
  const [profiles, setProfiles] = useState<SiteCoworkerDeliveryProfileRow[]>([]);
  const [events, setEvents] = useState<SiteCoworkerDeliveryEventsResponse | null>(null);
  const [sla, setSla] = useState<SiteCoworkerDeliverySlaResponse | null>(null);
  const [forms, setForms] = useState<Record<string, ChannelFormState>>({});
  const [selectedPluginCode, setSelectedPluginCode] = useState("");
  const [selectedChannel, setSelectedChannel] = useState<"telegram" | "line" | "teams" | "webhook">("telegram");
  const [preview, setPreview] = useState<SiteCoworkerDeliveryPreviewResponse | null>(null);
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});
  const [escalationPolicy, setEscalationPolicy] = useState<SiteCoworkerDeliveryEscalationPolicyResponse | null>(null);
  const [escalationScheduler, setEscalationScheduler] = useState<SiteCoworkerDeliveryEscalationSchedulerResponse | null>(null);
  const [escalationFederation, setEscalationFederation] = useState<SiteCoworkerDeliveryEscalationFederationResponse | null>(null);
  const [escalationForm, setEscalationForm] = useState<EscalationFormState>({
    enabled: false,
    escalate_after_minutes: 15,
    max_escalation_count: 2,
    fallback_channels: "telegram,line",
    escalate_on_statuses: "approval_required,failed",
    owner: "security",
  });
  const [busyKey, setBusyKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    if (!selectedSite || !canView) {
      setPlugins(null);
      setProfiles([]);
      setEvents(null);
      setSla(null);
      setEscalationFederation(null);
      setForms({});
      setPreview(null);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [federationData, pluginData, profileData, eventData, slaData] = await Promise.all([
        fetchCoworkerDeliveryEscalationFederation({ limit: 200 }),
        fetchSiteCoworkerPlugins(selectedSite.site_id),
        fetchSiteCoworkerDeliveryProfiles(selectedSite.site_id),
        fetchSiteCoworkerDeliveryEvents(selectedSite.site_id, { limit: 20 }),
        fetchSiteCoworkerDeliverySla(selectedSite.site_id, { limit: 100 }),
      ]);
      setEscalationFederation(federationData);
      setPlugins(pluginData);
      setProfiles(profileData.rows || []);
      setEvents(eventData);
      setSla(slaData);
      setForms(
        (profileData.rows || []).reduce<Record<string, ChannelFormState>>((acc, row) => {
          acc[row.channel] = buildChannelForm(row);
          return acc;
        }, {}),
      );
      const installed = (pluginData.rows || []).filter((row) => row.installed);
      if (!selectedPluginCode && installed[0]) {
        setSelectedPluginCode(installed[0].plugin_code);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "coworker_delivery_load_failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [selectedSite?.site_id, canView]);

  const installedPlugins = useMemo(() => (plugins?.rows || []).filter((row) => row.installed), [plugins]);
  const selectedPlugin = useMemo(
    () => installedPlugins.find((row) => row.plugin_code === selectedPluginCode) || installedPlugins[0] || null,
    [installedPlugins, selectedPluginCode],
  );
  const selectedSiteFederationRow = useMemo(
    () => escalationFederation?.rows.find((row) => row.site_id === selectedSite?.site_id) || null,
    [escalationFederation, selectedSite?.site_id],
  );

  useEffect(() => {
    if (!selectedPlugin && installedPlugins[0]) {
      setSelectedPluginCode(installedPlugins[0].plugin_code);
    }
  }, [installedPlugins, selectedPlugin]);

  useEffect(() => {
    const loadEscalation = async () => {
      if (!selectedSite || !canView || !selectedPlugin?.plugin_code) {
        setEscalationPolicy(null);
        return;
      }
      try {
        const response = await fetchSiteCoworkerDeliveryEscalationPolicy(selectedSite.site_id, selectedPlugin.plugin_code);
        setEscalationPolicy(response);
        setEscalationForm({
          enabled: response.policy.enabled,
          escalate_after_minutes: response.policy.escalate_after_minutes,
          max_escalation_count: response.policy.max_escalation_count,
          fallback_channels: (response.policy.fallback_channels || []).join(","),
          escalate_on_statuses: (response.policy.escalate_on_statuses || []).join(","),
          owner: response.policy.owner,
        });
      } catch {
        setEscalationPolicy(null);
      }
    };
    void loadEscalation();
  }, [selectedSite?.site_id, selectedPlugin?.plugin_code, canView]);

  const updateForm = (channel: string, patch: Partial<ChannelFormState>) => {
    setForms((prev) => ({
      ...prev,
      [channel]: {
        ...(prev[channel] || {
          enabled: false,
          min_severity: "medium",
          delivery_mode: "manual",
          require_approval: true,
          include_thai_summary: true,
          webhook_url: "",
          owner: "security",
        }),
        ...patch,
      },
    }));
  };

  const saveProfile = async (channel: "telegram" | "line" | "teams" | "webhook") => {
    if (!selectedSite) return;
    const form = forms[channel];
    if (!form) return;
    setBusyKey(`${channel}:save`);
    setError("");
    setMessage("");
    try {
      const response = await upsertSiteCoworkerDeliveryProfile(selectedSite.site_id, {
        channel,
        enabled: form.enabled,
        min_severity: form.min_severity,
        delivery_mode: form.delivery_mode,
        require_approval: form.require_approval,
        include_thai_summary: form.include_thai_summary,
        webhook_url: form.webhook_url,
        owner: form.owner,
      });
      setMessage(`delivery profile ${response.status}: ${channel}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "coworker_delivery_save_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runPreview = async () => {
    if (!selectedSite || !selectedPlugin) return;
    setBusyKey("preview");
    setError("");
    setMessage("");
    try {
      const response = await previewSiteCoworkerDelivery(selectedSite.site_id, selectedPlugin.plugin_code, {
        channel: selectedChannel,
      });
      setPreview(response);
      setMessage(`preview ready: ${selectedChannel} / ${selectedPlugin.display_name_th}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "coworker_delivery_preview_failed");
    } finally {
      setBusyKey("");
    }
  };

  const dispatchPreview = async (dryRun: boolean) => {
    if (!selectedSite || !selectedPlugin) return;
    setBusyKey(dryRun ? "dispatch:dry" : "dispatch:apply");
    setError("");
    setMessage("");
    try {
      const response = await dispatchSiteCoworkerDelivery(selectedSite.site_id, selectedPlugin.plugin_code, {
        channel: selectedChannel,
        dry_run: dryRun,
        force: false,
        actor: "dashboard_operator",
      });
      setMessage(
        response.status === "approval_required"
          ? `delivery queued for approval: ${selectedChannel}`
          : `delivery ${response.status}: ${selectedChannel}`,
      );
      setPreview({
        status: response.status,
        site_id: response.site_id,
        site_code: response.site_code,
        plugin: response.plugin as SiteCoworkerDeliveryPreviewResponse["plugin"],
        profile: response.profile,
        preview: response.preview,
        run: { run_id: "", status: response.status, created_at: response.event.created_at },
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "coworker_delivery_dispatch_failed");
    } finally {
      setBusyKey("");
    }
  };

  const reviewEvent = async (eventId: string, approve: boolean) => {
    if (!selectedSite) return;
    setBusyKey(`${eventId}:${approve ? "approve" : "reject"}`);
    setError("");
    setMessage("");
    try {
      const response = await reviewSiteCoworkerDeliveryEvent(selectedSite.site_id, eventId, {
        approve,
        actor: "security_reviewer",
        note: reviewNotes[eventId] || "",
      });
      setMessage(`delivery ${response.status}: ${eventId}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "coworker_delivery_review_failed");
    } finally {
      setBusyKey("");
    }
  };

  const saveEscalationPolicy = async () => {
    if (!selectedSite || !selectedPlugin) return;
    setBusyKey("escalation:save");
    setError("");
    setMessage("");
    try {
      const response = await upsertSiteCoworkerDeliveryEscalationPolicy(selectedSite.site_id, {
        plugin_code: selectedPlugin.plugin_code,
        enabled: escalationForm.enabled,
        escalate_after_minutes: escalationForm.escalate_after_minutes,
        max_escalation_count: escalationForm.max_escalation_count,
        fallback_channels: escalationForm.fallback_channels
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean) as Array<"telegram" | "line" | "teams" | "webhook">,
        escalate_on_statuses: escalationForm.escalate_on_statuses
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
        owner: escalationForm.owner,
      });
      setEscalationPolicy(response);
      setMessage(`escalation policy ${response.status}: ${selectedPlugin.plugin_code}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "coworker_delivery_escalation_policy_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runEscalationSweep = async (dryRun: boolean) => {
    if (!selectedSite || !selectedPlugin) return;
    setBusyKey(dryRun ? "escalation:dry" : "escalation:apply");
    setError("");
    setMessage("");
    try {
      const response: SiteCoworkerDeliveryEscalationRunResponse = await runSiteCoworkerDeliveryEscalation(selectedSite.site_id, {
        plugin_code: selectedPlugin.plugin_code,
        dry_run: dryRun,
        actor: "delivery_escalator_ai",
      });
      setMessage(
        `escalation ${response.status}: executed=${response.executed_count} skipped=${response.skipped_count} plugin=${selectedPlugin.plugin_code}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "coworker_delivery_escalation_run_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runEscalationSchedulerSweep = async (dryRun: boolean) => {
    if (!selectedSite || !selectedPlugin) return;
    setBusyKey(dryRun ? "escalation:scheduler:dry" : "escalation:scheduler:apply");
    setError("");
    setMessage("");
    try {
      const response = await runCoworkerDeliveryEscalationScheduler({
        site_id: selectedSite.site_id,
        plugin_code: selectedPlugin.plugin_code,
        limit: 50,
        dry_run_override: dryRun,
        actor: "delivery_escalator_scheduler",
      });
      setEscalationScheduler(response);
      setMessage(
        `escalation scheduler: executed=${response.executed_count} skipped=${response.skipped_count} site=${selectedSite.site_code}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "coworker_delivery_escalation_scheduler_failed");
    } finally {
      setBusyKey("");
    }
  };

  return (
    <section className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">Phase 77 Delivery Layer</h2>
          <p className="mt-1 text-xs text-slate-400 wrap-anywhere">
            Thai-native delivery profiles for AI co-workers. Preview and push plugin output to Telegram, LINE, Teams, or webhook
            without changing the customer workflow.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-md border border-slate-600 px-3 py-2 text-xs text-slate-200 hover:border-slate-400"
        >
          Refresh
        </button>
      </div>

      <p className="mt-2 text-xs text-slate-500 wrap-anywhere">
        Selected site: {selectedSite?.tenant_code || "-"} / {selectedSite?.site_code || "-"} | viewer={String(canView)} policy_editor=
        {String(canEditPolicy)} approver={String(canApprove)}
      </p>
      {loading ? <p className="mt-3 text-sm text-slate-400">Loading delivery profiles...</p> : null}
      {error ? <p className="mt-3 text-sm text-danger wrap-anywhere">{error}</p> : null}
      {message ? <p className="mt-3 text-xs text-accent wrap-anywhere">{message}</p> : null}

      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_360px]">
        <div>
          <div className="grid gap-3 md:grid-cols-2">
            {CHANNELS.map((channel) => {
              const form = forms[channel];
              if (!form) return null;
              return (
                <article key={channel} className="rounded-lg border border-slate-800 bg-panelAlt/20 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-300">{channel}</h3>
                    <span className="rounded-md border border-slate-700 px-2 py-0.5 text-[10px] text-slate-300">
                      {form.delivery_mode}
                    </span>
                  </div>
                  <div className="mt-3 space-y-2 text-[11px] text-slate-300">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.enabled}
                        onChange={(event) => updateForm(channel, { enabled: event.target.checked })}
                      />
                      Enabled
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.require_approval}
                        onChange={(event) => updateForm(channel, { require_approval: event.target.checked })}
                      />
                      Require approval
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={form.include_thai_summary}
                        onChange={(event) => updateForm(channel, { include_thai_summary: event.target.checked })}
                      />
                      Include Thai summary
                    </label>
                  </div>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <label className="text-[11px] text-slate-400">
                      Min Severity
                      <select
                        value={form.min_severity}
                        onChange={(event) =>
                          updateForm(channel, {
                            min_severity: event.target.value as ChannelFormState["min_severity"],
                          })
                        }
                        className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
                      >
                        <option value="low">low</option>
                        <option value="medium">medium</option>
                        <option value="high">high</option>
                        <option value="critical">critical</option>
                      </select>
                    </label>
                    <label className="text-[11px] text-slate-400">
                      Delivery Mode
                      <select
                        value={form.delivery_mode}
                        onChange={(event) =>
                          updateForm(channel, {
                            delivery_mode: event.target.value as ChannelFormState["delivery_mode"],
                          })
                        }
                        className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
                      >
                        <option value="manual">manual</option>
                        <option value="auto">auto</option>
                      </select>
                    </label>
                  </div>
                  {(channel === "teams" || channel === "webhook") ? (
                    <label className="mt-3 block text-[11px] text-slate-400">
                      Webhook URL
                      <input
                        value={form.webhook_url}
                        onChange={(event) => updateForm(channel, { webhook_url: event.target.value })}
                        className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
                      />
                    </label>
                  ) : null}
                  <label className="mt-3 block text-[11px] text-slate-400">
                    Owner
                    <input
                      value={form.owner}
                      onChange={(event) => updateForm(channel, { owner: event.target.value })}
                      className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
                    />
                  </label>
                  <div className="mt-3 flex items-center gap-2">
                    <button
                      type="button"
                      disabled={!canEditPolicy || busyKey === `${channel}:save`}
                      onClick={() => void saveProfile(channel)}
                      className="rounded border border-sky-500/50 bg-sky-500/10 px-2 py-1 text-[11px] font-semibold text-sky-300 hover:bg-sky-500/20 disabled:opacity-60"
                    >
                      Save Profile
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </div>

        <aside className="space-y-4">
          <div className="rounded-lg border border-slate-800 bg-panelAlt/20 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-300">Escalation Policy</h3>
            <p className="mt-2 text-[11px] text-slate-400 wrap-anywhere">
              Selected plugin: {selectedPlugin?.plugin_code || "-"} | policy_status={escalationPolicy?.status || "unloaded"}
            </p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <label className="text-[11px] text-slate-400">
                Escalate After Minutes
                <input
                  type="number"
                  value={escalationForm.escalate_after_minutes}
                  onChange={(event) =>
                    setEscalationForm((prev) => ({ ...prev, escalate_after_minutes: Number(event.target.value || 15) }))
                  }
                  className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
                />
              </label>
              <label className="text-[11px] text-slate-400">
                Max Escalations
                <input
                  type="number"
                  value={escalationForm.max_escalation_count}
                  onChange={(event) =>
                    setEscalationForm((prev) => ({ ...prev, max_escalation_count: Number(event.target.value || 2) }))
                  }
                  className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
                />
              </label>
            </div>
            <label className="mt-3 block text-[11px] text-slate-400">
              Fallback Channels
              <input
                value={escalationForm.fallback_channels}
                onChange={(event) => setEscalationForm((prev) => ({ ...prev, fallback_channels: event.target.value }))}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
              />
            </label>
            <label className="mt-3 block text-[11px] text-slate-400">
              Escalate On Statuses
              <input
                value={escalationForm.escalate_on_statuses}
                onChange={(event) => setEscalationForm((prev) => ({ ...prev, escalate_on_statuses: event.target.value }))}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
              />
            </label>
            <label className="mt-3 flex items-center gap-2 text-[11px] text-slate-300">
              <input
                type="checkbox"
                checked={escalationForm.enabled}
                onChange={(event) => setEscalationForm((prev) => ({ ...prev, enabled: event.target.checked }))}
              />
              Enable escalation
            </label>
            <label className="mt-3 block text-[11px] text-slate-400">
              Owner
              <input
                value={escalationForm.owner}
                onChange={(event) => setEscalationForm((prev) => ({ ...prev, owner: event.target.value }))}
                className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
              />
            </label>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={!canEditPolicy || !selectedPlugin || busyKey === "escalation:save"}
                onClick={() => void saveEscalationPolicy()}
                className="rounded border border-sky-500/50 bg-sky-500/10 px-2 py-1 text-[11px] font-semibold text-sky-300 hover:bg-sky-500/20 disabled:opacity-60"
              >
                Save Escalation Policy
              </button>
              <button
                type="button"
                disabled={!canApprove || !selectedPlugin || busyKey === "escalation:dry"}
                onClick={() => void runEscalationSweep(true)}
                className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
              >
                Dry-Run Escalation
              </button>
              <button
                type="button"
                disabled={!canApprove || !selectedPlugin || busyKey === "escalation:apply"}
                onClick={() => void runEscalationSweep(false)}
                className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] font-semibold text-warning hover:bg-warning/20 disabled:opacity-60"
              >
                Run Escalation
              </button>
              <button
                type="button"
                disabled={!canApprove || !selectedPlugin || busyKey === "escalation:scheduler:dry"}
                onClick={() => void runEscalationSchedulerSweep(true)}
                className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
              >
                Dry-Run Scheduler
              </button>
              <button
                type="button"
                disabled={!canApprove || !selectedPlugin || busyKey === "escalation:scheduler:apply"}
                onClick={() => void runEscalationSchedulerSweep(false)}
                className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] font-semibold text-accent hover:bg-accent/20 disabled:opacity-60"
              >
                Run Scheduler
              </button>
            </div>
            {escalationScheduler ? (
              <div className="mt-3 rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-[11px] text-slate-300">
                <p className="text-slate-100">
                  Scheduler executed={escalationScheduler.executed_count} skipped={escalationScheduler.skipped_count}
                </p>
                <p className="mt-1 text-slate-400">
                  dry_run={String(escalationScheduler.dry_run)} scheduled_policies={escalationScheduler.scheduled_policy_count}
                </p>
              </div>
            ) : null}
          </div>

          <div className="rounded-lg border border-slate-800 bg-panelAlt/20 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-300">Approval SLA</h3>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Pending approvals</p>
                <p className="mt-1 text-lg font-semibold text-slate-100">{sla?.summary.pending_approval_count ?? 0}</p>
              </div>
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Overdue</p>
                <p className="mt-1 text-lg font-semibold text-danger">{sla?.summary.overdue_count ?? 0}</p>
              </div>
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Reviewed</p>
                <p className="mt-1 text-lg font-semibold text-slate-100">{sla?.summary.approved_or_reviewed_count ?? 0}</p>
              </div>
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Avg latency</p>
                <p className="mt-1 text-lg font-semibold text-warning">
                  {Math.round(sla?.summary.average_approval_latency_seconds ?? 0)}s
                </p>
              </div>
            </div>
            {(sla?.pending_rows || []).length > 0 ? (
              <div className="mt-3 max-h-48 space-y-2 overflow-auto">
                {(sla?.pending_rows || []).map((row) => (
                  <div key={row.event_id} className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                    <p className="text-slate-100 wrap-anywhere">
                      [{row.channel}] {row.title}
                    </p>
                    <p className={`mt-1 wrap-anywhere ${row.overdue ? "text-danger" : "text-slate-400"}`}>
                      due_at={row.due_at}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-xs text-slate-500">No pending delivery approvals.</p>
            )}
          </div>

          <div className="rounded-lg border border-slate-800 bg-panelAlt/20 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-300">Federation Escalation Posture</h3>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Healthy Sites</p>
                <p className="mt-1 text-lg font-semibold text-accent">{escalationFederation?.summary.healthy_sites ?? 0}</p>
              </div>
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Attention Sites</p>
                <p className="mt-1 text-lg font-semibold text-warning">{escalationFederation?.summary.attention_sites ?? 0}</p>
              </div>
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Pending Total</p>
                <p className="mt-1 text-lg font-semibold text-slate-100">{escalationFederation?.summary.pending_approval_total ?? 0}</p>
              </div>
              <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-400">Overdue Total</p>
                <p className="mt-1 text-lg font-semibold text-danger">{escalationFederation?.summary.overdue_total ?? 0}</p>
              </div>
            </div>
            {selectedSiteFederationRow ? (
              <div className="mt-3 rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="font-semibold text-slate-100">
                  {selectedSiteFederationRow.site_code} [{selectedSiteFederationRow.status}]
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">
                  enabled_profiles={selectedSiteFederationRow.enabled_profile_count} auto_profiles=
                  {selectedSiteFederationRow.auto_profile_count} escalation_policies=
                  {selectedSiteFederationRow.enabled_escalation_policy_count}
                </p>
                <p className="mt-1 text-slate-400 wrap-anywhere">
                  pending={selectedSiteFederationRow.pending_approval_count} overdue={selectedSiteFederationRow.overdue_count} avg_latency=
                  {selectedSiteFederationRow.average_approval_latency_seconds}s
                </p>
                <p className="mt-1 text-slate-500 wrap-anywhere">{selectedSiteFederationRow.recommended_action}</p>
              </div>
            ) : (
              <p className="mt-3 text-xs text-slate-500">No federation posture available for the selected site yet.</p>
            )}
          </div>

          <div className="rounded-lg border border-slate-800 bg-panelAlt/20 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-300">Thai Delivery Preview</h3>
            <div className="mt-3 grid gap-2">
              <label className="text-[11px] text-slate-400">
                Plugin
                <select
                  value={selectedPlugin?.plugin_code || ""}
                  onChange={(event) => setSelectedPluginCode(event.target.value)}
                  className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
                >
                  {(installedPlugins || []).map((row) => (
                    <option key={row.plugin_code} value={row.plugin_code}>
                      {row.display_name_th}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-[11px] text-slate-400">
                Channel
                <select
                  value={selectedChannel}
                  onChange={(event) => setSelectedChannel(event.target.value as typeof selectedChannel)}
                  className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
                >
                  {CHANNELS.map((channel) => (
                    <option key={channel} value={channel}>
                      {channel}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                type="button"
                disabled={!selectedPlugin || busyKey === "preview"}
                onClick={() => void runPreview()}
                className="rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] font-semibold text-warning hover:bg-warning/20 disabled:opacity-60"
              >
                Build Thai Preview
              </button>
              <button
                type="button"
                disabled={!selectedPlugin || !canApprove || busyKey === "dispatch:dry"}
                onClick={() => void dispatchPreview(true)}
                className="rounded border border-slate-600 px-2 py-1 text-[11px] text-slate-200 hover:border-slate-400 disabled:opacity-60"
              >
                Dry-Run Dispatch
              </button>
              <button
                type="button"
                disabled={!selectedPlugin || !canApprove || busyKey === "dispatch:apply"}
                onClick={() => void dispatchPreview(false)}
                className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] font-semibold text-accent hover:bg-accent/20 disabled:opacity-60"
              >
                Send Now
              </button>
            </div>

            {preview ? (
              <div className="mt-3 rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <p className="text-slate-200 wrap-anywhere">
                  {preview.preview.channel} / {preview.preview.severity} / {preview.preview.title}
                </p>
                <pre className="mt-2 whitespace-pre-wrap break-words text-slate-300">{preview.preview.message}</pre>
              </div>
            ) : (
              <p className="mt-3 text-xs text-slate-500">No preview yet.</p>
            )}
          </div>

          <div className="rounded-lg border border-slate-800 bg-panelAlt/20 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-300">Delivery Event Feed</h3>
            <div className="mt-3 max-h-[420px] overflow-auto space-y-2">
              {(events?.rows || []).length === 0 ? <p className="text-xs text-slate-500">No delivery events yet.</p> : null}
              {(events?.rows || []).map((row) => (
                <div key={row.event_id} className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                  <p className="text-slate-100 wrap-anywhere">
                    {row.display_name_th || row.plugin_code} [{row.channel}] [{row.status}]
                  </p>
                  <p className="mt-1 text-slate-400 wrap-anywhere">
                    severity={row.severity} dry_run={String(row.dry_run)} actor={row.actor}
                  </p>
                  <p className="mt-1 text-slate-300 wrap-anywhere">{row.title}</p>
                  {row.approval_required && row.status === "approval_required" ? (
                    <div className="mt-2 space-y-2">
                      <input
                        value={reviewNotes[row.event_id] || ""}
                        onChange={(event) =>
                          setReviewNotes((prev) => ({
                            ...prev,
                            [row.event_id]: event.target.value,
                          }))
                        }
                        placeholder="review note"
                        className="w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-[11px] text-slate-100"
                      />
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          disabled={!canApprove || busyKey === `${row.event_id}:approve`}
                          onClick={() => void reviewEvent(row.event_id, true)}
                          className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] font-semibold text-accent hover:bg-accent/20 disabled:opacity-60"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          disabled={!canApprove || busyKey === `${row.event_id}:reject`}
                          onClick={() => void reviewEvent(row.event_id, false)}
                          className="rounded border border-danger/60 bg-danger/10 px-2 py-1 text-[11px] font-semibold text-danger hover:bg-danger/20 disabled:opacity-60"
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}
