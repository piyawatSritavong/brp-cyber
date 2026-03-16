from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import blue_threat_localizer_promotion


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


def test_upsert_blue_threat_localizer_routing_policy_normalizes_payload() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id)
    db = _FakeDB(object_map={site_id: site}, scalar_values=[None])

    result = blue_threat_localizer_promotion.upsert_blue_threat_localizer_routing_policy(
        db,
        site_id=site_id,
        stakeholder_groups=["SOC_L1", "security_lead"],
        group_channel_map={"SOC_L1": ["Telegram"], "security_lead": ["LINE"]},
        category_group_map={"Phishing": ["soc_l1", "security_lead"]},
        min_priority_score=72,
        min_risk_tier="critical",
        auto_promote_on_gap=True,
        auto_apply_autotune=False,
        dispatch_via_action_center=True,
        playbook_promotion_enabled=True,
        owner="security",
    )

    assert result["status"] == "ok"
    policy = result["policy"]
    assert policy["stakeholder_groups"] == ["soc_l1", "security_lead"]
    assert policy["group_channel_map"]["soc_l1"] == ["telegram"]
    assert policy["category_group_map"]["phishing"] == ["soc_l1", "security_lead"]
    assert policy["min_priority_score"] == 72
    assert policy["min_risk_tier"] == "critical"
    assert len(db.added) == 1


def test_promote_blue_threat_localizer_gap_dispatches_and_runs_followups(monkeypatch) -> None:
    site_id = uuid4()
    tenant_id = uuid4()
    localizer_run_id = uuid4()
    site = SimpleNamespace(id=site_id, tenant_id=tenant_id, site_code="duck-sec-ai", display_name="Duck Sec AI")
    tenant = SimpleNamespace(id=tenant_id, tenant_code="acb")
    localizer_run = SimpleNamespace(
        id=localizer_run_id,
        site_id=site_id,
        priority_score=88,
        risk_tier="high",
        details_json='{"detection_gap":{"missing_categories":["web","phishing"]}}',
    )
    db = _FakeDB(object_map={site_id: site, tenant_id: tenant, localizer_run_id: localizer_run}, scalar_values=[None])

    monkeypatch.setattr(
        blue_threat_localizer_promotion,
        "dispatch_manual_alert",
        lambda db, **kwargs: {"status": "queued", "routing": {"group": kwargs["source"], "channels": kwargs["payload"]["channels"]}},
    )
    monkeypatch.setattr(
        blue_threat_localizer_promotion,
        "run_detection_autotune",
        lambda db, **kwargs: {"status": "ok", "run": {"run_id": "autotune_1"}},
    )
    monkeypatch.setattr(
        blue_threat_localizer_promotion,
        "execute_playbook",
        lambda db, **kwargs: {"status": "queued", "execution": {"execution_id": f'exec_{kwargs["playbook_code"]}'}},
    )

    result = blue_threat_localizer_promotion.promote_blue_threat_localizer_gap(
        db,
        site_id=site_id,
        localizer_run_id=localizer_run_id,
        auto_apply_override=True,
        playbook_promotion_override=True,
        actor="promotion_ai",
    )

    assert result["status"] == "promoted"
    promotion = result["promotion"]
    assert set(promotion["promoted_categories"]) == {"web", "phishing"}
    assert "soc_l1" in promotion["routed_groups"]
    assert "security_lead" in promotion["routed_groups"]
    assert promotion["playbook_codes"] == ["block-ip-and-waf-tighten", "notify-and-clear-session"]
    assert promotion["autotune_run_id"] == "autotune_1"
    assert "gap_promotion" in blue_threat_localizer_promotion._safe_json_dict(localizer_run.details_json)


def test_list_blue_threat_localizer_promotion_runs_returns_rows() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id)
    row = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        localizer_run_id=uuid4(),
        status="promoted",
        promoted_categories_json='["web"]',
        routed_groups_json='["soc_l1"]',
        playbook_codes_json='["block-ip-and-waf-tighten"]',
        autotune_run_id="autotune_1",
        details_json='{"dispatches":[]}',
        actor="promotion_ai",
        created_at=datetime.now(timezone.utc),
    )
    db = _FakeDB(object_map={site_id: site}, scalar_batches=[[row]])

    result = blue_threat_localizer_promotion.list_blue_threat_localizer_promotion_runs(db, site_id=site_id, limit=10)

    assert result["status"] == "ok"
    assert result["count"] == 1
    assert result["rows"][0]["status"] == "promoted"
