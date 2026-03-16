from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import competitive as competitive_api
from app.main import app


def _token_has_scope(verified: dict[str, object], required_scope: str) -> bool:
    scopes = set(verified.get("scopes", []))
    return "*" in scopes or required_scope in scopes


def test_blue_log_refiner_routes_enforce_permissions(monkeypatch) -> None:
    site_id = uuid4()
    monkeypatch.setattr(competitive_api, "token_has_scope", _token_has_scope)
    monkeypatch.setattr(
        competitive_api,
        "list_log_refiner_mapping_packs",
        lambda source="": {"status": "ok", "count": 1, "rows": [{"source": source or "generic"}]},
    )
    monkeypatch.setattr(
        competitive_api,
        "get_blue_log_refiner_policy",
        lambda db, site_id, connector_source="generic": {"status": "ok", "policy": {"site_id": str(site_id), "connector_source": connector_source}},
    )
    monkeypatch.setattr(
        competitive_api,
        "get_blue_log_refiner_schedule_policy",
        lambda db, site_id, connector_source="generic": {"status": "ok", "policy": {"site_id": str(site_id), "connector_source": connector_source}},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_blue_log_refiner_runs",
        lambda db, site_id, connector_source="", limit=20: {"status": "ok", "count": 0, "rows": []},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_blue_log_refiner_feedback",
        lambda db, site_id, connector_source="", limit=20: {"status": "ok", "count": 0, "rows": []},
    )
    monkeypatch.setattr(
        competitive_api,
        "list_blue_log_refiner_callbacks",
        lambda db, site_id, connector_source="", limit=20: {"status": "ok", "count": 0, "rows": []},
    )
    monkeypatch.setattr(
        competitive_api,
        "upsert_blue_log_refiner_policy",
        lambda db, **kwargs: {"status": "ok", "policy": {"site_id": str(kwargs["site_id"]), "connector_source": kwargs["connector_source"]}},
    )
    monkeypatch.setattr(
        competitive_api,
        "upsert_blue_log_refiner_schedule_policy",
        lambda db, **kwargs: {"status": "ok", "policy": {"site_id": str(kwargs["site_id"]), "connector_source": kwargs["connector_source"]}},
    )
    monkeypatch.setattr(
        competitive_api,
        "run_blue_log_refiner",
        lambda db, **kwargs: {"status": "ok", "site_id": str(kwargs["site_id"]), "run": {"run_id": "run_1", "noise_reduction_pct": 80}},
    )
    monkeypatch.setattr(
        competitive_api,
        "run_blue_log_refiner_scheduler",
        lambda db, limit=200, dry_run_override=None, actor="scheduler": {
            "timestamp": "2026-03-16T00:00:00+00:00",
            "scheduled_policy_count": 1,
            "executed_count": 1,
            "skipped_count": 0,
            "executed": [],
            "skipped": [],
        },
    )
    monkeypatch.setattr(
        competitive_api,
        "submit_blue_log_refiner_feedback",
        lambda db, **kwargs: {"status": "ok", "feedback": {"feedback_type": kwargs["feedback_type"]}},
    )
    monkeypatch.setattr(
        competitive_api,
        "ingest_blue_log_refiner_callback",
        lambda db, **kwargs: {
            "status": "ok",
            "site_id": str(kwargs["site_id"]),
            "site_code": "duck",
            "callback": {"callback_id": "cb_1", "connector_source": kwargs["connector_source"], "status": "ok"},
            "matched_run": None,
        },
    )

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "viewer", "scopes": ["control_plane:read"]},
    )
    with TestClient(app) as client:
        mapping_ok = client.get("/competitive/blue/log-refiner/mapping-packs?source=splunk", headers={"Authorization": "Bearer demo"})
        policy_ok = client.get(
            f"/competitive/sites/{site_id}/blue/log-refiner/policy?connector_source=splunk",
            headers={"Authorization": "Bearer demo"},
        )
        schedule_ok = client.get(
            f"/competitive/sites/{site_id}/blue/log-refiner/schedule-policy?connector_source=splunk",
            headers={"Authorization": "Bearer demo"},
        )
        callbacks_ok = client.get(
            f"/competitive/sites/{site_id}/blue/log-refiner/callbacks?connector_source=splunk",
            headers={"Authorization": "Bearer demo"},
        )
        run_denied = client.post(
            f"/competitive/sites/{site_id}/blue/log-refiner/run",
            json={"connector_source": "splunk"},
            headers={"Authorization": "Bearer demo"},
        )
        callback_denied = client.post(
            f"/competitive/sites/{site_id}/blue/log-refiner/callback",
            json={"connector_source": "splunk"},
            headers={"Authorization": "Bearer demo"},
        )
        scheduler_denied = client.post(
            "/competitive/blue/log-refiner/scheduler/run?limit=10",
            headers={"Authorization": "Bearer demo"},
        )
        feedback_denied = client.post(
            f"/competitive/sites/{site_id}/blue/log-refiner/feedback",
            json={"connector_source": "splunk"},
            headers={"Authorization": "Bearer demo"},
        )
        assert mapping_ok.status_code == 200
        assert policy_ok.status_code == 200
        assert schedule_ok.status_code == 200
        assert callbacks_ok.status_code == 200
        assert run_denied.status_code == 403
        assert callback_denied.status_code == 403
        assert scheduler_denied.status_code == 403
        assert feedback_denied.status_code == 403

    monkeypatch.setattr(
        competitive_api,
        "verify_admin_token",
        lambda _token: {"valid": True, "actor": "approver", "scopes": ["control_plane:write"]},
    )
    with TestClient(app) as client:
        policy_save = client.post(
            f"/competitive/sites/{site_id}/blue/log-refiner/policy",
            json={"connector_source": "splunk", "execution_mode": "pre_ingest"},
            headers={"Authorization": "Bearer demo"},
        )
        schedule_save = client.post(
            f"/competitive/sites/{site_id}/blue/log-refiner/schedule-policy",
            json={"connector_source": "splunk", "schedule_interval_minutes": 60},
            headers={"Authorization": "Bearer demo"},
        )
        run_ok = client.post(
            f"/competitive/sites/{site_id}/blue/log-refiner/run",
            json={"connector_source": "splunk", "dry_run": True},
            headers={"Authorization": "Bearer demo"},
        )
        callback_ok = client.post(
            f"/competitive/sites/{site_id}/blue/log-refiner/callback",
            json={"connector_source": "splunk", "total_events": 100, "kept_events": 25, "dropped_events": 75},
            headers={"Authorization": "Bearer demo"},
        )
        scheduler_ok = client.post(
            "/competitive/blue/log-refiner/scheduler/run?limit=10",
            headers={"Authorization": "Bearer demo"},
        )
        feedback_ok = client.post(
            f"/competitive/sites/{site_id}/blue/log-refiner/feedback",
            json={"connector_source": "splunk", "feedback_type": "keep_signal"},
            headers={"Authorization": "Bearer demo"},
        )
        assert policy_save.status_code == 200
        assert schedule_save.status_code == 200
        assert run_ok.status_code == 200
        assert callback_ok.status_code == 200
        assert scheduler_ok.status_code == 200
        assert feedback_ok.status_code == 200
