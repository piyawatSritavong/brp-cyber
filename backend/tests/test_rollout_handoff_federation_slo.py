from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_rollout_handoff_federation as federation


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self._counter = 0

    def set(self, key: str, value: str) -> bool:
        self.values[key] = value
        return True

    def get(self, key: str):
        return self.values.get(key)

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self._counter += 1
        event_id = f"{self._counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]


class _Tenant:
    def __init__(self, tenant_id, tenant_code: str) -> None:
        self.id = tenant_id
        self.tenant_code = tenant_code


class _Query:
    def __init__(self, tenant):
        self._tenant = tenant

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._tenant


class _DB:
    def __init__(self, tenant):
        self.tenant = tenant

    def query(self, _model):
        return _Query(self.tenant)


def test_rollout_handoff_federation_slo_profile_roundtrip() -> None:
    fake = FakeRedis()
    federation.redis_client = fake

    upserted = federation.upsert_rollout_handoff_federation_slo_profile(
        "acb",
        {"max_federated_risk_score": 40, "notify_on_breach": False},
    )
    assert upserted["status"] == "upserted"

    loaded = federation.get_rollout_handoff_federation_slo_profile("acb")
    assert loaded["status"] in {"ok", "default"}
    assert loaded["profile"]["max_federated_risk_score"] == 40
    assert loaded["profile"]["notify_on_breach"] is False


def test_rollout_handoff_federation_slo_evaluate_and_breach_history() -> None:
    fake = FakeRedis()
    federation.redis_client = fake
    tenant = _Tenant(uuid4(), "acb")
    db = _DB(tenant)
    orig_heatmap = federation.rollout_handoff_federation_heatmap
    orig_get_policy = federation.get_rollout_handoff_policy
    orig_upsert_policy = federation.upsert_rollout_handoff_policy
    orig_notify = federation.send_telegram_message
    try:
        federation.rollout_handoff_federation_heatmap = lambda db, limit=200: {
            "rows": [
                {
                    "tenant_id": str(tenant.id),
                    "tenant_code": "acb",
                    "federated_risk_score": 92,
                    "risk_tier": "critical",
                    "blocked_count": 3,
                    "containment_event_count": 9,
                }
            ]
        }
        federation.get_rollout_handoff_policy = lambda tenant_id: {"policy": {}}
        federation.upsert_rollout_handoff_policy = lambda tenant_id, **kwargs: {"policy": kwargs}
        federation.send_telegram_message = lambda message: True

        _ = federation.upsert_rollout_handoff_federation_slo_profile(
            "acb",
            {
                "max_federated_risk_score": 50,
                "max_allowed_risk_tier": "medium",
                "max_blocked_count": 1,
                "max_containment_events": 5,
                "auto_escalate_on_breach": True,
                "notify_on_breach": True,
                "min_escalation_tier": "high",
            },
        )

        result = federation.evaluate_rollout_handoff_federation_slo(db, tenant_code="acb", limit=20, dry_run_escalation=False)
        assert result["status"] == "ok"
        assert result["breach"] is True
        assert len(result["breaches"]) >= 1
        assert result["escalation"]["status"] in {"applied", "dry_run", "skipped_tier"}

        history = federation.rollout_handoff_federation_slo_breach_history("acb", limit=20)
        assert history["count"] >= 1
    finally:
        federation.rollout_handoff_federation_heatmap = orig_heatmap
        federation.get_rollout_handoff_policy = orig_get_policy
        federation.upsert_rollout_handoff_policy = orig_upsert_policy
        federation.send_telegram_message = orig_notify


def test_rollout_handoff_federation_executive_digest() -> None:
    fake = FakeRedis()
    federation.redis_client = fake
    tenants = [_Tenant(uuid4(), "acb"), _Tenant(uuid4(), "xyz")]
    orig_list = federation._list_tenants
    orig_heatmap = federation.rollout_handoff_federation_heatmap
    try:
        federation._list_tenants = lambda db, limit: tenants[:limit]
        federation.rollout_handoff_federation_heatmap = lambda db, limit=200: {
            "rows": [
                {"tenant_code": "acb", "risk_tier": "high", "federated_risk_score": 66},
                {"tenant_code": "xyz", "risk_tier": "low", "federated_risk_score": 10},
            ]
        }

        _ = federation.upsert_rollout_handoff_federation_slo_profile("acb", {"max_breaches_per_day": 2})
        _ = federation.upsert_rollout_handoff_federation_slo_profile("xyz", {"max_breaches_per_day": 2})
        fake.set(federation._slo_budget_key("acb"), "2")
        fake.set(federation._slo_budget_key("xyz"), "0")

        digest = federation.rollout_handoff_federation_executive_digest(db=None, limit=20)
        assert digest["count"] == 2
        assert digest["breach_budget_exhausted_count"] == 1
    finally:
        federation._list_tenants = orig_list
        federation.rollout_handoff_federation_heatmap = orig_heatmap
