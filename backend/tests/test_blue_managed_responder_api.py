from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.api import integrations as integrations_api
from app.main import app


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_managed_responder_routes_require_permission_and_return_payload(monkeypatch) -> None:
    site_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "get_managed_responder_policy",
        lambda db, site_id: {"status": "ok", "policy": {"site_id": str(site_id), "min_severity": "medium"}},
    )
    monkeypatch.setattr(
        competitive_api,
        "upsert_managed_responder_policy",
        lambda db, **kwargs: {"status": "updated", "policy": {"site_id": str(kwargs["site_id"]), "action_mode": kwargs["action_mode"]}},
    )
    monkeypatch.setattr(
        competitive_api,
        "run_managed_responder",
        lambda db, **kwargs: {"status": "dry_run", "site_id": str(kwargs["site_id"]), "run": {"run_id": "run_demo", "selected_action": "block_ip"}},
    )
    monkeypatch.setattr(
        competitive_api,
        "run_managed_responder_scheduler",
        lambda db, **kwargs: {"scheduled_policy_count": 1, "executed_count": 1, "skipped_count": 0, "executed": []},
    )
    monkeypatch.setattr(
        competitive_api,
        "review_managed_responder_run",
        lambda db, **kwargs: {"status": "applied", "run": {"run_id": str(kwargs["run_id"])}},
    )
    monkeypatch.setattr(
        competitive_api,
        "rollback_managed_responder_run",
        lambda db, **kwargs: {"status": "rolled_back", "run": {"run_id": str(kwargs["run_id"])}},
    )
    monkeypatch.setattr(
        competitive_api,
        "verify_managed_responder_evidence_chain",
        lambda db, site_id, limit=100: {"status": "ok", "site_id": str(site_id), "count": 1, "valid": True, "rows": []},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_managed_responder_vendor_packs",
        lambda source="": {"status": "ok", "count": 1, "rows": [{"connector_source": source or "cloudflare"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_managed_responder_callbacks",
        lambda db, **kwargs: {"status": "ok", "site_id": str(kwargs["site_id"]), "site_code": "duck-sec-ai", "count": 1, "rows": [{"callback_id": "cb_demo"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "ingest_managed_responder_callback",
        lambda db, **kwargs: {
            "status": "ok",
            "site_id": str(kwargs["site_id"]),
            "site_code": "duck-sec-ai",
            "run": {"run_id": str(kwargs["run_id"]), "status": "verified"},
            "callback": {"callback_id": "cb_demo", "contract_code": kwargs["contract_code"]},
            "contract": {"contract_code": kwargs["contract_code"]},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "list_managed_responder_runs",
        lambda db, site_id, limit=20: {"site_id": str(site_id), "count": 1, "rows": [{"run_id": "run_demo"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )

    with TestClient(app) as client:
        view_ok = client.get(f"/competitive/sites/{site_id}/blue/managed-responder/policy", headers={"Authorization": "Bearer demo"})
        assert view_ok.status_code == 200
        assert view_ok.json()["status"] == "ok"

        denied_write = client.post(
            f"/competitive/sites/{site_id}/blue/managed-responder/policy",
            json={},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_write.status_code == 403

        denied_run = client.post(
            f"/competitive/sites/{site_id}/blue/managed-responder/run",
            json={},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_run.status_code == 403

        denied_scheduler = client.post(
            "/competitive/blue/managed-responder/scheduler/run",
            headers={"Authorization": "Bearer demo"},
        )
        assert denied_scheduler.status_code == 403
        evidence_ok = client.get(
            f"/competitive/sites/{site_id}/blue/managed-responder/evidence/verify",
            headers={"Authorization": "Bearer demo"},
        )
        vendor_packs_ok = client.get("/competitive/blue/managed-responder/vendor-packs?source=cloudflare", headers={"Authorization": "Bearer demo"})
        callbacks_ok = client.get(
            f"/competitive/sites/{site_id}/blue/managed-responder/callbacks?connector_source=cloudflare",
            headers={"Authorization": "Bearer demo"},
        )
        assert evidence_ok.status_code == 200
        assert vendor_packs_ok.status_code == 200
        assert callbacks_ok.status_code == 200

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "editor", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        write_ok = client.post(
            f"/competitive/sites/{site_id}/blue/managed-responder/policy",
            json={"action_mode": "block_ip"},
            headers={"Authorization": "Bearer demo"},
        )
        run_ok = client.post(
            f"/competitive/sites/{site_id}/blue/managed-responder/run",
            json={},
            headers={"Authorization": "Bearer demo"},
        )
        review_ok = client.post(
            f"/competitive/sites/{site_id}/blue/managed-responder/runs/{uuid4()}/review",
            json={"approve": True, "approver": "security_lead", "note": "approved"},
            headers={"Authorization": "Bearer demo"},
        )
        rollback_ok = client.post(
            f"/competitive/sites/{site_id}/blue/managed-responder/runs/{uuid4()}/rollback",
            json={"actor": "security_operator", "note": "rollback"},
            headers={"Authorization": "Bearer demo"},
        )
        runs_ok = client.get(f"/competitive/sites/{site_id}/blue/managed-responder/runs", headers={"Authorization": "Bearer demo"})
        evidence_verify = client.get(
            f"/competitive/sites/{site_id}/blue/managed-responder/evidence/verify",
            headers={"Authorization": "Bearer demo"},
        )
        callback_ingest = client.post(
            f"/competitive/sites/{site_id}/blue/managed-responder/runs/{uuid4()}/callback",
            json={
                "connector_source": "cloudflare",
                "contract_code": "cloudflare_firewall_rule_result_v2",
                "payload": {"rule_id": "cf-rule-001"},
            },
            headers={"Authorization": "Bearer demo"},
        )
        assert write_ok.status_code == 200
        assert write_ok.json()["status"] == "updated"
        assert run_ok.status_code == 200
        assert run_ok.json()["status"] == "dry_run"
        assert review_ok.status_code == 200
        assert review_ok.json()["status"] == "applied"
        assert rollback_ok.status_code == 200
        assert rollback_ok.json()["status"] == "rolled_back"
        assert runs_ok.status_code == 200
        assert runs_ok.json()["count"] == 1
        assert evidence_verify.status_code == 200
        assert evidence_verify.json()["valid"] is True
        assert callback_ingest.status_code == 200
        assert callback_ingest.json()["callback"]["contract_code"] == "cloudflare_firewall_rule_result_v2"
        scheduler_ok = client.post("/competitive/blue/managed-responder/scheduler/run", headers={"Authorization": "Bearer demo"})
        assert scheduler_ok.status_code == 200
        assert scheduler_ok.json()["executed_count"] == 1


def test_integration_adapter_templates_route_returns_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        integrations_api,
        "list_adapter_invoke_templates",
        lambda source="": {
            "count": 1,
            "rows": [
                {
                    "source": source or "splunk",
                    "display_name": "Splunk Alert to Blue Thai Alert Translator",
                    "default_event_kind": "security_event",
                    "recommended_plugin_codes": ["blue_thai_alert_translator"],
                    "notes": ["demo"],
                    "field_mapping": [],
                    "invoke_payload": {"source": "splunk", "payload": {"message": "alert"}},
                }
            ],
        },
    )

    with TestClient(app) as client:
        response = client.get("/integrations/adapters/templates?source=splunk")
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        assert payload["rows"][0]["source"] == "splunk"
