from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services.control_plane_compliance import build_control_plane_compliance_evidence
from app.services.control_plane_production_readiness import (
    _find_tenant,
    evaluate_prod_v1_readiness_final,
    get_prod_v1_burn_rate_profile,
    get_prod_v1_go_live_runbook,
    prod_v1_burn_rate_guard_history,
    prod_v1_go_live_closure_history,
)
from app.services.orchestrator_pilot_onboarding import get_pilot_onboarding_profile
from app.services.rollout_handoff_auth import (
    get_rollout_handoff_policy,
    rollout_handoff_governance_snapshot,
    rollout_handoff_receipts,
)


def _phase_status(*, ready: bool, blockers: list[str], completed: bool = False, pending: bool = False) -> str:
    if completed:
        return "completed"
    if pending:
        return "pending"
    if blockers:
        return "blocked"
    if ready:
        return "ready"
    return "needs_action"


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        rows.append(item)
    return rows


def production_rollout_integration_playbook(
    db: Session,
    tenant_code: str,
    *,
    max_monthly_cost_usd: float = 50.0,
    handoff_limit: int = 200,
    closure_limit: int = 20,
    burn_rate_limit: int = 20,
) -> dict[str, Any]:
    tenant = _find_tenant(db, tenant_code)
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}

    compliance = build_control_plane_compliance_evidence()
    readiness = evaluate_prod_v1_readiness_final(db, tenant.tenant_code, max_monthly_cost_usd=max_monthly_cost_usd)
    onboarding = get_pilot_onboarding_profile(tenant.id)
    handoff_policy = get_rollout_handoff_policy(tenant.id)
    handoff_receipts = rollout_handoff_receipts(tenant.id, limit=max(1, handoff_limit))
    handoff_governance = rollout_handoff_governance_snapshot(tenant.id, limit=max(1, handoff_limit))
    runbook_resp = get_prod_v1_go_live_runbook(tenant.tenant_code)
    burn_rate_profile_resp = get_prod_v1_burn_rate_profile(tenant.tenant_code)
    closure_history = prod_v1_go_live_closure_history(tenant_code=tenant.tenant_code, limit=max(1, closure_limit))
    burn_rate_history = prod_v1_burn_rate_guard_history(tenant_code=tenant.tenant_code, limit=max(1, burn_rate_limit))

    controls = compliance.get("controls", {}) if isinstance(compliance.get("controls", {}), dict) else {}
    auth_posture = compliance.get("auth_posture", {}) if isinstance(compliance.get("auth_posture", {}), dict) else {}
    objective_gate = readiness.get("objective_gate", {}) if isinstance(readiness.get("objective_gate", {}), dict) else {}
    handoff_policy_row = handoff_policy.get("policy", {}) if isinstance(handoff_policy.get("policy", {}), dict) else {}
    handoff_risk = (
        handoff_governance.get("risk_snapshot", {})
        if isinstance(handoff_governance.get("risk_snapshot", {}), dict)
        else {}
    )
    runbook = runbook_resp.get("runbook", {}) if isinstance(runbook_resp.get("runbook", {}), dict) else {}
    burn_rate_profile = (
        burn_rate_profile_resp.get("profile", {})
        if isinstance(burn_rate_profile_resp.get("profile", {}), dict)
        else {}
    )
    latest_closure = closure_history.get("rows", [{}])[0] if closure_history.get("rows") else {}
    latest_burn_rate = burn_rate_history.get("rows", [{}])[0] if burn_rate_history.get("rows") else {}
    latest_burn_payload = (
        latest_burn_rate.get("payload", {}) if isinstance(latest_burn_rate.get("payload", {}), dict) else {}
    )
    latest_burn_action = (
        latest_burn_payload.get("action", {}) if isinstance(latest_burn_payload.get("action", {}), dict) else {}
    )

    preflight_blockers: list[str] = []
    preflight_actions: list[str] = []
    if not bool(controls.get("idp_enforced_for_production", False)):
        preflight_blockers.append("idp_enforced_for_production")
        preflight_actions.append("Configure IdP-backed admin auth or disable local bootstrap before production rollout.")
    if not bool(controls.get("local_bootstrap_disabled", False)):
        preflight_blockers.append("local_bootstrap_disabled")
        preflight_actions.append("Disable local bootstrap tokens for production-bound control-plane access.")
    if not bool(controls.get("immutable_retention_policy_flag", False)):
        preflight_blockers.append("immutable_retention_policy_flag")
        preflight_actions.append("Enable the immutable retention policy flag for the audit publication target.")
    if not bool(controls.get("s3_object_lock_ready", False)):
        preflight_blockers.append("s3_object_lock_ready")
        preflight_actions.append("Validate S3 Object Lock or equivalent WORM publication settings on the target bucket.")
    preflight_ready = not preflight_blockers

    onboarding_ready = onboarding.get("status") == "ok" and bool(onboarding.get("target_asset", ""))
    objective_pass = bool(objective_gate.get("overall_pass", readiness.get("final_gate", {}).get("objective_pass", False)))
    pilot_blockers: list[str] = []
    pilot_actions: list[str] = []
    if not onboarding_ready:
        pilot_blockers.append("pilot_onboarding_profile")
        pilot_actions.append("Configure the pilot onboarding profile with tenant code, target asset, and strategy profile.")
    if not objective_pass:
        pilot_blockers.append("objective_gate")
        pilot_actions.append("Resolve failed objective-gate signals before advancing beyond pilot.")
    pilot_ready = not pilot_blockers

    handoff_receipt_count = int(handoff_receipts.get("count", 0) or 0)
    handoff_max_risk = int(handoff_risk.get("max_risk_score", 0) or 0)
    handoff_block_threshold = int(handoff_policy_row.get("risk_threshold_block", 85) or 85)
    handoff_harden_threshold = int(handoff_policy_row.get("risk_threshold_harden", 60) or 60)
    handoff_blocked_count = int(handoff_risk.get("blocked_count", 0) or 0)

    handoff_blockers: list[str] = []
    handoff_actions: list[str] = []
    if not bool(handoff_policy_row.get("containment_playbook_enabled", True)):
        handoff_blockers.append("containment_playbook_disabled")
        handoff_actions.append("Enable the rollout handoff containment playbook before external reviewer access.")
    if handoff_max_risk >= handoff_block_threshold:
        handoff_blockers.append("handoff_risk_above_block_threshold")
        handoff_actions.append("Reduce rollout handoff risk below the block threshold before issuing reviewer tokens.")
    if handoff_blocked_count > 0:
        handoff_blockers.append("prior_handoff_token_blocked")
        handoff_actions.append("Review rollout handoff anomalies and containment events before continuing.")
    if handoff_receipt_count == 0:
        handoff_actions.append("Issue and validate at least one rollout handoff token to exercise the external reviewer path.")
    elif handoff_max_risk >= handoff_harden_threshold:
        handoff_actions.append("Review handoff hardening thresholds; recent reviewer traffic reached the harden threshold.")
    handoff_ready = not handoff_blockers and handoff_receipt_count > 0

    runbook_complete = bool(readiness.get("final_gate", {}).get("runbook_pass", False))
    cost_pass = bool(readiness.get("final_gate", {}).get("cost_pass", False))
    go_live_executed = str(latest_closure.get("status", "")) == "closed" and str(tenant.status).lower() == "production"
    go_live_blockers = [str(item.get("reason", "unknown")) for item in readiness.get("blockers", []) if item.get("reason")]
    go_live_actions: list[str] = []
    if not runbook_complete:
        go_live_actions.append("Complete every production-v1 runbook checklist item before requesting closure.")
    if not cost_pass:
        go_live_actions.append("Resolve cost anomalies or budget breaches before production promotion.")
    if not objective_pass:
        go_live_actions.append("Resolve objective-gate failures before production promotion.")
    if preflight_ready and pilot_ready and handoff_ready and bool(readiness.get("production_v1_ready", False)) and not go_live_executed:
        go_live_actions.append("Execute the production-v1 go-live close flow with the approved change ticket.")
    if not preflight_ready or not pilot_ready or not handoff_ready:
        go_live_actions.append("Resolve upstream preflight, pilot, and handoff blockers before final closure.")
    go_live_ready = preflight_ready and pilot_ready and handoff_ready and bool(readiness.get("production_v1_ready", False))

    burn_profile_configured = burn_rate_profile_resp.get("status") == "ok"
    burn_guard_exercised = int(burn_rate_history.get("count", 0) or 0) > 0
    latest_burn_rollback = bool(latest_burn_action.get("executed", False)) and str(latest_burn_action.get("type", "")) == "auto_rollback"

    post_go_live_blockers: list[str] = []
    post_go_live_actions: list[str] = []
    post_go_live_pending = str(tenant.status).lower() != "production"
    if post_go_live_pending:
        post_go_live_actions.append("Promote the tenant to production through the go-live closure flow before post-go-live validation.")
    else:
        if not burn_profile_configured:
            post_go_live_blockers.append("burn_rate_profile_not_configured")
            post_go_live_actions.append("Configure the production-v1 burn-rate guard profile immediately after promotion.")
        if not burn_guard_exercised:
            post_go_live_actions.append("Run the burn-rate guard once post-go-live to verify rollback automation and telemetry.")
        if latest_burn_rollback:
            post_go_live_blockers.append("latest_burn_rate_guard_triggered_rollback")
            post_go_live_actions.append("Investigate the latest burn-rate rollback event before declaring rollout stable.")

    post_go_live_ready = not post_go_live_blockers and burn_profile_configured and burn_guard_exercised and not post_go_live_pending

    phases = [
        {
            "id": "preflight",
            "title": "Control Plane Preflight",
            "status": _phase_status(ready=preflight_ready, blockers=preflight_blockers),
            "ready": preflight_ready,
            "checks": [
                {"name": "idp_enforced_for_production", "pass": bool(controls.get("idp_enforced_for_production", False))},
                {"name": "local_bootstrap_disabled", "pass": bool(controls.get("local_bootstrap_disabled", False))},
                {"name": "immutable_retention_policy_flag", "pass": bool(controls.get("immutable_retention_policy_flag", False))},
                {"name": "s3_object_lock_ready", "pass": bool(controls.get("s3_object_lock_ready", False))},
            ],
            "blockers": preflight_blockers,
            "next_actions": _unique(preflight_actions),
            "details": {"compliance": compliance, "auth_posture": auth_posture},
            "references": {
                "api": [
                    "GET /control-plane/auth/posture",
                    "GET /control-plane/compliance/evidence",
                ]
            },
        },
        {
            "id": "pilot",
            "title": "Pilot Validation",
            "status": _phase_status(ready=pilot_ready, blockers=pilot_blockers),
            "ready": pilot_ready,
            "checks": [
                {"name": "pilot_onboarding_profile", "pass": onboarding_ready},
                {"name": "objective_gate_pass", "pass": objective_pass},
            ],
            "blockers": pilot_blockers,
            "next_actions": _unique(pilot_actions),
            "details": {
                "pilot_onboarding": onboarding,
                "objective_gate": objective_gate,
            },
            "references": {
                "api": [
                    f"GET /control-plane/orchestrator/pilot/onboarding/{tenant.id}",
                    f"GET /control-plane/orchestrator/pilot/onboarding/{tenant.id}/checklist",
                    f"GET /control-plane/production-v1/readiness-final/{tenant.tenant_code}",
                ]
            },
        },
        {
            "id": "handoff",
            "title": "External Handoff Hardening",
            "status": _phase_status(ready=handoff_ready, blockers=handoff_blockers),
            "ready": handoff_ready,
            "checks": [
                {"name": "containment_playbook_enabled", "pass": bool(handoff_policy_row.get("containment_playbook_enabled", True))},
                {"name": "handoff_flow_exercised", "pass": handoff_receipt_count > 0},
                {"name": "risk_below_block_threshold", "pass": handoff_max_risk < handoff_block_threshold},
                {"name": "no_blocked_handoff_events", "pass": handoff_blocked_count == 0},
            ],
            "blockers": handoff_blockers,
            "next_actions": _unique(handoff_actions),
            "details": {
                "policy": handoff_policy_row,
                "receipts": handoff_receipts,
                "governance_snapshot": handoff_governance,
            },
            "references": {
                "api": [
                    f"POST /control-plane/orchestrator/pilot/rollout-handoff/issue?tenant_id={tenant.id}",
                    f"GET /control-plane/orchestrator/pilot/rollout-handoff/policy/{tenant.id}",
                    f"GET /control-plane/orchestrator/pilot/rollout-handoff/receipts/{tenant.id}",
                    f"GET /control-plane/orchestrator/pilot/rollout-handoff/governance/{tenant.id}",
                ]
            },
        },
        {
            "id": "go_live",
            "title": "Production Go-Live Closure",
            "status": _phase_status(
                ready=go_live_ready,
                blockers=go_live_blockers,
                completed=go_live_executed,
            ),
            "ready": go_live_ready,
            "checks": [
                {"name": "objective_gate_pass", "pass": objective_pass},
                {"name": "cost_guardrail_pass", "pass": cost_pass},
                {"name": "runbook_complete", "pass": runbook_complete},
                {"name": "preflight_complete", "pass": preflight_ready},
                {"name": "pilot_complete", "pass": pilot_ready},
                {"name": "handoff_complete", "pass": handoff_ready},
            ],
            "blockers": _unique(go_live_blockers),
            "next_actions": _unique(go_live_actions),
            "details": {
                "readiness": readiness,
                "runbook_status": runbook_resp.get("status", "unknown"),
                "runbook": runbook,
                "closure_history": closure_history,
                "latest_closure": latest_closure,
            },
            "references": {
                "api": [
                    f"GET /control-plane/production-v1/runbook/{tenant.tenant_code}",
                    f"GET /control-plane/production-v1/readiness-final/{tenant.tenant_code}",
                    "POST /control-plane/production-v1/go-live/close",
                    f"GET /control-plane/production-v1/go-live/closure-history?tenant_code={tenant.tenant_code}",
                ]
            },
        },
        {
            "id": "post_go_live",
            "title": "Post-Go-Live Guard",
            "status": _phase_status(
                ready=post_go_live_ready,
                blockers=post_go_live_blockers,
                completed=post_go_live_ready,
                pending=post_go_live_pending,
            ),
            "ready": post_go_live_ready,
            "checks": [
                {"name": "tenant_in_production", "pass": not post_go_live_pending},
                {"name": "burn_rate_profile_configured", "pass": burn_profile_configured},
                {"name": "burn_rate_guard_exercised", "pass": burn_guard_exercised},
                {"name": "latest_guard_did_not_rollback", "pass": not latest_burn_rollback},
            ],
            "blockers": post_go_live_blockers,
            "next_actions": _unique(post_go_live_actions),
            "details": {
                "burn_rate_profile_status": burn_rate_profile_resp.get("status", "unknown"),
                "burn_rate_profile": burn_rate_profile,
                "burn_rate_history": burn_rate_history,
                "latest_burn_rate_event": latest_burn_rate,
            },
            "references": {
                "api": [
                    f"GET /control-plane/production-v1/burn-rate/profile/{tenant.tenant_code}",
                    f"POST /control-plane/production-v1/burn-rate/evaluate/{tenant.tenant_code}",
                    f"GET /control-plane/production-v1/burn-rate/history?tenant_code={tenant.tenant_code}",
                ]
            },
        },
    ]

    open_actions = _unique([action for phase in phases for action in phase.get("next_actions", [])])
    blocked_phase_count = len([phase for phase in phases if phase.get("status") == "blocked"])
    rollout_ready = preflight_ready and pilot_ready and handoff_ready and go_live_ready

    return {
        "status": "ok",
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.tenant_code,
        "tenant_status": str(tenant.status),
        "summary": {
            "rollout_ready": rollout_ready,
            "go_live_executed": go_live_executed,
            "post_go_live_ready": post_go_live_ready,
            "blocked_phase_count": blocked_phase_count,
            "open_action_count": len(open_actions),
            "recommended_actions": open_actions,
        },
        "phases": phases,
    }
