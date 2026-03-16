from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.api import integrations as integrations_api
from app.main import app


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_embedded_workflow_admin_routes_require_permission(monkeypatch) -> None:
    site_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "list_site_embedded_workflow_endpoints",
        lambda db, site_id, limit=100: {"site_id": str(site_id), "count": 0, "rows": []},
    )
    monkeypatch.setattr(
        competitive_api,
        "upsert_site_embedded_workflow_endpoint",
        lambda db, **kwargs: {"status": "created", "endpoint": {"endpoint_code": kwargs["endpoint_code"]}, "token": "emb_demo", "invoke_path": "/integrations/embedded/sites/demo/x/invoke"},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_site_embedded_workflow_invocations",
        lambda db, site_id, endpoint_code="", limit=100: {"site_id": str(site_id), "count": 0, "rows": []},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_site_embedded_invoke_packs",
        lambda db, site_id, endpoint_code="", limit=100: {
            "site_id": str(site_id),
            "count": 1,
            "rows": [
                {
                    "endpoint": {"endpoint_code": "soc-alert-translator", "plugin_code": "blue_thai_alert_translator"},
                    "invoke_pack": {"invoke_path": "/integrations/embedded/sites/demo/soc-alert-translator/invoke"},
                }
            ],
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "verify_site_embedded_automation_packs",
        lambda db, site_id, endpoint_code="", limit=100: {
            "status": "ok",
            "site_id": str(site_id),
            "site_code": "duck-sec-ai",
            "count": 1,
            "ok_count": 1,
            "warning_count": 0,
            "error_count": 0,
            "rows": [],
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "list_site_embedded_activation_bundles",
        lambda db, site_id, endpoint_code="", limit=100: {
            "status": "ok",
            "site_id": str(site_id),
            "site_code": "duck-sec-ai",
            "count": 1,
            "ready_count": 1,
            "needs_attention_count": 0,
            "blocked_count": 0,
            "rows": [],
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "embedded_automation_federation_snapshot",
        lambda db, connector_source="", limit=200: {
            "status": "ok",
            "generated_at": "2026-03-15T00:00:00+00:00",
            "connector_source": connector_source,
            "count": 1,
            "summary": {"total_sites": 1, "ready_sites": 1, "warning_sites": 0, "error_sites": 0, "not_configured_sites": 0, "total_endpoints": 1, "ready_endpoints": 1, "warning_endpoints": 0, "error_endpoints": 0},
            "rows": [],
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )

    with TestClient(app) as client:
        view_ok = client.get(f"/competitive/sites/{site_id}/embedded/endpoints", headers={"Authorization": "Bearer demo"})
        assert view_ok.status_code == 200
        packs_ok = client.get(f"/competitive/sites/{site_id}/embedded/invoke-packs", headers={"Authorization": "Bearer demo"})
        assert packs_ok.status_code == 200
        assert packs_ok.json()["count"] == 1
        verify_ok = client.get(f"/competitive/sites/{site_id}/embedded/automation-verify", headers={"Authorization": "Bearer demo"})
        assert verify_ok.status_code == 200
        assert verify_ok.json()["ok_count"] == 1
        bundles_ok = client.get(f"/competitive/sites/{site_id}/embedded/activation-bundles", headers={"Authorization": "Bearer demo"})
        assert bundles_ok.status_code == 200
        assert bundles_ok.json()["ready_count"] == 1
        federation_ok = client.get("/competitive/embedded/federation/readiness", headers={"Authorization": "Bearer demo"})
        assert federation_ok.status_code == 200
        assert federation_ok.json()["summary"]["ready_sites"] == 1

        denied = client.post(
            f"/competitive/sites/{site_id}/embedded/endpoints",
            json={"endpoint_code": "soc-alert-translator", "plugin_code": "blue_thai_alert_translator"},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "editor", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        allowed = client.post(
            f"/competitive/sites/{site_id}/embedded/endpoints",
            json={"endpoint_code": "soc-alert-translator", "workflow_type": "soar_playbook", "plugin_code": ""},
            headers={"Authorization": "Bearer demo"},
        )
        assert allowed.status_code == 200
        assert allowed.json()["status"] == "created"


def test_embedded_workflow_public_invoke_maps_service_result(monkeypatch) -> None:
    monkeypatch.setattr(
        integrations_api,
        "invoke_site_embedded_workflow",
        lambda db, **kwargs: {
            "status": "dry_run",
            "site_code": kwargs["site_code"],
            "endpoint": {"endpoint_code": kwargs["endpoint_code"]},
            "invocation": {"invocation_id": str(uuid4())},
        },
    )

    with TestClient(app) as client:
        ok = client.post(
            "/integrations/embedded/sites/duck-sec-ai/soc-alert-translator/invoke",
            json={"source": "splunk", "payload": {"message": "alert"}},
            headers={"X-BRP-Embed-Token": "emb_demo.secret"},
        )
        assert ok.status_code == 200
        assert ok.json()["status"] == "dry_run"

    monkeypatch.setattr(
        integrations_api,
        "invoke_site_embedded_workflow",
        lambda db, **kwargs: {"status": "forbidden", "reason": "invalid_embed_token"},
    )
    with TestClient(app) as client:
        denied = client.post(
            "/integrations/embedded/sites/duck-sec-ai/soc-alert-translator/invoke",
            json={"source": "splunk", "payload": {"message": "alert"}},
            headers={"X-BRP-Embed-Token": "wrong"},
        )
        assert denied.status_code == 403

    monkeypatch.setattr(
        integrations_api,
        "invoke_site_embedded_workflow",
        lambda db, **kwargs: {"status": "guardrail_blocked", "reason": "rate_limit_exceeded"},
    )
    with TestClient(app) as client:
        limited = client.post(
            "/integrations/embedded/sites/duck-sec-ai/soc-alert-translator/invoke",
            json={"source": "splunk", "payload": {"message": "alert"}},
            headers={"X-BRP-Embed-Token": "emb_demo.secret"},
        )
        assert limited.status_code == 429

    monkeypatch.setattr(
        integrations_api,
        "invoke_site_embedded_workflow",
        lambda db, **kwargs: {"status": "guardrail_blocked", "reason": "replay_detected"},
    )
    with TestClient(app) as client:
        replayed = client.post(
            "/integrations/embedded/sites/duck-sec-ai/soc-alert-translator/invoke",
            json={"source": "splunk", "payload": {"message": "alert"}},
            headers={"X-BRP-Embed-Token": "emb_demo.secret"},
        )
        assert replayed.status_code == 409
