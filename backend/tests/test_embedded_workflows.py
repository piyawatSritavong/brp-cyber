from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import embedded_workflows


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


class _FakeRedis:
    def __init__(self):
        self.kv = {}
        self.zsets = {}

    def zadd(self, key, mapping):
        bucket = self.zsets.setdefault(key, {})
        bucket.update(mapping)

    def zremrangebyscore(self, key, min_score, max_score):
        bucket = self.zsets.setdefault(key, {})
        for member, score in list(bucket.items()):
            if min_score <= score <= max_score:
                bucket.pop(member, None)

    def zcard(self, key):
        return len(self.zsets.get(key, {}))

    def expire(self, key, _seconds):
        return True

    def exists(self, key):
        return 1 if key in self.kv else 0

    def set(self, key, value, ex=None):
        self.kv[key] = {"value": value, "ex": ex}
        return True


def test_upsert_embedded_endpoint_generates_token(monkeypatch) -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    plugin = SimpleNamespace(plugin_code="blue_thai_alert_translator")
    db = _FakeDB(object_map={site_id: site}, scalar_values=[plugin, None])
    monkeypatch.setattr(embedded_workflows, "ensure_builtin_plugins", lambda _db: {"count": 7})
    monkeypatch.setattr(embedded_workflows, "ensure_builtin_playbooks", lambda _db: {"count": 3})

    result = embedded_workflows.upsert_site_embedded_workflow_endpoint(
        db,
        site_id=site_id,
        endpoint_code="soc-alert-translator",
        plugin_code="blue_thai_alert_translator",
        connector_source="splunk",
        config={"lookback_limit": 10},
        rotate_secret=False,
    )

    assert result["status"] == "created"
    assert result["token"].startswith("emb_")
    assert result["invoke_path"].endswith("/integrations/embedded/sites/duck-sec-ai/soc-alert-translator/invoke")
    assert len(db.added) == 1


def test_upsert_embedded_soar_endpoint_allows_blank_plugin_and_normalizes_playbook(monkeypatch) -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    db = _FakeDB(object_map={site_id: site}, scalar_values=[None])
    monkeypatch.setattr(embedded_workflows, "ensure_builtin_plugins", lambda _db: {"count": 7})
    monkeypatch.setattr(embedded_workflows, "ensure_builtin_playbooks", lambda _db: {"count": 3})

    result = embedded_workflows.upsert_site_embedded_workflow_endpoint(
        db,
        site_id=site_id,
        endpoint_code="crowdstrike-managed-response",
        workflow_type="soar_playbook",
        plugin_code="",
        connector_source="crowdstrike",
        config={"playbook_code": "isolate-host-and-reset-session"},
        rotate_secret=False,
    )

    assert result["status"] == "created"
    assert result["endpoint"]["workflow_type"] == "soar_playbook"
    assert result["endpoint"]["plugin_code"] == ""
    assert result["endpoint"]["config"]["default_playbook_code"] == "isolate-host-and-reset-session"
    assert "isolate-host-and-reset-session" in result["endpoint"]["config"]["allowed_playbook_codes"]


