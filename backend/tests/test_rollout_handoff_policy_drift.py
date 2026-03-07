from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_rollout_handoff_policy_drift as drift


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


def test_rollout_handoff_policy_drift_baseline_and_evaluate() -> None:
    fake = FakeRedis()
    drift.redis_client = fake

    tenant_id = uuid4()
    orig_get_policy = drift.get_rollout_handoff_policy
    orig_notify = drift.send_telegram_message
    try:
        baseline = drift.upsert_rollout_handoff_policy_drift_baseline(
            {
                "baseline_policy": {"risk_threshold_block": 70, "containment_action_critical": "revoke_token"},
                "notify_on_high_critical": True,
            }
        )
        assert baseline["status"] == "upserted"

        loaded = drift.get_rollout_handoff_policy_drift_baseline()
        assert loaded["status"] in {"ok", "default"}
        assert loaded["baseline"]["baseline_policy"]["risk_threshold_block"] == 70

        drift.get_rollout_handoff_policy = lambda tenant_id: {
            "policy": {"risk_threshold_block": 90, "containment_action_critical": "log_only"}
        }
        sent: list[str] = []
        drift.send_telegram_message = lambda message: sent.append(message) or True

        result = drift.evaluate_rollout_handoff_policy_drift(tenant_id, "acb", notify=True)
        assert result["status"] == "ok"
        assert result["drift_detected"] is True
        assert result["mismatch_count"] >= 1
        assert result["drift_severity"] in {"high", "critical"}
        assert len(sent) >= 1
    finally:
        drift.get_rollout_handoff_policy = orig_get_policy
        drift.send_telegram_message = orig_notify


def test_rollout_handoff_policy_drift_heatmap_and_reconcile() -> None:
    fake = FakeRedis()
    drift.redis_client = fake
    tenants = [_Tenant(uuid4(), "acb"), _Tenant(uuid4(), "xyz")]
    orig_list = drift._list_tenants
    orig_get_policy = drift.get_rollout_handoff_policy
    orig_upsert_policy = drift.upsert_rollout_handoff_policy
    try:
        drift._list_tenants = lambda db, limit: tenants[:limit]
        _ = drift.upsert_rollout_handoff_policy_drift_baseline(
            {"baseline_policy": {"risk_threshold_block": 70, "containment_action_critical": "revoke_token"}}
        )

        def _policy(tenant_id):
            if str(tenant_id) == str(tenants[0].id):
                return {"policy": {"risk_threshold_block": 95, "containment_action_critical": "log_only"}}
            return {"policy": {"risk_threshold_block": 70, "containment_action_critical": "revoke_token"}}

        drift.get_rollout_handoff_policy = _policy
        heat = drift.rollout_handoff_policy_drift_heatmap(db=None, limit=20, notify=False)
        assert heat["count"] == 2
        assert heat["drifted_count"] >= 1

        dry = drift.apply_rollout_handoff_policy_drift_reconciliation(
            db=None, limit=20, min_severity="low", dry_run=True
        )
        assert dry["count"] >= 1
        assert dry["rows"][0]["status"] == "dry_run"

        drift.upsert_rollout_handoff_policy = lambda **kwargs: {"policy": kwargs}
        applied = drift.apply_rollout_handoff_policy_drift_reconciliation(
            db=None, limit=20, min_severity="low", dry_run=False
        )
        assert applied["count"] >= 1
        assert applied["rows"][0]["status"] == "applied"
    finally:
        drift._list_tenants = orig_list
        drift.get_rollout_handoff_policy = orig_get_policy
        drift.upsert_rollout_handoff_policy = orig_upsert_policy
