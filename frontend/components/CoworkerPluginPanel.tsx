import { useEffect, useMemo, useState } from "react";

import {
  fetchCoworkerPlugins,
  fetchSiteCoworkerPluginRuns,
  fetchSiteCoworkerPlugins,
  runCoworkerPluginScheduler,
  runSiteCoworkerPlugin,
  upsertSiteCoworkerPluginBinding,
} from "@/lib/api";
import type {
  CoworkerPluginCatalogResponse,
  SiteCoworkerPluginListResponse,
  SiteCoworkerPluginRow,
  SiteCoworkerPluginRunListResponse,
  SiteRow,
} from "@/lib/types";

type Props = {
  selectedSite: SiteRow | null;
  canView: boolean;
  canEditPolicy: boolean;
  canApprove: boolean;
  fixedCategory?: "red" | "blue" | "purple";
};

type BindingFormState = {
  enabled: boolean;
  auto_run: boolean;
  schedule_interval_minutes: number;
  notify_channels: string;
  owner: string;
  configText: string;
};

const CATEGORY_OPTIONS = [
  { value: "", label: "all" },
  { value: "red", label: "red" },
  { value: "blue", label: "blue" },
  { value: "purple", label: "purple" },
];

const CATEGORY_ORDER = ["red", "blue", "purple"];

function categoryClass(category: string): string {
  switch (category) {
    case "red":
      return "border-danger/60 bg-danger/10 text-danger";
    case "blue":
      return "border-sky-400/50 bg-sky-500/10 text-sky-300";
    case "purple":
      return "border-warning/60 bg-warning/10 text-warning";
    default:
      return "border-slate-600 bg-panelAlt/30 text-slate-300";
  }
}

function buildBindingForm(row: SiteCoworkerPluginRow): BindingFormState {
  const config = row.binding?.config || row.default_config || {};
  return {
    enabled: Boolean(row.binding?.enabled),
    auto_run: Boolean(row.binding?.auto_run),
    schedule_interval_minutes: row.binding?.schedule_interval_minutes ?? 60,
    notify_channels: (row.binding?.notify_channels || []).join(","),
    owner: row.binding?.owner || "security",
    configText: JSON.stringify(config, null, 2),
  };
}

