from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import blue_managed_responder


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


def test_run_managed_responder_dry_run_persists_history() -> None:
    site_id = uuid4()
    candidate_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    candidate = SimpleNamespace(
        id=candidate_id,
        event_type="waf_http",
        source_ip="203.0.113.20",
        ai_severity="high",
        ai_recommendation="block_ip",
        status="open",
        action_taken="",
    )
    db = _FakeDB(object_map={site_id: site}, scalar_values=[None, None], scalar_batches=[[candidate], []])

    result = blue_managed_responder.run_managed_responder(db, site_id=site_id, dry_run=True)

    assert result["status"] == "dry_run"
    assert result["candidate_event"]["event_id"] == str(candidate_id)
    assert result["run"]["selected_action"] == "block_ip"
    assert result["run"]["dry_run"] is True
    assert result["run"]["evidence_signature"]
    assert len(db.added) == 1


def test_run_managed_responder_apply_dispatches_soar(monkeypatch) -> None:
    site_id = uuid4()
    candidate_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    policy = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        min_severity="medium",
        action_mode="limit_user",
        dispatch_playbook=True,
        playbook_code="block-ip-and-waf-tighten",
        require_approval=False,
        dry_run_default=False,
        enabled=True,
        owner="security",
        created_at=None,
        updated_at=None,
    )
    candidate = SimpleNamespace(
        id=candidate_id,
        event_type="endpoint_detection",
        source_ip="10.10.4.44",
        ai_severity="high",
        ai_recommendation="block_ip",
        status="open",
        action_taken="",
    )
    db = _FakeDB(object_map={site_id: site}, scalar_values=[policy, None], scalar_batches=[[candidate], []])
    monkeypatch.setattr(
        blue_managed_responder,
        "apply_blue_recommendation",
        lambda db, site_id, event_id, action: {"status": "applied", "event_id": str(event_id), "action": action},
    )
    monkeypatch.setattr(
        blue_managed_responder,
        "execute_playbook",
        lambda db, **kwargs: {"status": "pending_approval", "execution": {"execution_id": "exec_123"}},
    )

    result = blue_managed_responder.run_managed_responder(db, site_id=site_id, dry_run=False)

    assert result["status"] == "pending_approval"
    assert result["run"]["selected_action"] == "limit_user"
    assert result["run"]["action_applied"] is True
    assert result["run"]["playbook_dispatched"] is True
    assert result["run"]["playbook_execution_id"] == "exec_123"


def test_run_managed_responder_apply_records_connector_confirmation(monkeypatch) -> None:
    site_id = uuid4()
    candidate_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", config_json='{"managed_responder_connector_source":"cloudflare"}')
    policy = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        min_severity="medium",
        action_mode="block_ip",
        dispatch_playbook=False,
        playbook_code="",
        require_approval=False,
        dry_run_default=False,
        enabled=True,
        owner="security",
        created_at=None,
        updated_at=None,
    )
    candidate = SimpleNamespace(
        id=candidate_id,
        event_type="waf_http",
        source_ip="203.0.113.20",
        ai_severity="high",
        ai_recommendation="block_ip",
        status="open",
        action_taken="",
        payload_json="{}",
    )
    db = _FakeDB(object_map={site_id: site}, scalar_values=[policy, None], scalar_batches=[[candidate], []])
    monkeypatch.setattr(
        blue_managed_responder,
        "apply_blue_recommendation",
        lambda db, site_id, event_id, action: {"status": "applied", "event_id": str(event_id), "action": action},
    )

    result = blue_managed_responder.run_managed_responder(db, site_id=site_id, dry_run=False, force=True)

    assert result["status"] in {"applied", "partial"}
    assert result["run"]["connector_source"] == "cloudflare"
    assert result["run"]["connector_action_status"] == "confirmed"
    assert result["run"]["connector_confirmation_status"] == "confirmed"
    assert result["connector_result"]["operation"] == "firewall.access_rule.block"


