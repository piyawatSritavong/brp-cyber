from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.main import app


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_red_plugin_intelligence_routes_require_expected_permissions(monkeypatch) -> None:
    site_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "list_red_plugin_intelligence",
        lambda db, site_id, source_type="", limit=20: {"status": "ok", "site_id": str(site_id), "count": 0, "rows": []},
    )
    monkeypatch.setattr(
        competitive_api,
        "get_red_plugin_safety_policy",
        lambda db, site_id, target_type="web": {"status": "ok", "site_id": str(site_id), "policy": {"target_type": target_type}},
    )
    monkeypatch.setattr(
        competitive_api,
        "lint_red_plugin_output",
        lambda db, site_id, plugin_code, run_id=None, content_override="": {
            "status": "ok",
            "site_id": str(site_id),
            "plugin_code": plugin_code,
            "run_id": "",
            "lint": {"status": "pass", "issues": [], "warnings": [], "line_count": 1, "kind": "nuclei_template", "target_type": "web", "preview_excerpt": ""},
            "safety_policy": {},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "list_red_plugin_sync_sources",
        lambda db, site_id, limit=20: {"status": "ok", "site_id": str(site_id), "count": 0, "rows": []},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_red_plugin_sync_runs",
        lambda db, site_id, limit=20: {"status": "ok", "site_id": str(site_id), "count": 0, "rows": []},
    )
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )

    with TestClient(app) as client:
        intel = client.get(f"/competitive/sites/{site_id}/red/plugin-intelligence", headers={"Authorization": "Bearer demo"})
        policy = client.get(f"/competitive/sites/{site_id}/red/plugin-safety-policy", headers={"Authorization": "Bearer demo"})
        sync_sources = client.get(
            f"/competitive/sites/{site_id}/red/plugin-intelligence/sync-sources",
            headers={"Authorization": "Bearer demo"},
        )
        sync_runs = client.get(
            f"/competitive/sites/{site_id}/red/plugin-intelligence/sync-runs",
            headers={"Authorization": "Bearer demo"},
        )
        lint = client.post(
            f"/competitive/sites/{site_id}/red/plugins/red_template_writer/lint",
            json={},
            headers={"Authorization": "Bearer demo"},
        )
        denied_import = client.post(
            f"/competitive/sites/{site_id}/red/plugin-intelligence/import",
            json={"items": []},
            headers={"Authorization": "Bearer demo"},
        )
        denied_policy = client.post(
            f"/competitive/sites/{site_id}/red/plugin-safety-policy",
            json={"target_type": "web"},
            headers={"Authorization": "Bearer demo"},
        )
        denied_sync_source = client.post(
            f"/competitive/sites/{site_id}/red/plugin-intelligence/sync-sources",
            json={"source_name": "feed", "source_url": "https://example.com/feed.json"},
            headers={"Authorization": "Bearer demo"},
        )
        denied_export = client.post(
            f"/competitive/sites/{site_id}/red/plugins/red_template_writer/export",
            json={"export_kind": "bundle"},
            headers={"Authorization": "Bearer demo"},
        )
        denied_sync = client.post(
            f"/competitive/sites/{site_id}/red/plugin-intelligence/sync",
            json={"dry_run": True},
            headers={"Authorization": "Bearer demo"},
        )
        denied_scheduler = client.post(
            "/competitive/red/plugin-intelligence/scheduler/run",
            headers={"Authorization": "Bearer demo"},
        )
        denied_publish = client.post(
            f"/competitive/sites/{site_id}/red/plugins/red_template_writer/publish-threat-pack",
            json={},
            headers={"Authorization": "Bearer demo"},
        )

        assert intel.status_code == 200
        assert policy.status_code == 200
        assert sync_sources.status_code == 200
        assert sync_runs.status_code == 200
        assert lint.status_code == 200
        assert denied_import.status_code == 403
        assert denied_policy.status_code == 403
        assert denied_sync_source.status_code == 403
        assert denied_export.status_code == 403
        assert denied_sync.status_code == 403
        assert denied_scheduler.status_code == 403
        assert denied_publish.status_code == 403


