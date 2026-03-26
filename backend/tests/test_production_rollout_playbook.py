from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_production_rollout_playbook as playbook


class _Tenant:
    def __init__(self, tenant_id, tenant_code: str, status: str = "staging") -> None:
        self.id = tenant_id
        self.tenant_code = tenant_code
        self.status = status


class _Db:
    pass


def test_production_rollout_playbook_ready_for_go_live() -> None:
    tenant = _Tenant(uuid4(), "acb", status="staging")

    orig_find = playbook._find_tenant
    orig_compliance = playbook.build_control_plane_compliance_evidence
    orig_onboarding = playbook.get_pilot_onboarding_profile
    orig_policy = playbook.get_rollout_handoff_policy
    orig_receipts = playbook.rollout_handoff_receipts
    orig_governance = playbook.rollout_handoff_governance_snapshot
    orig_runbook = playbook.get_prod_v1_go_live_runbook
    orig_burn_profile = playbook.get_prod_v1_burn_rate_profile
    orig_readiness = playbook.evaluate_prod_v1_readiness_final
    orig_closure = playbook.prod_v1_go_live_closure_history
    orig_burn_history = playbook.prod_v1_burn_rate_guard_history
    try:
        playbook._find_tenant = lambda db, tenant_code: tenant if tenant_code == "acb" else None
        playbook.build_control_plane_compliance_evidence = lambda: {
            "overall_pass": True,
            "controls": {
                "idp_enforced_for_production": True,
                "local_bootstrap_disabled": True,
                "immutable_retention_policy_flag": True,
                "s3_object_lock_ready": True,
            },
            "auth_posture": {"auth_provider": "idp"},
        }
        playbook.get_pilot_onboarding_profile = lambda tenant_id: {
            "status": "ok",
            "tenant_id": str(tenant_id),
            "tenant_code": "acb",
            "target_asset": "https://acb.example",
        }
        playbook.get_rollout_handoff_policy = lambda tenant_id: {
            "tenant_id": str(tenant_id),
            "policy": {
                "containment_playbook_enabled": True,
                "risk_threshold_harden": 60,
                "risk_threshold_block": 85,
            },
        }
        playbook.rollout_handoff_receipts = lambda tenant_id, limit=200: {
            "tenant_id": str(tenant_id),
            "count": 1,
            "rows": [{"id": "1-0"}],
        }
        playbook.rollout_handoff_governance_snapshot = lambda tenant_id, limit=200: {
            "tenant_id": str(tenant_id),
            "risk_snapshot": {"count": 1, "max_risk_score": 10, "blocked_count": 0},
            "containment_event_count": 0,
        }
        playbook.get_prod_v1_go_live_runbook = lambda tenant_code: {
            "status": "ok",
            "tenant_code": tenant_code,
            "runbook": {"items": {"dr_smoke_passed": True}},
        }
        playbook.get_prod_v1_burn_rate_profile = lambda tenant_code: {
            "status": "ok",
            "tenant_code": tenant_code,
            "profile": {"rollback_target_status": "staging"},
        }
        playbook.evaluate_prod_v1_readiness_final = lambda db, tenant_code, max_monthly_cost_usd=50.0: {
            "status": "ok",
            "tenant_id": str(tenant.id),
            "tenant_code": tenant_code,
            "production_v1_ready": True,
            "final_gate": {"objective_pass": True, "cost_pass": True, "runbook_pass": True},
            "objective_gate": {"overall_pass": True, "gates": {}},
            "blockers": [],
        }
        playbook.prod_v1_go_live_closure_history = lambda tenant_code="", limit=20: {"count": 0, "rows": []}
        playbook.prod_v1_burn_rate_guard_history = lambda tenant_code="", limit=20: {"count": 0, "rows": []}

        result = playbook.production_rollout_integration_playbook(_Db(), "acb")
        assert result["status"] == "ok"
        assert result["summary"]["rollout_ready"] is True
        phases = {row["id"]: row for row in result["phases"]}
        assert phases["go_live"]["status"] == "ready"
        assert phases["post_go_live"]["status"] == "pending"
    finally:
        playbook._find_tenant = orig_find
        playbook.build_control_plane_compliance_evidence = orig_compliance
        playbook.get_pilot_onboarding_profile = orig_onboarding
        playbook.get_rollout_handoff_policy = orig_policy
        playbook.rollout_handoff_receipts = orig_receipts
        playbook.rollout_handoff_governance_snapshot = orig_governance
        playbook.get_prod_v1_go_live_runbook = orig_runbook
        playbook.get_prod_v1_burn_rate_profile = orig_burn_profile
        playbook.evaluate_prod_v1_readiness_final = orig_readiness
        playbook.prod_v1_go_live_closure_history = orig_closure
        playbook.prod_v1_burn_rate_guard_history = orig_burn_history


