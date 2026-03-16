from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import integrations as integrations_api
from app.main import app


def test_public_soar_connector_callback_route_accepts_valid_payload(monkeypatch) -> None:
    monkeypatch.setattr(integrations_api, "verify_webhook_signature", lambda raw, signature: True)
    monkeypatch.setattr(integrations_api, "_lookup_site_by_code", lambda db, site_code: SimpleNamespace(id=uuid4(), site_code=site_code))
    monkeypatch.setattr(
        integrations_api,
        "ingest_playbook_connector_result",
        lambda db, **kwargs: {
            "status": "ok",
            "execution": {"execution_id": str(kwargs["execution_id"]), "status": "verified"},
            "connector_result": {"connector_source": kwargs["connector_source"], "contract_code": kwargs["contract_code"]},
            "contract": {"contract_code": kwargs["contract_code"]},
        },
    )

    with TestClient(app) as client:
        response = client.post(
            f"/integrations/soar/sites/acb-site/executions/{uuid4()}/callback",
            json={
                "connector_source": "cloudflare",
                "contract_code": "cloudflare_block_result_v1",
                "status": "confirmed",
                "payload": {"result": {"blocked_ip": "203.0.113.10"}},
            },
        )

    assert response.status_code == 200
    assert response.json()["connector_result"]["connector_source"] == "cloudflare"


def test_public_managed_responder_callback_route_accepts_valid_payload(monkeypatch) -> None:
    monkeypatch.setattr(integrations_api, "verify_webhook_signature", lambda raw, signature: True)
    monkeypatch.setattr(
        integrations_api,
        "ingest_managed_responder_callback",
        lambda db, **kwargs: {
            "status": "ok",
            "site_id": str(uuid4()),
            "site_code": kwargs["site_code"],
            "run": {"run_id": str(kwargs["run_id"]), "status": "verified"},
            "callback": {"connector_source": kwargs["connector_source"], "contract_code": kwargs["contract_code"]},
            "contract": {"contract_code": kwargs["contract_code"]},
        },
    )

    with TestClient(app) as client:
        response = client.post(
            f"/integrations/blue/managed-responder/sites/acb-site/runs/{uuid4()}/callback",
            json={
                "connector_source": "paloalto",
                "contract_code": "paloalto_dynamic_block_result_v1",
                "status": "confirmed",
                "payload": {"rule_name": "brp-acb-dynamic-block"},
            },
        )

    assert response.status_code == 200
    assert response.json()["callback"]["connector_source"] == "paloalto"
