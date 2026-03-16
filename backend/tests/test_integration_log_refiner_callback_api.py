from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import integrations as integrations_api
from app.main import app


def test_public_log_refiner_callback_route_accepts_valid_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        integrations_api,
        "ingest_blue_log_refiner_callback",
        lambda db, **kwargs: {
            "status": "ok",
            "site_id": "site-1",
            "site_code": kwargs["site_code"],
            "callback": {
                "callback_id": "cb_1",
                "connector_source": kwargs["connector_source"],
                "status": "ok",
            },
            "matched_run": None,
        },
    )

    with TestClient(app) as client:
        response = client.post(
            "/integrations/blue/log-refiner/sites/acb-site/callback",
            json={
                "connector_source": "splunk",
                "total_events": 100,
                "kept_events": 22,
                "dropped_events": 78,
            },
        )

    assert response.status_code == 200
    assert response.json()["callback"]["connector_source"] == "splunk"
