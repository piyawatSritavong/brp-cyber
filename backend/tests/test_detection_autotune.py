from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import detection_autotune


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, scalar_values=None, scalar_batches=None, object_map=None):
        self.scalar_values = list(scalar_values or [])
        self.scalar_batches = list(scalar_batches or [])
        self.object_map = object_map or {}
        self.added = []

    def get(self, _model, object_id):
        return self.object_map.get(object_id)

    def scalar(self, _stmt):
        if not self.scalar_values:
            return None
        return self.scalar_values.pop(0)

    def scalars(self, _stmt):
        rows = self.scalar_batches.pop(0) if self.scalar_batches else []
        return _FakeScalarResult(rows)

    def add(self, row):
        self.added.append(row)

    def commit(self):
        return None

    def refresh(self, row):
        if getattr(row, "id", None) is None:
            row.id = uuid4()
        return None


def test_upsert_detection_autotune_policy_creates_record() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", tenant_id=uuid4())
    db = _FakeDB(scalar_values=[None], object_map={site_id: site})

    result = detection_autotune.upsert_detection_autotune_policy(
        db,
        site_id=site_id,
        min_risk_score=65,
        min_risk_tier="high",
        target_detection_coverage_pct=92,
        max_rules_per_run=4,
        auto_apply=True,
        route_alert=True,
        schedule_interval_minutes=30,
        enabled=True,
        owner="secops",
    )
    assert result["status"] == "created"
    assert result["policy"]["min_risk_score"] == 65
    assert result["policy"]["auto_apply"] is True
    assert len(db.added) == 1


def test_run_detection_autotune_executes_tuning_and_persists_run(monkeypatch) -> None:
    site_id = uuid4()
    tenant_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", tenant_id=tenant_id)
    tenant = SimpleNamespace(id=tenant_id, tenant_code="acb")
    db = _FakeDB(object_map={site_id: site, tenant_id: tenant})

    monkeypatch.setattr(
        detection_autotune,
        "get_detection_autotune_policy",
        lambda _db, _site_id: {
            "status": "ok",
            "policy": {
                "site_id": str(_site_id),
                "min_risk_score": 60,
                "min_risk_tier": "high",
                "target_detection_coverage_pct": 90,
                "max_rules_per_run": 3,
                "auto_apply": True,
                "route_alert": True,
                "schedule_interval_minutes": 60,
                "enabled": True,
                "owner": "security",
            },
        },
    )
    monkeypatch.setattr(
        detection_autotune,
        "_site_risk_signal",
        lambda _db, _site_id, lookback_events=500: {
            "risk_score": 78,
            "risk_tier": "high",
            "exploit_risk": 72,
            "blue_event_count": 10,
            "suspicious_event_count": 8,
            "open_suspicious_count": 4,
            "applied_suspicious_count": 2,
            "detection_coverage": 0.55,
            "apply_rate": 0.25,
        },
    )
    monkeypatch.setattr(
        detection_autotune,
        "run_detection_copilot_tuning",
        lambda _db, _site_id, payload: {
            "status": "completed",
            "tuning_run_id": str(uuid4()),
            "recommendations": [{"rule_name": "velocity"}, {"rule_name": "identity"}],
            "before_metrics": {"detection_coverage": 0.55},
            "after_metrics": {"detection_coverage": 0.78},
            "expected_detection_coverage_delta": 0.23,
        },
    )
    monkeypatch.setattr(
        detection_autotune,
        "dispatch_manual_alert",
        lambda _db, **kwargs: {"status": "ok", "routing": {"status": "dispatched"}},
    )

    result = detection_autotune.run_detection_autotune(
        db,
        site_id=site_id,
        dry_run=False,
        force=False,
        actor="tester",
    )
    assert result["status"] == "ok"
    assert result["execution"]["should_tune"] is True
    assert result["execution"]["recommendation_count"] == 2
    assert result["execution"]["applied_count"] == 2
    assert result["run"]["risk_tier"] == "high"
    assert len(db.added) == 1


def test_run_detection_autotune_scheduler_executes_due_policy(monkeypatch) -> None:
    site_id = uuid4()
    policy = SimpleNamespace(
        site_id=site_id,
        enabled=True,
        schedule_interval_minutes=30,
        updated_at=datetime.now(timezone.utc),
    )
    site = SimpleNamespace(id=site_id, site_code="duck")
    db = _FakeDB(scalar_batches=[[policy]], scalar_values=[None], object_map={site_id: site})

    monkeypatch.setattr(
        detection_autotune,
        "run_detection_autotune",
        lambda _db, site_id, dry_run=None, force=False, actor="": {
            "status": "ok",
            "run": {"run_id": str(uuid4())},
            "risk": {"risk_tier": "medium"},
        },
    )

    result = detection_autotune.run_detection_autotune_scheduler(db, limit=100, actor="scheduler")
    assert result["scheduled_policy_count"] == 1
    assert result["executed_count"] == 1
    assert result["skipped_count"] == 0
