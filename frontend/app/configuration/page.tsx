"use client";

import { useEffect, useState } from "react";

import {
  createPhaseScopeCheck,
  fetchCompetitiveObjectives,
  fetchIntegrationAdapters,
  fetchSites,
  ingestIntegrationEvent,
  upsertSite,
  upsertThreatContentPack,
} from "@/lib/api";
import type { CompetitiveObjectivesResponse, IntegrationAdaptersResponse, SiteRow } from "@/lib/types";

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

export default function ConfigurationPage() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [rows, setRows] = useState<SiteRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [adapters, setAdapters] = useState<IntegrationAdaptersResponse | null>(null);
  const [objectives, setObjectives] = useState<CompetitiveObjectivesResponse | null>(null);

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
    void fetchCompetitiveObjectives().then(setObjectives).catch(() => undefined);
  }, []);

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

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <header className="mb-5">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Configuration</p>
        <h1 className="mt-1 text-2xl font-bold text-ink sm:text-3xl">Customer Sites Settings</h1>
        <p className="mt-2 text-sm text-slate-400">Add/update customer site records. Data is persisted and loaded from DB.</p>
      </header>

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
