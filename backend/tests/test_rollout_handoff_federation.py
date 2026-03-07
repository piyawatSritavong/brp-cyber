from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_rollout_handoff_federation as federation


class _Tenant:
    def __init__(self, tenant_id, tenant_code: str) -> None:
        self.id = tenant_id
        self.tenant_code = tenant_code


def test_rollout_handoff_federation_heatmap_and_matrix() -> None:
    tenants = [_Tenant(uuid4(), "acb"), _Tenant(uuid4(), "xyz")]
    federation._list_tenants = lambda db, limit: tenants[:limit]

    def _gov(tenant_id, limit=200):
        if str(tenant_id) == str(tenants[0].id):
            return {"risk_snapshot": {"max_risk_score": 88, "blocked_count": 2}, "containment_event_count": 4}
        return {"risk_snapshot": {"max_risk_score": 20, "blocked_count": 0}, "containment_event_count": 1}

    federation.rollout_handoff_governance_snapshot = _gov

    heatmap = federation.rollout_handoff_federation_heatmap(db=None, limit=20)
    assert heatmap["count"] == 2
    assert heatmap["rows"][0]["tenant_code"] == "acb"
    assert heatmap["rows"][0]["risk_tier"] in {"high", "critical"}

    matrix = federation.rollout_handoff_escalation_matrix(db=None, limit=20)
    assert matrix["count"] == 2
    assert "escalation_plan" in matrix["rows"][0]


def test_apply_rollout_handoff_escalation_matrix_dry_run_and_apply() -> None:
    tenant_id = uuid4()
    federation.rollout_handoff_escalation_matrix = lambda db, limit=200: {
        "rows": [
            {"tenant_id": str(tenant_id), "risk_tier": "critical", "federated_risk_score": 94},
            {"tenant_id": str(uuid4()), "risk_tier": "medium", "federated_risk_score": 44},
        ]
    }
    federation.get_rollout_handoff_policy = lambda tenant_id: {
        "policy": {
            "anomaly_detection_enabled": True,
            "auto_revoke_on_ip_mismatch": True,
            "max_denied_attempts_before_revoke": 3,
            "adaptive_hardening_enabled": True,
            "risk_threshold_harden": 60,
            "risk_threshold_block": 85,
            "harden_session_ttl_seconds": 300,
            "containment_high_threshold": 60,
            "containment_critical_threshold": 85,
            "containment_action_high": "harden_session",
        }
    }
    federation.upsert_rollout_handoff_policy = lambda **kwargs: {"policy": kwargs}

    dry = federation.apply_rollout_handoff_escalation_matrix(db=None, limit=20, min_tier="high", dry_run=True)
    assert dry["count"] == 1
    assert dry["rows"][0]["status"] == "dry_run"

    applied = federation.apply_rollout_handoff_escalation_matrix(db=None, limit=20, min_tier="high", dry_run=False)
    assert applied["count"] == 1
    assert applied["rows"][0]["status"] == "applied"
