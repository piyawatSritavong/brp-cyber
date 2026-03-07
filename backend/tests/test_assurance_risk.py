from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_assurance_risk as risk


class _Tenant:
    def __init__(self, tenant_id, tenant_code: str) -> None:
        self.id = tenant_id
        self.tenant_code = tenant_code


def test_assurance_risk_heatmap_and_recommendations() -> None:
    tenants = [_Tenant(uuid4(), "acb"), _Tenant(uuid4(), "xyz")]
    risk._list_tenants = lambda db, limit: tenants[:limit]
    risk.objective_gate_dashboard = lambda limit=200: {
        "rows": [
            {"tenant_id": str(tenants[0].id), "overall_pass": False, "failed_gate_count": 4},
            {"tenant_id": str(tenants[1].id), "overall_pass": True, "failed_gate_count": 0},
        ]
    }

    def _contract_eval(tenant_id, tenant_code, limit=200):
        if tenant_code == "acb":
            return {"status": "ok", "evaluation": {"contract_pass": False}}
        return {"status": "ok", "evaluation": {"contract_pass": True}}

    risk.evaluate_assurance_contract = _contract_eval
    risk.assurance_remediation_effectiveness = lambda tenant_code, limit=200: {
        "average_effectiveness_delta": -0.1 if tenant_code == "acb" else 0.1,
        "rollback_batches": 2 if tenant_code == "acb" else 0,
    }

    heatmap = risk.assurance_risk_heatmap(db=None, limit=20)
    assert heatmap["count"] == 2
    assert heatmap["rows"][0]["tenant_code"] == "acb"
    assert heatmap["rows"][0]["risk_tier"] in {"high", "critical"}

    rec = risk.assurance_risk_recommendations(db=None, limit=20)
    assert rec["count"] >= 1


def test_apply_assurance_risk_recommendations() -> None:
    risk.assurance_risk_recommendations = lambda db, limit=200: {
        "rows": [
            {"tenant_code": "acb", "risk_tier": "critical", "risk_score": 90, "recommended_policy_pack": {"notify_only": False}},
            {"tenant_code": "xyz", "risk_tier": "medium", "risk_score": 40, "recommended_policy_pack": {"notify_only": False}},
        ]
    }
    risk.get_assurance_policy_pack = lambda tenant_code: {"policy_pack": {"pack_version": "1.0"}}
    risk.upsert_assurance_policy_pack = lambda tenant_code, payload: {"status": "upserted", "tenant_code": tenant_code}

    dry = risk.apply_assurance_risk_recommendations(db=None, limit=20, max_tier="high", dry_run=True)
    assert dry["count"] == 1
    assert dry["rows"][0]["tenant_code"] == "acb"

    applied = risk.apply_assurance_risk_recommendations(db=None, limit=20, max_tier="high", dry_run=False)
    assert applied["count"] == 1
    assert applied["rows"][0]["status"] == "upserted"
