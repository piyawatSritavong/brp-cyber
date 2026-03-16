from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.main import app


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_purple_attack_layer_workflow_routes(monkeypatch) -> None:
    site_id = uuid4()
    layer_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "list_purple_attack_layer_workspaces",
        lambda db, site_id, limit=20: {
            "status": "ok",
            "site_id": str(site_id),
            "site_code": "duck-sec-ai",
            "count": 1,
            "rows": [{"workspace_id": str(layer_id), "layer_name": "Purple Layer", "source_kind": "imported", "actor": "purple_operator", "title": "Purple Layer", "notes": "", "layer": {}, "summary": {"technique_count": 1}, "created_at": "", "updated_at": ""}],
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "import_purple_attack_layer_workspace",
        lambda db, **kwargs: {
            "status": "ok",
            "site_id": str(kwargs["site_id"]),
            "site_code": "duck-sec-ai",
            "workspace": {"workspace_id": str(layer_id), "layer_name": kwargs["layer_name"], "source_kind": "imported", "actor": kwargs["actor"], "title": kwargs["layer_name"], "notes": kwargs["notes"], "layer": kwargs["layer_document"], "summary": {"technique_count": 1}, "created_at": "", "updated_at": ""},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "update_purple_attack_layer_workspace",
        lambda db, **kwargs: {
            "status": "ok",
            "site_id": str(kwargs["site_id"]),
            "site_code": "duck-sec-ai",
            "workspace": {"workspace_id": str(kwargs["layer_id"]), "layer_name": kwargs["layer_name"] or "Purple Layer", "source_kind": "imported", "actor": kwargs["actor"], "title": "Purple Layer", "notes": kwargs["notes"], "layer": {}, "summary": {"technique_count": 1}, "created_at": "", "updated_at": ""},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "export_purple_attack_layer_workspace",
        lambda db, **kwargs: {
            "status": "ok",
            "site_id": str(kwargs["site_id"]),
            "site_code": "duck-sec-ai",
            "workspace": {"workspace_id": str(kwargs["layer_id"])},
            "export": {"export_type": "attack_layer_workspace", "export_format": kwargs["export_format"], "filename": "layer.svg", "generated_at": "", "content": "<svg />"},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "export_live_purple_attack_layer_graphic",
        lambda db, **kwargs: {
            "status": "ok",
            "site_id": str(kwargs["site_id"]),
            "site_code": "duck-sec-ai",
            "export": {"export_type": "attack_layer_live", "export_format": kwargs["export_format"], "filename": "live.svg", "generated_at": "", "technique_count": 2, "content": "<svg />"},
        },
    )

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        list_ok = client.get(f"/competitive/sites/{site_id}/purple/mitre-heatmap/layers?limit=10", headers={"Authorization": "Bearer demo"})
        export_ok = client.post(
            f"/competitive/sites/{site_id}/purple/mitre-heatmap/layers/{layer_id}/export",
            json={"export_format": "svg"},
            headers={"Authorization": "Bearer demo"},
        )
        live_ok = client.post(
            f"/competitive/sites/{site_id}/purple/mitre-heatmap/graphical-export",
            json={"export_format": "svg"},
            headers={"Authorization": "Bearer demo"},
        )
        import_denied = client.post(
            f"/competitive/sites/{site_id}/purple/mitre-heatmap/layers/import",
            json={"layer_name": "Purple Layer", "layer_document": {"techniques": []}},
            headers={"Authorization": "Bearer demo"},
        )
        assert list_ok.status_code == 200
        assert export_ok.status_code == 200
        assert live_ok.status_code == 200
        assert import_denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "editor", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        import_ok = client.post(
            f"/competitive/sites/{site_id}/purple/mitre-heatmap/layers/import",
            json={"layer_name": "Purple Layer", "layer_document": {"techniques": [{"techniqueID": "T1110"}]}, "notes": "imported"},
            headers={"Authorization": "Bearer demo"},
        )
        edit_ok = client.post(
            f"/competitive/sites/{site_id}/purple/mitre-heatmap/layers/{layer_id}/edit",
            json={"notes": "updated", "technique_overrides": [{"techniqueID": "T1110", "score": 90}]},
            headers={"Authorization": "Bearer demo"},
        )
        assert import_ok.status_code == 200
        assert edit_ok.status_code == 200
