from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.main import app
from app.services.competitive_federation import action_center_sla_federation_snapshot


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_competitive_rbac_requires_view_scope_for_action_center_events(monkeypatch) -> None:
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "test", "scopes": ["control_plane:read"]},
    )
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(competitive_api, "list_action_center_events", lambda db, tenant_code="", severity="", limit=200: {"count": 0, "rows": []})

    with TestClient(app) as client:
        denied = client.get("/competitive/action-center/events")
        assert denied.status_code == 403

        allowed = client.get("/competitive/action-center/events", headers={"Authorization": "Bearer demo"})
        assert allowed.status_code == 200
        assert allowed.json()["count"] == 0


def test_competitive_auth_context_maps_roles_from_scopes(monkeypatch) -> None:
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "test", "scopes": ["control_plane:write"]},
    )
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)

    with TestClient(app) as client:
        context = client.get("/competitive/auth/context", headers={"Authorization": "Bearer demo"})
        assert context.status_code == 200
        data = context.json()
        assert data["permissions"]["can_view"] is True
        assert data["permissions"]["can_edit_policy"] is True
        assert data["permissions"]["can_approve"] is True
        assert "policy_editor" in data["roles"]
        assert "approver" in data["roles"]


def test_competitive_rbac_blocks_policy_write_for_read_only_scope(monkeypatch) -> None:
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "test", "scopes": ["control_plane:read"]},
    )
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "upsert_action_center_policy",
        lambda db, **kwargs: {"status": "created", "policy": kwargs},
    )

    with TestClient(app) as client:
        denied = client.post(
            "/competitive/action-center/policies",
            json={
                "tenant_code": "acb",
                "policy_version": "1.0",
                "owner": "test",
                "telegram_enabled": True,
                "line_enabled": False,
                "min_severity": "high",
                "routing_tags": [],
            },
            headers={"Authorization": "Bearer demo"},
        )
        assert denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "test", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        allowed = client.post(
            "/competitive/action-center/policies",
            json={
                "tenant_code": "acb",
                "policy_version": "1.0",
                "owner": "test",
                "telegram_enabled": True,
                "line_enabled": False,
                "min_severity": "high",
                "routing_tags": [],
            },
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed.status_code == 200
        assert allowed.json()["status"] == "created"


def test_competitive_rbac_blocks_connector_credential_rotate_without_approve_scope(monkeypatch) -> None:
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "rotate_connector_credential",
        lambda db, **kwargs: {"status": "rotated", "credential": kwargs, "generated_secret": False},
    )

    with TestClient(app) as client:
        denied = client.post(
            "/competitive/connectors/credentials/rotate",
            json={
                "tenant_code": "acb",
                "connector_source": "splunk",
                "credential_name": "api_key",
                "rotation_reason": "manual_test",
                "actor": "reviewer",
            },
            headers={"Authorization": "Bearer demo"},
        )
        assert denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        allowed = client.post(
            "/competitive/connectors/credentials/rotate",
            json={
                "tenant_code": "acb",
                "connector_source": "splunk",
                "credential_name": "api_key",
                "rotation_reason": "manual_test",
                "actor": "reviewer",
            },
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed.status_code == 200
        assert allowed.json()["status"] == "rotated"


def test_competitive_secops_data_tier_benchmark_requires_view_scope(monkeypatch) -> None:
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "tenant_data_tier_benchmark",
        lambda db, tenant_code, lookback_hours=24, sample_limit=2000: {
            "status": "ok",
            "tenant_code": tenant_code,
            "lookback_hours": lookback_hours,
            "event_counts": {"total_events": 10},
        },
    )

    with TestClient(app) as client:
        denied = client.get("/competitive/secops/data-tier/benchmark?tenant_code=acb")
        assert denied.status_code == 403

        allowed = client.get(
            "/competitive/secops/data-tier/benchmark?tenant_code=acb&lookback_hours=12&sample_limit=100",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed.status_code == 200
        payload = allowed.json()
        assert payload["status"] == "ok"
        assert payload["tenant_code"] == "acb"
        assert payload["lookback_hours"] == 12


def test_competitive_connector_hygiene_requires_view_scope(monkeypatch) -> None:
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "evaluate_connector_credential_hygiene",
        lambda db, tenant_code, connector_source="", warning_days=7, limit=200: {
            "status": "ok",
            "tenant_code": tenant_code,
            "count": 1,
        },
    )

    with TestClient(app) as client:
        denied = client.get("/competitive/connectors/credentials/hygiene?tenant_code=acb")
        assert denied.status_code == 403

        allowed = client.get(
            "/competitive/connectors/credentials/hygiene?tenant_code=acb&warning_days=5&limit=10",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed.status_code == 200
        assert allowed.json()["status"] == "ok"


def test_competitive_connector_auto_rotate_requires_approve_scope(monkeypatch) -> None:
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "auto_rotate_due_credentials",
        lambda db, **kwargs: {
            "status": "ok",
            "candidate_count": 2,
            "executed_count": 0,
            "failed_count": 0,
            "tenant_code": kwargs.get("tenant_code", ""),
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "evaluate_connector_credential_hygiene",
        lambda db, **kwargs: {"status": "ok", "risk": {"risk_tier": "high", "risk_score": 75}},
    )
    monkeypatch.setattr(
        competitive_api,
        "dispatch_manual_alert",
        lambda db, **kwargs: {"status": "ok", "routing": {"status": "dispatched"}},
    )

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        denied = client.post(
            "/competitive/connectors/credentials/auto-rotate",
            json={"tenant_code": "acb", "dry_run": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        allowed = client.post(
            "/competitive/connectors/credentials/auto-rotate",
            json={"tenant_code": "acb", "dry_run": True, "route_alert": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed.status_code == 200
        payload = allowed.json()
        assert payload["status"] == "ok"
        assert payload["tenant_code"] == "acb"
        assert payload["candidate_count"] == 2


def test_competitive_connector_hygiene_policy_and_scheduler_rbac(monkeypatch) -> None:
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "upsert_credential_hygiene_policy",
        lambda db, **kwargs: {"status": "created", "policy": kwargs},
    )
    monkeypatch.setattr(
        competitive_api,
        "get_credential_hygiene_policy",
        lambda db, tenant_code, connector_source="*": {
            "status": "ok",
            "policy": {"tenant_code": tenant_code, "connector_source": connector_source, "warning_days": 7},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "run_credential_hygiene_scheduler",
        lambda db, limit=200, actor="credential_guard_ai", dry_run_override=None: {
            "timestamp": "2026-03-11T00:00:00+00:00",
            "scheduled_policy_count": 1,
            "executed_count": 1,
            "skipped_count": 0,
            "executed": [],
            "skipped": [],
        },
    )

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        denied_write = client.post(
            "/competitive/connectors/credentials/hygiene/policies",
            json={"tenant_code": "acb"},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_write.status_code == 403

        allowed_read = client.get(
            "/competitive/connectors/credentials/hygiene/policies?tenant_code=acb&connector_source=*",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_read.status_code == 200
        assert allowed_read.json()["status"] == "ok"

        denied_scheduler = client.post(
            "/competitive/connectors/credentials/hygiene/scheduler/run?limit=10",
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_scheduler.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "editor", "scopes": ["competitive:policy:write"]},
    )
    with TestClient(app) as client:
        allowed_write = client.post(
            "/competitive/connectors/credentials/hygiene/policies",
            json={"tenant_code": "acb"},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_write.status_code == 200

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["competitive:approve"]},
    )
    with TestClient(app) as client:
        allowed_scheduler = client.post(
            "/competitive/connectors/credentials/hygiene/scheduler/run?limit=10&dry_run_override=true",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_scheduler.status_code == 200
        assert allowed_scheduler.json()["executed_count"] == 1


def test_competitive_delivery_escalation_federation_requires_view_scope(monkeypatch) -> None:
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "coworker_delivery_escalation_federation_snapshot",
        lambda db, plugin_code="", approval_sla_minutes=None, limit=200: {
            "status": "ok",
            "generated_at": "2026-03-15T00:00:00+00:00",
            "plugin_code": plugin_code,
            "approval_sla_minutes": approval_sla_minutes or 15,
            "count": 1,
            "summary": {
                "total_sites": 1,
                "healthy_sites": 1,
                "attention_sites": 0,
                "not_configured_sites": 0,
                "pending_approval_total": 0,
                "overdue_total": 0,
                "enabled_profile_total": 2,
                "enabled_escalation_policy_total": 1,
            },
            "rows": [],
        },
    )

    with TestClient(app) as client:
        denied = client.get("/competitive/coworker/delivery/escalation/federation")
        assert denied.status_code == 403

        allowed = client.get(
            "/competitive/coworker/delivery/escalation/federation?plugin_code=blue_thai_alert_translator&approval_sla_minutes=20",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed.status_code == 200
        payload = allowed.json()
        assert payload["status"] == "ok"
        assert payload["summary"]["healthy_sites"] == 1


def test_competitive_connector_reliability_rbac(monkeypatch) -> None:
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "upsert_connector_reliability_policy",
        lambda db, **kwargs: {"status": "created", "policy": kwargs},
    )
    monkeypatch.setattr(
        competitive_api,
        "get_connector_reliability_policy",
        lambda db, tenant_code, connector_source="*": {
            "status": "ok",
            "policy": {"tenant_code": tenant_code, "connector_source": connector_source},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "list_connector_dead_letter_backlog",
        lambda db, tenant_code, connector_source="", limit=200: {
            "status": "ok",
            "tenant_code": tenant_code,
            "summary": {"unresolved_count": 1},
            "rows": [],
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "run_connector_dead_letter_replay",
        lambda db, tenant_code, connector_source="*", dry_run=None, actor="": {
            "status": "ok",
            "run": {"run_id": "r-1"},
            "execution": {"selected_count": 1},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "run_connector_replay_scheduler",
        lambda db, limit=200, dry_run_override=None, actor="connector_replay_ai": {
            "timestamp": "2026-03-11T00:00:00+00:00",
            "scheduled_policy_count": 1,
            "executed_count": 1,
            "skipped_count": 0,
            "executed": [],
            "skipped": [],
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "connector_reliability_federation",
        lambda db, limit=200: {"count": 1, "rows": [{"tenant_code": "acb", "risk_tier": "medium"}]},
    )

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        denied_policy = client.post(
            "/competitive/connectors/reliability/policies",
            json={"tenant_code": "acb"},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_policy.status_code == 403

        denied_replay = client.post(
            "/competitive/connectors/reliability/replay",
            json={"tenant_code": "acb"},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_replay.status_code == 403

        allowed_policy_get = client.get(
            "/competitive/connectors/reliability/policies?tenant_code=acb&connector_source=*",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_policy_get.status_code == 200
        assert allowed_policy_get.json()["status"] == "ok"

        allowed_backlog = client.get(
            "/competitive/connectors/reliability/backlog?tenant_code=acb",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_backlog.status_code == 200

        allowed_federation = client.get(
            "/competitive/connectors/reliability/federation?limit=10",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_federation.status_code == 200
        assert allowed_federation.json()["count"] == 1

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["competitive:approve"]},
    )
    with TestClient(app) as client:
        allowed_replay = client.post(
            "/competitive/connectors/reliability/replay",
            json={"tenant_code": "acb", "dry_run": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_replay.status_code == 200
        assert allowed_replay.json()["status"] == "ok"

        allowed_scheduler = client.post(
            "/competitive/connectors/reliability/scheduler/run?limit=10&dry_run_override=true",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_scheduler.status_code == 200
        assert allowed_scheduler.json()["executed_count"] == 1


def test_competitive_detection_autotune_rbac(monkeypatch) -> None:
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "upsert_detection_autotune_policy",
        lambda db, **kwargs: {"status": "created", "policy": kwargs},
    )
    monkeypatch.setattr(
        competitive_api,
        "get_detection_autotune_policy",
        lambda db, site_id: {"status": "ok", "policy": {"site_id": str(site_id), "min_risk_score": 60}},
    )
    monkeypatch.setattr(
        competitive_api,
        "run_detection_autotune",
        lambda db, site_id, dry_run=None, force=False, actor="": {
            "status": "ok",
            "site_id": str(site_id),
            "execution": {"should_tune": True},
            "run": {"run_id": "run-1"},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "list_detection_autotune_runs",
        lambda db, site_id, limit=50: {"site_id": str(site_id), "count": 1, "rows": [{"run_id": "r1"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "run_detection_autotune_scheduler",
        lambda db, limit=200, dry_run_override=None, actor="blue_autotune_ai": {
            "timestamp": "2026-03-11T00:00:00+00:00",
            "scheduled_policy_count": 1,
            "executed_count": 1,
            "skipped_count": 0,
        },
    )

    site_id = str(uuid4())
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        denied_policy = client.post(
            f"/competitive/sites/{site_id}/blue/detection-autotune/policy",
            json={"min_risk_score": 70},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_policy.status_code == 403

        denied_run = client.post(
            f"/competitive/sites/{site_id}/blue/detection-autotune/run",
            json={"dry_run": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_run.status_code == 403

        allowed_get = client.get(
            f"/competitive/sites/{site_id}/blue/detection-autotune/policy",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_get.status_code == 200
        assert allowed_get.json()["status"] == "ok"

        allowed_runs = client.get(
            f"/competitive/sites/{site_id}/blue/detection-autotune/runs?limit=20",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_runs.status_code == 200
        assert allowed_runs.json()["count"] == 1

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "editor", "scopes": ["competitive:policy:write"]},
    )
    with TestClient(app) as client:
        allowed_policy = client.post(
            f"/competitive/sites/{site_id}/blue/detection-autotune/policy",
            json={"min_risk_score": 70},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_policy.status_code == 200

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["competitive:approve"]},
    )
    with TestClient(app) as client:
        allowed_run = client.post(
            f"/competitive/sites/{site_id}/blue/detection-autotune/run",
            json={"dry_run": True, "force": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_run.status_code == 200
        assert allowed_run.json()["status"] == "ok"

        allowed_scheduler = client.post(
            "/competitive/blue/detection-autotune/scheduler/run?limit=10&dry_run_override=true",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_scheduler.status_code == 200
        assert allowed_scheduler.json()["executed_count"] == 1


def test_competitive_red_exploit_autopilot_rbac(monkeypatch) -> None:
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "upsert_red_exploit_autopilot_policy",
        lambda db, **kwargs: {"status": "created", "policy": kwargs},
    )
    monkeypatch.setattr(
        competitive_api,
        "get_red_exploit_autopilot_policy",
        lambda db, site_id: {"status": "ok", "policy": {"site_id": str(site_id), "min_risk_score": 50}},
    )
    monkeypatch.setattr(
        competitive_api,
        "run_red_exploit_autopilot",
        lambda db, site_id, dry_run=None, force=False, actor="": {
            "status": "dry_run",
            "site_id": str(site_id),
            "execution": {"should_run": True, "executed": False},
            "run": {"run_id": "run-1"},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "list_red_exploit_autopilot_runs",
        lambda db, site_id, limit=50: {"site_id": str(site_id), "count": 1, "rows": [{"run_id": "r1"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "run_red_exploit_autopilot_scheduler",
        lambda db, limit=200, dry_run_override=None, actor="red_exploit_autopilot_ai": {
            "timestamp": "2026-03-11T00:00:00+00:00",
            "scheduled_policy_count": 1,
            "executed_count": 1,
            "skipped_count": 0,
        },
    )

    site_id = str(uuid4())
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        denied_policy = client.post(
            f"/competitive/sites/{site_id}/red/exploit-autopilot/policy",
            json={"min_risk_score": 65},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_policy.status_code == 403

        denied_run = client.post(
            f"/competitive/sites/{site_id}/red/exploit-autopilot/run",
            json={"dry_run": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_run.status_code == 403

        allowed_get = client.get(
            f"/competitive/sites/{site_id}/red/exploit-autopilot/policy",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_get.status_code == 200
        assert allowed_get.json()["status"] == "ok"

        allowed_runs = client.get(
            f"/competitive/sites/{site_id}/red/exploit-autopilot/runs?limit=20",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_runs.status_code == 200
        assert allowed_runs.json()["count"] == 1

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "editor", "scopes": ["competitive:policy:write"]},
    )
    with TestClient(app) as client:
        allowed_policy = client.post(
            f"/competitive/sites/{site_id}/red/exploit-autopilot/policy",
            json={"min_risk_score": 65},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_policy.status_code == 200

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["competitive:approve"]},
    )
    with TestClient(app) as client:
        allowed_run = client.post(
            f"/competitive/sites/{site_id}/red/exploit-autopilot/run",
            json={"dry_run": True, "force": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_run.status_code == 200
        assert allowed_run.json()["status"] == "dry_run"

        allowed_scheduler = client.post(
            "/competitive/red/exploit-autopilot/scheduler/run?limit=10&dry_run_override=true",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_scheduler.status_code == 200
        assert allowed_scheduler.json()["executed_count"] == 1


def test_competitive_threat_content_pipeline_rbac(monkeypatch) -> None:
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "upsert_threat_content_pipeline_policy",
        lambda db, **kwargs: {"status": "created", "policy": kwargs},
    )
    monkeypatch.setattr(
        competitive_api,
        "get_threat_content_pipeline_policy",
        lambda db, scope="global": {"status": "ok", "policy": {"scope": scope, "max_packs_per_run": 8}},
    )
    monkeypatch.setattr(
        competitive_api,
        "run_threat_content_pipeline",
        lambda db, scope="global", dry_run=None, force=False, actor="": {
            "status": "dry_run",
            "scope": scope,
            "execution": {"should_run": True, "candidate_count": 3},
            "run": {"run_id": "run-1"},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "list_threat_content_pipeline_runs",
        lambda db, scope="", limit=100: {"count": 1, "rows": [{"run_id": "r1", "scope": scope}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "run_threat_content_pipeline_scheduler",
        lambda db, limit=200, dry_run_override=None, actor="threat_content_pipeline_ai": {
            "timestamp": "2026-03-11T00:00:00+00:00",
            "scheduled_policy_count": 1,
            "executed_count": 1,
            "skipped_count": 0,
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "threat_content_pipeline_federation",
        lambda db, limit=200, stale_after_hours=48: {"count": 2, "stale_count": 0, "rows": []},
    )

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        denied_policy = client.post(
            "/competitive/threat-content/pipeline/policies",
            json={"scope": "global"},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_policy.status_code == 403

        denied_run = client.post(
            "/competitive/threat-content/pipeline/run",
            json={"scope": "global", "dry_run": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_run.status_code == 403

        allowed_get = client.get(
            "/competitive/threat-content/pipeline/policies?scope=global",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_get.status_code == 200
        assert allowed_get.json()["status"] == "ok"

        allowed_runs = client.get(
            "/competitive/threat-content/pipeline/runs?scope=global&limit=20",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_runs.status_code == 200
        assert allowed_runs.json()["count"] == 1

        allowed_federation = client.get(
            "/competitive/threat-content/pipeline/federation?limit=20&stale_after_hours=24",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_federation.status_code == 200
        assert allowed_federation.json()["count"] == 2

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "editor", "scopes": ["competitive:policy:write"]},
    )
    with TestClient(app) as client:
        allowed_policy = client.post(
            "/competitive/threat-content/pipeline/policies",
            json={"scope": "global"},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_policy.status_code == 200

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["competitive:approve"]},
    )
    with TestClient(app) as client:
        allowed_run = client.post(
            "/competitive/threat-content/pipeline/run",
            json={"scope": "global", "dry_run": True, "force": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_run.status_code == 200
        assert allowed_run.json()["status"] == "dry_run"

        allowed_scheduler = client.post(
            "/competitive/threat-content/pipeline/scheduler/run?limit=10&dry_run_override=true",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_scheduler.status_code == 200
        assert allowed_scheduler.json()["executed_count"] == 1


def test_competitive_coworker_plugin_rbac(monkeypatch) -> None:
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "list_coworker_plugins",
        lambda db, category="", active_only=True: {"count": 2, "rows": [{"plugin_code": "blue_log_refiner"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_site_coworker_plugins",
        lambda db, site_id, category="": {"site_id": str(site_id), "count": 1, "rows": [{"plugin_code": "blue_log_refiner"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "upsert_site_coworker_plugin_binding",
        lambda db, **kwargs: {"status": "created", "binding": kwargs},
    )
    monkeypatch.setattr(
        competitive_api,
        "run_site_coworker_plugin",
        lambda db, site_id, plugin_code, dry_run=None, force=False, actor="": {
            "status": "dry_run",
            "site_id": str(site_id),
            "plugin": {"plugin_code": plugin_code},
            "run": {"run_id": "run-1"},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "list_site_coworker_plugin_runs",
        lambda db, site_id, category="", limit=100: {"site_id": str(site_id), "count": 1, "rows": [{"run_id": "r1"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "run_coworker_plugin_scheduler",
        lambda db, limit=200, dry_run_override=None, actor="coworker_plugin_ai": {
            "timestamp": "2026-03-14T00:00:00+00:00",
            "scheduled_binding_count": 1,
            "executed_count": 1,
            "skipped_count": 0,
        },
    )

    site_id = str(uuid4())
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        allowed_catalog = client.get("/competitive/coworker/plugins", headers={"Authorization": "Bearer demo"})
        assert allowed_catalog.status_code == 200
        assert allowed_catalog.json()["count"] == 2

        allowed_site_plugins = client.get(
            f"/competitive/sites/{site_id}/coworker/plugins",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_site_plugins.status_code == 200
        assert allowed_site_plugins.json()["count"] == 1

        allowed_runs = client.get(
            f"/competitive/sites/{site_id}/coworker/plugins/runs?limit=20",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_runs.status_code == 200
        assert allowed_runs.json()["count"] == 1

        denied_binding = client.post(
            f"/competitive/sites/{site_id}/coworker/plugins/bindings",
            json={"plugin_code": "blue_log_refiner"},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_binding.status_code == 403

        denied_run = client.post(
            f"/competitive/sites/{site_id}/coworker/plugins/blue_log_refiner/run",
            json={"dry_run": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_run.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "editor", "scopes": ["competitive:policy:write"]},
    )
    with TestClient(app) as client:
        allowed_binding = client.post(
            f"/competitive/sites/{site_id}/coworker/plugins/bindings",
            json={"plugin_code": "blue_log_refiner", "auto_run": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_binding.status_code == 200
        assert allowed_binding.json()["status"] == "created"

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["competitive:approve"]},
    )
    with TestClient(app) as client:
        allowed_run = client.post(
            f"/competitive/sites/{site_id}/coworker/plugins/blue_log_refiner/run",
            json={"dry_run": True, "force": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_run.status_code == 200
        assert allowed_run.json()["status"] == "dry_run"

        allowed_scheduler = client.post(
            "/competitive/coworker/plugins/scheduler/run?limit=10&dry_run_override=true",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_scheduler.status_code == 200
        assert allowed_scheduler.json()["executed_count"] == 1


def test_competitive_coworker_delivery_rbac(monkeypatch) -> None:
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "list_site_coworker_delivery_profiles",
        lambda db, site_id: {"site_id": str(site_id), "count": 4, "rows": [{"channel": "telegram"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "upsert_site_coworker_delivery_profile",
        lambda db, **kwargs: {"status": "created", "profile": kwargs},
    )
    monkeypatch.setattr(
        competitive_api,
        "preview_site_coworker_delivery",
        lambda db, site_id, plugin_code, channel: {
            "status": "ok",
            "site_id": str(site_id),
            "plugin": {"plugin_code": plugin_code},
            "preview": {"channel": channel, "message": "preview"},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "dispatch_site_coworker_delivery",
        lambda db, site_id, plugin_code, channel, dry_run=None, force=False, actor="": {
            "status": "dry_run",
            "site_id": str(site_id),
            "plugin": {"plugin_code": plugin_code},
            "event": {"event_id": "evt-1", "channel": channel},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "list_site_coworker_delivery_events",
        lambda db, site_id, channel="", limit=100: {"site_id": str(site_id), "count": 1, "rows": [{"event_id": "evt-1"}]},
    )

    site_id = str(uuid4())
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        allowed_profiles = client.get(
            f"/competitive/sites/{site_id}/coworker/delivery/profiles",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_profiles.status_code == 200
        assert allowed_profiles.json()["count"] == 4

        allowed_preview = client.post(
            f"/competitive/sites/{site_id}/coworker/delivery/blue_log_refiner/preview",
            json={"channel": "telegram"},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_preview.status_code == 200
        assert allowed_preview.json()["status"] == "ok"

        allowed_events = client.get(
            f"/competitive/sites/{site_id}/coworker/delivery/events?limit=20",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_events.status_code == 200
        assert allowed_events.json()["count"] == 1

        denied_profile = client.post(
            f"/competitive/sites/{site_id}/coworker/delivery/profiles",
            json={"channel": "telegram"},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_profile.status_code == 403

        denied_dispatch = client.post(
            f"/competitive/sites/{site_id}/coworker/delivery/blue_log_refiner/dispatch",
            json={"channel": "telegram", "dry_run": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_dispatch.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "editor", "scopes": ["competitive:policy:write"]},
    )
    with TestClient(app) as client:
        allowed_profile = client.post(
            f"/competitive/sites/{site_id}/coworker/delivery/profiles",
            json={"channel": "telegram", "enabled": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_profile.status_code == 200
        assert allowed_profile.json()["status"] == "created"

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["competitive:approve"]},
    )
    with TestClient(app) as client:
        allowed_dispatch = client.post(
            f"/competitive/sites/{site_id}/coworker/delivery/blue_log_refiner/dispatch",
            json={"channel": "telegram", "dry_run": True, "force": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed_dispatch.status_code == 200
        assert allowed_dispatch.json()["status"] == "dry_run"


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _SequencedDB:
    def __init__(self, batches):
        self._batches = list(batches)

    def scalars(self, _stmt):
        rows = self._batches.pop(0) if self._batches else []
        return _FakeScalarResult(rows)


@dataclass
class _BreachRow:
    tenant_id: object
    severity: str
    routed: bool
    created_at: datetime


@dataclass
class _DispatchRow:
    tenant_id: object
    severity: str
    telegram_status: str
    line_status: str
    created_at: datetime


def test_action_center_sla_federation_snapshot_builds_risk_tiers() -> None:
    tenant_id = uuid4()
    now = datetime.now(timezone.utc)
    tenants = [SimpleNamespace(id=tenant_id, tenant_code="acb", created_at=now)]
    breaches = [
        _BreachRow(tenant_id=tenant_id, severity="critical", routed=True, created_at=now),
        _BreachRow(tenant_id=tenant_id, severity="high", routed=True, created_at=now),
    ]
    dispatches = [
        _DispatchRow(tenant_id=tenant_id, severity="high", telegram_status="sent", line_status="disabled", created_at=now),
        _DispatchRow(tenant_id=tenant_id, severity="critical", telegram_status="failed", line_status="sent", created_at=now),
    ]
    db = _SequencedDB([tenants, breaches, dispatches])
    snapshot = action_center_sla_federation_snapshot(db, lookback_hours=24, limit=100)

    assert snapshot["count"] == 1
    assert snapshot["rows"][0]["tenant_code"] == "acb"
    assert snapshot["rows"][0]["risk_tier"] in {"medium", "high", "critical"}
    assert snapshot["rows"][0]["breach_count"] == 2


def test_competitive_delivery_review_and_sla_routes_require_permissions(monkeypatch) -> None:
    site_id = uuid4()
    event_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "get_site_coworker_delivery_sla",
        lambda db, site_id, limit=100, approval_sla_minutes=None: {
            "status": "ok",
            "site_id": str(site_id),
            "site_code": "duck-sec-ai",
            "approval_sla_minutes": 15,
            "summary": {
                "total_events": 1,
                "pending_approval_count": 1,
                "overdue_count": 0,
                "approved_or_reviewed_count": 0,
                "average_approval_latency_seconds": 0,
            },
            "pending_rows": [],
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "review_site_coworker_delivery_event",
        lambda db, site_id, event_id, approve, actor="security_reviewer", note="": {
            "status": "sent" if approve else "rejected",
            "site_id": str(site_id),
            "site_code": "duck-sec-ai",
            "event": {
                "event_id": str(event_id),
                "site_id": str(site_id),
                "plugin_id": "",
                "plugin_code": "blue_log_refiner",
                "display_name_th": "AI Log Refiner",
                "channel": "telegram",
                "status": "sent" if approve else "rejected",
                "dry_run": False,
                "severity": "high",
                "title": "delivery",
                "preview_text": "delivery preview",
                "actor": actor,
                "response": {},
                "approval_required": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        },
    )

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["competitive:read"]},
    )
    with TestClient(app) as client:
        allowed = client.get(
            f"/competitive/sites/{site_id}/coworker/delivery/sla",
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed.status_code == 200
        denied = client.post(
            f"/competitive/sites/{site_id}/coworker/delivery/events/{event_id}/review",
            json={"approve": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["competitive:approve"]},
    )
    with TestClient(app) as client:
        reviewed = client.post(
            f"/competitive/sites/{site_id}/coworker/delivery/events/{event_id}/review",
            json={"approve": True, "actor": "security_reviewer"},
            headers={"Authorization": "Bearer demo"},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["status"] == "sent"
