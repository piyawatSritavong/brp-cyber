from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.services import purple_attack_layer_workflows


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, *, object_map=None):
        self.object_map = object_map or {}
        self.added = []

    def get(self, _model, object_id):
        return self.object_map.get(object_id)

    def scalars(self, _stmt):
        return _FakeScalarResult(list(self.added))

    def add(self, row):
        if getattr(row, "id", None) is None:
            row.id = uuid4()
        self.added.append(row)
        self.object_map[row.id] = row

    def commit(self):
        return None

    def refresh(self, row):
        self.object_map[row.id] = row
        return None


def test_import_update_and_export_attack_layer_workspace(monkeypatch) -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", display_name="Duck Sec AI")
    db = _FakeDB(object_map={site_id: site})

    imported = purple_attack_layer_workflows.import_purple_attack_layer_workspace(
        db,
        site_id=site_id,
        layer_name="Purple Layer",
        layer_document={
            "name": "Purple Layer",
            "domain": "enterprise-attack",
            "techniques": [{"techniqueID": "T1110", "score": 80, "comment": "baseline"}],
        },
        notes="initial import",
    )

    workspace_id = uuid4()
    db.added[0].id = workspace_id
    db.object_map[workspace_id] = db.added[0]

    updated = purple_attack_layer_workflows.update_purple_attack_layer_workspace(
        db,
        site_id=site_id,
        layer_id=workspace_id,
        technique_overrides=[{"techniqueID": "T1110", "score": 95, "color": "#F76C45"}],
        notes="updated",
    )
    exported = purple_attack_layer_workflows.export_purple_attack_layer_workspace(
        db,
        site_id=site_id,
        layer_id=workspace_id,
        export_format="svg",
    )

    assert imported["status"] == "ok"
    assert updated["status"] == "ok"
    assert updated["workspace"]["summary"]["technique_count"] == 1
    assert exported["status"] == "ok"
    assert exported["export"]["export_format"] == "svg"
    assert "<svg" in exported["export"]["content"]


def test_export_live_attack_layer_graphic(monkeypatch) -> None:
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", display_name="Duck Sec AI")
    db = _FakeDB(object_map={site_id: site})
    monkeypatch.setattr(
        purple_attack_layer_workflows,
        "generate_purple_executive_scorecard",
        lambda _db, _site_id, **_kwargs: {
            "heatmap": [
                {"technique_id": "T1110", "detection_status": "covered", "recommendation": "tighten auth"},
                {"technique_id": "T1566", "detection_status": "gap", "recommendation": "improve mailbox telemetry"},
            ]
        },
    )

    result = purple_attack_layer_workflows.export_live_purple_attack_layer_graphic(db, site_id=site_id, export_format="svg")

    assert result["status"] == "ok"
    assert result["export"]["export_format"] == "svg"
    assert "T1110" in result["export"]["content"]
