from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import connector_credential_hygiene


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, scalar_values=None, scalar_batches=None, tenant_map=None):
        self.scalar_values = list(scalar_values or [])
        self.scalar_batches = list(scalar_batches or [])
        self.tenant_map = tenant_map or {}
        self.added = []

    def scalar(self, _stmt):
        if not self.scalar_values:
            return None
        return self.scalar_values.pop(0)

    def scalars(self, _stmt):
        rows = self.scalar_batches.pop(0) if self.scalar_batches else []
        return _FakeScalarResult(rows)

    def get(self, _model, object_id):
        return self.tenant_map.get(object_id)

    def add(self, row):
        self.added.append(row)

    def commit(self):
        return None

    def refresh(self, row):
        if getattr(row, "id", None) is None:
            row.id = uuid4()
        return None


def test_upsert_credential_hygiene_policy_creates_record() -> None:
    tenant = SimpleNamespace(id=uuid4(), tenant_code="acb")
    db = _FakeDB(scalar_values=[tenant, None])

    result = connector_credential_hygiene.upsert_credential_hygiene_policy(
        db,
        tenant_code="acb",
        connector_source="splunk",
        warning_days=9,
        max_rotate_per_run=15,
        auto_apply=True,
        route_alert=True,
        schedule_interval_minutes=30,
        enabled=True,
        owner="security_team",
    )
    assert result["status"] == "created"
    assert result["policy"]["connector_source"] == "splunk"
    assert result["policy"]["warning_days"] == 9
    assert result["policy"]["auto_apply"] is True
    assert len(db.added) == 1


def test_run_credential_hygiene_for_tenant_persists_run(monkeypatch) -> None:
    tenant = SimpleNamespace(id=uuid4(), tenant_code="acb")
    db = _FakeDB(scalar_values=[tenant])

    monkeypatch.setattr(
        connector_credential_hygiene,
        "get_credential_hygiene_policy",
        lambda _db, tenant_code, connector_source="*": {
            "status": "ok",
            "policy": {
                "warning_days": 7,
                "max_rotate_per_run": 20,
                "auto_apply": False,
                "route_alert": True,
                "connector_source": connector_source,
            },
        },
    )
    monkeypatch.setattr(
        connector_credential_hygiene,
        "auto_rotate_due_credentials",
        lambda _db, **_kwargs: {
            "status": "ok",
            "candidate_count": 2,
            "selected_count": 2,
            "planned_count": 2,
            "executed_count": 0,
            "failed_count": 0,
        },
    )
    monkeypatch.setattr(
        connector_credential_hygiene,
        "evaluate_connector_credential_hygiene",
        lambda _db, **_kwargs: {
            "status": "ok",
            "summary": {"expired_count": 0, "rotation_due_count": 2},
            "risk": {"risk_score": 71, "risk_tier": "high"},
        },
    )
    monkeypatch.setattr(
        connector_credential_hygiene,
        "dispatch_manual_alert",
        lambda _db, **_kwargs: {"status": "ok", "routing": {"status": "dispatched"}},
    )

    result = connector_credential_hygiene.run_credential_hygiene_for_tenant(
        db,
        tenant_code="acb",
        connector_source="splunk",
        dry_run=True,
        actor="tester",
    )
    assert result["status"] == "ok"
    assert result["run"]["risk_tier"] == "high"
    assert result["run"]["candidate_count"] == 2
    assert result["alert"]["status"] == "ok"
    assert len(db.added) == 1


def test_run_credential_hygiene_scheduler_executes_due_policy(monkeypatch) -> None:
    tenant_id = uuid4()
    policy = SimpleNamespace(
        tenant_id=tenant_id,
        connector_source="splunk",
        schedule_interval_minutes=60,
        updated_at=datetime.now(timezone.utc),
    )
    tenant = SimpleNamespace(id=tenant_id, tenant_code="acb")
    db = _FakeDB(scalar_batches=[[policy]], scalar_values=[None], tenant_map={tenant_id: tenant})

    monkeypatch.setattr(
        connector_credential_hygiene,
        "run_credential_hygiene_for_tenant",
        lambda _db, tenant_code, connector_source="*", dry_run=None, actor="": {
            "status": "ok",
            "run": {"run_id": str(uuid4()), "risk_tier": "medium"},
        },
    )

    result = connector_credential_hygiene.run_credential_hygiene_scheduler(
        db,
        limit=100,
        actor="tester",
        dry_run_override=True,
    )
    assert result["scheduled_policy_count"] == 1
    assert result["executed_count"] == 1
    assert result["skipped_count"] == 0
