from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.db.models import BlueEventLog, Site, SoarPlaybook, SoarPlaybookExecution
from app.services import soar_playbook_hub


class _FakeDB:
    def __init__(self, *, execution=None, site=None, playbook=None, event=None, scalar_batches=None):
        self.execution = execution
        self.site = site
        self.playbook = playbook
        self.event = event
        self.scalar_batches = list(scalar_batches or [])
        self.added = []

    def get(self, model, _id):
        if model is SoarPlaybookExecution:
            return self.execution
        if model is Site:
            return self.site
        if model is SoarPlaybook:
            return self.playbook
        if model is BlueEventLog:
            return self.event
        return None

    def scalar(self, _stmt):
        return self.event

    def scalars(self, _stmt):
        rows = self.scalar_batches.pop(0) if self.scalar_batches else []

        class _Result:
            def __init__(self, items):
                self._items = items

            def all(self):
                return self._items

        return _Result(rows)

    def add(self, row):
        self.added.append(row)

    def commit(self):
        return None

    def refresh(self, _row):
        return None


def test_list_marketplace_packs_filters_by_audience() -> None:
    result = soar_playbook_hub.list_marketplace_packs(audience="soc", limit=10)
    assert result["count"] >= 1
    assert all(row["audience"] == "soc" for row in result["rows"])
    assert "source_type" in result["rows"][0]
    assert "trust_tier" in result["rows"][0]


def test_list_marketplace_packs_filters_by_source_and_connector() -> None:
    result = soar_playbook_hub.list_marketplace_packs(source_type="partner", connector_source="cloudflare", limit=10)

    assert result["count"] >= 1
    assert all(row["source_type"] == "partner" for row in result["rows"])
    assert all("cloudflare" in row["supported_connectors"] for row in result["rows"])
    assert "source_type" in result["available_filters"]
    assert "connector_source" in result["available_filters"]


def test_install_marketplace_pack_calls_upsert_for_each_playbook(monkeypatch) -> None:
    calls: list[str] = []

    def _fake_upsert(_db, **kwargs):
        calls.append(kwargs["playbook_code"])
        return {"status": "created", "playbook": {"playbook_code": kwargs["playbook_code"], "scope": kwargs["scope"]}}

    monkeypatch.setattr(soar_playbook_hub, "upsert_playbook", _fake_upsert)

    result = soar_playbook_hub.install_marketplace_pack(object(), pack_code="cloud_edge_containment_pack", scope_override="partner")

    assert result["status"] == "installed"
    assert result["installed_count"] == 2
    assert "block-ip-and-waf-tighten" in calls
    assert "rate-limit-and-cookie-reset" in calls


def test_verify_playbook_execution_persists_post_action_verification() -> None:
    site_id = uuid4()
    execution_id = uuid4()
    playbook_id = uuid4()
    event_id = uuid4()
    now = datetime.now(timezone.utc)
    site = SimpleNamespace(id=site_id, tenant_id=uuid4(), site_code="duck")
    playbook = SimpleNamespace(
        id=playbook_id,
        playbook_code="block-ip-and-waf-tighten",
        action_policy_json='{"rollback_supported":true}',
    )
    execution = SimpleNamespace(
        id=execution_id,
        site_id=site_id,
        playbook_id=playbook_id,
        status="applied",
        requested_by="blue_ai",
        approved_by="security_lead",
        approval_required=False,
        run_params_json=json.dumps({"event_id": str(event_id)}),
        result_json="{}",
        created_at=now,
        updated_at=now,
        playbook=playbook,
    )
    event = SimpleNamespace(id=event_id, site_id=site_id, status="applied", action_taken="block-ip-and-waf-tighten", created_at=now)
    db = _FakeDB(execution=execution, site=site, playbook=playbook, event=event)

    result = soar_playbook_hub.verify_playbook_execution(db, execution_id=execution_id, actor="verifier")

    assert result["status"] == "verified"
    assert result["verification"]["action_reflected"] is True
    assert result["verification"]["target_event_id"] == str(event_id)
    assert json.loads(execution.result_json)["post_action_verification"]["status"] == "verified"


def test_list_connector_result_contracts_filters_by_connector() -> None:
    result = soar_playbook_hub.list_connector_result_contracts(connector_source="cloudflare")

    assert result["status"] == "ok"
    assert result["count"] >= 1
    assert all(row["connector_source"] == "cloudflare" for row in result["rows"])


def test_ingest_playbook_connector_result_updates_execution_and_verification() -> None:
    site_id = uuid4()
    execution_id = uuid4()
    playbook_id = uuid4()
    now = datetime.now(timezone.utc)
    playbook = SimpleNamespace(
        id=playbook_id,
        playbook_code="block-ip-and-waf-tighten",
        action_policy_json='{"rollback_supported":true}',
    )
    execution = SimpleNamespace(
        id=execution_id,
        site_id=site_id,
        playbook_id=playbook_id,
        status="applied",
        requested_by="blue_ai",
        approved_by="security_lead",
        approval_required=False,
        run_params_json=json.dumps({"event_id": ""}),
        result_json="{}",
        created_at=now,
        updated_at=now,
        playbook=playbook,
    )
    site = SimpleNamespace(id=site_id, tenant_id=uuid4(), site_code="duck")
    db = _FakeDB(execution=execution, site=site, playbook=playbook, event=None, scalar_batches=[[]])

    result = soar_playbook_hub.ingest_playbook_connector_result(
        db,
        execution_id=execution_id,
        site_id=site_id,
        connector_source="cloudflare",
        contract_code="cloudflare_block_result_v1",
        external_action_ref="edge-1",
        webhook_event_id="webhook-1",
        status="confirmed",
        payload={"result": {"blocked_ip": "203.0.113.10", "rule_mode": "strict", "edge_status": "confirmed"}},
        actor="vendor_callback",
    )

    assert result["status"] == "ok"
    assert result["connector_result"]["connector_source"] == "cloudflare"
    assert result["execution"]["status"] == "verified"
    stored = json.loads(execution.result_json)
    assert stored["connector_result_contract"]["contract_code"] == "cloudflare_block_result_v1"
