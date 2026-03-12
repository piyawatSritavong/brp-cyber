import { useEffect, useState } from "react";

import {
  approveSoarExecution,
  executeSoarPlaybook,
  fetchSiteSoarExecutions,
  fetchSoarMarketplaceOverview,
  fetchSoarPlaybooks,
  fetchTenantPlaybookPolicy,
  upsertTenantPlaybookPolicy,
  upsertSoarPlaybook,
} from "@/lib/api";
import type { SiteRow, SoarExecutionListResponse, SoarMarketplaceOverview, SoarPlaybookListResponse } from "@/lib/types";

type Props = {
  selectedSite: SiteRow | null;
  canView: boolean;
  canEditPolicy: boolean;
  canApprove: boolean;
};

export function SOARPlaybookPanel({ selectedSite, canView, canEditPolicy, canApprove }: Props) {
  const [playbooks, setPlaybooks] = useState<SoarPlaybookListResponse | null>(null);
  const [executions, setExecutions] = useState<SoarExecutionListResponse | null>(null);
  const [overview, setOverview] = useState<SoarMarketplaceOverview | null>(null);
  const [policySummary, setPolicySummary] = useState<string>("No tenant policy loaded");
  const [delegatedApproversInput, setDelegatedApproversInput] = useState("security_lead,ciso_ai");
  const [blockedCodesInput, setBlockedCodesInput] = useState("");
  const [allowPartnerScope, setAllowPartnerScope] = useState(true);
  const [autoApproveDryRun, setAutoApproveDryRun] = useState(true);
  const [containmentNeedsApproval, setContainmentNeedsApproval] = useState(true);
  const [partnerNeedsApproval, setPartnerNeedsApproval] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const [pb, ov, ex] = await Promise.all([
        fetchSoarPlaybooks({ active_only: true, limit: 50 }),
        fetchSoarMarketplaceOverview(500),
        selectedSite ? fetchSiteSoarExecutions(selectedSite.site_id, { limit: 30 }) : Promise.resolve({ count: 0, rows: [] }),
      ]);
      setPlaybooks(pb);
      setOverview(ov);
      setExecutions(ex);
      if (selectedSite?.tenant_code && canView) {
        const policy = await fetchTenantPlaybookPolicy(selectedSite.tenant_code);
        const delegated = policy.policy.delegated_approvers || [];
        const blocked = policy.policy.blocked_playbook_codes || [];
        const approvalByScope = policy.policy.require_approval_by_scope || {};
        const approvalByCategory = policy.policy.require_approval_by_category || {};
        setDelegatedApproversInput(delegated.join(","));
        setBlockedCodesInput(blocked.join(","));
        setAllowPartnerScope(Boolean(policy.policy.allow_partner_scope));
        setAutoApproveDryRun(Boolean(policy.policy.auto_approve_dry_run));
        setContainmentNeedsApproval(Boolean(approvalByCategory.containment));
        setPartnerNeedsApproval(Boolean(approvalByScope.partner));
        setPolicySummary(
          `v${policy.policy.policy_version} owner=${policy.policy.owner} delegated=${delegated.length} blocked=${blocked.length}`,
        );
      } else {
        setPolicySummary(canView ? "No tenant selected" : "No permission to view tenant policy");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "soar_load_failed");
    }
  };

  useEffect(() => {
    void load();
    const timer = setInterval(() => void load(), 15000);
    return () => clearInterval(timer);
  }, [selectedSite?.site_id]);

  const seedDefaultPlaybooks = async () => {
    setBusy(true);
    setError("");
    try {
      await upsertSoarPlaybook({
        playbook_code: "isolate-host-fast",
        title: "Isolate Host Fast",
        category: "containment",
        description: "Isolate suspicious host and restrict lateral movement quickly.",
        version: "1.0.0",
        scope: "community",
        steps: ["validate_alert_context", "isolate_endpoint", "notify_soc_channel", "collect_forensics_snapshot"],
        action_policy: { approval_required: true, rollback_supported: true },
        is_active: true,
      });
      await upsertSoarPlaybook({
        playbook_code: "block-ip-and-waf-tighten",
        title: "Block IP + Tighten WAF",
        category: "response",
        description: "Block high-risk source IP and tighten WAF challenge threshold.",
        version: "1.0.0",
        scope: "partner",
        steps: ["validate_ip_risk", "block_ip_firewall", "tighten_waf_rule", "open_case_ticket"],
        action_policy: { approval_required: true, rollback_supported: true },
        is_active: true,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "seed_playbook_failed");
    } finally {
      setBusy(false);
    }
  };

  const runPlaybook = async (playbookCode: string) => {
    if (!selectedSite) return;
    setBusy(true);
    setError("");
    try {
      await executeSoarPlaybook(selectedSite.site_id, playbookCode, {
        actor: "ai_orchestrator",
        require_approval: true,
        dry_run: true,
        params: { reason: "auto_suggest_from_blue_signal" },
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "run_playbook_failed");
    } finally {
      setBusy(false);
    }
  };

  const savePolicyMatrix = async () => {
    if (!selectedSite?.tenant_code) {
      setError("No tenant_code on selected site");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const delegated = delegatedApproversInput
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
      const blocked = blockedCodesInput
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean);
      await upsertTenantPlaybookPolicy({
        tenant_code: selectedSite.tenant_code,
        policy_version: "1.1",
        owner: "phase66",
        require_approval_by_scope: { partner: partnerNeedsApproval, private: true, community: false },
        require_approval_by_category: { containment: containmentNeedsApproval },
        delegated_approvers: delegated,
        blocked_playbook_codes: blocked,
        allow_partner_scope: allowPartnerScope,
        auto_approve_dry_run: autoApproveDryRun,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "save_policy_matrix_failed");
    } finally {
      setBusy(false);
    }
  };

  const approveExecution = async (executionId: string, approve: boolean) => {
    setBusy(true);
    setError("");
    try {
      await approveSoarExecution(executionId, {
        approve,
        approver: "security_lead",
        note: approve ? "approved for production-safe action" : "rejected by reviewer",
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "approve_playbook_failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300">SOAR Playbook Hub</h2>
        <button
          type="button"
          disabled={busy || !canEditPolicy}
          onClick={() => void seedDefaultPlaybooks()}
          className="rounded-md border border-accent/60 bg-accent/15 px-3 py-1.5 text-xs text-accent hover:bg-accent/25 disabled:opacity-60"
        >
          Seed Default Playbooks
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-400">Marketplace + approval lifecycle for one-click response automation.</p>
      <p className="mt-1 text-xs text-slate-500">
        RBAC: viewer={String(canView)} policy_editor={String(canEditPolicy)} approver={String(canApprove)}
      </p>
      {error ? <p className="mt-2 text-sm text-danger">{error}</p> : null}

      {overview ? (
        <p className="mt-2 text-xs text-slate-300 wrap-anywhere">
          total={overview.total_playbooks} active={overview.active_playbooks} scopes={JSON.stringify(overview.scope_counts)}
        </p>
      ) : null}
      <div className="mt-2 rounded border border-slate-800 bg-panelAlt/20 p-2 text-xs">
        <p className="text-slate-300">Tenant Policy Matrix</p>
        <p className="mt-1 text-slate-400 wrap-anywhere">{policySummary}</p>
        <label className="mt-2 block text-slate-400">
          Delegated Approvers (comma separated)
          <input
            value={delegatedApproversInput}
            onChange={(event) => setDelegatedApproversInput(event.target.value)}
            className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
          />
        </label>
        <label className="mt-2 block text-slate-400">
          Blocked Playbook Codes
          <input
            value={blockedCodesInput}
            onChange={(event) => setBlockedCodesInput(event.target.value)}
            className="mt-1 w-full rounded border border-slate-700 bg-panelAlt/40 px-2 py-1 text-xs text-slate-100"
          />
        </label>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-slate-300">
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={allowPartnerScope} onChange={(event) => setAllowPartnerScope(event.target.checked)} />
            allow partner scope
          </label>
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={autoApproveDryRun} onChange={(event) => setAutoApproveDryRun(event.target.checked)} />
            auto-approve dry-run
          </label>
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={partnerNeedsApproval}
              onChange={(event) => setPartnerNeedsApproval(event.target.checked)}
            />
            partner needs approval
          </label>
          <label className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={containmentNeedsApproval}
              onChange={(event) => setContainmentNeedsApproval(event.target.checked)}
            />
            containment needs approval
          </label>
        </div>
        <button
          type="button"
          disabled={!selectedSite || busy || !canEditPolicy}
          onClick={() => void savePolicyMatrix()}
          className="mt-2 rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
        >
          Save Policy Matrix
        </button>
      </div>

      <div className="mt-3 max-h-44 overflow-auto rounded border border-slate-800 p-2 text-xs">
        <p className="mb-2 text-slate-400">Available Playbooks</p>
        {(playbooks?.rows || []).length === 0 ? <p className="text-slate-500">No playbooks yet.</p> : null}
        {(playbooks?.rows || []).map((pb) => (
          <div key={pb.playbook_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">{pb.title}</p>
            <p className="mt-1 text-slate-400 wrap-anywhere">
              code={pb.playbook_code} scope={pb.scope} v{pb.version}
            </p>
            <button
              type="button"
              disabled={!selectedSite || busy || !canApprove}
              onClick={() => void runPlaybook(pb.playbook_code)}
              className="mt-2 rounded border border-warning/60 bg-warning/10 px-2 py-1 text-[11px] text-warning hover:bg-warning/20 disabled:opacity-60"
            >
              Execute Dry-Run
            </button>
          </div>
        ))}
      </div>

      <div className="mt-3 max-h-44 overflow-auto rounded border border-slate-800 p-2 text-xs">
        <p className="mb-2 text-slate-400">Execution Queue (Selected Site)</p>
        {(executions?.rows || []).length === 0 ? <p className="text-slate-500">No executions yet.</p> : null}
        {(executions?.rows || []).map((ex) => (
          <div key={ex.execution_id} className="mb-2 rounded border border-slate-800 bg-panelAlt/30 p-2">
            <p className="text-slate-200 wrap-anywhere">
              status={ex.status} requested_by={ex.requested_by}
            </p>
            <p className="mt-1 text-slate-400 wrap-anywhere">created={ex.created_at}</p>
            {ex.status === "pending_approval" ? (
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  disabled={busy || !canApprove}
                  onClick={() => void approveExecution(ex.execution_id, true)}
                  className="rounded border border-accent/60 bg-accent/10 px-2 py-1 text-[11px] text-accent hover:bg-accent/20 disabled:opacity-60"
                >
                  Approve
                </button>
                <button
                  type="button"
                  disabled={busy || !canApprove}
                  onClick={() => void approveExecution(ex.execution_id, false)}
                  className="rounded border border-danger/60 bg-danger/10 px-2 py-1 text-[11px] text-danger hover:bg-danger/20 disabled:opacity-60"
                >
                  Reject
                </button>
              </div>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}
