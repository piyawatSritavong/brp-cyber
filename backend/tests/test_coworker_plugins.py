from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import coworker_plugins


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


def test_upsert_site_coworker_plugin_binding_creates_record(monkeypatch) -> None:
    site_id = uuid4()
    plugin_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", tenant=SimpleNamespace(tenant_code="acb"))
    plugin = SimpleNamespace(
        id=plugin_id,
        plugin_code="blue_log_refiner",
        display_name="Blue Log Refiner",
        display_name_th="AI Log Refiner",
        category="blue",
        plugin_kind="log_refiner",
        execution_mode="scheduled",
        description="",
        value_statement="",
        default_config_json="{}",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db = _FakeDB(scalar_values=[plugin, None], object_map={site_id: site})
    monkeypatch.setattr(coworker_plugins, "ensure_builtin_plugins", lambda _db: {"count": 5})

    result = coworker_plugins.upsert_site_coworker_plugin_binding(
        db,
        site_id=site_id,
        plugin_code="blue_log_refiner",
        enabled=True,
        auto_run=True,
        schedule_interval_minutes=30,
        notify_channels=["telegram"],
        config={"lookback_limit": 100},
        owner="secops",
    )
    assert result["status"] == "created"
    assert result["binding"]["auto_run"] is True
    assert len(db.added) == 1


def test_run_site_coworker_plugin_executes_handler_and_persists_run(monkeypatch) -> None:
    site_id = uuid4()
    plugin_id = uuid4()
    tenant = SimpleNamespace(tenant_code="acb")
    site = SimpleNamespace(id=site_id, site_code="duck", tenant=tenant)
    plugin = SimpleNamespace(
        id=plugin_id,
        plugin_code="blue_log_refiner",
        display_name="Blue Log Refiner",
        display_name_th="AI Log Refiner",
        category="blue",
        plugin_kind="log_refiner",
        execution_mode="scheduled",
        description="",
        value_statement="",
        default_config_json='{"lookback_limit":200}',
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    binding = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        plugin_id=plugin_id,
        enabled=True,
        auto_run=True,
        schedule_interval_minutes=30,
        notify_channels_json='["telegram"]',
        config_json='{"lookback_limit":50}',
        owner="security",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db = _FakeDB(scalar_values=[plugin, binding], object_map={site_id: site})
    monkeypatch.setattr(coworker_plugins, "ensure_builtin_plugins", lambda _db: {"count": 5})
    monkeypatch.setitem(
        coworker_plugins.PLUGIN_HANDLERS,
        "blue_log_refiner",
        lambda _db, _site, config: (
            {"lookback_limit": config["lookback_limit"]},
            {"headline": "AI Log Refiner", "severity": "medium", "summary_th": "คัด noise แล้ว"},
        ),
    )
    monkeypatch.setattr(
        coworker_plugins,
        "dispatch_manual_alert",
        lambda _db, **kwargs: {"status": "ok", "routing": {"status": "dispatched"}, "payload": kwargs},
    )

    result = coworker_plugins.run_site_coworker_plugin(
        db,
        site_id=site_id,
        plugin_code="blue_log_refiner",
        dry_run=False,
        force=False,
        actor="tester",
    )
    assert result["status"] == "ok"
    assert result["run"]["alert_routed"] is True
    assert result["run"]["output_summary"]["headline"] == "AI Log Refiner"
    assert len(db.added) == 1


def test_run_coworker_plugin_scheduler_executes_due_binding(monkeypatch) -> None:
    site_id = uuid4()
    plugin_id = uuid4()
    binding = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        plugin_id=plugin_id,
        enabled=True,
        auto_run=True,
        schedule_interval_minutes=30,
        updated_at=datetime.now(timezone.utc),
    )
    site = SimpleNamespace(id=site_id, site_code="duck")
    plugin = SimpleNamespace(id=plugin_id, plugin_code="blue_log_refiner")
    db = _FakeDB(
        scalar_batches=[[binding]],
        scalar_values=[None],
        object_map={site_id: site, plugin_id: plugin},
    )
    monkeypatch.setattr(coworker_plugins, "ensure_builtin_plugins", lambda _db: {"count": 5})
    monkeypatch.setattr(
        coworker_plugins,
        "run_site_coworker_plugin",
        lambda _db, site_id, plugin_code, dry_run=None, force=False, actor="": {
            "status": "dry_run",
            "run": {"run_id": str(uuid4())},
        },
    )

    result = coworker_plugins.run_coworker_plugin_scheduler(db, limit=100, actor="scheduler")
    assert result["scheduled_binding_count"] == 1
    assert result["executed_count"] == 1
    assert result["skipped_count"] == 0


def test_red_exploit_code_generator_supports_bash_output(monkeypatch) -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", base_url="https://duck-sec-ai.vercel.app/")
    db = _FakeDB(scalar_values=[None])
    monkeypatch.setattr(
        coworker_plugins,
        "get_latest_red_plugin_intelligence",
        lambda _db, **kwargs: {
            "title": "Thai auth advisory",
            "cve_id": "CVE-2026-1111",
            "target_surface": kwargs["target_surface"],
            "target_type": kwargs["target_type"],
        },
    )
    monkeypatch.setattr(
        coworker_plugins,
        "get_red_plugin_safety_policy",
        lambda _db, **kwargs: {
            "policy": {
                "target_type": kwargs["target_type"],
                "allow_network_calls": True,
                "require_comment_header": True,
                "require_disclaimer": True,
            }
        },
    )

    input_summary, output_summary = coworker_plugins._run_red_exploit_code_generator(
        db,
        site,
        {"target_surface": "/admin-login", "target_type": "web", "target_language": "bash"},
    )

    assert input_summary["target_language"] == "bash"
    assert output_summary["language"] == "bash"
    assert "set -euo pipefail" in output_summary["script_preview"]
    assert "--max-time 10" in output_summary["script_preview"]
    assert set(output_summary["script_variants"]) == {"python", "bash", "curl"}
