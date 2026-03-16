from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import red_plugin_intelligence


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


def test_import_red_plugin_intelligence_creates_rows() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", display_name="Duck")
    db = _FakeDB(object_map={site_id: site}, scalar_values=[None])

    result = red_plugin_intelligence.import_red_plugin_intelligence(
        db,
        site_id=site_id,
        items=[
            {
                "source_type": "cve",
                "source_name": "manual",
                "source_item_id": "CVE-2026-0001",
                "title": "CVE-2026-0001 auth bypass",
                "summary_th": "รายละเอียดช่องโหว่",
                "cve_id": "CVE-2026-0001",
                "target_surface": "/admin-login",
                "target_type": "web",
                "references": ["https://example.com/advisory"],
            }
        ],
    )

    assert result["status"] == "ok"
    assert result["created_count"] == 1
    assert result["count"] == 1
    assert len(db.added) == 1


def test_list_red_plugin_intelligence_returns_rows() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck")
    row = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        source_type="news",
        source_name="manual",
        source_item_id="n1",
        title="Thai auth attack trend",
        summary_th="summary",
        cve_id="",
        target_surface="/admin",
        target_type="web",
        tags_json='["news","web"]',
        references_json='["https://example.com/news"]',
        payload_json="{}",
        published_at=datetime.now(timezone.utc),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db = _FakeDB(object_map={site_id: site}, scalar_batches=[[row]])

    result = red_plugin_intelligence.list_red_plugin_intelligence(db, site_id=site_id, limit=10)

    assert result["status"] == "ok"
    assert result["count"] == 1
    assert result["rows"][0]["title"] == "Thai auth attack trend"


def test_lint_red_plugin_output_uses_policy_and_detects_issues() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck")
    plugin = SimpleNamespace(id=uuid4(), plugin_code="red_exploit_code_generator")
    run = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        plugin_id=plugin.id,
        input_summary_json='{"target_surface":"/admin-login","target_type":"web"}',
        output_summary_json='{"script_preview":"import subprocess\\nprint(\\"oops\\")","target_type":"web"}',
        created_at=datetime.now(timezone.utc),
    )
    policy = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        target_type="web",
        max_http_requests_per_run=5,
        max_script_lines=80,
        allow_network_calls=True,
        require_comment_header=True,
        require_disclaimer=True,
        allowed_modules_json='["requests"]',
        blocked_modules_json='["subprocess","socket"]',
        enabled=True,
        owner="security",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db = _FakeDB(object_map={site_id: site}, scalar_values=[plugin, run, policy])

    result = red_plugin_intelligence.lint_red_plugin_output(
        db,
        site_id=site_id,
        plugin_code="red_exploit_code_generator",
    )

    assert result["status"] == "ok"
    assert result["lint"]["status"] == "fail"
    assert "blocked module detected: subprocess" in result["lint"]["issues"]


def test_export_red_plugin_output_builds_bundle() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", display_name="Duck")
    plugin = SimpleNamespace(id=uuid4(), plugin_code="red_template_writer", display_name="Nuclei AI-Template Writer")
    run = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        plugin_id=plugin.id,
        input_summary_json='{"target_surface":"/admin-login","target_type":"web"}',
        output_summary_json='{"template_preview":"id: brp-test\\ninfo:\\n  severity: info\\nhttp:\\n  - method: GET\\n    path:\\n      - \\"{{BaseURL}}/admin-login\\"","target_type":"web"}',
        created_at=datetime.now(timezone.utc),
    )
    policy = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        target_type="web",
        max_http_requests_per_run=5,
        max_script_lines=80,
        allow_network_calls=True,
        require_comment_header=True,
        require_disclaimer=True,
        allowed_modules_json='["requests"]',
        blocked_modules_json='["subprocess","socket"]',
        enabled=True,
        owner="security",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    intel = SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        source_type="article",
        source_name="manual",
        source_item_id="a1",
        title="Thai admin bypass article",
        summary_th="summary",
        cve_id="CVE-2026-0001",
        target_surface="/admin-login",
        target_type="web",
        tags_json='["web"]',
        references_json='["https://example.com/article"]',
        payload_json="{}",
        published_at=datetime.now(timezone.utc),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db = _FakeDB(
        object_map={site_id: site},
        scalar_values=[plugin, run, plugin, run, policy],
        scalar_batches=[[intel]],
    )

    result = red_plugin_intelligence.export_red_plugin_output(
        db,
        site_id=site_id,
        plugin_code="red_template_writer",
        export_kind="threat_content_bundle",
    )

    assert result["status"] == "ok"
    assert result["export"]["export_kind"] == "threat_content_bundle"
    assert result["export"]["threat_content_suggestion"]["title"] == "Thai admin bypass article"


