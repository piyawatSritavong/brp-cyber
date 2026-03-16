from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.main import app


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_virtual_expert_routes_require_permission_and_return_payload(monkeypatch) -> None:
    site_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "run_social_engineering_simulator",
        lambda db, **kwargs: {"status": "simulated", "site_id": str(kwargs["site_id"]), "run": {"campaign_name": "demo"}},
    )
    monkeypatch.setattr(
        competitive_api,
        "run_threat_intelligence_localizer",
        lambda db, **kwargs: {"status": "completed", "site_id": str(kwargs["site_id"]), "run": {"headline": "demo"}},
    )
    monkeypatch.setattr(
        competitive_api,
        "generate_purple_roi_dashboard",
        lambda db, **kwargs: {"status": "completed", "site_id": str(kwargs["site_id"]), "snapshot": {"snapshot_id": "demo"}},
    )
    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )

    with TestClient(app) as client:
        denied = client.post(
            f"/competitive/sites/{site_id}/red/social-simulator/run",
            json={},
            headers={"Authorization": "Bearer demo"},
        )
        assert denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        red_ok = client.post(
            f"/competitive/sites/{site_id}/red/social-simulator/run",
            json={},
            headers={"Authorization": "Bearer demo"},
        )
        blue_ok = client.post(
            f"/competitive/sites/{site_id}/blue/threat-localizer/run",
            json={},
            headers={"Authorization": "Bearer demo"},
        )
        purple_ok = client.post(
            f"/competitive/sites/{site_id}/purple/roi-dashboard/generate",
            json={},
            headers={"Authorization": "Bearer demo"},
        )
        assert red_ok.status_code == 200
        assert red_ok.json()["status"] == "simulated"
        assert blue_ok.status_code == 200
        assert blue_ok.json()["status"] == "completed"
        assert purple_ok.status_code == 200
        assert purple_ok.json()["status"] == "completed"
