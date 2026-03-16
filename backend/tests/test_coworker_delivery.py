from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import coworker_delivery


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


def test_upsert_site_coworker_delivery_profile_creates_record() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck")
    db = _FakeDB(scalar_values=[None], object_map={site_id: site})

    result = coworker_delivery.upsert_site_coworker_delivery_profile(
        db,
        site_id=site_id,
        channel="telegram",
        enabled=True,
        min_severity="high",
        delivery_mode="auto",
        require_approval=True,
        include_thai_summary=True,
        webhook_url="",
        owner="secops",
    )
    assert result["status"] == "created"
    assert result["profile"]["channel"] == "telegram"
    assert result["profile"]["delivery_mode"] == "auto"
    assert len(db.added) == 1


def test_preview_site_coworker_delivery_builds_thai_message() -> None:
    site_id = uuid4()
    plugin_id = uuid4()
    run_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", display_name="Duck Sec AI")
    plugin = SimpleNamespace(
        id=plugin_id,
        plugin_code="blue_log_refiner",
        display_name="Blue Log Refiner",
        display_name_th="AI Log Refiner",
        category="blue",
        is_active=True,
    )
    run = SimpleNamespace(
        id=run_id,
        status="ok",
        output_summary_json='{"headline":"AI Log Refiner","severity":"high","summary_th":"คัด noise เหลือ 3 เหตุการณ์"}',
        created_at=datetime.now(timezone.utc),
    )
    profile = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        channel="telegram",
        enabled=True,
        min_severity="medium",
        delivery_mode="manual",
        require_approval=True,
        include_thai_summary=True,
        webhook_url="",
        owner="security",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db = _FakeDB(
        scalar_values=[plugin, run, profile],
        object_map={site_id: site},
    )

    result = coworker_delivery.preview_site_coworker_delivery(
        db,
        site_id=site_id,
        plugin_code="blue_log_refiner",
        channel="telegram",
    )
    assert result["status"] == "ok"
    assert result["preview"]["channel"] == "telegram"
    assert "คัด noise เหลือ 3 เหตุการณ์" in result["preview"]["message"]


def test_dispatch_site_coworker_delivery_records_sent_event(monkeypatch) -> None:
    site_id = uuid4()
    plugin_id = uuid4()
    run_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", display_name="Duck Sec AI")
    plugin = SimpleNamespace(
        id=plugin_id,
        plugin_code="purple_incident_ghostwriter",
        display_name="Incident Report Ghostwriter",
        display_name_th="ผู้ช่วยร่าง Incident Report",
        category="purple",
        is_active=True,
    )
    run = SimpleNamespace(
        id=run_id,
        status="ok",
        output_summary_json='{"headline":"ร่าง Incident Report","severity":"high","summary_th":"พร้อมส่งทีมบริหาร"}',
        created_at=datetime.now(timezone.utc),
    )
    profile = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        channel="line",
        enabled=True,
        min_severity="medium",
        delivery_mode="auto",
        require_approval=False,
        include_thai_summary=True,
        webhook_url="",
        owner="security",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db = _FakeDB(
        scalar_values=[plugin, run, profile, plugin],
        object_map={site_id: site},
    )
    monkeypatch.setattr(coworker_delivery, "send_line_message", lambda message: "Incident Report" in message or "ร่าง Incident Report" in message)

    result = coworker_delivery.dispatch_site_coworker_delivery(
        db,
        site_id=site_id,
        plugin_code="purple_incident_ghostwriter",
        channel="line",
        dry_run=False,
        force=False,
        actor="dashboard_operator",
    )
    assert result["status"] == "sent"
    assert result["event"]["channel"] == "line"
    assert len(db.added) == 1


def test_review_site_coworker_delivery_event_dispatches_after_approval(monkeypatch) -> None:
    site_id = uuid4()
    plugin_id = uuid4()
    event_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", display_name="Duck Sec AI")
    plugin = SimpleNamespace(
        id=plugin_id,
        plugin_code="blue_thai_alert_translator",
        display_name="Thai Alert Translator",
        display_name_th="ตัวแปล Alert ภาษาไทย",
        category="blue",
        is_active=True,
    )
    event = SimpleNamespace(
        id=event_id,
        site_id=site_id,
        plugin_id=plugin_id,
        plugin=plugin,
        channel="telegram",
        status="approval_required",
        dry_run=False,
        severity="high",
        title="ต้องตรวจสอบ Alert",
        preview_text="alert preview",
        actor="dashboard_operator",
        response_json='{"profile":{"enabled":true,"webhook_url":"","require_approval":true},"preview":{"title":"ต้องตรวจสอบ Alert","message":"แจ้งเตือนภาษาไทย","payload":{"severity":"high"}},"approval_requested_at":"2026-03-15T00:00:00+00:00"}',
        created_at=datetime.now(timezone.utc),
    )
    db = _FakeDB(object_map={site_id: site, event_id: event})
    monkeypatch.setattr(coworker_delivery, "send_telegram_message", lambda message: "แจ้งเตือนภาษาไทย" in message)

    result = coworker_delivery.review_site_coworker_delivery_event(
        db,
        site_id=site_id,
        event_id=event_id,
        approve=True,
        actor="security_reviewer",
        note="approved for dispatch",
    )

    assert result["status"] == "sent"
    assert result["event"]["status"] == "sent"
    assert result["event"]["approval_required"] is True


