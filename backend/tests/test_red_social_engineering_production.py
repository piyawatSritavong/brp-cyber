from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import red_social_engineering


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

    def flush(self):
        for row in self.added:
            if getattr(row, "id", None) is None:
                row.id = uuid4()
        return None

    def commit(self):
        return None

    def refresh(self, row):
        if getattr(row, "id", None) is None:
            row.id = uuid4()
        return None


def test_run_social_engineering_simulator_creates_pending_approval_with_roster() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, tenant_id=uuid4(), site_code="duck", display_name="Duck Sec AI", base_url="https://duck-sec-ai.vercel.app/")
    policy = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        connector_type="simulated",
        sender_name="Security Awareness",
        sender_email="security@duck.test",
        subject_prefix="[Awareness]",
        landing_base_url="https://duck-sec-ai.vercel.app",
        report_mailbox="soc@duck.test",
        require_approval=True,
        enable_open_tracking=True,
        enable_click_tracking=True,
        max_emails_per_run=20,
        kill_switch_active=False,
        allowed_domains_json='["duck-sec-ai.vercel.app"]',
        connector_config_json='{"simulate_delivery":true}',
        enabled=True,
        owner="security",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    pack = SimpleNamespace(pack_code="thai-phish-1", category="phishing")
    event = SimpleNamespace(ai_severity="high", payload_json='{"message":"credential phishing"}')
    roster = [
        SimpleNamespace(id=uuid4(), email="narisara@duck-sec-ai.vercel.app", full_name="Narisara", department="finance", tags_json='["finance"]'),
        SimpleNamespace(id=uuid4(), email="anucha@duck-sec-ai.vercel.app", full_name="Anucha", department="hr", tags_json='["hr"]'),
    ]
    db = _FakeDB(object_map={site_id: site}, scalar_values=[policy], scalar_batches=[[pack], [event], roster])

    result = red_social_engineering.run_social_engineering_simulator(
        db,
        site_id=site_id,
        campaign_name="q2_thai_phish",
        employee_segment="all_staff",
        email_count=10,
        difficulty="high",
        dry_run=False,
        actor="red_social_ai",
    )

    assert result["status"] == "pending_approval"
    assert result["run"]["execution"]["status"] == "pending_approval"
    assert result["run"]["execution"]["approval_required"] is True
    assert result["run"]["email_count"] == 2


def test_review_social_campaign_approval_dispatches_telemetry() -> None:
    site_id = uuid4()
    run_id = uuid4()
    execution_id = uuid4()
    now = datetime.now(timezone.utc)
    site = SimpleNamespace(id=site_id, tenant_id=uuid4(), site_code="duck", display_name="Duck Sec AI", base_url="https://duck-sec-ai.vercel.app/")
    run = SimpleNamespace(
        id=run_id,
        site_id=site_id,
        campaign_name="q2_thai_phish",
        employee_segment="all_staff",
        language="th",
        difficulty="medium",
        impersonation_brand="Duck Sec AI",
        email_count=1,
        dry_run=False,
        risk_score=72,
        risk_tier="high",
        summary_th="demo summary",
        details_json="{}",
        created_at=now,
    )
    execution = SimpleNamespace(
        id=execution_id,
        site_id=site_id,
        run_id=run_id,
        connector_type="simulated",
        status="pending_approval",
        approval_required=True,
        requested_by="red_social_ai",
        reviewed_by="",
        review_note="",
        dispatch_mode="queued",
        reviewed_at=None,
        dispatched_at=None,
        completed_at=None,
        killed_at=None,
        killed_by="",
        kill_reason="",
        connector_config_json='{"simulate_delivery":true}',
        telemetry_summary_json="{}",
        created_at=now,
        updated_at=now,
    )
    run.execution = execution
    policy = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        connector_type="simulated",
        sender_name="Security Awareness",
        sender_email="security@duck.test",
        subject_prefix="[Awareness]",
        landing_base_url="https://duck-sec-ai.vercel.app",
        report_mailbox="soc@duck.test",
        require_approval=True,
        enable_open_tracking=True,
        enable_click_tracking=True,
        max_emails_per_run=20,
        kill_switch_active=False,
        allowed_domains_json='["duck-sec-ai.vercel.app"]',
        connector_config_json='{"simulate_delivery":true}',
        enabled=True,
        owner="security",
        created_at=now,
        updated_at=now,
    )
    roster = [SimpleNamespace(id=uuid4(), email="narisara@duck-sec-ai.vercel.app", full_name="Narisara", department="finance", tags_json='["finance"]')]
    db = _FakeDB(object_map={site_id: site}, scalar_values=[run, execution, policy], scalar_batches=[roster])

    result = red_social_engineering.review_social_campaign(
        db,
        site_id=site_id,
        run_id=run_id,
        approve=True,
        actor="security_lead",
        note="approved",
    )

    assert result["status"] == "completed"
    assert result["run"]["execution"]["status"] == "completed"
    summary = result["run"]["execution"]["telemetry_summary"]
    assert int(summary["delivered_count"]) >= 1


