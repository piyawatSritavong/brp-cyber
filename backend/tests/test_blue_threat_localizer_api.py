from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.main import app


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_blue_threat_localizer_routes_enforce_permissions(monkeypatch) -> None:
    site_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "get_threat_localizer_policy",
        lambda db, site_id: {"status": "ok", "policy": {"site_id": str(site_id), "focus_region": "thailand"}},
    )
    monkeypatch.setattr(
        competitive_api,
        "upsert_threat_localizer_policy",
        lambda db, **kwargs: {"status": "updated", "policy": kwargs},
    )
    monkeypatch.setattr(
        competitive_api,
        "import_threat_feed_items",
        lambda db, **kwargs: {"status": "ok", "imported_count": len(kwargs.get("items", [])), "updated_count": 0},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_threat_feed_items",
        lambda db, **kwargs: {"status": "ok", "count": 1, "rows": [{"title": "Thai feed"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_threat_sector_profiles",
        lambda: {"status": "ok", "count": 1, "rows": [{"sector": "finance", "label_th": "การเงิน/ธนาคาร"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_threat_feed_adapter_templates",
        lambda source="": {
            "status": "ok",
            "count": 1,
            "rows": [{"source": source or "generic", "display_name": "Generic Adapter", "field_mapping": [], "categories_supported": []}],
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "import_threat_feed_adapter_payload",
        lambda db, **kwargs: {
            "status": "ok",
            "adapter_source": kwargs.get("source", "generic"),
            "normalized_count": 1,
            "imported_count": 1,
            "updated_count": 0,
            "rows": [],
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "run_threat_localizer_scheduler",
        lambda db, **kwargs: {"status": "ok", "scheduled_policy_count": 1, "executed_count": 1, "skipped_count": 0, "executed": [], "skipped": [], "generated_at": "2026-03-15T00:00:00+00:00"},
    )

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        view_policy = client.get(f"/competitive/sites/{site_id}/blue/threat-localizer/policy", headers={"Authorization": "Bearer demo"})
        view_feed = client.get("/competitive/blue/threat-localizer/feed-items", headers={"Authorization": "Bearer demo"})
        view_adapters = client.get("/competitive/blue/threat-localizer/feed-adapters?source=splunk", headers={"Authorization": "Bearer demo"})
        view_profiles = client.get("/competitive/blue/threat-localizer/sector-profiles", headers={"Authorization": "Bearer demo"})
        denied_policy_write = client.post(
            f"/competitive/sites/{site_id}/blue/threat-localizer/policy",
            json={},
            headers={"Authorization": "Bearer demo"},
        )
        denied_feed_import = client.post(
            "/competitive/blue/threat-localizer/feed-items/import",
            json={"items": []},
            headers={"Authorization": "Bearer demo"},
        )
        denied_adapter_import = client.post(
            "/competitive/blue/threat-localizer/feed-adapters/import",
            json={"source": "splunk", "payload": {"results": []}},
            headers={"Authorization": "Bearer demo"},
        )
        denied_scheduler = client.post(
            "/competitive/blue/threat-localizer/scheduler/run",
            headers={"Authorization": "Bearer demo"},
        )

        assert view_policy.status_code == 200
        assert view_feed.status_code == 200
        assert view_adapters.status_code == 200
        assert view_profiles.status_code == 200
        assert denied_policy_write.status_code == 403
        assert denied_feed_import.status_code == 403
        assert denied_adapter_import.status_code == 403
        assert denied_scheduler.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        save_policy = client.post(
            f"/competitive/sites/{site_id}/blue/threat-localizer/policy",
            json={
                "focus_region": "thailand",
                "sector": "finance",
                "subscribed_categories": ["identity", "phishing"],
                "recurring_digest_enabled": True,
                "schedule_interval_minutes": 240,
                "min_feed_priority": "medium",
                "enabled": True,
                "owner": "security",
            },
            headers={"Authorization": "Bearer demo"},
        )
        import_feed = client.post(
            "/competitive/blue/threat-localizer/feed-items/import",
            json={
                "source_name": "thai-cert",
                "items": [{"title": "Thai credential phishing"}],
                "actor": "feed_editor",
            },
            headers={"Authorization": "Bearer demo"},
        )
        import_feed_adapter = client.post(
            "/competitive/blue/threat-localizer/feed-adapters/import",
            json={
                "source": "splunk",
                "payload": {"results": [{"search_name": "Thai credential phishing"}]},
                "actor": "feed_adapter_editor",
            },
            headers={"Authorization": "Bearer demo"},
        )
        run_scheduler = client.post(
            "/competitive/blue/threat-localizer/scheduler/run?limit=50&dry_run_override=true",
            headers={"Authorization": "Bearer demo"},
        )

        assert save_policy.status_code == 200
        assert save_policy.json()["status"] == "updated"
        assert import_feed.status_code == 200
        assert import_feed.json()["status"] == "ok"
        assert import_feed_adapter.status_code == 200
        assert import_feed_adapter.json()["adapter_source"] == "splunk"
        assert run_scheduler.status_code == 200
        assert run_scheduler.json()["status"] == "ok"
