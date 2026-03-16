from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.main import app


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_soar_marketplace_pack_routes_respect_permissions(monkeypatch) -> None:
    execution_id = uuid4()
    site_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "list_marketplace_packs",
        lambda **kwargs: {
            "count": 1,
            "rows": [
                {
                    "pack_code": "thai_identity_containment_pack",
                    "audience": "soc",
                    "source_type": kwargs.get("source_type", "community"),
                    "trust_tier": kwargs.get("trust_tier", "community_reviewed"),
                    "supported_connectors": [kwargs.get("connector_source", "generic") or "generic"],
                }
            ],
            "available_filters": {"source_type": ["community", "partner"]},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "install_marketplace_pack",
        lambda db, **kwargs: {"status": "installed", "pack": {"pack_code": kwargs["pack_code"]}, "installed_count": 2},
    )
    monkeypatch.setattr(
        competitive_api,
        "verify_playbook_execution",
        lambda db, **kwargs: {"status": "verified", "verification": {"status": "verified"}, "execution": {"execution_id": str(kwargs["execution_id"])}},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_connector_result_contracts",
        lambda **kwargs: {"status": "ok", "count": 1, "rows": [{"contract_code": "cloudflare_block_result_v1", "connector_source": "cloudflare"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "ingest_playbook_connector_result",
        lambda db, **kwargs: {
            "status": "ok",
            "execution": {"execution_id": str(kwargs["execution_id"]), "status": "verified"},
            "connector_result": {"contract_code": kwargs["contract_code"], "connector_source": kwargs["connector_source"]},
            "contract": {"contract_code": kwargs["contract_code"]},
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "list_playbook_connector_results",
        lambda db, **kwargs: {"status": "ok", "count": 1, "rows": [{"contract_code": "cloudflare_block_result_v1"}], "execution": {"execution_id": str(kwargs["execution_id"])}},
    )

    with TestClient(app) as client:
        packs = client.get("/competitive/soar/marketplace/packs?source_type=community&connector_source=generic")
        assert packs.status_code == 200
        assert packs.json()["count"] == 1
        assert packs.json()["rows"][0]["source_type"] == "community"

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        install_denied = client.post(
            "/competitive/soar/marketplace/packs/thai_identity_containment_pack/install",
            json={"actor": "viewer"},
            headers={"Authorization": "Bearer demo"},
        )
        verify_denied = client.post(
            f"/competitive/soar/executions/{execution_id}/verify",
            json={"actor": "viewer"},
            headers={"Authorization": "Bearer demo"},
        )
        contracts_ok = client.get(
            "/competitive/soar/contracts/results?connector_source=cloudflare",
            headers={"Authorization": "Bearer demo"},
        )
        callback_denied = client.post(
            f"/competitive/sites/{site_id}/soar/executions/{execution_id}/connector-result",
            json={"connector_source": "cloudflare", "contract_code": "cloudflare_block_result_v1"},
            headers={"Authorization": "Bearer demo"},
        )
        assert install_denied.status_code == 403
        assert verify_denied.status_code == 403
        assert contracts_ok.status_code == 200
        assert callback_denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "editor", "scopes": ["competitive:policy:write"]},
    )
    with TestClient(app) as client:
        install_ok = client.post(
            "/competitive/soar/marketplace/packs/thai_identity_containment_pack/install",
            json={"actor": "editor", "scope_override": "community"},
            headers={"Authorization": "Bearer demo"},
        )
        assert install_ok.status_code == 200
        assert install_ok.json()["status"] == "installed"

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["competitive:approve"]},
    )
    with TestClient(app) as client:
        verify_ok = client.post(
            f"/competitive/soar/executions/{execution_id}/verify",
            json={"actor": "approver"},
            headers={"Authorization": "Bearer demo"},
        )
        callback_ok = client.post(
            f"/competitive/sites/{site_id}/soar/executions/{execution_id}/connector-result",
            json={"connector_source": "cloudflare", "contract_code": "cloudflare_block_result_v1"},
            headers={"Authorization": "Bearer demo"},
        )
        assert verify_ok.status_code == 200
        assert verify_ok.json()["status"] == "verified"
        assert callback_ok.status_code == 200

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        callback_rows = client.get(
            f"/competitive/sites/{site_id}/soar/executions/{execution_id}/connector-results?limit=10",
            headers={"Authorization": "Bearer demo"},
        )
        assert callback_rows.status_code == 200
