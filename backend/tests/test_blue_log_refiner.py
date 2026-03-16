from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import blue_log_refiner


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, *, scalar_values=None, scalar_batches=None, object_map=None):
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


def test_run_blue_log_refiner_returns_kpi_and_feedback_adjustments() -> None:
    site_id = uuid4()
    now = datetime.now(timezone.utc)
    site = SimpleNamespace(id=site_id, site_code="duck", display_name="Duck")
    policy = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        connector_source="splunk",
        execution_mode="pre_ingest",
        lookback_limit=200,
        min_keep_severity="medium",
        drop_recommendation_codes_json='["ignore"]',
        target_noise_reduction_pct=60,
        average_event_size_kb=4,
        enabled=True,
        owner="security",
        created_at=now,
        updated_at=now,
    )
    events = [
        SimpleNamespace(
            event_type="waf_http",
            ai_severity="low",
            source_ip="203.0.113.10",
            ai_recommendation="ignore",
            payload_json='{"source":"splunk"}',
            created_at=now,
        ),
        SimpleNamespace(
            event_type="auth_login",
            ai_severity="medium",
            source_ip="203.0.113.11",
            ai_recommendation="notify_team",
            payload_json='{"source":"splunk"}',
            created_at=now,
        ),
    ]
    feedback = [
        SimpleNamespace(
            event_type="waf_http",
            recommendation_code="ignore",
            feedback_type="keep_signal",
            created_at=now,
        )
    ]
    db = _FakeDB(object_map={site_id: site}, scalar_values=[policy], scalar_batches=[events, feedback])

    result = blue_log_refiner.run_blue_log_refiner(
        db,
        site_id=site_id,
        connector_source="splunk",
        dry_run=True,
    )

    assert result["site_code"] == "duck"
    assert result["run"]["total_events"] == 2
    assert result["run"]["feedback_adjusted_events"] >= 1
    assert result["run"]["estimated_storage_saved_kb"] >= 0
    assert len(db.added) == 1


def test_submit_blue_log_refiner_feedback_persists_row() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck")
    db = _FakeDB(object_map={site_id: site})

    result = blue_log_refiner.submit_blue_log_refiner_feedback(
        db,
        site_id=site_id,
        connector_source="cloudflare",
        feedback_type="false_positive",
        event_type="waf_http",
        recommendation_code="ignore",
        note="safe office IP",
        actor="analyst_1",
    )

    assert result["status"] == "ok"
    assert result["feedback"]["feedback_type"] == "false_positive"
    assert result["feedback"]["connector_source"] == "cloudflare"
    assert len(db.added) == 1


def test_ingest_blue_log_refiner_callback_correlates_to_latest_run() -> None:
    site_id = uuid4()
    run_id = uuid4()
    now = datetime.now(timezone.utc)
    site = SimpleNamespace(id=site_id, site_code="duck")
    run = SimpleNamespace(
        id=run_id,
        site_id=site_id,
        connector_source="splunk",
        execution_mode="pre_ingest",
        dry_run=False,
        status="ok",
        total_events=100,
        kept_events=20,
        dropped_events=80,
        feedback_adjusted_events=0,
        noise_reduction_pct=80,
        estimated_storage_saved_kb=320,
        details_json="{}",
        created_at=now,
    )
    db = _FakeDB(object_map={site_id: site, run_id: run})

    result = blue_log_refiner.ingest_blue_log_refiner_callback(
        db,
        site_id=site_id,
        connector_source="splunk",
        source_system="splunk",
        callback_type="stream_result",
        total_events=120,
        kept_events=60,
        dropped_events=60,
        estimated_storage_saved_kb=336,
        run_id=run_id,
        actor="splunk_callback",
    )

    assert result["site_code"] == "duck"
    assert result["callback"]["connector_source"] == "splunk"
    assert result["matched_run"]["run_id"] == str(run_id)
    assert result["status"] == "warning"
    assert '"callback_correlation"' in run.details_json
    assert len(db.added) == 1


def test_run_blue_log_refiner_scheduler_executes_due_schedule(monkeypatch) -> None:
    site_id = uuid4()
    now = datetime.now(timezone.utc)
    site = SimpleNamespace(id=site_id, site_code="duck")
    schedule = SimpleNamespace(
        site_id=site_id,
        connector_source="splunk",
        schedule_interval_minutes=30,
        dry_run_default=True,
        callback_ingest_enabled=True,
        enabled=True,
        updated_at=now,
        created_at=now,
    )
    db = _FakeDB(object_map={site_id: site}, scalar_batches=[[schedule]])

    monkeypatch.setattr(
        blue_log_refiner,
        "get_blue_log_refiner_policy",
        lambda _db, site_id, connector_source="generic": {
            "status": "ok",
            "policy": {"site_id": str(site_id), "connector_source": connector_source, "enabled": True},
        },
    )
    monkeypatch.setattr(
        blue_log_refiner,
        "run_blue_log_refiner",
        lambda _db, **kwargs: {
            "status": "ok",
            "run": {"run_id": "run_1", "noise_reduction_pct": 82},
        },
    )

    result = blue_log_refiner.run_blue_log_refiner_scheduler(db, limit=10, dry_run_override=None, actor="scheduler")

    assert result["scheduled_policy_count"] == 1
    assert result["executed_count"] == 1
    assert result["executed"][0]["connector_source"] == "splunk"
