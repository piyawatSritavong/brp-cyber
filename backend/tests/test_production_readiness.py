from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_production_readiness as pr


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
    def __init__(self, tenant_id, tenant_code: str, status: str = "staging") -> None:
        self.id = tenant_id
        self.tenant_code = tenant_code
        self.status = status


class _Db:
    def commit(self) -> None:
        return None

    def refresh(self, tenant: object) -> None:
        return None


def test_prod_v1_readiness_and_closure() -> None:
    fake = FakeRedis()
    pr.redis_client = fake
    tenant = _Tenant(uuid4(), "acb", status="staging")

    orig_find = pr._find_tenant
    orig_gate = pr.evaluate_and_persist_objective_gate
    orig_cost = pr.evaluate_orchestration_cost_guardrail
    try:
        pr._find_tenant = lambda db, tenant_code: tenant if tenant_code == "acb" else None
        pr.evaluate_and_persist_objective_gate = lambda tenant_id, max_monthly_cost_usd=50.0: {
            "overall_pass": True,
            "gates": {"red": {"pass": True}, "blue": {"pass": True}},
        }
        pr.evaluate_orchestration_cost_guardrail = lambda tenant_id, tenant_code, apply_actions=False: {
            "state": {"breached": False, "anomaly": False},
            "metrics": {"pressure_ratio": 0.4},
        }

        runbook_up = pr.upsert_prod_v1_go_live_runbook(
            "acb",
            {
                "owner": "ops",
                "change_ticket": "CHG-60",
                "items": {
                    "dr_smoke_passed": True,
                    "security_signoff": True,
                    "legal_signoff": True,
                    "rollback_validated": True,
                    "oncall_ready": True,
                    "observability_ready": True,
                    "incident_playbook_ready": True,
                    "change_ticket_linked": True,
                },
            },
        )
        assert runbook_up["status"] == "upserted"

        readiness = pr.evaluate_prod_v1_readiness_final(_Db(), "acb")
        assert readiness["status"] == "ok"
        assert readiness["production_v1_ready"] is True

        dry = pr.close_prod_v1_go_live(
            _Db(),
            "acb",
            approved_by="ciso-ai",
            change_ticket="CHG-60",
            dry_run=True,
            promote_on_pass=True,
        )
        assert dry["status"] == "ready"
        assert tenant.status == "staging"

        closed = pr.close_prod_v1_go_live(
            _Db(),
            "acb",
            approved_by="ciso-ai",
            change_ticket="CHG-60",
            dry_run=False,
            promote_on_pass=True,
        )
        assert closed["status"] == "closed"
        assert tenant.status == "production"

        history = pr.prod_v1_go_live_closure_history(tenant_code="acb", limit=20)
        assert history["count"] >= 2
    finally:
        pr._find_tenant = orig_find
        pr.evaluate_and_persist_objective_gate = orig_gate
        pr.evaluate_orchestration_cost_guardrail = orig_cost


def test_prod_v1_readiness_blocked_when_runbook_incomplete() -> None:
    fake = FakeRedis()
    pr.redis_client = fake
    tenant = _Tenant(uuid4(), "acb", status="staging")

    orig_find = pr._find_tenant
    orig_gate = pr.evaluate_and_persist_objective_gate
    orig_cost = pr.evaluate_orchestration_cost_guardrail
    try:
        pr._find_tenant = lambda db, tenant_code: tenant
        pr.evaluate_and_persist_objective_gate = lambda tenant_id, max_monthly_cost_usd=50.0: {"overall_pass": True, "gates": {}}
        pr.evaluate_orchestration_cost_guardrail = lambda tenant_id, tenant_code, apply_actions=False: {
            "state": {"breached": False, "anomaly": False},
            "metrics": {},
        }

        readiness = pr.evaluate_prod_v1_readiness_final(_Db(), "acb")
        assert readiness["production_v1_ready"] is False
        assert len(readiness["blockers"]) >= 1
        assert readiness["blockers"][0]["type"] == "runbook"
    finally:
        pr._find_tenant = orig_find
        pr.evaluate_and_persist_objective_gate = orig_gate
        pr.evaluate_orchestration_cost_guardrail = orig_cost


def test_prod_v1_burn_rate_guard_auto_rollback_and_cooldown() -> None:
    fake = FakeRedis()
    pr.redis_client = fake
    tenant = _Tenant(uuid4(), "acb", status="production")

    orig_find = pr._find_tenant
    orig_slo = pr.get_slo_snapshot
    orig_notify = pr.send_telegram_message
    try:
        pr._find_tenant = lambda db, tenant_code: tenant
        pr.get_slo_snapshot = lambda tenant_id: {
            "requests_total": 1000,
            "requests_failed": 80,
            "availability": 0.92,
        }
        pr.send_telegram_message = lambda message: True

        profile = pr.upsert_prod_v1_burn_rate_profile(
            "acb",
            {
                "error_budget_fraction_per_day": 0.01,
                "burn_rate_warn_threshold": 1.0,
                "burn_rate_rollback_threshold": 2.0,
                "auto_rollback_on_breach": True,
                "rollback_target_status": "staging",
                "cooldown_minutes": 60,
            },
        )
        assert profile["status"] == "upserted"

        applied = pr.evaluate_prod_v1_burn_rate_guard(_Db(), "acb", apply=True)
        assert applied["status"] == "ok"
        assert applied["decision"]["should_rollback"] is True
        assert applied["action"]["executed"] is True
        assert tenant.status == "staging"

        # move back to production then validate cooldown blocks repeated rollback
        tenant.status = "production"
        blocked = pr.evaluate_prod_v1_burn_rate_guard(_Db(), "acb", apply=True)
        assert blocked["status"] == "ok"
        assert blocked["decision"]["should_rollback"] is True
        assert blocked["action"]["executed"] is False
        assert blocked["action"]["reason"] == "cooldown_active"

        history = pr.prod_v1_burn_rate_guard_history(tenant_code="acb", limit=20)
        assert history["count"] >= 2
    finally:
        pr._find_tenant = orig_find
        pr.get_slo_snapshot = orig_slo
        pr.send_telegram_message = orig_notify
