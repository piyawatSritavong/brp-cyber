from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import blue_threat_localizer


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


def test_import_threat_feed_items_tracks_import_and_update() -> None:
    existing = SimpleNamespace(
        id=uuid4(),
        source_name="thai-cert",
        source_item_id="feed-001",
        title="old",
        summary_th="old",
        category="identity",
        severity="medium",
        focus_region="thailand",
        sectors_json='["general"]',
        iocs_json="[]",
        references_json="[]",
        payload_json="{}",
        published_at=None,
        is_active=True,
        created_at=None,
        updated_at=None,
    )
    db = _FakeDB(scalar_values=[None, existing])

    result = blue_threat_localizer.import_threat_feed_items(
        db,
        source_name="thai-cert",
        items=[
            {
                "source_item_id": "feed-000",
                "title": "Thai brute-force against admin portals",
                "summary_th": "พบ brute force ต่อพอร์ทัลผู้ดูแลในไทย",
                "category": "web",
                "severity": "high",
                "focus_region": "thailand",
                "sectors": ["government", "general"],
            },
            {
                "source_item_id": "feed-001",
                "title": "Updated Thai credential phishing",
                "summary_th": "อัปเดต phishing ภาษาไทยที่เลียนแบบหน้า login",
                "category": "phishing",
                "severity": "critical",
                "focus_region": "thailand",
                "sectors": ["finance", "general"],
            },
        ],
    )

    assert result["status"] == "ok"
    assert result["imported_count"] == 1
    assert result["updated_count"] == 1
    assert existing.title == "Updated Thai credential phishing"
    assert existing.severity == "critical"
    assert len(db.added) == 1