def test_production_rollout_playbook_collects_blockers_and_actions() -> None:
    tenant = _Tenant(uuid4(), "acb", status="staging")

    orig_find = playbook._find_tenant
    orig_compliance = playbook.build_control_plane_compliance_evidence
    orig_onboarding = playbook.get_pilot_onboarding_profile
    orig_policy = playbook.get_rollout_handoff_policy
    orig_receipts = playbook.rollout_handoff_receipts
    orig_governance = playbook.rollout_handoff_governance_snapshot
    orig_runbook = playbook.get_prod_v1_go_live_runbook
    orig_burn_profile = playbook.get_prod_v1_burn_rate_profile
    orig_readiness = playbook.evaluate_prod_v1_readiness_final
    orig_closure = playbook.prod_v1_go_live_closure_history
    orig_burn_history = playbook.prod_v1_burn_rate_guard_history
    try:
        playbook._find_tenant = lambda db, tenant_code: tenant
        playbook.build_control_plane_compliance_evidence = lambda: {
            "overall_pass": False,
            "controls": {
                "idp_enforced_for_production": False,
                "local_bootstrap_disabled": False,
                "immutable_retention_policy_flag": False,
                "s3_object_lock_ready": False,
            },
            "auth_posture": {"auth_provider": "local"},
        }
        playbook.get_pilot_onboarding_profile = lambda tenant_id: {"status": "not_found", "tenant_id": str(tenant_id)}
        playbook.get_rollout_handoff_policy = lambda tenant_id: {
            "tenant_id": str(tenant_id),
            "policy": {
                "containment_playbook_enabled": True,
                "risk_threshold_harden": 60,
                "risk_threshold_block": 85,
            },
        }
        playbook.rollout_handoff_receipts = lambda tenant_id, limit=200: {
            "tenant_id": str(tenant_id),
            "count": 0,
            "rows": [],
        }
        playbook.rollout_handoff_governance_snapshot = lambda tenant_id, limit=200: {
            "tenant_id": str(tenant_id),
            "risk_snapshot": {"count": 1, "max_risk_score": 90, "blocked_count": 1},
            "containment_event_count": 1,
        }
        playbook.get_prod_v1_go_live_runbook = lambda tenant_code: {
            "status": "default",
            "tenant_code": tenant_code,
            "runbook": {"items": {}},
        }
        playbook.get_prod_v1_burn_rate_profile = lambda tenant_code: {
            "status": "default",
            "tenant_code": tenant_code,
            "profile": {},
        }
        playbook.evaluate_prod_v1_readiness_final = lambda db, tenant_code, max_monthly_cost_usd=50.0: {
            "status": "ok",
            "tenant_id": str(tenant.id),
            "tenant_code": tenant_code,
            "production_v1_ready": False,
            "final_gate": {"objective_pass": False, "cost_pass": False, "runbook_pass": False},
            "objective_gate": {"overall_pass": False, "gates": {}},
            "blockers": [
                {"type": "objective_gate", "reason": "objective_gate_not_passed"},
                {"type": "cost_guardrail", "reason": "cost_breach_or_anomaly_detected"},
                {"type": "runbook", "reason": "go_live_checklist_incomplete"},
            ],
        }
        playbook.prod_v1_go_live_closure_history = lambda tenant_code="", limit=20: {"count": 0, "rows": []}
        playbook.prod_v1_burn_rate_guard_history = lambda tenant_code="", limit=20: {"count": 0, "rows": []}

        result = playbook.production_rollout_integration_playbook(_Db(), "acb")
        phases = {row["id"]: row for row in result["phases"]}
        assert result["summary"]["rollout_ready"] is False
        assert phases["preflight"]["status"] == "blocked"
        assert phases["pilot"]["status"] == "blocked"
        assert phases["handoff"]["status"] == "blocked"
        assert phases["go_live"]["status"] == "blocked"
        assert "Configure IdP-backed admin auth or disable local bootstrap before production rollout." in result["summary"]["recommended_actions"]
    finally:
        playbook._find_tenant = orig_find
        playbook.build_control_plane_compliance_evidence = orig_compliance
        playbook.get_pilot_onboarding_profile = orig_onboarding
        playbook.get_rollout_handoff_policy = orig_policy
        playbook.rollout_handoff_receipts = orig_receipts
        playbook.rollout_handoff_governance_snapshot = orig_governance
        playbook.get_prod_v1_go_live_runbook = orig_runbook
        playbook.get_prod_v1_burn_rate_profile = orig_burn_profile
        playbook.evaluate_prod_v1_readiness_final = orig_readiness
        playbook.prod_v1_go_live_closure_history = orig_closure
        playbook.prod_v1_burn_rate_guard_history = orig_burn_history
