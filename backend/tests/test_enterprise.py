from __future__ import annotations

from uuid import uuid4

from app.core.config import settings
from app.services import control_plane_orchestration_cost_guardrail as cost_guardrail
from app.services.enterprise import cost_meter, model_router, quotas, slo


class FakeRedis:
    def __init__(self) -> None:
        self.strings: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self._counter = 0

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.strings[key] = value
        return True

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(key, {}).update(mapping)
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

    def hincrby(self, key: str, field: str, amount: int) -> int:
        bucket = self.hashes.setdefault(key, {})
        current = int(bucket.get(field, "0"))
        updated = current + amount
        bucket[field] = str(updated)
        return updated

    def hincrbyfloat(self, key: str, field: str, amount: float) -> float:
        bucket = self.hashes.setdefault(key, {})
        current = float(bucket.get(field, "0"))
        updated = current + amount
        bucket[field] = str(updated)
        return updated

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self._counter += 1
        event_id = f"{self._counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id


def test_quota_router_cost_and_slo() -> None:
    fake = FakeRedis()
    quotas.redis_client = fake
    cost_meter.redis_client = fake
    slo.redis_client = fake
    cost_guardrail.redis_client = fake
    orig_notify = cost_guardrail.send_telegram_message
    cost_guardrail.send_telegram_message = lambda message: True

    tenant_id = uuid4()

    try:
        default_quota = quotas.get_quota(tenant_id)
        assert default_quota["events_per_month"] == settings.tenant_default_events_per_month

        updated_quota = quotas.set_quota(tenant_id, 100, 20, 5000)
        assert updated_quota["tokens_per_month"] == 5000

        state = quotas.check_quota(tenant_id, events=10, actions=1, tokens=200)
        assert state["allowed"] is True

        usage = quotas.add_usage(tenant_id, events=10, actions=1, tokens=2000)
        assert usage["events"] == 10

        decision = model_router.route_model(tenant_id, task_type="purple_report", complexity="high", estimated_tokens=500)
        assert decision.selected_model == settings.model_reasoning

        cost_guardrail.upsert_orchestration_cost_guardrail_profile(
            tenant_id,
            {"monthly_cost_limit_usd": 1.0, "monthly_token_limit": 1000, "force_fallback_on_pressure": True},
        )
        cost_guardrail.evaluate_orchestration_cost_guardrail(tenant_id, "acb", apply_actions=True)
        fallback_decision = model_router.route_model(tenant_id, task_type="purple_report", complexity="high", estimated_tokens=500)
        assert fallback_decision.selected_model == settings.model_fallback_when_over_quota
        assert fallback_decision.reason == "cost_guardrail_fallback_override"

        cost = cost_meter.record_cost(tenant_id, tokens=500, model_name=decision.selected_model)
        assert cost["usd"] > 0

        slo.record_http_result(tenant_id, duration_seconds=0.12, success=True)
        slo.record_http_result(tenant_id, duration_seconds=0.20, success=False)
        snapshot = slo.get_slo_snapshot(tenant_id)
        assert snapshot["requests_total"] == 2.0
        assert snapshot["requests_failed"] == 1.0
    finally:
        cost_guardrail.send_telegram_message = orig_notify