def test_run_threat_localizer_uses_feed_matches_and_sector_profile() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", display_name="Duck Sec AI")
    policy = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        focus_region="thailand",
        sector="finance",
        subscribed_categories_json='["identity","phishing","ransomware","web"]',
        recurring_digest_enabled=True,
        schedule_interval_minutes=180,
        min_feed_priority="medium",
        enabled=True,
        owner="security",
        created_at=None,
        updated_at=None,
    )
    exploit = SimpleNamespace(risk_score=88)
    event = SimpleNamespace(ai_severity="high", payload_json='{"message":"credential login brute against admin"}')
    pack = SimpleNamespace(pack_code="identity-abuse-pack", category="identity", title="Identity Abuse Pack")
    feed = SimpleNamespace(
        id=uuid4(),
        source_name="thaicert",
        source_item_id="feed-100",
        title="Thai finance phishing wave",
        summary_th="พบ phishing ภาษาไทยปลอม OTP และหน้า login กลุ่มธนาคาร",
        category="phishing",
        severity="high",
        focus_region="thailand",
        sectors_json='["finance","general"]',
        iocs_json='["198.51.100.77"]',
        references_json='["https://example.org/threat/feed-100"]',
        payload_json='{"campaign":"otp-phish"}',
        published_at=datetime.now(timezone.utc),
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
    assert result["run"]["risk_tier"] in {"high", "critical"}
    assert result["run"]["details"]["feed_match_count"] == 1
    assert result["run"]["details"]["site_impact_score"] >= 60
    assert result["run"]["details"]["sector_profile"]["sector"] == "finance"
    assert result["run"]["details"]["headline_rows"][0]["source_name"] == "thaicert"


def test_run_threat_localizer_scheduler_executes_due_policies(monkeypatch) -> None:
    site_id = uuid4()
    policy = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        focus_region="thailand",
        sector="government",
        subscribed_categories_json='["identity","phishing"]',
        recurring_digest_enabled=True,
        schedule_interval_minutes=60,
        min_feed_priority="medium",
        enabled=True,
        updated_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db = _FakeDB(scalar_batches=[[policy]], scalar_values=[None])
    calls: list[dict[str, object]] = []

    def _fake_run(db, **kwargs):
        calls.append(kwargs)
        return {"status": "completed", "run": {"run_id": "run_demo"}}

    monkeypatch.setattr(blue_threat_localizer, "run_threat_intelligence_localizer", _fake_run)

    result = blue_threat_localizer.run_threat_localizer_scheduler(db, limit=10, dry_run_override=False)

    assert result["status"] == "ok"
    assert result["scheduled_policy_count"] == 1
    assert result["executed_count"] == 1
    assert result["skipped_count"] == 0
    assert calls[0]["site_id"] == site_id
    assert calls[0]["digest_mode"] is True
    assert calls[0]["dry_run"] is False


def test_import_threat_feed_adapter_payload_normalizes_vendor_payload() -> None:
    db = _FakeDB(scalar_values=[None])

    result = blue_threat_localizer.import_threat_feed_adapter_payload(
        db,
        source="splunk",
        payload={
            "results": [
                {
                    "sid": "splunk-001",
                    "search_name": "Thai admin brute force",
                    "description": "Repeated failed login against admin portal from suspicious IP",
                    "severity": "high",
                    "category": "identity",
                    "region": "thailand",
                    "src_ip": "198.51.100.20",
                    "tags": ["finance"],
                }
            ]
        },
    )

    assert result["status"] == "ok"
    assert result["adapter_source"] == "splunk"
    assert result["normalized_count"] == 1
    assert result["rows"][0]["source_name"] == "splunk"
    assert result["rows"][0]["category"] == "identity"
    assert result["rows"][0]["severity"] == "high"


def test_run_threat_localizer_builds_detection_gap_correlation() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", display_name="Duck Sec AI")
    policy = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        focus_region="thailand",
        sector="finance",
        subscribed_categories_json='["phishing","web"]',
        recurring_digest_enabled=True,
        schedule_interval_minutes=180,
        min_feed_priority="medium",
        enabled=True,
        owner="security",
        created_at=None,
        updated_at=None,
    )
    exploit = SimpleNamespace(risk_score=72)
    event = SimpleNamespace(ai_severity="high", payload_json='{"message":"thai phishing lure against finance users"}')
    pack = SimpleNamespace(pack_code="phishing-pack", category="phishing", title="Phishing Pack")
    feed = SimpleNamespace(
        id=uuid4(),
        source_name="splunk",
        source_item_id="feed-200",
        title="Thai finance phishing wave",
        summary_th="พบ phishing ภาษาไทยปลอมหน้า login กลุ่มการเงิน",
        category="phishing",
        severity="high",
        focus_region="thailand",
        sectors_json='["finance","general"]',
        iocs_json='["login-clone.example"]',
        references_json="[]",
        payload_json="{}",
        published_at=datetime.now(timezone.utc),
        is_active=True,
        created_at=None,
        updated_at=None,
    )
    rule = SimpleNamespace(
        rule_name="Thai phishing lure detector",
        rule_logic_json='{"keywords":["phishing","mail"]}',
        updated_at=datetime.now(timezone.utc),
    )
    endpoint = SimpleNamespace(
        connector_source="cloudflare",
        updated_at=datetime.now(timezone.utc),
        enabled=True,
    )
    db = _FakeDB(
        object_map={site_id: site},
        scalar_values=[policy, exploit],
        scalar_batches=[[event], [pack], [feed], [rule], [endpoint]],
    )

    result = blue_threat_localizer.run_threat_intelligence_localizer(
        db,
        site_id=site_id,
        focus_region="thailand",
        sector="finance",
        dry_run=True,
    )

    detection_gap = result["run"]["details"]["detection_gap"]
    coverage_rows = detection_gap["coverage_rows"]
    assert detection_gap["correlation_status"] == "covered_baseline"
    assert detection_gap["missing_categories"] == []
    assert coverage_rows[0]["category"] == "phishing"
    assert coverage_rows[0]["matched_rule_count"] >= 1
    assert "cloudflare" in coverage_rows[0]["connector_sources"]
