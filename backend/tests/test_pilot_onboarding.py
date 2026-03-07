from __future__ import annotations

from uuid import uuid4

from app.services import orchestrator_pilot_onboarding as ob


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(key, {}).update(mapping)
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))


def test_pilot_onboarding_profile_and_checklist() -> None:
    fake = FakeRedis()
    ob.redis_client = fake
    ob.evaluate_and_persist_objective_gate = lambda tenant_id: {
        "overall_pass": True,
        "gates": {"red": {"pass": True}, "blue": {"pass": True}},
    }

    tenant_id = uuid4()
    upserted = ob.upsert_pilot_onboarding_profile(
        tenant_id=tenant_id,
        tenant_code="acb",
        target_asset="acb.example.com/admin-login",
        strategy_profile="balanced",
    )
    assert upserted["status"] == "ok"

    checklist = ob.pilot_onboarding_checklist(tenant_id)
    assert checklist["ready"] is True
    assert all(item["pass"] for item in checklist["checks"])
