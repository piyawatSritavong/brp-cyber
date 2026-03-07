from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_compliance_package_index as cp


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.counter = 0

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self.counter += 1
        eid = f"{self.counter}-0"
        self.streams.setdefault(key, []).append((eid, fields))
        return eid

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]


def test_export_and_status_package_index() -> None:
    fake = FakeRedis()
    cp.redis_client = fake
    cp.evaluate_assurance_contract = lambda tenant_id, tenant_code, limit=100: {"status": "ok", "evaluation": {}}
    cp.signed_tenant_risk_bulletin_status = lambda tenant_code, limit=1: {"rows": [{"id": "b-1"}]}
    cp.signed_delivery_proof_status = lambda tenant_code, limit=1: {"rows": [{"id": "p-1"}]}
    cp.assurance_slo_breach_history = lambda tenant_code, limit=100: {"rows": [{"id": "s-1"}]}
    cp.tenant_verifier_kit_status = lambda tenant_code, limit=1: {"rows": [{"id": "k-1"}]}

    result = cp.export_tenant_compliance_package_index(
        tenant_id=uuid4(),
        tenant_code="acb",
        destination_dir="./tmp/compliance/test_evidence_package",
        limit=10,
    )
    assert result["status"] == "exported"

    status = cp.tenant_compliance_package_index_status("acb", limit=10)
    assert status["count"] == 1