def test_invoke_embedded_blue_endpoint_ingests_and_runs_plugin(monkeypatch) -> None:
    site_id = uuid4()
    endpoint_id = uuid4()
    token = "emb_demo.secret"
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    endpoint = SimpleNamespace(
        id=endpoint_id,
        site_id=site_id,
        endpoint_code="soc-alert-translator",
        workflow_type="coworker_plugin",
        plugin_code="blue_thai_alert_translator",
        connector_source="splunk",
        default_event_kind="security_event",
        secret_hash=embedded_workflows._hash_secret(token),
        enabled=True,
        dry_run_default=True,
        config_json='{"lookback_limit":15}',
        owner="security",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db = _FakeDB(scalar_values=[site, endpoint])
    monkeypatch.setattr(embedded_workflows, "redis_client", _FakeRedis())

    monkeypatch.setattr(
        embedded_workflows,
        "ingest_integration_event",
        lambda _db, **kwargs: {
            "status": "accepted",
            "integration_event_id": str(uuid4()),
            "blue_event_id": str(uuid4()),
        },
    )
    monkeypatch.setattr(embedded_workflows, "record_connector_event", lambda _db, **kwargs: None)
    monkeypatch.setattr(
        embedded_workflows,
        "upsert_site_coworker_plugin_binding",
        lambda _db, **kwargs: {"status": "updated", "binding": kwargs},
    )
    monkeypatch.setattr(
        embedded_workflows,
        "run_site_coworker_plugin",
        lambda _db, **kwargs: {
            "status": "dry_run",
            "run": {"run_id": str(uuid4()), "status": "dry_run"},
            "alert": {"status": "skipped"},
        },
    )

    result = embedded_workflows.invoke_site_embedded_workflow(
        db,
        site_code="duck-sec-ai",
        endpoint_code="soc-alert-translator",
        token=token,
        source="splunk",
        event_kind="security_event",
        payload={"message": "suspicious login burst", "severity": "high"},
        config={"max_alerts": 5},
        dry_run=False,
        actor="siem_webhook",
    )

    assert result["status"] == "dry_run"
    assert result["preprocess"]["status"] == "integration_ingested"
    assert result["invocation"]["source"] == "splunk"
    assert len(db.added) == 1


def test_invoke_embedded_endpoint_blocks_disallowed_actor(monkeypatch) -> None:
    site_id = uuid4()
    endpoint_id = uuid4()
    token = "emb_demo.secret"
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    endpoint = SimpleNamespace(
        id=endpoint_id,
        site_id=site_id,
        endpoint_code="soc-alert-translator",
        workflow_type="coworker_plugin",
        plugin_code="blue_thai_alert_translator",
        connector_source="splunk",
        default_event_kind="security_event",
        secret_hash=embedded_workflows._hash_secret(token),
        enabled=True,
        dry_run_default=True,
        config_json='{"allowed_actors":["splunk_soar"]}',
        owner="security",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db = _FakeDB(scalar_values=[site, endpoint])
    monkeypatch.setattr(embedded_workflows, "redis_client", _FakeRedis())
    monkeypatch.setattr(embedded_workflows, "record_connector_event", lambda _db, **kwargs: None)

    result = embedded_workflows.invoke_site_embedded_workflow(
        db,
        site_code="duck-sec-ai",
        endpoint_code="soc-alert-translator",
        token=token,
        source="splunk",
        payload={"message": "alert", "severity": "high"},
        actor="unknown_client",
    )

    assert result["status"] == "guardrail_blocked"
    assert result["reason"] == "actor_not_allowed"
    assert result["invocation"]["status"] == "guardrail_blocked"


def test_verify_embedded_automation_packs_reports_policy_issue(monkeypatch) -> None:
    site_id = uuid4()
    tenant_id = uuid4()
    endpoint_id = uuid4()
    site = SimpleNamespace(id=site_id, tenant_id=tenant_id, site_code="duck-sec-ai")
    endpoint = SimpleNamespace(
        id=endpoint_id,
        site_id=site_id,
        endpoint_code="cloudflare-waf-playbook",
        workflow_type="soar_playbook",
        plugin_code="",
        connector_source="cloudflare",
        default_event_kind="waf_event",
        secret_hash="hash",
        enabled=True,
        dry_run_default=True,
        config_json='{"playbook_code":"block-ip-and-waf-tighten","allowed_playbook_codes":["block-ip-and-waf-tighten"]}',
        owner="security",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    playbook = SimpleNamespace(playbook_code="block-ip-and-waf-tighten", is_active=True, scope="private", category="containment")
    db = _FakeDB(object_map={site_id: site}, scalar_values=[playbook], scalar_batches=[[endpoint]])
    monkeypatch.setattr(embedded_workflows, "ensure_builtin_plugins", lambda _db: {"count": 7})
    monkeypatch.setattr(embedded_workflows, "ensure_builtin_playbooks", lambda _db: {"count": 3})
    monkeypatch.setattr(
        embedded_workflows,
        "_get_policy_for_tenant",
        lambda _db, _tenant_id: {"blocked_playbook_codes": ["block-ip-and-waf-tighten"], "allow_partner_scope": True},
    )

    result = embedded_workflows.verify_site_embedded_automation_packs(db, site_id=site_id, limit=10)

    assert result["status"] == "ok"
    assert result["error_count"] == 1
    issue_codes = [issue["code"] for issue in result["rows"][0]["verification"]["issues"]]
    assert "playbook_blocked_by_policy" in issue_codes


def test_list_site_embedded_activation_bundles_merges_handoff_status(monkeypatch) -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai")
    monkeypatch.setattr(
        embedded_workflows,
        "list_site_embedded_invoke_packs",
        lambda _db, **kwargs: {
            "site_id": str(site_id),
            "site_code": "duck-sec-ai",
            "count": 1,
            "rows": [
                {
                    "endpoint": {
                        "endpoint_id": str(uuid4()),
                        "endpoint_code": "crowdstrike-managed-response",
                        "workflow_type": "soar_playbook",
                        "connector_source": "crowdstrike",
                        "enabled": True,
                    },
                    "invoke_pack": {
                        "display_name": "CrowdStrike Detection to Managed AI Responder",
                        "vendor_preset_code": "crowdstrike_detection_to_managed_responder",
                        "automation_pack": {"workflow_type": "soar_playbook"},
                        "curl_example": "curl example",
                    },
                }
            ],
        },
    )
    monkeypatch.setattr(
        embedded_workflows,
        "verify_site_embedded_automation_packs",
        lambda _db, **kwargs: {
            "status": "ok",
            "site_id": str(site_id),
            "site_code": "duck-sec-ai",
            "count": 1,
            "rows": [
                {
                    "endpoint": {"endpoint_code": "crowdstrike-managed-response"},
                    "verification": {
                        "status": "warning",
                        "issues": [{"level": "warning", "code": "allowlist_missing", "message": "allowlist empty"}],
                    },
                }
            ],
        },
    )
    db = _FakeDB(object_map={site_id: site})

    result = embedded_workflows.list_site_embedded_activation_bundles(db, site_id=site_id, limit=10)

    assert result["status"] == "ok"
    assert result["needs_attention_count"] == 1
    assert result["rows"][0]["handoff"]["status"] == "needs_attention"
    assert result["rows"][0]["handoff"]["missing_items"] == ["allowlist empty"]


def test_embedded_automation_federation_snapshot_aggregates_status(monkeypatch) -> None:
    site_ready_id = uuid4()
    site_empty_id = uuid4()
    ready_site = SimpleNamespace(id=site_ready_id, site_code="ready-site", tenant_code="acb", updated_at=datetime.now(timezone.utc), created_at=datetime.now(timezone.utc))
    empty_site = SimpleNamespace(id=site_empty_id, site_code="empty-site", tenant_code="xyz", updated_at=datetime.now(timezone.utc), created_at=datetime.now(timezone.utc))
    db = _FakeDB(scalar_batches=[[ready_site, empty_site]])
    monkeypatch.setattr(
        embedded_workflows,
        "verify_site_embedded_automation_packs",
        lambda _db, site_id, **kwargs: {
            "rows": [
                {
                    "endpoint": {"workflow_type": "soar_playbook", "connector_source": "crowdstrike"},
                    "verification": {"status": "ok", "effective_approval_required": True},
                }
            ]
            if site_id == site_ready_id
            else []
        },
    )
    monkeypatch.setattr(
        embedded_workflows,
        "list_site_embedded_invoke_packs",
        lambda _db, site_id, **kwargs: {
            "rows": [
                {"endpoint": {"connector_source": "crowdstrike"}, "invoke_pack": {"vendor_preset_code": "crowdstrike_detection_to_managed_responder"}}
            ]
            if site_id == site_ready_id
            else []
        },
    )

    result = embedded_workflows.embedded_automation_federation_snapshot(db, limit=10)

    assert result["status"] == "ok"
    assert result["summary"]["ready_sites"] == 1
    assert result["summary"]["not_configured_sites"] == 1
    assert result["summary"]["total_endpoints"] == 1
    assert result["rows"][0]["status"] in {"ready", "not_configured"}
