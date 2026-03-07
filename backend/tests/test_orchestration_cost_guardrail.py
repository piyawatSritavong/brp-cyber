from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_orchestration_cost_guardrail as cg


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.counter = 0

    def set(self, key: str, value: str) -> bool:
        self.values[key] = value
        return True

    def get(self, key: str):
        return self.values.get(key)

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self.counter += 1
        eid = f"{self.counter}-0"
        self.streams.setdefault(key, []).append((eid, fields))
        return eid

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]


class _Tenant:
    def __init__(self, tenant_id, tenant_code: str) -> None:
        self.id = tenant_id
        self.tenant_code = tenant_code


def test_orchestration_cost_guardrail_profile_and_evaluate() -> None:
    fake = FakeRedis()
    cg.redis_client = fake
    tenant_id = uuid4()

    orig_cost = cg.get_cost
    orig_usage = cg.get_usage
    orig_quota = cg.get_quota
    orig_set_quota = cg.set_quota
    orig_notify = cg.send_telegram_message
    try:
        meter = {"usd": 1.0, "tokens": 1000}
        cg.get_cost = lambda tenant_id: {"usd": meter["usd"], "tokens": meter["tokens"]}
        cg.get_usage = lambda tenant_id: {"tokens": meter["tokens"]}
        cg.get_quota = lambda tenant_id: {"events_per_month": 1000, "actions_per_day": 100, "tokens_per_month": 5000000}
        cg.set_quota = lambda tenant_id, events_per_month, actions_per_day, tokens_per_month: {
            "tokens_per_month": tokens_per_month
        }
        sent: list[str] = []
        cg.send_telegram_message = lambda message: sent.append(message) or True

        up = cg.upsert_orchestration_cost_guardrail_profile(
            tenant_id,
            {
                "monthly_cost_limit_usd": 50.0,
                "monthly_token_limit": 2_000_000,
                "hard_stop_on_limit": True,
                "force_fallback_on_pressure": True,
                "preemptive_throttle_on_anomaly": True,
                "anomaly_delta_threshold": 0.1,
                "anomaly_min_pressure_ratio": 0.2,
                "throttle_mode_on_anomaly": "conservative",
            },
        )
        assert up["status"] == "upserted"

        baseline = cg.evaluate_orchestration_cost_guardrail(tenant_id, "acb", apply_actions=True)
        assert baseline["state"]["anomaly"] is False

        meter["usd"] = 120.0
        meter["tokens"] = 2_500_000
        eval_res = cg.evaluate_orchestration_cost_guardrail(tenant_id, "acb", apply_actions=True)
        assert eval_res["status"] == "ok"
        assert eval_res["state"]["breached"] is True
        assert eval_res["state"]["anomaly"] is True
        assert len(eval_res["actions"]) >= 1
        assert eval_res["state"]["routing_override"] == "fallback_only"
        assert eval_res["state"]["throttle_override"] == "conservative"
        assert cg.get_orchestration_cost_throttle_override(tenant_id)["throttle_override"] == "conservative"

        meter["usd"] = 1.0
        meter["tokens"] = 1000
        cleared = cg.evaluate_orchestration_cost_guardrail(tenant_id, "acb", apply_actions=True)
        assert cleared["state"]["pressure"] is False
        assert cleared["state"]["routing_override"] == ""
        assert cleared["state"]["throttle_override"] == ""
        anomaly_state = cg.get_orchestration_cost_anomaly_state(tenant_id)
        assert anomaly_state["status"] in {"ok", "default"}
        assert len(sent) >= 1

        events = cg.orchestration_cost_guardrail_events(tenant_id, limit=20)
        assert events["count"] >= 1
    finally:
        cg.get_cost = orig_cost
        cg.get_usage = orig_usage
        cg.get_quota = orig_quota
        cg.set_quota = orig_set_quota
        cg.send_telegram_message = orig_notify


def test_orchestration_cost_guardrail_enterprise_snapshot() -> None:
    fake = FakeRedis()
    cg.redis_client = fake
    tenants = [_Tenant(uuid4(), "acb"), _Tenant(uuid4(), "xyz")]
    orig_list = cg._list_tenants
    orig_eval = cg.evaluate_orchestration_cost_guardrail
    try:
        cg._list_tenants = lambda db, limit: tenants[:limit]
        cg.evaluate_orchestration_cost_guardrail = lambda tenant_id, tenant_code, apply_actions=False: {
            "state": {"severity": "critical" if tenant_code == "acb" else "normal", "breached": tenant_code == "acb", "pressure": True},
            "metrics": {"monthly_cost_usd": 60.0 if tenant_code == "acb" else 10.0, "monthly_tokens": 1000, "pressure_ratio": 1.2 if tenant_code == "acb" else 0.2},
        }
        snap = cg.orchestration_cost_guardrail_enterprise_snapshot(db=None, limit=20, apply_actions=False)
        assert snap["count"] == 2
        assert snap["breached_count"] == 1
    finally:
        cg._list_tenants = orig_list
        cg.evaluate_orchestration_cost_guardrail = orig_eval
