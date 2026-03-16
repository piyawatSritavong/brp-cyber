from __future__ import annotations

import base64
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from app.services import purple_roi_dashboard


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

    def get(self, _model, object_id):
        return self.object_map.get(object_id)

    def scalar(self, _stmt):
        if not self.scalar_values:
            return None
        return self.scalar_values.pop(0)

    def scalars(self, _stmt):
        rows = self.scalar_batches.pop(0) if self.scalar_batches else []
        return _FakeScalarResult(rows)


def _snapshot(site_id, created_at, validated, automation, noise, saved, high=1):
    created_at_value = datetime.fromisoformat(created_at.replace("Z", "+00:00")) if isinstance(created_at, str) else created_at
    return SimpleNamespace(
        id=uuid4(),
        site_id=site_id,
        lookback_days=30,
        status="completed",
        summary_json=(
            '{'
            f'"site_id":"{site_id}",'
            '"site_code":"duck",'
            '"headline_th":"roi headline",'
            '"board_statement_th":"roi statement",'
            '"board_metrics":{'
            f'"validated_findings":{validated},'
            f'"high_risk_findings":{high},'
            f'"automation_coverage_pct":{automation},'
            f'"noise_reduction_pct":{noise},'
            f'"estimated_manual_effort_saved_usd":{saved}'
            '}'
            '}'
        ),
        details_json='{"top_value_drivers":[{"driver":"Validated risk reduction","statement_th":"validated"}]}',
        created_at=created_at_value,
    )


def test_list_purple_roi_trends_returns_deltas() -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", display_name="Duck")
    latest = _snapshot(site_id, "2026-03-15T00:00:00+00:00", validated=5, automation=72, noise=81, saved=320)
    previous = _snapshot(site_id, "2026-03-14T00:00:00+00:00", validated=3, automation=60, noise=70, saved=250)
    db = _FakeDB(object_map={site_id: site}, scalar_batches=[[latest, previous]])

    result = purple_roi_dashboard.list_purple_roi_trends(db, site_id=site_id, limit=12)

    assert result["status"] == "ok"
    assert result["count"] == 2
    assert result["summary"]["validated_findings_delta"] == 2.0
    assert result["summary"]["automation_coverage_delta_pct"] == 12.0
    assert result["summary"]["direction"] == "improving"


def test_build_purple_roi_portfolio_rollup_aggregates_latest_snapshots() -> None:
    tenant = SimpleNamespace(id=uuid4(), tenant_code="acb")
    site_a_id = uuid4()
    site_b_id = uuid4()
    site_a = SimpleNamespace(id=site_a_id, site_code="duck-a", display_name="Duck A", tenant=tenant)
    site_b = SimpleNamespace(id=site_b_id, site_code="duck-b", display_name="Duck B", tenant=tenant)
    latest_a = _snapshot(site_a_id, "2026-03-15T00:00:00+00:00", validated=5, automation=72, noise=81, saved=320)
    latest_b = _snapshot(site_b_id, "2026-03-15T00:00:00+00:00", validated=2, automation=40, noise=30, saved=80)
    db = _FakeDB(scalar_batches=[[site_a, site_b]], scalar_values=[latest_a, latest_b])

    result = purple_roi_dashboard.build_purple_roi_portfolio_rollup(db, tenant_code="acb", limit=50)

    assert result["status"] == "ok"
    assert result["count"] == 2
    assert result["summary"]["sites_with_snapshots"] == 2
    assert result["summary"]["total_validated_findings"] == 7.0
    assert result["summary"]["highest_value_site_code"] == "duck-a"


