from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.main import app


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_red_social_engineering_production_routes_require_permissions(monkeypatch) -> None:
    site_id = uuid4()
    run_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "list_social_template_packs",
        lambda **kwargs: {
            "status": "ok",
            "campaign_type": kwargs.get("campaign_type", ""),
            "jurisdiction": kwargs.get("jurisdiction", "th"),
            "count": 1,
            "rows": [{"template_pack_code": "th_awareness_basic", "campaign_type": kwargs.get("campaign_type", "awareness") or "awareness"}],
        },
    )
    monkeypatch.setattr(competitive_api, "get_social_engineering_policy", lambda db, **kwargs: {"status": "ok", "policy": {"connector_type": "simulated"}})
    monkeypatch.setattr(competitive_api, "upsert_social_engineering_policy", lambda db, **kwargs: {"status": "updated", "policy": {"connector_type": "simulated"}})
    monkeypatch.setattr(competitive_api, "import_social_roster", lambda db, **kwargs: {"status": "ok", "imported_count": 1, "updated_count": 0, "rows": []})
    monkeypatch.setattr(competitive_api, "list_social_roster", lambda db, **kwargs: {"status": "ok", "count": 1, "summary": {"active_count": 1, "high_risk_count": 0, "departments": ["finance"]}, "rows": []})
    monkeypatch.setattr(competitive_api, "review_social_campaign", lambda db, **kwargs: {"status": "completed", "run": {"run_id": str(kwargs["run_id"])}})
    monkeypatch.setattr(competitive_api, "kill_social_campaign", lambda db, **kwargs: {"status": "killed", "run": {"run_id": str(kwargs["run_id"])}})
    monkeypatch.setattr(competitive_api, "get_social_campaign_telemetry", lambda db, **kwargs: {"status": "ok", "summary": {"delivered_count": 1}, "rows": []})
    monkeypatch.setattr(
        competitive_api,
        "ingest_social_provider_callback",
        lambda db, **kwargs: {
            "status": "ok",
            "site_id": str(kwargs["site_id"]),
            "site_code": "duck",
            "run": {"run_id": str(kwargs["run_id"])},
            "recipient": {"recipient_email": kwargs["recipient_email"], "delivery_status": kwargs["event_type"]},
            "callback": {
                "event_type": kwargs["event_type"],
                "connector_type": kwargs["connector_type"],
                "occurred_at": kwargs["occurred_at"] or "",
                "provider_event_id": kwargs["provider_event_id"],
            },
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )

    with TestClient(app) as client:
        policy_ok = client.get(f"/competitive/sites/{site_id}/red/social-simulator/policy", headers={"Authorization": "Bearer demo"})
        template_packs_ok = client.get(
            "/competitive/red/social-simulator/template-packs?campaign_type=finance_notice&jurisdiction=th",
            headers={"Authorization": "Bearer demo"},
        )
        roster_ok = client.get(f"/competitive/sites/{site_id}/red/social-simulator/roster", headers={"Authorization": "Bearer demo"})
        telemetry_ok = client.get(f"/competitive/sites/{site_id}/red/social-simulator/telemetry", headers={"Authorization": "Bearer demo"})
        callback_denied = client.post(
            f"/competitive/sites/{site_id}/red/social-simulator/provider-callback",
            json={
                "run_id": str(run_id),
                "connector_type": "smtp",
                "event_type": "opened",
                "recipient_email": "narisara@example.com",
            },
            headers={"Authorization": "Bearer demo"},
        )
        review_denied = client.post(
            f"/competitive/sites/{site_id}/red/social-simulator/{run_id}/review",
            json={"approve": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert policy_ok.status_code == 200
        assert template_packs_ok.status_code == 200
        assert roster_ok.status_code == 200
        assert telemetry_ok.status_code == 200
        assert template_packs_ok.json()["campaign_type"] == "finance_notice"
        assert callback_denied.status_code == 403
        assert review_denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "operator", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        roster_import = client.post(
            f"/competitive/sites/{site_id}/red/social-simulator/roster/import",
            json={"entries": [{"email": "narisara@example.com"}]},
            headers={"Authorization": "Bearer demo"},
        )
        policy_save = client.post(
            f"/competitive/sites/{site_id}/red/social-simulator/policy",
            json={
                "connector_type": "simulated",
                "sender_name": "Demo",
                "sender_email": "demo@example.com",
                "campaign_type": "finance_notice",
                "template_pack_code": "th_finance_regulated",
                "evidence_retention_days": 365,
                "legal_ack_required": True,
            },
            headers={"Authorization": "Bearer demo"},
        )
        review_ok = client.post(
            f"/competitive/sites/{site_id}/red/social-simulator/{run_id}/review",
            json={"approve": True},
            headers={"Authorization": "Bearer demo"},
        )
        kill_ok = client.post(
            f"/competitive/sites/{site_id}/red/social-simulator/{run_id}/kill",
            json={"actor": "security_operator"},
            headers={"Authorization": "Bearer demo"},
        )
        callback_ok = client.post(
            f"/competitive/sites/{site_id}/red/social-simulator/provider-callback",
            json={
                "run_id": str(run_id),
                "connector_type": "smtp",
                "event_type": "clicked",
                "recipient_email": "narisara@example.com",
                "provider_event_id": "evt-001",
                "occurred_at": "2026-03-15T09:15:00+07:00",
                "metadata": {"provider": "smtp_gateway"},
            },
            headers={"Authorization": "Bearer demo"},
        )
        assert roster_import.status_code == 200
        assert policy_save.status_code == 200
        assert review_ok.status_code == 200
        assert kill_ok.status_code == 200
        assert callback_ok.status_code == 200
        assert callback_ok.json()["callback"]["event_type"] == "clicked"
