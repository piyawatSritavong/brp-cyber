from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import SoarPlaybookExecution
from app.services import action_center, connector_sla, soar_playbook_hub


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, tenant=None, rows=None, execution=None, site=None):
        self.tenant = tenant
        self.rows = rows or []
        self.execution = execution
        self.site = site
        self.added = []

    def scalar(self, _stmt):
        return self.tenant

    def scalars(self, _stmt):
        return _FakeScalarResult(self.rows)

    def get(self, model, _id):
        if model is SoarPlaybookExecution:
            return self.execution
        return self.site

    def add(self, row):
        self.added.append(row)

    def flush(self):
        if self.added and getattr(self.added[-1], "id", None) is None:
            self.added[-1].id = uuid4()

    def commit(self):
        return None

    def refresh(self, row):
        if getattr(row, "id", None) is None:
            row.id = uuid4()
        return None


@dataclass
class _ConnectorEventRow:
    status: str
    event_type: str
    latency_ms: int
    site_id: object


def test_soar_execute_playbook_respects_blocked_code_policy(monkeypatch) -> None:
    site_id = uuid4()
    tenant_id = uuid4()
    db = _FakeDB()
    db.site = SimpleNamespace(id=site_id, tenant_id=tenant_id, site_code="duck-site")
    db.tenant = SimpleNamespace(
        id=uuid4(),
        playbook_code="block-ip-and-waf-tighten",
        is_active=True,
        scope="partner",
        category="response",
        steps_json="[]",
        action_policy_json="{}",
    )
    monkeypatch.setattr(
        soar_playbook_hub,
        "_get_policy_for_tenant",
        lambda _db, _tenant_id: {
            "blocked_playbook_codes": ["block-ip-and-waf-tighten"],
            "allow_partner_scope": True,
            "require_approval_by_scope": {},
            "require_approval_by_category": {},
            "auto_approve_dry_run": True,
        },
    )

    result = soar_playbook_hub.execute_playbook(
        db,
        site_id=site_id,
        playbook_code="block-ip-and-waf-tighten",
        actor="ai",
        require_approval=False,
        dry_run=True,
        params={},
    )
    assert result["status"] == "blocked_by_policy"


def test_soar_approve_requires_delegated_approver(monkeypatch) -> None:
    execution = SimpleNamespace(
        id=uuid4(),
        site_id=uuid4(),
        playbook_id=uuid4(),
        status="pending_approval",
        requested_by="ai",
        approved_by="",
        approval_required=True,
        run_params_json="{}",
        result_json="{}",
        created_at=None,
        updated_at=None,
    )
    site = SimpleNamespace(id=execution.site_id, tenant_id=uuid4())
    db = _FakeDB(execution=execution, site=site)
    monkeypatch.setattr(
        soar_playbook_hub,
        "_get_policy_for_tenant",
        lambda _db, _tenant_id: {
            "delegated_approvers": ["alice"],
        },
    )

    denied = soar_playbook_hub.approve_playbook_execution(
        db,
        execution_id=execution.id,
        approve=True,
        approver="bob",
        note="attempt",
    )
    assert denied["status"] == "approver_not_authorized"

    allowed = soar_playbook_hub.approve_playbook_execution(
        db,
        execution_id=execution.id,
        approve=True,
        approver="security_lead",
        note="approved",
    )
    assert allowed["status"] == "applied"


def test_action_center_route_alert_respects_min_severity(monkeypatch) -> None:
    tenant_id = uuid4()
    db = _FakeDB()
    calls = {"telegram": 0, "line": 0}

    monkeypatch.setattr(
        action_center,
        "_get_policy_for_tenant",
        lambda _db, _tenant_id: {
            "min_severity": "high",
            "telegram_enabled": True,
            "line_enabled": True,
        },
    )
    monkeypatch.setattr(action_center, "send_telegram_message", lambda _text: calls.__setitem__("telegram", calls["telegram"] + 1) or True)
    monkeypatch.setattr(action_center, "send_line_message", lambda _text: calls.__setitem__("line", calls["line"] + 1) or True)

    low = action_center.route_alert(
        db,
        tenant_id=tenant_id,
        site_id=None,
        source="connector_sla",
        severity="low",
        title="low-sev",
        message="skip expected",
    )
    assert low["telegram_status"] == "skipped_threshold"
    assert low["line_status"] == "skipped_threshold"
    assert calls["telegram"] == 0
    assert calls["line"] == 0

    high = action_center.route_alert(
        db,
        tenant_id=tenant_id,
        site_id=None,
        source="connector_sla",
        severity="high",
        title="high-sev",
        message="dispatch expected",
    )
    assert high["telegram_status"] == "sent"
    assert high["line_status"] == "sent"
    assert calls["telegram"] == 1
    assert calls["line"] == 1


def test_connector_sla_evaluate_detects_breach_and_routes(monkeypatch) -> None:
    tenant = SimpleNamespace(id=uuid4(), tenant_code="acb")
    rows = [
        _ConnectorEventRow(status="failed", event_type="dead_letter", latency_ms=9000, site_id=uuid4()),
        _ConnectorEventRow(status="failed", event_type="delivery_attempt", latency_ms=8000, site_id=uuid4()),
        _ConnectorEventRow(status="success", event_type="delivery_attempt", latency_ms=7000, site_id=uuid4()),
    ]
    db = _FakeDB(tenant=tenant, rows=rows)

    monkeypatch.setattr(
        connector_sla,
        "get_connector_sla_profile",
        lambda _db, _tenant_code, _connector_source: {
            "profile": {
                "enabled": True,
                "min_events": 1,
                "min_success_rate": 95,
                "max_dead_letter_count": 0,
                "max_average_latency_ms": 1000,
                "notify_on_breach": True,
            }
        },
    )
    monkeypatch.setattr(
        connector_sla,
        "route_alert",
        lambda _db, **_kwargs: {"status": "dispatched", "telegram_status": "sent", "line_status": "disabled"},
    )

    result = connector_sla.evaluate_connector_sla(
        db,
        tenant_code="acb",
        connector_source="splunk",
        lookback_limit=100,
        route_alert_on_breach=True,
    )
    assert result["status"] == "evaluated"
    assert result["breach_detected"] is True
    assert result["routing"]["status"] == "dispatched"
