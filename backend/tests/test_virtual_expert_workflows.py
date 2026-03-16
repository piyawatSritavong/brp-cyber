from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import blue_threat_localizer, purple_roi_dashboard, red_social_engineering


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


def test_run_social_engineering_simulator_persists_thai_campaign() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", display_name="Duck Sec AI", base_url="https://duck-sec-ai.vercel.app/")
    pack = SimpleNamespace(pack_code="thai-phish-1", category="phishing")
    event = SimpleNamespace(ai_severity="high", payload_json='{"message":"credential phishing"}')
    db = _FakeDB(object_map={site_id: site}, scalar_batches=[[pack], [event], []])

    result = red_social_engineering.run_social_engineering_simulator(
        db,
        site_id=site_id,
        campaign_name="q1_thai_phish",
        employee_segment="finance",
        email_count=120,
        difficulty="high",
        impersonation_brand="Duck HR",
        dry_run=True,
    )

    assert result["status"] == "simulated"
    assert result["run"]["campaign_name"] == "q1_thai_phish"
    assert result["run"]["risk_tier"] in {"medium", "high", "critical"}
    assert "email_subjects_th" in result["run"]["details"]
    assert len(db.added) >= 2


def test_run_threat_intelligence_localizer_returns_localized_headlines() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", display_name="Duck Sec AI")
    policy = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        focus_region="thailand",
        sector="finance",
        subscribed_categories_json='["identity","phishing","ransomware","web"]',
        recurring_digest_enabled=True,
        schedule_interval_minutes=240,
        min_feed_priority="medium",
        enabled=True,
        owner="security",
        created_at=None,
        updated_at=None,
    )
    exploit = SimpleNamespace(risk_score=72)
    event = SimpleNamespace(ai_severity="medium", payload_json='{"message":"login auth brute"}')
    pack = SimpleNamespace(pack_code="id-1", category="identity", title="Identity abuse pack")
    feed = SimpleNamespace(
        id=uuid4(),
        source_name="thai-cert",
        source_item_id="feed-1",
        title="Thai credential phishing",
        summary_th="พบ phishing ภาษาไทยเลียนแบบหน้า login",
        category="phishing",
        severity="high",
        focus_region="thailand",
        sectors_json='["finance","general"]',
        iocs_json='["198.51.100.44"]',
        references_json='["https://example.org/feed-1"]',
        payload_json='{"campaign":"thai-phish"}',
        published_at=None,
        is_active=True,
        created_at=None,
        updated_at=None,
    )
    db = _FakeDB(object_map={site_id: site}, scalar_values=[policy, exploit], scalar_batches=[[event], [pack], [feed]])

    result = blue_threat_localizer.run_threat_intelligence_localizer(
        db,
        site_id=site_id,
        focus_region="thailand",
        sector="finance",
        dry_run=True,
    )

    assert result["status"] == "completed"
    assert result["run"]["priority_score"] >= 18
    assert "headline_rows" in result["run"]["details"]
    assert result["run"]["details"]["feed_match_count"] >= 1
    assert result["run"]["details"]["site_impact_score"] >= 1
    assert "ไทย" in result["run"]["summary_th"] or "thailand" in result["run"]["summary_th"].lower()
    assert len(db.added) == 1


def test_generate_purple_roi_dashboard_snapshot_returns_board_metrics() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", display_name="Duck Sec AI")
    red_scan = SimpleNamespace(ai_summary="AI Red Assessment: risk=high score=80.")
    exploit = SimpleNamespace(risk_score=84)
    blue_open = SimpleNamespace(ai_severity="high", status="open", ai_recommendation="block_ip")
    blue_applied = SimpleNamespace(ai_severity="medium", status="applied", ai_recommendation="limit_user")
    blue_noise = SimpleNamespace(ai_severity="low", status="open", ai_recommendation="ignore")
    purple = SimpleNamespace(created_at=datetime.now(timezone.utc))
    rule = SimpleNamespace(updated_at=datetime.now(timezone.utc))
    db = _FakeDB(
        object_map={site_id: site},
        scalar_batches=[[red_scan], [exploit], [blue_open, blue_applied, blue_noise], [purple], [rule]],
    )

    result = purple_roi_dashboard.generate_purple_roi_dashboard(
        db,
        site_id=site_id,
        lookback_days=30,
        analyst_hourly_cost_usd=20.0,
        analyst_minutes_per_alert=10,
    )

    assert result["status"] == "completed"
    board_metrics = result["snapshot"]["summary"]["board_metrics"]
    assert board_metrics["validated_findings"] >= 1
    assert board_metrics["noise_reduction_pct"] > 0
    assert result["snapshot"]["details"]["top_value_drivers"]
    assert len(db.added) == 1