def test_kill_social_campaign_marks_execution_and_recipients() -> None:
    site_id = uuid4()
    run_id = uuid4()
    execution_id = uuid4()
    now = datetime.now(timezone.utc)
    site = SimpleNamespace(id=site_id, tenant_id=uuid4(), site_code="duck", display_name="Duck Sec AI", base_url="https://duck-sec-ai.vercel.app/")
    run = SimpleNamespace(
        id=run_id,
        site_id=site_id,
        campaign_name="q2_thai_phish",
        employee_segment="all_staff",
        language="th",
        difficulty="medium",
        impersonation_brand="Duck Sec AI",
        email_count=1,
        dry_run=False,
        risk_score=72,
        risk_tier="high",
        summary_th="demo summary",
        details_json="{}",
        created_at=now,
    )
    execution = SimpleNamespace(
        id=execution_id,
        site_id=site_id,
        run_id=run_id,
        connector_type="simulated",
        status="completed",
        approval_required=False,
        requested_by="red_social_ai",
        reviewed_by="",
        review_note="",
        dispatch_mode="simulated",
        reviewed_at=None,
        dispatched_at=now,
        completed_at=now,
        killed_at=None,
        killed_by="",
        kill_reason="",
        connector_config_json='{"simulate_delivery":true}',
        telemetry_summary_json="{}",
        created_at=now,
        updated_at=now,
    )
    run.execution = execution
    recipient = SimpleNamespace(
        id=uuid4(),
        run_id=run_id,
        execution_id=execution_id,
        roster_entry_id=uuid4(),
        recipient_email="narisara@duck-sec-ai.vercel.app",
        recipient_name="Narisara",
        department="finance",
        delivery_status="opened",
        sent_at=now,
        opened_at=now,
        clicked_at=None,
        reported_at=None,
        telemetry_json="{}",
        created_at=now,
        updated_at=now,
    )
    db = _FakeDB(object_map={site_id: site}, scalar_values=[run, execution], scalar_batches=[[recipient]])

    result = red_social_engineering.kill_social_campaign(
        db,
        site_id=site_id,
        run_id=run_id,
        actor="security_operator",
        note="campaign killed",
        activate_site_kill_switch=False,
    )

    assert result["status"] == "killed"
    assert result["run"]["execution"]["status"] == "killed"
    assert result["run"]["execution"]["killed_by"] == "security_operator"


def test_ingest_social_provider_callback_updates_recipient_and_summary() -> None:
    site_id = uuid4()
    run_id = uuid4()
    execution_id = uuid4()
    recipient_id = uuid4()
    now = datetime.now(timezone.utc)
    site = SimpleNamespace(id=site_id, tenant_id=uuid4(), site_code="duck", display_name="Duck Sec AI", base_url="https://duck-sec-ai.vercel.app/")
    run = SimpleNamespace(
        id=run_id,
        site_id=site_id,
        campaign_name="thai_awareness",
        employee_segment="finance",
        language="th",
        difficulty="medium",
        impersonation_brand="Duck Sec AI",
        email_count=1,
        dry_run=False,
        risk_score=68,
        risk_tier="high",
        summary_th="demo summary",
        details_json="{}",
        created_at=now,
    )
    execution = SimpleNamespace(
        id=execution_id,
        site_id=site_id,
        run_id=run_id,
        connector_type="smtp",
        status="connector_ready",
        approval_required=False,
        requested_by="red_social_ai",
        reviewed_by="security_lead",
        review_note="approved",
        dispatch_mode="smtp",
        reviewed_at=now,
        dispatched_at=None,
        completed_at=None,
        killed_at=None,
        killed_by="",
        kill_reason="",
        connector_config_json='{"provider":"smtp_gateway"}',
        telemetry_summary_json="{}",
        created_at=now,
        updated_at=now,
    )
    run.execution = execution
    recipient = SimpleNamespace(
        id=recipient_id,
        run_id=run_id,
        execution_id=execution_id,
        roster_entry_id=uuid4(),
        recipient_email="narisara@duck-sec-ai.vercel.app",
        recipient_name="Narisara",
        department="finance",
        delivery_status="queued",
        sent_at=None,
        opened_at=None,
        clicked_at=None,
        reported_at=None,
        telemetry_json="{}",
        created_at=now,
        updated_at=now,
    )
    db = _FakeDB(
        object_map={site_id: site},
        scalar_values=[run, execution, recipient],
        scalar_batches=[[recipient]],
    )

    result = red_social_engineering.ingest_social_provider_callback(
        db,
        site_id=site_id,
        run_id=run_id,
        connector_type="smtp",
        event_type="clicked",
        recipient_email="Narisara@duck-sec-ai.vercel.app",
        occurred_at="2026-03-15T09:15:00+07:00",
        provider_event_id="smtp-evt-001",
        metadata={"provider": "smtp_gateway", "message_id": "msg-001"},
        actor="smtp_webhook",
    )

    assert result["status"] == "ok"
    assert result["callback"]["event_type"] == "clicked"
    assert result["recipient"]["delivery_status"] == "clicked"
    assert result["recipient"]["opened_at"]
    assert result["recipient"]["clicked_at"]
    assert result["run"]["execution"]["status"] == "completed"
    assert int(result["run"]["execution"]["telemetry_summary"]["clicked_count"]) == 1
    assert int(result["run"]["execution"]["telemetry_summary"]["opened_count"]) == 1
