from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_orchestration_failover as fo


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.counter = 0

    def set(self, key: str, value: str) -> bool:
        self.values[key] = value
        return True

    def get(self, key: str):
        return self.values.get(key)

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(key, {}).update(mapping)
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))

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


def test_orchestration_failover_profile_health_and_drill() -> None:
    fake = FakeRedis()
    fo.redis_client = fake
    tenant_id = uuid4()
    sent: list[str] = []

    orig_activate = fo.get_tenant_activation_state
    orig_incidents = fo.pilot_incidents
    orig_notify = fo.send_telegram_message
    try:
        fo.get_tenant_activation_state = lambda tenant_id: {"status": "active", "consecutive_failures": 2}
        fo.pilot_incidents = lambda tenant_id, limit=30: {
            "count": 3,
            "rows": [{"severity": "high"}, {"severity": "critical"}, {"severity": "low"}],
        }
        fo.send_telegram_message = lambda message: sent.append(message) or True

        up = fo.upsert_orchestration_failover_profile(
            tenant_id,
            {
                "auto_failover_enabled": True,
                "health_score_failover_threshold": 70,
                "max_high_incidents_before_failover": 2,
            },
        )
        assert up["status"] == "upserted"

        eval_res = fo.evaluate_orchestration_failover_health(
            tenant_id,
            "acb",
            allow_auto_failover=True,
        )
        assert eval_res["status"] == "ok"
        assert eval_res["failover_recommended"] is True
        assert eval_res["auto_failover_executed"] is True

        drill = fo.trigger_orchestration_failover_drill(tenant_id, "acb", reason="manual", dry_run=True)
        assert drill["status"] == "dry_run"

        events = fo.orchestration_failover_events(tenant_id, limit=20)
        assert events["count"] >= 1
        assert len(sent) >= 1
    finally:
        fo.get_tenant_activation_state = orig_activate
        fo.pilot_incidents = orig_incidents
        fo.send_telegram_message = orig_notify


def test_orchestration_failover_enterprise_snapshot() -> None:
    fake = FakeRedis()
    fo.redis_client = fake
    tenants = [_Tenant(uuid4(), "acb"), _Tenant(uuid4(), "xyz")]
    orig_list = fo._list_tenants
    orig_eval = fo.evaluate_orchestration_failover_health
    try:
        fo._list_tenants = lambda db, limit: tenants[:limit]
        fo.evaluate_orchestration_failover_health = lambda tenant_id, tenant_code, allow_auto_failover=False: {
            "health": {"health_score": 55 if tenant_code == "acb" else 90, "high_incidents": 2 if tenant_code == "acb" else 0},
            "failover_recommended": tenant_code == "acb",
        }
        snap = fo.orchestration_failover_enterprise_snapshot(db=None, limit=20)
        assert snap["count"] == 2
        assert snap["failover_candidates"] == 1
    finally:
        fo._list_tenants = orig_list
        fo.evaluate_orchestration_failover_health = orig_eval
