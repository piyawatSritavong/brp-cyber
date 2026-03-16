from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import site_ops


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, scalar_batches=None, site_map=None, pack_map=None):
        self.scalar_batches = list(scalar_batches or [])
        self.site_map = site_map or {}
        self.pack_map = pack_map or {}

    def scalars(self, _stmt):
        rows = self.scalar_batches.pop(0) if self.scalar_batches else []
        return _FakeScalarResult(rows)

    def get(self, model, object_id):
        model_name = getattr(model, "__name__", "")
        if model_name == "Site":
            return self.site_map.get(object_id)
        if model_name == "ThreatContentPack":
            return self.pack_map.get(object_id)
        return None


@dataclass
class _RedExploitPathRun:
    threat_pack_id: object | None
    proof_json: str
    created_at: datetime


@dataclass
class _BlueEvent:
    ai_severity: str
    status: str
    created_at: datetime


@dataclass
class _Rule:
    rule_name: str
    rule_logic_json: str
    updated_at: datetime


def test_generate_purple_executive_scorecard_returns_heatmap_and_sla() -> None:
    now = datetime.now(timezone.utc)
    site_id = uuid4()
    pack_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", tenant=SimpleNamespace(tenant_code="acb"))
    pack = SimpleNamespace(id=pack_id, mitre_techniques_json='["T1110","T1190"]')
    red_runs = [
        _RedExploitPathRun(
            threat_pack_id=pack_id,
            proof_json='{"mitre_techniques":["T1110"]}',
            created_at=now,
        )
    ]
    blue_rows = [
        _BlueEvent(ai_severity="high", status="applied", created_at=now),
        _BlueEvent(ai_severity="medium", status="open", created_at=now),
        _BlueEvent(ai_severity="low", status="open", created_at=now),
    ]
    rules = [
        _Rule(
            rule_name="Velocity guard for /admin-login",
            rule_logic_json='{"signal":"failed_login_spike"}',
            updated_at=now,
        )
    ]
    db = _FakeDB(
        scalar_batches=[red_runs, blue_rows, rules],
        site_map={site_id: site},
        pack_map={pack_id: pack},
    )

    result = site_ops.generate_purple_executive_scorecard(
        db,
        site_id,
        lookback_runs=30,
        lookback_events=500,
        sla_target_seconds=120,
    )
    assert result["status"] == "completed"
    assert result["summary"]["site_code"] == "duck-sec-ai"
    assert result["summary"]["attacked_techniques"] >= 1
    assert isinstance(result["heatmap"], list)
    assert "sla_status" in result["remediation_sla"]
    assert result["remediation_sla"]["suspicious_event_count"] == 2


def test_purple_executive_federation_aggregates_sites(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    site_1 = SimpleNamespace(id=uuid4(), site_code="duck-sec-ai", tenant=SimpleNamespace(tenant_code="acb"), created_at=now)
    site_2 = SimpleNamespace(id=uuid4(), site_code="zeta-app", tenant=SimpleNamespace(tenant_code="zeta"), created_at=now)
    db = _FakeDB(scalar_batches=[[site_1, site_2]])

    def _fake_scorecard(_db, site_id, **_kwargs):
        if site_id == site_1.id:
            return {
                "status": "completed",
                "summary": {"heatmap_coverage": 0.8, "attacked_techniques": 5, "covered_techniques": 4},
                "remediation_sla": {"estimated_mttr_seconds": 90, "target_mttr_seconds": 120, "sla_status": "pass", "apply_rate": 0.9},
            }
        return {
            "status": "completed",
            "summary": {"heatmap_coverage": 0.3, "attacked_techniques": 6, "covered_techniques": 2},
            "remediation_sla": {"estimated_mttr_seconds": 240, "target_mttr_seconds": 120, "sla_status": "at_risk", "apply_rate": 0.4},
        }

    monkeypatch.setattr(site_ops, "generate_purple_executive_scorecard", _fake_scorecard)
    result = site_ops.purple_executive_federation(db, limit=200, lookback_runs=30, lookback_events=500, sla_target_seconds=120)
    assert result["status"] == "completed"
    assert result["count"] == 2
    assert result["at_risk_sites"] == 1
    assert result["rows"][0]["site_code"] == "zeta-app"


def test_generate_nist_csf_gap_template_returns_framework_controls() -> None:
    now = datetime.now(timezone.utc)
    site_id = uuid4()
    site = SimpleNamespace(id=site_id, site_code="duck-sec-ai", tenant=SimpleNamespace(tenant_code="acb"))
    red_rows = [SimpleNamespace(findings_json='{"risk_score":55,"missing_security_headers":["content-security-policy"],"sensitive_paths_open":[{"path":"/admin"}]}', created_at=now)]
    blue_rows = [
        _BlueEvent(ai_severity="high", status="applied", created_at=now),
        _BlueEvent(ai_severity="medium", status="open", created_at=now),
    ]
    purple_rows = [SimpleNamespace(created_at=now)]
    db = _FakeDB(scalar_batches=[red_rows, blue_rows, purple_rows], site_map={site_id: site})

    result = site_ops.generate_nist_csf_gap_template(db, site_id, limit=100)

    assert result["status"] == "completed"
    assert result["framework"] == "NIST Cybersecurity Framework 2.0"
    assert len(result["controls"]) == 4
    assert result["controls"][0]["control_id"] == "ID.RA-01"