def test_export_purple_roi_board_pack_builds_sections_and_slides(monkeypatch) -> None:
    tenant = SimpleNamespace(id=uuid4(), tenant_code="acb")
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", display_name="Duck", tenant=tenant)
    latest = _snapshot(site_id, "2026-03-15T00:00:00+00:00", validated=5, automation=72, noise=81, saved=320)
    db = _FakeDB(object_map={site_id: site}, scalar_values=[latest])
    monkeypatch.setattr(
        purple_roi_dashboard,
        "list_purple_roi_trends",
        lambda db, site_id, limit=12: {
            "status": "ok",
            "site_id": str(site_id),
            "count": 2,
            "summary": {
                "trend_points": 2,
                "latest_created_at": "2026-03-15T00:00:00+00:00",
                "validated_findings_delta": 2,
                "automation_coverage_delta_pct": 10,
                "noise_reduction_delta_pct": 6,
                "estimated_manual_effort_saved_delta_usd": 70,
                "direction": "improving",
            },
            "rows": [],
        },
    )
    monkeypatch.setattr(
        purple_roi_dashboard,
        "build_purple_roi_portfolio_rollup",
        lambda db, tenant_code="", limit=50: {
            "status": "ok",
            "tenant_code": tenant_code,
            "count": 1,
            "summary": {
                "tenant_code": tenant_code,
                "total_sites": 1,
                "sites_with_snapshots": 1,
                "no_snapshot_sites": 0,
                "total_validated_findings": 5,
                "total_estimated_manual_effort_saved_usd": 320,
                "average_automation_coverage_pct": 72,
                "average_noise_reduction_pct": 81,
                "highest_value_site_code": "duck",
            },
            "rows": [],
        },
    )

    result = purple_roi_dashboard.export_purple_roi_board_pack(
        db,
        site_id=site_id,
        export_format="ppt",
        template_pack="roi_risk_committee",
        title_override="ACB Board Pack",
        include_portfolio=True,
        tenant_code="acb",
        site_limit=50,
    )

    assert result["status"] == "ok"
    assert result["export"]["export_format"] == "ppt"
    assert result["export"]["title"] == "ACB Board Pack"
    assert result["export"]["includes_portfolio"] is True
    assert result["export"]["template_pack"]["pack_code"] == "roi_risk_committee"
    assert result["export"]["renderer"] == "native_binary"
    assert result["export"]["mime_type"] == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    assert result["export"]["filename"].endswith(".pptx")
    assert result["export"]["byte_size"] > 0
    assert len(result["export"]["sections"]) >= 4
    assert len(result["export"]["slides"]) >= 5
    assert base64.b64decode(result["export"]["content_base64"]).startswith(b"PK")


def test_list_purple_roi_template_packs_filters_by_audience() -> None:
    result = purple_roi_dashboard.list_purple_roi_template_packs(audience="board")

    assert result["status"] == "ok"
    assert result["count"] >= 1
    assert all(row["audience"] == "board" for row in result["rows"])


def test_export_purple_roi_board_pack_renders_pdf_binary(monkeypatch) -> None:
    tenant = SimpleNamespace(id=uuid4(), tenant_code="acb")
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck", display_name="Duck", tenant=tenant)
    latest = _snapshot(site_id, "2026-03-15T00:00:00+00:00", validated=4, automation=61, noise=77, saved=220)
    db = _FakeDB(object_map={site_id: site}, scalar_values=[latest])
    monkeypatch.setattr(
        purple_roi_dashboard,
        "list_purple_roi_trends",
        lambda db, site_id, limit=12: {"status": "ok", "site_id": str(site_id), "count": 1, "summary": {"trend_points": 1}, "rows": []},
    )

    result = purple_roi_dashboard.export_purple_roi_board_pack(
        db,
        site_id=site_id,
        export_format="pdf",
        template_pack="roi_board_minimal",
        title_override="PDF Board Pack",
        include_portfolio=False,
        tenant_code="acb",
        site_limit=50,
    )

    assert result["status"] == "ok"
    assert result["export"]["mime_type"] == "application/pdf"
    assert result["export"]["filename"].endswith(".pdf")
    assert result["export"]["byte_size"] > 0
    assert base64.b64decode(result["export"]["content_base64"]).startswith(b"%PDF")
