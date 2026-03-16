from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.main import app


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_blue_threat_localizer_routing_and_promotion_routes_enforce_permissions(monkeypatch) -> None:
    site_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "get_blue_threat_localizer_routing_policy",
        lambda db, site_id: {"status": "ok", "policy": {"site_id": str(site_id), "stakeholder_groups": ["soc_l1"]}},
    )
    monkeypatch.setattr(
        competitive_api,
        "upsert_blue_threat_localizer_routing_policy",
        lambda db, **kwargs: {"status": "ok", "policy": {"site_id": str(kwargs["site_id"]), "stakeholder_groups": kwargs["stakeholder_groups"]}},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_blue_threat_localizer_promotion_runs",
        lambda db, site_id, limit=20: {"status": "ok", "count": 1, "rows": [{"site_id": str(site_id), "status": "promoted"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "promote_blue_threat_localizer_gap",
        lambda db, **kwargs: {
            "status": "promoted",
            "site_id": str(kwargs["site_id"]),
            "site_code": "duck-sec-ai",
            "routing_policy": {"site_id": str(kwargs["site_id"])},
            "promotion": {"promotion_run_id": "promotion_1", "status": "promoted"},
        },
    )

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        routing_ok = client.get(
            f"/competitive/sites/{site_id}/blue/threat-localizer/routing-policy",
            headers={"Authorization": "Bearer demo"},
        )
        promotions_ok = client.get(
            f"/competitive/sites/{site_id}/blue/threat-localizer/promotion-runs?limit=10",
            headers={"Authorization": "Bearer demo"},
        )
        routing_denied = client.post(
            f"/competitive/sites/{site_id}/blue/threat-localizer/routing-policy",
            json={"stakeholder_groups": ["soc_l1"]},
            headers={"Authorization": "Bearer demo"},
        )
        promote_denied = client.post(
            f"/competitive/sites/{site_id}/blue/threat-localizer/promote-gap",
            json={},
            headers={"Authorization": "Bearer demo"},
        )
        assert routing_ok.status_code == 200
        assert promotions_ok.status_code == 200
        assert routing_denied.status_code == 403
        assert promote_denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        routing_save = client.post(
            f"/competitive/sites/{site_id}/blue/threat-localizer/routing-policy",
            json={
                "stakeholder_groups": ["soc_l1", "security_lead"],
                "group_channel_map": {"soc_l1": ["telegram"]},
                "category_group_map": {"phishing": ["soc_l1"]},
                "min_priority_score": 60,
                "min_risk_tier": "high",
                "auto_promote_on_gap": True,
                "auto_apply_autotune": False,
                "dispatch_via_action_center": True,
                "playbook_promotion_enabled": True,
                "owner": "security",
            },
            headers={"Authorization": "Bearer demo"},
        )
        promote_ok = client.post(
            f"/competitive/sites/{site_id}/blue/threat-localizer/promote-gap",
            json={"actor": "promotion_ai"},
            headers={"Authorization": "Bearer demo"},
        )
        assert routing_save.status_code == 200
        assert routing_save.json()["status"] == "ok"
        assert promote_ok.status_code == 200
        assert promote_ok.json()["status"] == "promoted"
