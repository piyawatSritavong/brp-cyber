from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import threat_content_pipeline


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, scalar_values=None, scalar_batches=None):
        self.scalar_values = list(scalar_values or [])
        self.scalar_batches = list(scalar_batches or [])
        self.added = []

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


def test_upsert_threat_content_pipeline_policy_creates_record() -> None:
    db = _FakeDB(scalar_values=[None])
    result = threat_content_pipeline.upsert_threat_content_pipeline_policy(
        db,
        scope="global",
        min_refresh_interval_minutes=720,
        preferred_categories=["identity", "ransomware"],
        max_packs_per_run=6,
        auto_activate=True,
        route_alert=False,
        enabled=True,
        owner="secops",
    )
    assert result["status"] == "created"
    assert result["policy"]["scope"] == "global"
    assert result["policy"]["max_packs_per_run"] == 6
    assert len(db.added) == 1


def test_run_threat_content_pipeline_executes_candidates(monkeypatch) -> None:
    db = _FakeDB(scalar_values=[None])

    monkeypatch.setattr(
        threat_content_pipeline,
        "get_threat_content_pipeline_policy",
        lambda _db, scope="global": {
            "status": "ok",
            "policy": {
                "scope": scope,
                "min_refresh_interval_minutes": 60,
                "preferred_categories": ["identity", "web"],
                "max_packs_per_run": 3,
                "auto_activate": True,
                "route_alert": False,
                "enabled": True,
                "owner": "security",
            },
        },
    )
    monkeypatch.setattr(
        threat_content_pipeline,
        "_select_candidates",
        lambda categories, max_packs: [
            {"pack_code": "identity_abuse_daily"},
            {"pack_code": "web_attack_surface_guard"},
        ],
    )

    results = iter(
        [
            {"status": "created", "pack_code": "identity_abuse_daily", "activate": True},
            {"status": "refreshed", "pack_code": "web_attack_surface_guard", "activate": True},
        ]
    )
    monkeypatch.setattr(
        threat_content_pipeline,
        "_apply_candidate",
        lambda _db, candidate, dry_run=False, auto_activate=True: next(results),
    )
    monkeypatch.setattr(
        threat_content_pipeline,
        "threat_content_pipeline_federation",
        lambda _db, limit=200, stale_after_hours=48: {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count": 2,
            "stale_count": 0,
            "rows": [],
        },
    )

    result = threat_content_pipeline.run_threat_content_pipeline(
        db,
        scope="global",
        dry_run=False,
        force=True,
        actor="tester",
    )
    assert result["status"] == "ok"
    assert result["execution"]["should_run"] is True
    assert result["execution"]["candidate_count"] == 2
    assert result["execution"]["created_count"] == 1
    assert result["execution"]["refreshed_count"] == 1
    assert len(db.added) == 1


def test_run_threat_content_pipeline_scheduler_executes_due_policy(monkeypatch) -> None:
    policy = SimpleNamespace(scope="global", enabled=True, updated_at=datetime.now(timezone.utc))
    db = _FakeDB(scalar_batches=[[policy]])

    monkeypatch.setattr(
        threat_content_pipeline,
        "run_threat_content_pipeline",
        lambda _db, scope="global", dry_run=None, force=False, actor="": {
            "status": "dry_run",
            "run": {"run_id": "run-1"},
            "execution": {"should_run": True, "candidate_count": 3},
        },
    )

    result = threat_content_pipeline.run_threat_content_pipeline_scheduler(db, limit=100, actor="scheduler")
    assert result["scheduled_policy_count"] == 1
    assert result["executed_count"] == 1
    assert result["skipped_count"] == 0