def test_run_managed_responder_blocks_allowlisted_source(monkeypatch) -> None:
    site_id = uuid4()
    candidate_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    candidate = SimpleNamespace(
        id=candidate_id,
        event_type="waf_http",
        source_ip="127.0.0.1",
        ai_severity="high",
        ai_recommendation="block_ip",
        status="open",
        action_taken="",
    )
    db = _FakeDB(object_map={site_id: site}, scalar_values=[None, None], scalar_batches=[[candidate], []])
    monkeypatch.setattr(blue_managed_responder.settings, "allowlist_ips", "127.0.0.1")
    monkeypatch.setattr(blue_managed_responder.settings, "blue_managed_responder_respect_allowlist", True)

    result = blue_managed_responder.run_managed_responder(db, site_id=site_id, dry_run=False)

    assert result["status"] == "guardrail_blocked"
    assert result["guardrails"]["reason"] == "allowlisted_source_ip"
    assert result["run"]["action_applied"] is False


def test_run_managed_responder_requires_approval_before_apply() -> None:
    site_id = uuid4()
    candidate_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    policy = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        min_severity="medium",
        action_mode="block_ip",
        dispatch_playbook=False,
        playbook_code="",
        require_approval=True,
        dry_run_default=False,
        enabled=True,
        owner="security",
        created_at=None,
        updated_at=None,
    )
    candidate = SimpleNamespace(
        id=candidate_id,
        event_type="waf_http",
        source_ip="198.51.100.5",
        ai_severity="high",
        ai_recommendation="block_ip",
        status="open",
        action_taken="",
    )
    db = _FakeDB(object_map={site_id: site}, scalar_values=[policy, None], scalar_batches=[[candidate], []])

    result = blue_managed_responder.run_managed_responder(db, site_id=site_id, dry_run=False)

    assert result["status"] == "pending_approval"
    assert result["run"]["action_applied"] is False
    assert result["action_result"]["status"] == "pending_approval"


def test_review_and_rollback_managed_responder_run() -> None:
    site_id = uuid4()
    run_id = uuid4()
    event_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    event = SimpleNamespace(id=event_id, site_id=site_id, status="open", action_taken="")
    run = SimpleNamespace(
        id=run_id,
        site_id=site_id,
        event_id=event_id,
        status="pending_approval",
        dry_run=False,
        selected_severity="high",
        selected_action="block_ip",
        playbook_code="",
        playbook_execution_id="",
        action_applied=False,
        playbook_dispatched=False,
        details_json='{"candidate_status_before":"open","candidate_action_before":"","approval_required":true,"rollback_supported":true}',
        created_at=None,
    )
    db = _FakeDB(object_map={site_id: site, run_id: run, event_id: event})

    approved = blue_managed_responder.review_managed_responder_run(
        db,
        site_id=site_id,
        run_id=run_id,
        approve=True,
        approver="security_lead",
        note="approved",
    )
    assert approved["status"] == "applied"
    assert event.status == "applied"
    assert event.action_taken == "block_ip"

    rolled_back = blue_managed_responder.rollback_managed_responder_run(
        db,
        site_id=site_id,
        run_id=run_id,
        actor="security_operator",
        note="false positive",
    )
    assert rolled_back["status"] == "rolled_back"
    assert event.status == "open"
    assert event.action_taken == ""


def test_rollback_managed_responder_run_records_connector_rollback() -> None:
    site_id = uuid4()
    run_id = uuid4()
    event_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    event = SimpleNamespace(id=event_id, site_id=site_id, status="applied", action_taken="block_ip")
    run = SimpleNamespace(
        id=run_id,
        site_id=site_id,
        event_id=event_id,
        status="applied",
        dry_run=False,
        selected_severity="high",
        selected_action="block_ip",
        playbook_code="",
        playbook_execution_id="",
        action_applied=True,
        playbook_dispatched=False,
        details_json='{"candidate_status_before":"open","candidate_action_before":"","approval_required":false,"rollback_supported":true,"connector_action_plan":{"connector_source":"cloudflare","rollback_payload":{"operation":"firewall.access_rule.remove","configuration":{"target":"ip","value":"203.0.113.20"}}}}',
        created_at=None,
    )
    db = _FakeDB(object_map={site_id: site, run_id: run, event_id: event})

    rolled_back = blue_managed_responder.rollback_managed_responder_run(
        db,
        site_id=site_id,
        run_id=run_id,
        actor="security_operator",
        note="false positive",
    )

    assert rolled_back["status"] == "rolled_back"
    assert rolled_back["connector_rollback"]["status"] == "rolled_back"
    assert rolled_back["run"]["connector_rollback_status"] == "rolled_back"


