from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import orchestrator as orchestrator_api
from app.main import app


def test_secure_pilot_endpoints_require_operator_token_and_scope() -> None:
    tenant_id = uuid4()

    orig_verify = orchestrator_api.verify_pilot_operator_token
    orig_allows = orchestrator_api.operator_allows_tenant
    orig_scope = orchestrator_api.operator_has_scope
    orig_activate = orchestrator_api.activate_pilot_session
    orig_deactivate = orchestrator_api.deactivate_pilot_session
    orig_status = orchestrator_api.get_pilot_session_status
    orig_incidents = orchestrator_api.pilot_incidents
    orig_rate_usage = orchestrator_api.get_tenant_rate_budget_usage
    orig_scheduler_profile = orchestrator_api.get_tenant_scheduler_profile
    orig_rollout_profile = orchestrator_api.get_tenant_rollout_profile
    orig_rollout_policy = orchestrator_api.get_tenant_rollout_policy
    orig_rollout_decisions = orchestrator_api.rollout_decision_history
    orig_rollout_evidence = orchestrator_api.rollout_evidence_history
    orig_rollout_evidence_verify = orchestrator_api.verify_rollout_evidence_chain
    orig_rollout_guard = orchestrator_api.get_rollout_guard_state
    orig_rollout_pending = orchestrator_api.list_pending_rollout_decisions
    orig_rollout_approve = orchestrator_api.approve_pending_rollout_decision
    try:
        orchestrator_api.verify_pilot_operator_token = lambda token: {
            "valid": token == "ok-token",
            "tenant_scope": "acb",
            "scopes": ["pilot:read", "pilot:write"],
        }
        orchestrator_api.operator_allows_tenant = lambda verified, tenant_code: tenant_code == "acb"
        orchestrator_api.operator_has_scope = lambda verified, scope: scope in set(verified.get("scopes", []))
        orchestrator_api.activate_pilot_session = lambda **kwargs: {"status": "pilot_running", "tenant_id": str(kwargs["tenant_id"])}
        orchestrator_api.deactivate_pilot_session = lambda tenant_id, reason="": {"status": "pilot_stopped", "tenant_id": str(tenant_id)}
        orchestrator_api.get_pilot_session_status = lambda tenant_id: {"tenant_id": str(tenant_id), "pilot": {"status": "running"}}
        orchestrator_api.pilot_incidents = lambda tenant_id, limit=100: {"tenant_id": str(tenant_id), "count": 1, "rows": [{"id": "1-0"}]}
        orchestrator_api.get_tenant_rate_budget_usage = lambda tenant_id, hour_epoch=None: {
            "tenant_id": str(tenant_id),
            "hour_bucket_epoch": 0,
            "cycles_used": 1,
            "red_events_used": 10,
        }
        orchestrator_api.get_tenant_scheduler_profile = lambda tenant_id: {
            "tenant_id": str(tenant_id),
            "profile": {"priority_tier": "normal"},
        }
        orchestrator_api.get_tenant_rollout_profile = lambda tenant_id: {
            "tenant_id": str(tenant_id),
            "profile": {"rollout_stage": "ga", "canary_percent": 100},
        }
        orchestrator_api.get_tenant_rollout_policy = lambda tenant_id: {
            "tenant_id": str(tenant_id),
            "policy": {"require_approval_for_demote": True},
        }
        orchestrator_api.rollout_decision_history = lambda tenant_id, limit=100: {
            "tenant_id": str(tenant_id),
            "count": 1,
            "rows": [{"id": "1-0", "action": "no_change"}],
        }
        orchestrator_api.rollout_evidence_history = lambda tenant_id, limit=100: {
            "tenant_id": str(tenant_id),
            "count": 1,
            "rows": [{"id": "1-0", "signature": "abc"}],
        }
        orchestrator_api.verify_rollout_evidence_chain = lambda tenant_id, limit=1000: {
            "tenant_id": str(tenant_id),
            "valid": True,
            "checked": 1,
        }
        orchestrator_api.get_rollout_guard_state = lambda tenant_id: {
            "tenant_id": str(tenant_id),
            "cooldown_active": False,
        }
        orchestrator_api.list_pending_rollout_decisions = lambda tenant_id, limit=100: {
            "tenant_id": str(tenant_id),
            "count": 1,
            "rows": [{"decision_id": "d1", "status": "pending_approval"}],
        }
        orchestrator_api.approve_pending_rollout_decision = lambda tenant_id, decision_id, approve=True, reviewer="": {
            "status": "approved_applied",
            "decision_id": decision_id,
        }

        with TestClient(app) as client:
            denied = client.post(
                "/orchestrator/pilot/secure/activate",
                json={
                    "tenant_id": str(tenant_id),
                    "target_asset": "acb.example.com/admin-login",
                },
                headers={"Authorization": "Bearer bad-token", "X-Tenant-Code": "acb"},
            )
            assert denied.status_code == 403

            ok = client.post(
                "/orchestrator/pilot/secure/activate",
                json={
                    "tenant_id": str(tenant_id),
                    "target_asset": "acb.example.com/admin-login",
                },
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert ok.status_code == 200
            assert ok.json()["status"] == "pilot_running"

            status = client.get(
                f"/orchestrator/pilot/secure/status/{tenant_id}",
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert status.status_code == 200
            assert status.json()["pilot"]["status"] == "running"

            incidents = client.get(
                f"/orchestrator/pilot/secure/incidents/{tenant_id}",
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert incidents.status_code == 200
            assert incidents.json()["count"] == 1

            usage = client.get(
                f"/orchestrator/pilot/secure/rate-budget/{tenant_id}/usage",
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert usage.status_code == 200
            assert usage.json()["cycles_used"] == 1

            scheduler_profile = client.get(
                f"/orchestrator/pilot/secure/scheduler-profile/{tenant_id}",
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert scheduler_profile.status_code == 200
            assert scheduler_profile.json()["profile"]["priority_tier"] == "normal"

            rollout_profile = client.get(
                f"/orchestrator/pilot/secure/rollout-profile/{tenant_id}",
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert rollout_profile.status_code == 200
            assert rollout_profile.json()["profile"]["rollout_stage"] == "ga"

            rollout_decisions = client.get(
                f"/orchestrator/pilot/secure/rollout/decisions/{tenant_id}",
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert rollout_decisions.status_code == 200
            assert rollout_decisions.json()["count"] == 1

            rollout_evidence = client.get(
                f"/orchestrator/pilot/secure/rollout/evidence/{tenant_id}",
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert rollout_evidence.status_code == 200
            assert rollout_evidence.json()["count"] == 1

            rollout_evidence_verify = client.get(
                f"/orchestrator/pilot/secure/rollout/evidence/verify/{tenant_id}",
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert rollout_evidence_verify.status_code == 200
            assert rollout_evidence_verify.json()["valid"] is True

            rollout_policy = client.get(
                f"/orchestrator/pilot/secure/rollout-policy/{tenant_id}",
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert rollout_policy.status_code == 200
            assert rollout_policy.json()["policy"]["require_approval_for_demote"] is True

            rollout_pending = client.get(
                f"/orchestrator/pilot/secure/rollout/pending/{tenant_id}",
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert rollout_pending.status_code == 200
            assert rollout_pending.json()["count"] == 1

            rollout_guard = client.get(
                f"/orchestrator/pilot/secure/rollout/guard/{tenant_id}",
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert rollout_guard.status_code == 200
            assert rollout_guard.json()["cooldown_active"] is False

            rollout_approve = client.post(
                "/orchestrator/pilot/secure/rollout/pending/approve",
                params={"tenant_id": str(tenant_id), "decision_id": "d1", "approve": "true"},
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert rollout_approve.status_code == 200
            assert rollout_approve.json()["status"] == "approved_applied"

            stop = client.post(
                f"/orchestrator/pilot/secure/deactivate/{tenant_id}",
                headers={"Authorization": "Bearer ok-token", "X-Tenant-Code": "acb"},
            )
            assert stop.status_code == 200
            assert stop.json()["status"] == "pilot_stopped"
    finally:
        orchestrator_api.verify_pilot_operator_token = orig_verify
        orchestrator_api.operator_allows_tenant = orig_allows
        orchestrator_api.operator_has_scope = orig_scope
        orchestrator_api.activate_pilot_session = orig_activate
        orchestrator_api.deactivate_pilot_session = orig_deactivate
        orchestrator_api.get_pilot_session_status = orig_status
        orchestrator_api.pilot_incidents = orig_incidents
        orchestrator_api.get_tenant_rate_budget_usage = orig_rate_usage
        orchestrator_api.get_tenant_scheduler_profile = orig_scheduler_profile
        orchestrator_api.get_tenant_rollout_profile = orig_rollout_profile
        orchestrator_api.get_tenant_rollout_policy = orig_rollout_policy
        orchestrator_api.rollout_decision_history = orig_rollout_decisions
        orchestrator_api.rollout_evidence_history = orig_rollout_evidence
        orchestrator_api.verify_rollout_evidence_chain = orig_rollout_evidence_verify
        orchestrator_api.get_rollout_guard_state = orig_rollout_guard
        orchestrator_api.list_pending_rollout_decisions = orig_rollout_pending
        orchestrator_api.approve_pending_rollout_decision = orig_rollout_approve
