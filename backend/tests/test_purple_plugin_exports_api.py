from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.main import app


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_purple_plugin_export_routes_enforce_permissions(monkeypatch) -> None:
    site_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "list_purple_export_template_packs",
        lambda kind="", audience="": {"status": "ok", "count": 1, "rows": [{"pack_code": "incident_company_standard"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "export_purple_mitre_heatmap",
        lambda db, **kwargs: {"status": "ok", "site_id": str(kwargs["site_id"]), "export": {"filename": "heatmap.md", "content": "# heatmap"}},
    )
    monkeypatch.setattr(
        competitive_api,
        "export_purple_incident_report",
        lambda db, **kwargs: {"status": "ok", "site_id": str(kwargs["site_id"]), "export": {"filename": "incident.md", "sections": []}},
    )
    monkeypatch.setattr(
        competitive_api,
        "export_purple_regulated_report",
        lambda db, **kwargs: {"status": "ok", "site_id": str(kwargs["site_id"]), "export": {"filename": "regulated.md", "sections": []}},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_purple_report_releases",
        lambda db, site_id, limit=20: {"status": "ok", "count": 1, "rows": [{"release_id": "rel_1", "site_id": str(site_id), "status": "pending_approval"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "request_purple_report_release",
        lambda db, **kwargs: {"status": "ok", "release": {"release_id": "rel_1", "site_id": str(kwargs["site_id"]), "status": "pending_approval"}},
    )
    monkeypatch.setattr(
        competitive_api,
        "review_purple_report_release",
        lambda db, **kwargs: {"status": "approved", "release": {"release_id": str(kwargs["release_id"]), "status": "approved"}},
    )

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        template_ok = client.get("/competitive/purple/export/template-packs", headers={"Authorization": "Bearer demo"})
        mitre_denied = client.post(
            f"/competitive/sites/{site_id}/purple/mitre-heatmap/export",
            json={},
            headers={"Authorization": "Bearer demo"},
        )
        incident_denied = client.post(
            f"/competitive/sites/{site_id}/purple/incident-report/export",
            json={},
            headers={"Authorization": "Bearer demo"},
        )
        regulated_denied = client.post(
            f"/competitive/sites/{site_id}/purple/regulatory-report/export",
            json={},
            headers={"Authorization": "Bearer demo"},
        )
        release_list_ok = client.get(
            f"/competitive/sites/{site_id}/purple/report-releases?limit=10",
            headers={"Authorization": "Bearer demo"},
        )
        release_request_denied = client.post(
            f"/competitive/sites/{site_id}/purple/report-releases",
            json={"report_kind": "incident_report"},
            headers={"Authorization": "Bearer demo"},
        )
        release_review_denied = client.post(
            "/competitive/purple/report-releases/302e4da8-4007-4f33-b3de-e26025a94848/review",
            json={"approve": True},
            headers={"Authorization": "Bearer demo"},
        )
        assert template_ok.status_code == 200
        assert template_ok.json()["count"] == 1
        assert mitre_denied.status_code == 403
        assert incident_denied.status_code == 403
        assert regulated_denied.status_code == 403
        assert release_list_ok.status_code == 200
        assert release_request_denied.status_code == 403
        assert release_review_denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        mitre_ok = client.post(
            f"/competitive/sites/{site_id}/purple/mitre-heatmap/export",
            json={"export_format": "csv"},
            headers={"Authorization": "Bearer demo"},
        )
        incident_ok = client.post(
            f"/competitive/sites/{site_id}/purple/incident-report/export",
            json={"template_pack": "incident_board_brief", "export_format": "pdf"},
            headers={"Authorization": "Bearer demo"},
        )
        regulated_ok = client.post(
            f"/competitive/sites/{site_id}/purple/regulatory-report/export",
            json={"template_pack": "regulated_nca_th", "export_format": "docx"},
            headers={"Authorization": "Bearer demo"},
        )
        release_request_ok = client.post(
            f"/competitive/sites/{site_id}/purple/report-releases",
            json={
                "report_kind": "incident_report",
                "export_format": "pdf",
                "title": "Incident Final",
                "filename": "incident-final.pdf",
                "payload": {"renderer": "native_binary"},
            },
            headers={"Authorization": "Bearer demo"},
        )
        release_review_ok = client.post(
            "/competitive/purple/report-releases/302e4da8-4007-4f33-b3de-e26025a94848/review",
            json={"approve": True, "approver": "security_lead"},
            headers={"Authorization": "Bearer demo"},
        )
        assert mitre_ok.status_code == 200
        assert incident_ok.status_code == 200
        assert regulated_ok.status_code == 200
        assert release_request_ok.status_code == 200
        assert release_review_ok.status_code == 200
