from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_assurance_remediation as ar


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.strings: dict[str, str] = {}
        self.counter = 0

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self.counter += 1
        event_id = f"{self.counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(key, {}).update(mapping)
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.strings[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

    def keys(self, pattern: str):
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k for k in self.hashes if k.startswith(prefix)]
        return [k for k in self.hashes if k == pattern]


def test_remediate_assurance_breach_pending() -> None:
    fake = FakeRedis()
    ar.redis_client = fake
    ar.send_telegram_message = lambda message: True

    tenant_id = uuid4()
    tenant_code = "acb"

    ar.evaluate_assurance_contract = lambda tenant_id, tenant_code, limit=100: {
        "status": "ok",
        "evaluation": {
            "contract_pass": False,
            "unmet_clauses": [
                {"clause": "min_gate_pass_rate", "gate": "blue"},
                {"clause": "max_enterprise_monthly_cost_usd"},
            ],
        },
    }
    ar.get_assurance_policy_pack = lambda tenant_code: {
        "status": "ok",
        "policy_pack": {
            "auto_apply_actions": [],
            "force_approval_actions": [],
            "blocked_actions": [],
            "max_auto_apply_actions_per_run": 0,
            "notify_only": False,
            "rollback_on_worse_result": True,
            "min_effectiveness_delta": 0.0,
        },
    }

    result = ar.remediate_assurance_breach(tenant_id, tenant_code, auto_apply=False)
    assert result["status"] == "remediation_planned"
    assert len(result["actions"]) >= 2

    status = ar.assurance_remediation_status(tenant_code, limit=10)
    assert status["count"] >= 2


def test_remediate_assurance_breach_applied() -> None:
    fake = FakeRedis()
    ar.redis_client = fake
    ar.send_telegram_message = lambda message: True

    tenant_id = uuid4()
    tenant_code = "acb"

    ar.evaluate_assurance_contract = lambda tenant_id, tenant_code, limit=100: {
        "status": "ok",
        "evaluation": {
            "contract_pass": False,
            "unmet_clauses": [{"clause": "min_overall_pass_rate"}],
        },
    }
    ar.get_assurance_policy_pack = lambda tenant_code: {
        "status": "ok",
        "policy_pack": {
            "auto_apply_actions": ["set_strategy_profile"],
            "force_approval_actions": [],
            "blocked_actions": [],
            "max_auto_apply_actions_per_run": 3,
            "notify_only": False,
            "rollback_on_worse_result": True,
            "min_effectiveness_delta": 0.0,
        },
    }

    result = ar.remediate_assurance_breach(tenant_id, tenant_code, auto_apply=True)
    assert result["status"] == "remediation_applied_or_planned"
    assert len(result["actions"]) == 1
    assert result["actions"][0]["status"] == "applied"


def test_approve_assurance_remediation_action() -> None:
    fake = FakeRedis()
    ar.redis_client = fake
    ar.send_telegram_message = lambda message: True
    ar.get_assurance_policy_pack = lambda tenant_code: {
        "status": "ok",
        "policy_pack": {
            "auto_apply_actions": [],
            "force_approval_actions": [],
            "blocked_actions": [],
            "max_auto_apply_actions_per_run": 0,
            "notify_only": False,
            "rollback_on_worse_result": True,
            "min_effectiveness_delta": 0.0,
        },
    }

    tenant_id = uuid4()
    tenant_code = "acb"
    ar.evaluate_assurance_contract = lambda tenant_id, tenant_code, limit=100: {
        "status": "ok",
        "evaluation": {
            "contract_pass": False,
            "unmet_clauses": [{"clause": "min_overall_pass_rate"}],
        },
    }

    planned = ar.remediate_assurance_breach(tenant_id, tenant_code, auto_apply=False)
    action_id = planned["actions"][0]["action_id"]
    approved = ar.approve_assurance_remediation_action(tenant_id, tenant_code, action_id, True)
    assert approved["status"] == "applied"


def test_effectiveness_and_rollback_guardrail() -> None:
    fake = FakeRedis()
    ar.redis_client = fake
    ar.send_telegram_message = lambda message: True

    tenant_id = uuid4()
    tenant_code = "acb"
    calls = {"n": 0}

    def _eval(tenant_id, tenant_code, limit=100):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "status": "ok",
                "evaluation": {
                    "contract_pass": False,
                    "overall_pass_rate": 0.6,
                    "unmet_clauses": [{"clause": "min_overall_pass_rate"}],
                },
            }
        return {
            "status": "ok",
            "evaluation": {
                "contract_pass": False,
                "overall_pass_rate": 0.4,
                "unmet_clauses": [{"clause": "min_overall_pass_rate"}],
            },
        }

    ar.evaluate_assurance_contract = _eval
    ar.get_assurance_policy_pack = lambda tenant_code: {
        "status": "ok",
        "policy_pack": {
            "auto_apply_actions": ["set_strategy_profile"],
            "force_approval_actions": [],
            "blocked_actions": [],
            "max_auto_apply_actions_per_run": 5,
            "notify_only": False,
            "rollback_on_worse_result": True,
            "min_effectiveness_delta": 0.0,
        },
    }

    result = ar.remediate_assurance_breach(tenant_id, tenant_code, auto_apply=False)
    assert result["status"] == "remediation_applied_or_planned"
    assert result["effectiveness"]["rollback_triggered"] == "1"

    score = ar.assurance_remediation_effectiveness(tenant_code, limit=20)
    assert score["count"] >= 1
    assert score["rollback_batches"] >= 1
