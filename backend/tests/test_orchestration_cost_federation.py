from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_orchestration_cost_federation as federation


class _Tenant:
    def __init__(self, tenant_id, tenant_code: str) -> None:
        self.id = tenant_id
        self.tenant_code = tenant_code


def test_cost_anomaly_federation_heatmap_and_matrix() -> None:
    tenants = [_Tenant(uuid4(), "acb"), _Tenant(uuid4(), "xyz")]
    orig_list = federation._list_tenants
    orig_eval = federation.evaluate_orchestration_cost_guardrail
    try:
        federation._list_tenants = lambda db, limit: tenants[:limit]

        def _eval(tenant_id, tenant_code, apply_actions=False):
            if tenant_code == "acb":
                return {
                    "state": {"breached": True, "anomaly": True, "pressure": True, "severity": "critical"},
                    "metrics": {
                        "pressure_ratio": 1.4,
                        "cost_ratio": 1.2,
                        "token_ratio": 1.1,
                        "monthly_cost_usd": 120.0,
                        "monthly_tokens": 2_000_000,
                    },
                }
            return {
                "state": {"breached": False, "anomaly": False, "pressure": False, "severity": "normal"},
                "metrics": {
                    "pressure_ratio": 0.3,
                    "cost_ratio": 0.2,
                    "token_ratio": 0.1,
                    "monthly_cost_usd": 5.0,
                    "monthly_tokens": 2000,
                },
            }

        federation.evaluate_orchestration_cost_guardrail = _eval

        heatmap = federation.orchestration_cost_anomaly_federation_heatmap(db=None, limit=20)
        assert heatmap["count"] == 2
        assert heatmap["critical_count"] == 1
        assert heatmap["rows"][0]["tenant_code"] == "acb"

        matrix = federation.orchestration_cost_policy_tightening_matrix(db=None, limit=20)
        assert matrix["count"] == 2
        assert matrix["rows"][0]["recommended_profile_patch"]["throttle_mode_on_anomaly"] == "strict"
    finally:
        federation._list_tenants = orig_list
        federation.evaluate_orchestration_cost_guardrail = orig_eval


def test_apply_cost_policy_tightening_dry_run_and_apply() -> None:
    tenant_id = uuid4()
    orig_matrix = federation.orchestration_cost_policy_tightening_matrix
    orig_get = federation.get_orchestration_cost_guardrail_profile
    orig_upsert = federation.upsert_orchestration_cost_guardrail_profile
    try:
        federation.orchestration_cost_policy_tightening_matrix = lambda db, limit=200: {
            "rows": [
                {
                    "tenant_id": str(tenant_id),
                    "tenant_code": "acb",
                    "risk_tier": "critical",
                    "recommended_profile_patch": {"pressure_ratio_threshold": 0.55, "throttle_mode_on_anomaly": "strict"},
                }
            ]
        }
        federation.get_orchestration_cost_guardrail_profile = lambda tenant_id: {
            "profile": {"pressure_ratio_threshold": 0.9, "throttle_mode_on_anomaly": "conservative"}
        }
        federation.upsert_orchestration_cost_guardrail_profile = lambda tenant_id, payload: {
            "status": "upserted",
            "profile": payload,
        }

        dry = federation.apply_orchestration_cost_policy_tightening_matrix(
            db=None,
            limit=20,
            min_tier="high",
            dry_run=True,
        )
        assert dry["count"] == 1
        assert dry["rows"][0]["status"] == "dry_run"

        applied = federation.apply_orchestration_cost_policy_tightening_matrix(
            db=None,
            limit=20,
            min_tier="high",
            dry_run=False,
        )
        assert applied["count"] == 1
        assert applied["rows"][0]["status"] == "applied"
        assert applied["rows"][0]["updated_profile"]["throttle_mode_on_anomaly"] == "strict"
    finally:
        federation.orchestration_cost_policy_tightening_matrix = orig_matrix
        federation.get_orchestration_cost_guardrail_profile = orig_get
        federation.upsert_orchestration_cost_guardrail_profile = orig_upsert
