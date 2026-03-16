from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.main import app


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_purple_roi_dashboard_routes_require_expected_permissions(monkeypatch) -> None:
    site_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "list_purple_roi_trends",
        lambda db, site_id, limit=12: {"status": "ok", "site_id": str(site_id), "count": 1, "summary": {}, "rows": []},
    )
    monkeypatch.setattr(
        competitive_api,
        "build_purple_roi_portfolio_rollup",
        lambda db, tenant_code="", limit=200: {"status": "ok", "tenant_code": tenant_code, "count": 1, "summary": {}, "rows": []},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_purple_roi_template_packs",
        lambda audience="": {"status": "ok", "count": 1, "rows": [{"pack_code": "roi_board_minimal", "audience": audience or "board"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "export_purple_roi_board_pack",
        lambda db, **kwargs: {
            "status": "ok",
            "site_id": str(kwargs["site_id"]),
            "site_code": "duck",
            "export": {
                "filename": "duck-roi.pdf",
                "sections": [],
                "slides": [],
                "renderer": "native_binary",
                "mime_type": "application/pdf",
                "byte_size": 128,
                "content_base64": "JVBERi0xLjQ=",
                "template_pack": {"pack_code": kwargs.get("template_pack", "roi_board_minimal"), "display_name": "Executive Minimal"},
            },
        },
    )

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        trends = client.get(f"/competitive/sites/{site_id}/purple/roi-dashboard/trends", headers={"Authorization": "Bearer demo"})
        portfolio = client.get("/competitive/purple/roi-dashboard/portfolio?tenant_code=acb", headers={"Authorization": "Bearer demo"})
        template_packs = client.get("/competitive/purple/roi-dashboard/template-packs?audience=board", headers={"Authorization": "Bearer demo"})
        export = client.post(
            f"/competitive/sites/{site_id}/purple/roi-dashboard/export",
            json={"export_format": "pdf", "template_pack": "roi_board_minimal", "tenant_code": "acb"},
            headers={"Authorization": "Bearer demo"},
        )
        generate_denied = client.post(
            f"/competitive/sites/{site_id}/purple/roi-dashboard/generate",
            json={},
            headers={"Authorization": "Bearer demo"},
        )

        assert trends.status_code == 200
        assert portfolio.status_code == 200
        assert template_packs.status_code == 200
        assert export.status_code == 200
        assert generate_denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "generate_purple_roi_dashboard",
        lambda db, **kwargs: {"status": "completed", "site_id": str(kwargs["site_id"]), "site_code": "duck", "snapshot": {"snapshot_id": "snap_1"}},
    )
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        generate_ok = client.post(
            f"/competitive/sites/{site_id}/purple/roi-dashboard/generate",
            json={"lookback_days": 30, "analyst_hourly_cost_usd": 18, "analyst_minutes_per_alert": 12},
            headers={"Authorization": "Bearer demo"},
        )
        assert generate_ok.status_code == 200
        assert generate_ok.json()["status"] == "completed"
