from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.main import app


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_purple_control_family_map_routes(monkeypatch) -> None:
    site_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "build_purple_control_family_map",
        lambda db, site_id, framework="combined": {
            "status": "ok",
            "site_id": str(site_id),
            "site_code": "duck-sec-ai",
            "framework": framework,
            "generated_at": "2026-03-16T00:00:00+00:00",
            "summary": {"family_count": 1, "implemented_family_count": 1, "partial_family_count": 0, "gap_family_count": 0, "heatmap_coverage": 1, "report_release_count": 1},
            "rows": [{"framework": "ISO27001", "family_code": "A.8", "family_name": "Tech", "coverage_status": "implemented", "coverage_pct": 1}],
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "export_purple_control_family_map",
        lambda db, site_id, framework="combined", export_format="markdown": {
            "status": "ok",
            "site_id": str(site_id),
            "site_code": "duck-sec-ai",
            "export": {"export_type": "control_family_map", "export_format": export_format, "filename": "map.md", "generated_at": "2026-03-16T00:00:00+00:00", "summary": {}, "rows": [], "content": "# control map"},
        },
    )

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        read_ok = client.get(f"/competitive/sites/{site_id}/purple/control-family-map?framework=combined", headers={"Authorization": "Bearer demo"})
        write_denied = client.post(
            f"/competitive/sites/{site_id}/purple/control-family-map/export",
            json={"framework": "combined", "export_format": "csv"},
            headers={"Authorization": "Bearer demo"},
        )
        assert read_ok.status_code == 200
        assert write_denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "editor", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        write_ok = client.post(
            f"/competitive/sites/{site_id}/purple/control-family-map/export",
            json={"framework": "nist_csf", "export_format": "json"},
            headers={"Authorization": "Bearer demo"},
        )
        assert write_ok.status_code == 200
        assert write_ok.json()["export"]["export_format"] == "json"
