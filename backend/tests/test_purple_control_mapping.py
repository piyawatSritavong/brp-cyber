from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services import purple_control_mapping


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


def test_build_purple_control_family_map_returns_rows(monkeypatch) -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", display_name="Duck Sec AI")
    db = _FakeDB(
        object_map={site_id: site},
        scalar_values=[SimpleNamespace(id=uuid4()), SimpleNamespace(id=uuid4())],
        scalar_batches=[
            [SimpleNamespace(rule_name="velocity")],
            [SimpleNamespace(owner="soc")],
            [SimpleNamespace(id=uuid4())],
            [SimpleNamespace(id=uuid4())],
            [SimpleNamespace(id=uuid4())],
            [SimpleNamespace(id=uuid4())],
        ],
    )
    monkeypatch.setattr(
        purple_control_mapping,
        "generate_iso27001_gap_template",
        lambda _db, _site_id, limit=200: {
            "controls": [
                {"control_id": "A.5.1", "status": "implemented"},
                {"control_id": "A.8.16", "status": "partial"},
            ]
        },
    )
    monkeypatch.setattr(
        purple_control_mapping,
        "generate_nist_csf_gap_template",
        lambda _db, _site_id, limit=200: {
            "controls": [
                {"control_id": "DE.AE-01", "status": "implemented"},
                {"control_id": "RS.MI-01", "status": "gap"},
            ]
        },
    )
    monkeypatch.setattr(
        purple_control_mapping,
        "generate_purple_executive_scorecard",
        lambda _db, _site_id, **_kwargs: {
            "summary": {"heatmap_coverage": 0.75},
            "remediation_sla": {"estimated_mttr_seconds": 90},
        },
    )

    result = purple_control_mapping.build_purple_control_family_map(db, site_id=site_id, framework="combined")

    assert result["status"] == "ok"
    assert result["summary"]["family_count"] >= 2
    assert any(row["framework"] == "ISO27001" for row in result["rows"])
    assert any(row["framework"] == "NIST_CSF" for row in result["rows"])


def test_export_purple_control_family_map_csv(monkeypatch) -> None:
    site_id = uuid4()
    db = _FakeDB()

    def _fake_build(_db, *, site_id, framework="combined"):
        return {
            "status": "ok",
            "site_id": str(site_id),
            "site_code": "duck-sec-ai",
            "summary": {"family_count": 1},
            "rows": [
                {
                    "framework": "ISO27001",
                    "family_code": "A.8",
                    "family_name": "ISO A.8 Technological Controls",
                    "coverage_status": "partial",
                    "coverage_pct": 0.5,
                    "control_total": 2,
                    "implemented_count": 1,
                    "partial_count": 1,
                    "gap_count": 0,
                    "policy_refs": ["managed_responder_policy"],
                    "evidence_refs": ["managed_responder_runs=2"],
                    "top_gaps": [],
                }
            ],
        }

    monkeypatch.setattr(purple_control_mapping, "build_purple_control_family_map", _fake_build)
    result = purple_control_mapping.export_purple_control_family_map(db, site_id=site_id, export_format="csv")

    assert result["status"] == "ok"
    assert result["export"]["export_format"] == "csv"
    assert "framework,family_code" in result["export"]["content"]
