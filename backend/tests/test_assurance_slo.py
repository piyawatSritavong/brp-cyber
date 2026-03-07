from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_assurance_slo as slo


class FakeRedis:
    def __init__(self) -> None:
        self.strings: dict[str, str] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.counter = 0

    def set(self, key: str, value: str) -> bool:
        self.strings[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

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


class _Query:
    def __init__(self, rows):
        self._rows = rows

    def limit(self, n):
        return self

    def all(self):
        return self._rows


class _DB:
    def __init__(self, rows):
        self._rows = rows

    def query(self, model):
        return _Query(self._rows)


def test_assurance_slo_profile_and_evaluate() -> None:
    fake = FakeRedis()
    slo.redis_client = fake

    tenant_id = uuid4()
    tenant_code = "acb"

    upsert = slo.upsert_assurance_slo_profile(tenant_code, {"max_breaches_per_day": 3})
    assert upsert["status"] == "upserted"

    slo.evaluate_assurance_contract = lambda tenant_id, tenant_code, limit=200: {
        "status": "ok",
        "evaluation": {"overall_pass_rate": 0.5},
    }
    slo.assurance_remediation_effectiveness = lambda tenant_code, limit=200: {
        "average_effectiveness_delta": -0.1,
        "rollback_batches": 2,
    }
    slo.get_slo_snapshot = lambda tenant_id: {"availability": 0.9, "requests_total": 100, "requests_failed": 20}

    result = slo.evaluate_assurance_slo(tenant_id, tenant_code, limit=20)
    assert result["status"] == "ok"
    assert result["breach"] is True
    assert result["breach_budget"]["consumed"] >= 1

    history = slo.assurance_slo_breach_history(tenant_code, limit=10)
    assert history["count"] >= 1


def test_assurance_executive_risk_digest() -> None:
    rows = [_Tenant(uuid4(), "acb"), _Tenant(uuid4(), "xyz")]
    db = _DB(rows)

    slo.assurance_risk_heatmap = lambda db, limit=200: {
        "rows": [
            {"tenant_code": "acb", "risk_tier": "critical", "risk_score": 90},
            {"tenant_code": "xyz", "risk_tier": "low", "risk_score": 10},
        ]
    }
    slo.evaluate_assurance_slo = lambda tenant_id, tenant_code, limit=200: {
        "breach": tenant_code == "acb",
        "breach_budget": {"remaining": 0 if tenant_code == "acb" else 3, "exhausted": tenant_code == "acb"},
    }

    digest = slo.assurance_executive_risk_digest(db, limit=20)
    assert digest["count"] == 2
    assert digest["breach_budget_exhausted_count"] == 1