def test_red_plugin_intelligence_routes_allow_write_and_export(monkeypatch) -> None:
    site_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "import_red_plugin_intelligence",
        lambda db, site_id, items, actor="": {
            "status": "ok",
            "site_id": str(site_id),
            "created_count": len(items),
            "updated_count": 0,
            "count": len(items),
            "rows": items,
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "upsert_red_plugin_safety_policy",
        lambda db, **kwargs: {"status": "updated", "policy": {"target_type": kwargs["target_type"], "allow_network_calls": kwargs["allow_network_calls"]}},
    )
    monkeypatch.setattr(
        competitive_api,
        "export_red_plugin_output",
        lambda db, **kwargs: {
            "status": "ok",
            "site_id": str(kwargs["site_id"]),
            "plugin_code": kwargs["plugin_code"],
            "run_id": "",
            "export": {"filename": "duck.yaml.json", "export_kind": kwargs["export_kind"], "artifact_type": "nuclei_template", "content": "", "metadata": {}, "lint": {}},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "upsert_red_plugin_sync_source",
        lambda db, **kwargs: {
            "status": "created",
            "source": {
                "sync_source_id": str(uuid4()),
                "site_id": str(kwargs["site_id"]),
                "source_name": kwargs["source_name"],
                "source_type": kwargs["source_type"],
                "source_url": kwargs["source_url"],
                "target_type": kwargs["target_type"],
                "parser_kind": kwargs["parser_kind"],
                "request_headers": kwargs["request_headers"],
                "sync_interval_minutes": kwargs["sync_interval_minutes"],
                "enabled": kwargs["enabled"],
                "last_synced_at": "",
                "owner": kwargs["owner"],
                "created_at": "",
                "updated_at": "",
            },
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "sync_red_plugin_intelligence_source",
        lambda db, **kwargs: {
            "status": "ok",
            "site_id": str(kwargs["site_id"]),
            "fetched_count": 2,
            "import_result": {"created_count": 2, "updated_count": 0},
            "run": {"sync_run_id": str(uuid4()), "status": "ok"},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "run_red_plugin_sync_scheduler",
        lambda db, **kwargs: {
            "status": "ok",
            "scheduled_source_count": 1,
            "executed_count": 1,
            "skipped_count": 0,
            "executed": [],
            "skipped": [],
            "generated_at": "",
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "publish_red_template_to_threat_pack",
        lambda db, **kwargs: {
            "status": "created",
            "site_id": str(kwargs["site_id"]),
            "actor": kwargs["actor"],
            "pack": {
                "pack_code": "duck-cve-2026-0001",
                "title": "Duck Pack",
                "category": "web",
                "mitre_techniques": ["T1190"],
                "attack_steps": ["nuclei template validation"],
                "validation_mode": "simulation_safe",
                "is_active": True,
                "updated_at": "",
            },
            "source_export": {},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["control_plane:write"]},
    )

    with TestClient(app) as client:
        imported = client.post(
            f"/competitive/sites/{site_id}/red/plugin-intelligence/import",
            json={"items": [{"title": "CVE", "source_type": "cve"}]},
            headers={"Authorization": "Bearer demo"},
        )
        policy = client.post(
            f"/competitive/sites/{site_id}/red/plugin-safety-policy",
            json={"target_type": "web", "allow_network_calls": False},
            headers={"Authorization": "Bearer demo"},
        )
        sync_source = client.post(
            f"/competitive/sites/{site_id}/red/plugin-intelligence/sync-sources",
            json={"source_name": "feed", "source_type": "news", "source_url": "https://example.com/feed.json", "target_type": "web"},
            headers={"Authorization": "Bearer demo"},
        )
        sync_run = client.post(
            f"/competitive/sites/{site_id}/red/plugin-intelligence/sync",
            json={"dry_run": False},
            headers={"Authorization": "Bearer demo"},
        )
        exported = client.post(
            f"/competitive/sites/{site_id}/red/plugins/red_template_writer/export",
            json={"export_kind": "threat_content_bundle"},
            headers={"Authorization": "Bearer demo"},
        )
        scheduler = client.post(
            "/competitive/red/plugin-intelligence/scheduler/run?limit=10&dry_run_override=false",
            headers={"Authorization": "Bearer demo"},
        )
        published = client.post(
            f"/competitive/sites/{site_id}/red/plugins/red_template_writer/publish-threat-pack",
            json={"activate": True},
            headers={"Authorization": "Bearer demo"},
        )

        assert imported.status_code == 200
        assert imported.json()["count"] == 1
        assert policy.status_code == 200
        assert policy.json()["policy"]["allow_network_calls"] is False
        assert sync_source.status_code == 200
        assert sync_source.json()["source"]["source_name"] == "feed"
        assert sync_run.status_code == 200
        assert sync_run.json()["fetched_count"] == 2
        assert exported.status_code == 200
        assert exported.json()["export"]["export_kind"] == "threat_content_bundle"
        assert scheduler.status_code == 200
        assert scheduler.json()["executed_count"] == 1
        assert published.status_code == 200
        assert published.json()["pack"]["pack_code"] == "duck-cve-2026-0001"