def test_upsert_red_plugin_sync_source_persists_normalized_row() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck")
    db = _FakeDB(object_map={site_id: site}, scalar_values=[None])

    result = red_plugin_intelligence.upsert_red_plugin_sync_source(
        db,
        site_id=site_id,
        source_name=" Threat Feed ",
        source_type="NEWS",
        source_url="https://example.com/feed.json",
        target_type="WEB",
        parser_kind="json_feed",
        request_headers={"Authorization": "Bearer token"},
        sync_interval_minutes=30,
        enabled=True,
        owner="ops",
    )

    assert result["status"] == "created"
    assert result["source"]["source_name"] == "Threat Feed"
    assert result["source"]["source_type"] == "news"
    assert result["source"]["target_type"] == "web"
    assert len(db.added) == 1


def test_sync_red_plugin_intelligence_source_imports_fetched_items(monkeypatch) -> None:
    site_id = uuid4()
    source_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck")
    source = SimpleNamespace(
        id=source_id,
        site_id=site_id,
        source_name="threat-feed",
        source_type="article",
        source_url="https://example.com/feed.json",
        target_type="web",
        parser_kind="json_feed",
        request_headers_json="{}",
        sync_interval_minutes=30,
        enabled=True,
        last_synced_at=None,
        updated_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        owner="ops",
    )
    db = _FakeDB(object_map={site_id: site}, scalar_values=[source])
    monkeypatch.setattr(
        red_plugin_intelligence,
        "_fetch_sync_source_payload",
        lambda row: (
            "ok",
            {
                "items": [
                    {
                        "title": "Thai auth advisory",
                        "summary": "summary",
                        "cve_id": "CVE-2026-1111",
                        "target_surface": "/admin-login",
                    }
                ]
            },
        ),
    )
    monkeypatch.setattr(
        red_plugin_intelligence,
        "import_red_plugin_intelligence",
        lambda db, site_id, items, actor="": {
            "status": "ok",
            "site_id": str(site_id),
            "count": len(items),
            "created_count": len(items),
            "updated_count": 0,
            "rows": items,
        },
    )

    result = red_plugin_intelligence.sync_red_plugin_intelligence_source(
        db,
        site_id=site_id,
        dry_run=False,
        actor="sync_tester",
    )

    assert result["status"] == "ok"
    assert result["fetched_count"] == 1
    assert result["import_result"]["created_count"] == 1
    assert result["run"]["status"] == "ok"
    assert len(db.added) == 1


def test_publish_red_template_to_threat_pack_creates_pack(monkeypatch) -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", display_name="Duck")
    db = _FakeDB(object_map={site_id: site}, scalar_values=[None])
    monkeypatch.setattr(
        red_plugin_intelligence,
        "export_red_plugin_output",
        lambda db, **kwargs: {
            "status": "ok",
            "site_id": str(site_id),
            "plugin_code": "red_template_writer",
            "run_id": str(uuid4()),
            "export": {
                "title": "Nuclei AI-Template Writer export for Duck",
                "threat_content_suggestion": {
                    "title": "CVE-2026-2222 auth bypass",
                    "category": "web",
                    "mitre_techniques": ["T1190"],
                },
                "metadata": {
                    "source_intelligence": {
                        "cve_id": "CVE-2026-2222",
                        "summary_th": "Validate admin auth bypass safely",
                        "target_type": "web",
                    }
                },
            },
        },
    )

    result = red_plugin_intelligence.publish_red_template_to_threat_pack(db, site_id=site_id, activate=True)

    assert result["status"] == "created"
    assert result["pack"]["pack_code"].startswith("duck-")
    assert result["pack"]["is_active"] is True
    assert "Validate admin auth bypass safely" in result["pack"]["attack_steps"]