function compactSummary(value: unknown): string {
  if (typeof value === "string") return value;
  if (value === null || value === undefined) return "";
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function categoryHeading(category: string): string {
  switch (category) {
    case "red":
      return "Red Plugins Category";
    case "blue":
      return "Blue Plugins Category";
    case "purple":
      return "Purple Plugins Category";
    default:
      return "Other Plugins Category";
  }
}

export function CoworkerPluginPanel({ selectedSite, canView, canEditPolicy, canApprove, fixedCategory }: Props) {
  const [catalog, setCatalog] = useState<CoworkerPluginCatalogResponse | null>(null);
  const [plugins, setPlugins] = useState<SiteCoworkerPluginListResponse | null>(null);
  const [runs, setRuns] = useState<SiteCoworkerPluginRunListResponse | null>(null);
  const [bindingForms, setBindingForms] = useState<Record<string, BindingFormState>>({});
  const [categoryFilter, setCategoryFilter] = useState(fixedCategory || "");
  const [loading, setLoading] = useState(false);
  const [busyKey, setBusyKey] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    if (!selectedSite || !canView) {
      setCatalog(null);
      setPlugins(null);
      setRuns(null);
      setBindingForms({});
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [catalogData, pluginData, runData] = await Promise.all([
        fetchCoworkerPlugins({ active_only: true }),
        fetchSiteCoworkerPlugins(selectedSite.site_id, { category: fixedCategory || categoryFilter || undefined }),
        fetchSiteCoworkerPluginRuns(selectedSite.site_id, { category: fixedCategory || categoryFilter || undefined, limit: 20 }),
      ]);
      setCatalog(catalogData);
      setPlugins(pluginData);
      setRuns(runData);
      setBindingForms(
        pluginData.rows.reduce<Record<string, BindingFormState>>((acc, row) => {
          acc[row.plugin_code] = buildBindingForm(row);
          return acc;
        }, {}),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "coworker_plugin_load_failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [selectedSite?.site_id, categoryFilter, canView, fixedCategory]);

  const latestRunByPlugin = useMemo(() => {
    const map = new Map<string, SiteCoworkerPluginRunListResponse["rows"][number]>();
    for (const row of runs?.rows || []) {
      if (!map.has(row.plugin_code)) {
        map.set(row.plugin_code, row);
      }
    }
    return map;
  }, [runs]);

  const pluginStats = useMemo(() => {
    const rows = plugins?.rows || [];
    return {
      catalog: catalog?.count || 0,
      installed: rows.filter((row) => row.installed).length,
      autoRun: rows.filter((row) => Boolean(row.binding?.auto_run)).length,
      recentRuns: runs?.count || 0,
    };
  }, [catalog, plugins, runs]);

  const groupedRows = useMemo(() => {
    const rows = plugins?.rows || [];
    const groups = new Map<string, SiteCoworkerPluginRow[]>();
    for (const row of rows) {
      const key = row.category || "other";
      const current = groups.get(key) || [];
      current.push(row);
      groups.set(key, current);
    }
    return [...CATEGORY_ORDER, ...Array.from(groups.keys()).filter((key) => !CATEGORY_ORDER.includes(key))]
      .filter((key) => (groups.get(key) || []).length > 0)
      .map((key) => ({
        category: key,
        rows: groups.get(key) || [],
      }));
  }, [plugins]);

  const updateForm = (pluginCode: string, patch: Partial<BindingFormState>) => {
    setBindingForms((prev) => ({
      ...prev,
      [pluginCode]: {
        ...(prev[pluginCode] || {
          enabled: false,
          auto_run: false,
          schedule_interval_minutes: 60,
          notify_channels: "",
          owner: "security",
          configText: "{}",
        }),
        ...patch,
      },
    }));
  };

  const saveBinding = async (row: SiteCoworkerPluginRow) => {
    if (!selectedSite) return;
    const form = bindingForms[row.plugin_code] || buildBindingForm(row);
    let config: Record<string, unknown> = {};
    try {
      config = JSON.parse(form.configText || "{}") as Record<string, unknown>;
    } catch {
      setError(`Invalid JSON config for ${row.plugin_code}`);
      return;
    }
    setBusyKey(`${row.plugin_code}:save`);
    setError("");
    setMessage("");
    try {
      const autoRun = row.execution_mode === "scheduled" ? form.auto_run : false;
      const response = await upsertSiteCoworkerPluginBinding(selectedSite.site_id, {
        plugin_code: row.plugin_code,
        enabled: form.enabled,
        auto_run: autoRun,
        schedule_interval_minutes: form.schedule_interval_minutes,
        notify_channels: form.notify_channels
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
        config,
        owner: form.owner,
      });
      setMessage(`${response.status}: ${row.display_name_th}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "coworker_plugin_save_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runPlugin = async (row: SiteCoworkerPluginRow, dryRun: boolean) => {
    if (!selectedSite) return;
    setBusyKey(`${row.plugin_code}:run:${dryRun ? "dry" : "apply"}`);
    setError("");
    setMessage("");
    try {
      const response = await runSiteCoworkerPlugin(selectedSite.site_id, row.plugin_code, {
        dry_run: dryRun,
        force: !dryRun,
        actor: "dashboard_operator",
      });
      const headline = compactSummary(response.run.output_summary?.headline);
      setMessage(`${row.display_name_th}: ${response.status}${headline ? ` | ${headline}` : ""}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "coworker_plugin_run_failed");
    } finally {
      setBusyKey("");
    }
  };

  const runScheduler = async () => {
    setBusyKey("scheduler");
    setError("");
    setMessage("");
    try {
      const response = await runCoworkerPluginScheduler({
        limit: 200,
        dry_run_override: true,
        actor: "dashboard_scheduler",
      });
      setMessage(
        `scheduler bindings=${response.scheduled_binding_count} executed=${response.executed_count} skipped=${response.skipped_count}`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "coworker_scheduler_failed");
    } finally {
      setBusyKey("");
    }
  };

  if (!selectedSite) {
    return (
      <section className="card p-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">AI Co-worker Plugins</h2>
        </div>
        <p className="mt-1 text-xs text-slate-400">
          Plugin-first intelligence layer for Red, Blue, and Purple tasks without replacing the customer workflow.
        </p>
        <p className="mt-3 text-xs text-slate-500">Select a site to install and run AI co-worker plugins.</p>
      </section>
    );
  }

  return (
    <section className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">AI Co-worker Plugins</h2>
          <p className="mt-1 text-xs text-slate-400 wrap-anywhere">
            Plugin-first intelligence layer for Thai-friendly cyber workflows. Install per-site helpers, keep the customer stack,
            and let AI handle repetitive triage, templating, and reporting.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {!fixedCategory ? (
            <select
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
              className="rounded-md border border-slate-700 bg-panelAlt/40 px-3 py-2 text-xs text-slate-100"
            >
              {CATEGORY_OPTIONS.map((option) => (
                <option key={option.value || "all"} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          ) : (
            <span className={`rounded-full border px-3 py-2 text-xs font-semibold uppercase ${categoryClass(fixedCategory)}`}>
              {fixedCategory} only
            </span>
          )}
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-md border border-slate-600 px-3 py-2 text-xs text-slate-200 hover:border-slate-400"
          >
            Refresh
          </button>
          <button
            type="button"
            disabled={!canApprove || busyKey === "scheduler"}
            onClick={() => void runScheduler()}
            className="rounded-md border border-accent/60 bg-accent/10 px-3 py-2 text-xs font-semibold text-accent hover:bg-accent/20 disabled:opacity-60"
          >
            Dry-Run Scheduler
          </button>
        </div>
      </div>

      <p className="mt-2 text-xs text-slate-500 wrap-anywhere">
        Selected site: {selectedSite.tenant_code}/{selectedSite.site_code} | viewer={String(canView)} policy_editor=
        {String(canEditPolicy)} approver={String(canApprove)}
      </p>
      {loading ? <p className="mt-3 text-sm text-slate-400">Loading plugin catalog...</p> : null}
      {error ? <p className="mt-3 text-sm text-danger wrap-anywhere">{error}</p> : null}
      {message ? <p className="mt-3 text-xs text-accent wrap-anywhere">{message}</p> : null}

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3">
          <p className="text-[11px] uppercase tracking-widest text-slate-400">Catalog</p>
          <p className="mt-2 text-2xl font-semibold text-slate-100">{pluginStats.catalog}</p>
        </div>
        <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3">
          <p className="text-[11px] uppercase tracking-widest text-slate-400">Installed</p>
          <p className="mt-2 text-2xl font-semibold text-slate-100">{pluginStats.installed}</p>
        </div>
        <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3">
          <p className="text-[11px] uppercase tracking-widest text-slate-400">Auto-Run</p>
          <p className="mt-2 text-2xl font-semibold text-accent">{pluginStats.autoRun}</p>
        </div>
        <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-3">
          <p className="text-[11px] uppercase tracking-widest text-slate-400">Recent Runs</p>
          <p className="mt-2 text-2xl font-semibold text-slate-100">{pluginStats.recentRuns}</p>
        </div>
      </div>

      <div className="mt-4 space-y-4">
        <div className="rounded-lg border border-slate-800 bg-panelAlt/20 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-300">What This Plugin Page Covers</h3>
          <div className="mt-3 space-y-2 text-xs text-slate-300">
            <p className="wrap-anywhere">1. Site-level plugin binding, ownership, scheduler interval, and config JSON.</p>
            <p className="wrap-anywhere">2. Manual dry-run/apply execution of plugins in the selected category.</p>
            <p className="wrap-anywhere">3. Recent plugin output so operators can validate AI behavior without leaving the category page.</p>
          </div>
        </div>

        <div className="space-y-5">
          {(plugins?.rows || []).length === 0 ? (
            <div className="rounded-md border border-slate-800 bg-panelAlt/25 p-4 text-xs text-slate-500">
              No plugins available for this site/category.
            </div>
          ) : null}
          {groupedRows.map((group) => (
            <div key={group.category} className="space-y-3">
              <div className="rounded-lg border border-slate-800 bg-panelAlt/15 px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase ${categoryClass(group.category)}`}>
                    {group.category}
                  </span>
                  <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-200">
                    {categoryHeading(group.category)}
                  </h3>
                </div>
                <p className="mt-1 text-[11px] text-slate-400 wrap-anywhere">
                  {group.category === "red"
                    ? "Red plugins accelerate validation, exploit-template creation, and active testing support."
                    : group.category === "blue"
                      ? "Blue plugins reduce alert noise, translate context to Thai, and speed operational response."
                      : "Purple plugins generate compliance, executive, and cross-team reporting outputs."}
                </p>
              </div>
              {group.rows.map((row) => {
                const form = bindingForms[row.plugin_code] || buildBindingForm(row);
                const latestRun = latestRunByPlugin.get(row.plugin_code);
                const latestHeadline = compactSummary(latestRun?.output_summary?.headline);
                const latestSummary = compactSummary(latestRun?.output_summary?.summary_th);
                const schedulerCapable = row.execution_mode === "scheduled";
                return (
                  <article key={row.plugin_code} className="rounded-lg border border-slate-800 bg-panelAlt/20 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-sm font-semibold text-slate-100 wrap-anywhere">{row.display_name_th}</h3>
                          <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase ${categoryClass(row.category)}`}>
                            {row.category}
                          </span>
                          <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[10px] uppercase text-slate-300">
                            {row.execution_mode}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-slate-400 wrap-anywhere">
                          {row.display_name} · {row.plugin_kind} · {row.plugin_code}
                        </p>
                      </div>
                      <div className="rounded-md border border-slate-700 bg-panelAlt/30 px-2 py-1 text-[11px] text-slate-300">
                        installed={String(row.installed)}
                      </div>
                    </div>

                    <p className="mt-3 text-xs text-slate-200 wrap-anywhere">{row.value_statement}</p>
                    <p className="mt-1 text-[11px] text-slate-400 wrap-anywhere">{row.description}</p>

                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <label className="rounded-md border border-slate-800 bg-panelAlt/20 p-2 text-[11px] text-slate-400">
                        Schedule Minutes
                        <input
                          type="number"
                          min={5}
                          max={1440}
                          disabled={!schedulerCapable}
                          value={form.schedule_interval_minutes}
                          onChange={(event) =>
                            updateForm(row.plugin_code, {
                              schedule_interval_minutes: Number(event.target.value || 60),
                            })
                          }
                          className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100 disabled:opacity-50"
                        />
                      </label>
                      <label className="rounded-md border border-slate-800 bg-panelAlt/20 p-2 text-[11px] text-slate-400">
                        Notify Channels
                        <input
                          value={form.notify_channels}
                          onChange={(event) => updateForm(row.plugin_code, { notify_channels: event.target.value })}
                          placeholder="telegram,line"
                          className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
                        />
                      </label>
                      <label className="rounded-md border border-slate-800 bg-panelAlt/20 p-2 text-[11px] text-slate-400">
                        Owner
                        <input
                          value={form.owner}
                          onChange={(event) => updateForm(row.plugin_code, { owner: event.target.value })}
                          className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
                        />
                      </label>
                      <div className="rounded-md border border-slate-800 bg-panelAlt/20 p-2 text-[11px] text-slate-300">
                        <label className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={form.enabled}
                            onChange={(event) => updateForm(row.plugin_code, { enabled: event.target.checked })}
                          />
                          Enable plugin on this site
                        </label>
                        <label className="mt-2 flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={form.auto_run}
                            disabled={!schedulerCapable}
                            onChange={(event) => updateForm(row.plugin_code, { auto_run: event.target.checked })}
                          />
                          Auto-run via scheduler
                        </label>
                      </div>
                    </div>

                    <label className="mt-3 block text-[11px] text-slate-400">
                      Plugin Config JSON
                      <textarea
                        rows={6}
                        value={form.configText}
                        onChange={(event) => updateForm(row.plugin_code, { configText: event.target.value })}
                        className="mt-1 min-h-[120px] w-full rounded border border-slate-700 bg-panelAlt/40 px-3 py-2 font-mono text-[11px] text-slate-100 wrap-anywhere"
                      />
                    </label>

                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        disabled={!canEditPolicy || busyKey === `${row.plugin_code}:save`}
                        onClick={() => void saveBinding(row)}
                        className="rounded-md border border-sky-500/50 bg-sky-500/10 px-3 py-2 text-xs font-semibold text-sky-300 hover:bg-sky-500/20 disabled:opacity-60"
                      >
                        Save Binding
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey === `${row.plugin_code}:run:dry`}
                        onClick={() => void runPlugin(row, true)}
                        className="rounded-md border border-warning/60 bg-warning/10 px-3 py-2 text-xs font-semibold text-warning hover:bg-warning/20 disabled:opacity-60"
                      >
                        Dry Run
                      </button>
                      <button
                        type="button"
                        disabled={!canApprove || busyKey === `${row.plugin_code}:run:apply`}
                        onClick={() => void runPlugin(row, false)}
                        className="rounded-md border border-accent/60 bg-accent/10 px-3 py-2 text-xs font-semibold text-accent hover:bg-accent/20 disabled:opacity-60"
                      >
                        Apply Run
                      </button>
                    </div>

                    {latestRun ? (
                      <div className="mt-3 rounded-md border border-slate-800 bg-panelAlt/20 p-3 text-xs">
                        <p className="text-slate-200 wrap-anywhere">
                          Latest Run: {latestRun.created_at} [{latestRun.status}] dry_run={String(latestRun.dry_run)} routed=
                          {String(latestRun.alert_routed)}
                        </p>
                        {latestHeadline ? <p className="mt-1 text-slate-300 wrap-anywhere">{latestHeadline}</p> : null}
                        {latestSummary ? <p className="mt-1 text-slate-400 wrap-anywhere">{latestSummary}</p> : null}
                      </div>
                    ) : null}
                  </article>
                );
              })}
            </div>
          ))}
        </div>

        <div className="rounded-lg border border-slate-800 bg-panelAlt/20 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-300">Recent Plugin Output</h3>
          <div className="mt-3 max-h-[520px] overflow-auto space-y-2">
            {(runs?.rows || []).length === 0 ? <p className="text-xs text-slate-500">No plugin runs for this site yet.</p> : null}
            {(runs?.rows || []).map((row) => (
              <div key={row.run_id} className="rounded-md border border-slate-800 bg-panelAlt/25 p-3 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase ${categoryClass(row.category)}`}>
                    {row.category}
                  </span>
                  <span className="text-slate-400 wrap-anywhere">{row.created_at}</span>
                </div>
                <p className="mt-2 text-slate-100 wrap-anywhere">
                  {row.display_name_th} [{row.status}]
                </p>
                <p className="mt-1 text-slate-300 wrap-anywhere">{compactSummary(row.output_summary?.headline)}</p>
                <p className="mt-1 text-slate-400 wrap-anywhere">{compactSummary(row.output_summary?.summary_th)}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
