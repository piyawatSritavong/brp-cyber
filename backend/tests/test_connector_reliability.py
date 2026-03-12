from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import connector_reliability


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


def test_upsert_connector_reliability_policy_creates_record() -> None:
    tenant = SimpleNamespace(id=uuid4(), tenant_code="acb")
    db = _FakeDB(scalar_values=[tenant, None])

    result = connector_reliability.upsert_connector_reliability_policy(
        db,
        tenant_code="acb",
        connector_source="splunk",
        max_replay_per_run=20,
        max_attempts=3,
        auto_replay_enabled=True,
        route_alert=True,
        schedule_interval_minutes=30,
        enabled=True,
        owner="security",
    )
    assert result["status"] == "created"
    assert result["policy"]["connector_source"] == "splunk"
    assert result["policy"]["max_replay_per_run"] == 20
    assert len(db.added) == 1


def test_run_connector_dead_letter_replay_records_run(monkeypatch) -> None:
    tenant = SimpleNamespace(id=uuid4(), tenant_code="acb")
    db = _FakeDB(scalar_values=[tenant])
    captured_events: list[dict[str, object]] = []

    monkeypatch.setattr(
        connector_reliability,
        "get_connector_reliability_policy",
        lambda _db, tenant_code, connector_source="*": {
            "status": "ok",
            "policy": {
                "connector_source": "*",
                "max_replay_per_run": 10,
                "max_attempts": 4,
                "auto_replay_enabled": True,
                "route_alert": True,
                "enabled": True,
            },
        },
    )
    monkeypatch.setattr(
        connector_reliability,
        "list_connector_dead_letter_backlog",
        lambda _db, tenant_code, connector_source="", limit=200: {
            "status": "ok",
            "summary": {"unresolved_count": 2},
            "rows": [
                {
                    "event_id": str(uuid4()),
                    "connector_source": "splunk",
                    "event_type": "dead_letter",
                    "attempt": 1,
                    "latency_ms": 220,
                    "error_message": "destination_api_timeout",
                    "replayed": False,
                },
                {
                    "event_id": str(uuid4()),
                    "connector_source": "sentinel",
                    "event_type": "dead_letter",
                    "attempt": 2,
                    "latency_ms": 340,
                    "error_message": "temporary_auth_failure",
                    "replayed": False,
                },
            ],
        },
    )
    monkeypatch.setattr(
        connector_reliability,
        "record_connector_event",
        lambda _db, **kwargs: captured_events.append(kwargs),
    )
    monkeypatch.setattr(
        connector_reliability,
        "dispatch_manual_alert",
        lambda _db, **kwargs: {"status": "ok", "routing": {"status": "dispatched"}},
    )

    result = connector_reliability.run_connector_dead_letter_replay(
        db,
        tenant_code="acb",
        connector_source="*",
        dry_run=False,
        actor="tester",
    )
    assert result["status"] == "ok"
    assert result["execution"]["selected_count"] == 2
    assert result["execution"]["replayed_count"] == 2
    assert result["execution"]["failed_count"] == 0
    assert result["run"]["status"] == "ok"
    assert len(db.added) == 1
    assert len(captured_events) >= 5  # retry + success per candidate + replay_batch


def test_run_connector_replay_scheduler_executes_due_policy(monkeypatch) -> None:
    tenant_id = uuid4()
    policy = SimpleNamespace(
        tenant_id=tenant_id,
        connector_source="splunk",
        enabled=True,
        updated_at=datetime.now(timezone.utc),
        schedule_interval_minutes=30,
    )
    tenant = SimpleNamespace(id=tenant_id, tenant_code="acb")
    db = _FakeDB(scalar_values=[None], scalar_batches=[[policy]], tenant_map={tenant_id: tenant})

    monkeypatch.setattr(
        connector_reliability,
        "run_connector_dead_letter_replay",
        lambda _db, tenant_code, connector_source="*", dry_run=None, actor="": {
            "status": "ok",
            "run": {"run_id": str(uuid4())},
            "risk": {"risk_tier": "low"},
        },
    )

    result = connector_reliability.run_connector_replay_scheduler(db, limit=100, actor="scheduler")
    assert result["scheduled_policy_count"] == 1
    assert result["executed_count"] == 1
    assert result["skipped_count"] == 0


@dataclass
class _RunRow:
    replayed_count: int
    failed_count: int


def test_connector_reliability_federation_aggregates_risk(monkeypatch) -> None:
    tenant_acb = SimpleNamespace(id=uuid4(), tenant_code="acb", created_at=datetime.now(timezone.utc))
    tenant_zeta = SimpleNamespace(id=uuid4(), tenant_code="zeta", created_at=datetime.now(timezone.utc))
    db = _FakeDB(
        scalar_batches=[
            [tenant_acb, tenant_zeta],
            [_RunRow(replayed_count=12, failed_count=1)],
            [_RunRow(replayed_count=2, failed_count=5)],
        ]
    )

    monkeypatch.setattr(
        connector_reliability,
        "list_connector_dead_letter_backlog",
        lambda _db, tenant_code, connector_source="", limit=200: {
            "status": "ok",
            "summary": {"unresolved_count": 2 if tenant_code == "acb" else 18},
            "rows": [],
        },
    )

    result = connector_reliability.connector_reliability_federation(db, limit=50)
    assert result["count"] == 2
    assert result["rows"][0]["tenant_code"] == "zeta"
    assert result["rows"][0]["risk_tier"] in {"high", "critical"}