def test_verify_managed_responder_evidence_chain() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    candidate1 = SimpleNamespace(
        id=uuid4(),
        event_type="waf_http",
        source_ip="203.0.113.20",
        ai_severity="high",
        ai_recommendation="block_ip",
        status="open",
        action_taken="",
    )
    db = _FakeDB(object_map={site_id: site}, scalar_values=[None, None], scalar_batches=[[candidate1], []])
    _ = blue_managed_responder.run_managed_responder(db, site_id=site_id, dry_run=True)
    first_run = db.added[-1]

    candidate2 = SimpleNamespace(
        id=uuid4(),
        event_type="endpoint_detection",
        source_ip="10.10.4.44",
        ai_severity="high",
        ai_recommendation="limit_user",
        status="open",
        action_taken="",
    )
    db.scalar_values.extend([None, first_run])
    db.scalar_batches.extend([[candidate2], []])
    _ = blue_managed_responder.run_managed_responder(db, site_id=site_id, dry_run=True)
    second_run = db.added[-1]

    verify_db = _FakeDB(object_map={site_id: site}, scalar_batches=[[second_run, first_run]])
    verify = blue_managed_responder.verify_managed_responder_evidence_chain(verify_db, site_id=site_id, limit=10)

    assert verify["valid"] is True
    assert verify["count"] == 2


def test_run_managed_responder_scheduler_executes_due_policies(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    site_id = uuid4()
    policy = SimpleNamespace(site_id=site_id, updated_at=now, enabled=True)
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    db = _FakeDB(object_map={site_id: site}, scalar_batches=[[policy]])
    monkeypatch.setattr(blue_managed_responder, "run_managed_responder", lambda db, **kwargs: {
        "status": "dry_run",
        "candidate_event": {"event_id": "evt_demo"},
        "run": {"run_id": "run_demo", "selected_action": "block_ip"},
    })

    result = blue_managed_responder.run_managed_responder_scheduler(db, limit=20, dry_run_override=True)

    assert result["scheduled_policy_count"] == 1
    assert result["executed_count"] == 1
    assert result["skipped_count"] == 0


def test_list_managed_responder_vendor_packs_includes_extended_connectors() -> None:
    result = blue_managed_responder.list_managed_responder_vendor_packs()

    sources = {row["connector_source"] for row in result["rows"]}
    assert result["status"] == "ok"
    assert {"paloalto", "fortinet", "defender", "sentinelone"}.issubset(sources)


def test_ingest_managed_responder_callback_updates_run_to_verified() -> None:
    site_id = uuid4()
    run_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    run = SimpleNamespace(
        id=run_id,
        site_id=site_id,
        event_id=None,
        status="applied",
        dry_run=False,
        selected_severity="high",
        selected_action="block_ip",
        playbook_code="",
        playbook_execution_id="",
        action_applied=True,
        playbook_dispatched=False,
        details_json='{"connector_action_result":{"status":"confirmed","confirmation":{"status":"pending"}}}',
        created_at=None,
    )
    db = _FakeDB(object_map={site_id: site, run_id: run}, scalar_values=[None])

    result = blue_managed_responder.ingest_managed_responder_callback(
        db,
        site_id=site_id,
        run_id=run_id,
        connector_source="paloalto",
        contract_code="paloalto_dynamic_block_result_v1",
        callback_type="dynamic_block",
        webhook_event_id="cb-001",
        external_action_ref="pan-commit-001",
        status="confirmed",
        payload={"rule_name": "brp-duck-sec-ai-dynamic-block"},
        actor="vendor_callback",
    )

    assert result["status"] == "ok"
    assert result["run"]["status"] == "verified"
    assert result["callback"]["connector_source"] == "paloalto"
    assert result["callback"]["contract_code"] == "paloalto_dynamic_block_result_v1"