def test_get_site_coworker_delivery_sla_counts_pending_and_reviewed() -> None:
    site_id = uuid4()
    plugin_id = uuid4()
    plugin = SimpleNamespace(
        id=plugin_id,
        plugin_code="purple_incident_ghostwriter",
        display_name="Incident Report Ghostwriter",
        display_name_th="ผู้ช่วยร่าง Incident Report",
        category="purple",
    )
    site = SimpleNamespace(id=site_id, site_code="duck")
    pending = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        plugin_id=plugin_id,
        plugin=plugin,
        channel="line",
        status="approval_required",
        dry_run=False,
        severity="high",
        title="pending event",
        preview_text="pending",
        actor="dashboard_operator",
        response_json="{}",
        created_at=datetime(2026, 3, 14, 0, 0, tzinfo=timezone.utc),
    )
    reviewed = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        plugin_id=plugin_id,
        plugin=plugin,
        channel="telegram",
        status="sent",
        dry_run=False,
        severity="high",
        title="reviewed event",
        preview_text="reviewed",
        actor="security_reviewer",
        response_json='{"review":{"approval_latency_seconds":120}}',
        created_at=datetime.now(timezone.utc),
    )
    db = _FakeDB(object_map={site_id: site}, scalar_batches=[[pending, reviewed]])

    result = coworker_delivery.get_site_coworker_delivery_sla(db, site_id=site_id, approval_sla_minutes=15)

    assert result["status"] == "ok"
    assert result["summary"]["pending_approval_count"] == 1
    assert result["summary"]["approved_or_reviewed_count"] == 1
    assert result["summary"]["average_approval_latency_seconds"] == 120


def test_run_coworker_delivery_escalation_scheduler_filters_site_and_plugin(monkeypatch) -> None:
    site_id = uuid4()
    policy = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        plugin_code="blue_thai_alert_translator",
        enabled=True,
        updated_at=datetime.now(timezone.utc),
    )
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    db = _FakeDB(object_map={site_id: site}, scalar_batches=[[policy]])
    monkeypatch.setattr(
        coworker_delivery,
        "run_site_coworker_delivery_escalation",
        lambda _db, **kwargs: {
            "status": "ok",
            "executed_count": 1,
            "skipped_count": 0,
            "site_id": str(kwargs["site_id"]),
            "site_code": "duck-sec-ai",
        },
    )

    result = coworker_delivery.run_coworker_delivery_escalation_scheduler(
        db,
        site_id=site_id,
        plugin_code="blue_thai_alert_translator",
        limit=10,
        dry_run_override=False,
        actor="scheduler",
    )

    assert result["scheduled_policy_count"] == 1
    assert result["executed_count"] == 1
    assert result["skipped_count"] == 0
    assert result["executed"][0]["plugin_code"] == "blue_thai_alert_translator"
    assert result["dry_run"] is False


def test_coworker_delivery_escalation_federation_snapshot_aggregates_sites(monkeypatch) -> None:
    site_attention_id = uuid4()
    site_empty_id = uuid4()
    attention_site = SimpleNamespace(
        id=site_attention_id,
        site_code="attention-site",
        tenant_code="acb",
        updated_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    empty_site = SimpleNamespace(
        id=site_empty_id,
        site_code="empty-site",
        tenant_code="xyz",
        updated_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    profile = SimpleNamespace(enabled=True, delivery_mode="auto", channel="telegram")
    policy = SimpleNamespace(enabled=True, plugin_code="blue_thai_alert_translator", updated_at=datetime.now(timezone.utc))
    db = _FakeDB(scalar_batches=[[attention_site, empty_site], [profile], [policy], [], []])
    monkeypatch.setattr(
        coworker_delivery,
        "get_site_coworker_delivery_sla",
        lambda _db, site_id, **kwargs: {
            "summary": {
                "pending_approval_count": 1 if site_id == site_attention_id else 0,
                "overdue_count": 0,
                "average_approval_latency_seconds": 90 if site_id == site_attention_id else 0,
            }
        },
    )

    result = coworker_delivery.coworker_delivery_escalation_federation_snapshot(db, limit=10)

    assert result["status"] == "ok"
    assert result["summary"]["attention_sites"] == 1
    assert result["summary"]["not_configured_sites"] == 1
    assert result["summary"]["enabled_profile_total"] == 1
