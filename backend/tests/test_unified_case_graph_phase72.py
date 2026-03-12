from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.competitive_engine import build_unified_case_graph


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, *, site=None, scalar_batches=None, scalar_values=None):
        self.site = site
        self.scalar_batches = list(scalar_batches or [])
        self.scalar_values = list(scalar_values or [])

    def get(self, _model, _object_id):
        return self.site

    def scalars(self, _stmt):
        rows = self.scalar_batches.pop(0) if self.scalar_batches else []
        return _FakeScalarResult(rows)

    def scalar(self, _stmt):
        if not self.scalar_values:
            return None
        return self.scalar_values.pop(0)


@dataclass
class _ExploitRun:
    id: object
    risk_score: int
    created_at: datetime


@dataclass
class _BlueEvent:
    id: object
    event_type: str
    ai_severity: str
    status: str
    created_at: datetime
    action_taken: str


@dataclass
class _Rule:
    id: object
    rule_name: str
    updated_at: datetime


@dataclass
class _SoarExecution:
    id: object
    result_json: str
    playbook_id: object
    status: str
    updated_at: datetime


@dataclass
class _ConnectorEvent:
    id: object
    connector_source: str
    event_type: str
    status: str
    payload_json: str
    created_at: datetime


@dataclass
class _ReplayRun:
    id: object
    connector_source: str
    status: str
    risk_tier: str
    replayed_count: int
    failed_count: int
    created_at: datetime


@dataclass
class _PurpleReport:
    id: object
    created_at: datetime


def test_build_unified_case_graph_includes_soar_connector_and_risk() -> None:
    now = datetime.now(timezone.utc)
    site = SimpleNamespace(id=uuid4(), tenant_id=uuid4(), site_code="duck-sec-ai", display_name="Duck Sec AI")

    dead_letter_id = uuid4()
    connector_retry_id = uuid4()

    db = _FakeDB(
        site=site,
        scalar_batches=[
            [_ExploitRun(id=uuid4(), risk_score=78, created_at=now)],
            [_BlueEvent(id=uuid4(), event_type="waf_http", ai_severity="high", status="open", created_at=now, action_taken="block-ip-and-waf-tighten")],
            [_Rule(id=uuid4(), rule_name="Velocity guard", updated_at=now)],
            [
                _SoarExecution(
                    id=uuid4(),
                    result_json='{"playbook_code":"block-ip-and-waf-tighten"}',
                    playbook_id=uuid4(),
                    status="applied",
                    updated_at=now,
                )
            ],
            [
                _ConnectorEvent(
                    id=dead_letter_id,
                    connector_source="splunk",
                    event_type="dead_letter",
                    status="failed",
                    payload_json="{}",
                    created_at=now,
                ),
                _ConnectorEvent(
                    id=connector_retry_id,
                    connector_source="splunk",
                    event_type="retry",
                    status="retrying",
                    payload_json=f'{{"replay_of_event_id":"{dead_letter_id}"}}',
                    created_at=now,
                ),
            ],
            [_ReplayRun(id=uuid4(), connector_source="splunk", status="ok", risk_tier="medium", replayed_count=1, failed_count=0, created_at=now)],
        ],
        scalar_values=[_PurpleReport(id=uuid4(), created_at=now)],
    )

    result = build_unified_case_graph(db, site.id, limit=50)

    assert result["status"] == "completed"
    assert result["summary"]["soar_executions"] == 1
    assert result["summary"]["connector_events"] == 2
    assert result["summary"]["connector_replay_runs"] == 1
    assert result["summary"]["risk_tier"] in {"medium", "high", "critical"}
    assert result["risk"]["unresolved_connector_dlq"] == 0
    assert len(result["timeline"]) >= 4
    edge_relations = {edge["relation"] for edge in result["graph"]["edges"]}
    assert "mitigated_by_playbook" in edge_relations
    assert "replayed_as" in edge_relations
