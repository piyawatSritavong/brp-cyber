from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_assurance_contracts as ac


class FakeRedis:
    def __init__(self) -> None:
        self.strings: dict[str, str] = {}

    def set(self, key: str, value: str) -> bool:
        self.strings[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.strings.get(key)


def test_upsert_and_get_assurance_contract() -> None:
    fake = FakeRedis()
    ac.redis_client = fake

    upsert = ac.upsert_assurance_contract(
        "acb",
        {
            "owner": "ciso-office",
            "min_samples": 10,
            "required_frameworks": ["soc2"],
        },
    )
    assert upsert["status"] == "upserted"

    loaded = ac.get_assurance_contract("acb")
    assert loaded["status"] == "ok"
    assert loaded["contract"]["owner"] == "ciso-office"
    assert loaded["contract"]["min_samples"] == 10


def test_evaluate_assurance_contract_pass_and_fail() -> None:
    fake = FakeRedis()
    ac.redis_client = fake

    tenant_id = uuid4()
    tenant_code = "acb"

    ac.upsert_assurance_contract(
        tenant_code,
        {
            "min_samples": 2,
            "min_overall_pass_rate": 0.5,
            "min_gate_pass_rate": 0.5,
            "max_enterprise_monthly_cost_usd": 60.0,
            "required_gates": ["red", "blue"],
            "required_frameworks": ["soc2"],
            "min_framework_readiness_score": 80.0,
        },
    )

    ac.list_objective_gate_history = lambda tenant_id, limit=100: [
        {
            "overall_pass": True,
            "gates": {
                "red": {"pass": True},
                "blue": {"pass": True},
                "enterprise": {"monthly_cost_usd": 45.0},
            },
        },
        {
            "overall_pass": False,
            "gates": {
                "red": {"pass": False},
                "blue": {"pass": True},
                "enterprise": {"monthly_cost_usd": 55.0},
            },
        },
    ]
    ac.regulatory_scorecard = lambda framework: {"status": "ok", "framework": framework, "readiness_score": 90}

    result = ac.evaluate_assurance_contract(tenant_id, tenant_code, limit=10)
    assert result["status"] == "ok"
    assert result["evaluation"]["contract_pass"] is True
    assert result["evaluation"]["overall_pass_rate"] == 0.5

    ac.regulatory_scorecard = lambda framework: {"status": "ok", "framework": framework, "readiness_score": 60}
    failed = ac.evaluate_assurance_contract(tenant_id, tenant_code, limit=10)
    assert failed["status"] == "ok"
    assert failed["evaluation"]["contract_pass"] is False
    assert len(failed["evaluation"]["unmet_clauses"]) >= 1
