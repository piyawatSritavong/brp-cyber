from __future__ import annotations

from dataclasses import dataclass

from app.services.connector_observability import connector_health_snapshot
from app.services.soar_playbook_hub import soar_marketplace_overview


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self, _stmt):
        return _FakeScalarResult(self._rows)


@dataclass
class _ConnectorRow:
    connector_source: str
    event_type: str
    status: str
    latency_ms: int


@dataclass
class _PlaybookRow:
    scope: str
    category: str
    is_active: bool


def test_connector_health_snapshot_aggregates_retry_and_dead_letter() -> None:
    db = _FakeDB(
        [
            _ConnectorRow(connector_source="splunk", event_type="delivery_attempt", status="success", latency_ms=100),
            _ConnectorRow(connector_source="splunk", event_type="retry", status="retrying", latency_ms=200),
            _ConnectorRow(connector_source="sentinel", event_type="dead_letter", status="failed", latency_ms=450),
            _ConnectorRow(connector_source="sentinel", event_type="delivery_attempt", status="success", latency_ms=80),
        ]
    )
    snapshot = connector_health_snapshot(db, limit=100)
    assert snapshot["total_events"] == 4
    assert snapshot["success_count"] == 2
    assert snapshot["retry_count"] >= 1
    assert snapshot["dead_letter_count"] == 1
    assert snapshot["failed_count"] >= 1
    assert snapshot["average_latency_ms"] > 0
    assert len(snapshot["sources"]) == 2


def test_soar_marketplace_overview_counts_scope_and_category() -> None:
    db = _FakeDB(
        [
            _PlaybookRow(scope="community", category="response", is_active=True),
            _PlaybookRow(scope="community", category="containment", is_active=False),
            _PlaybookRow(scope="partner", category="response", is_active=True),
        ]
    )
    summary = soar_marketplace_overview(db, limit=100)
    assert summary["total_playbooks"] == 3
    assert summary["active_playbooks"] == 2
    assert summary["scope_counts"]["community"] == 2
    assert summary["scope_counts"]["partner"] == 1
    assert summary["category_counts"]["response"] == 2

