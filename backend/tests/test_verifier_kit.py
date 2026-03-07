from __future__ import annotations

from app.services import control_plane_verifier_kit as vk


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


def test_export_tenant_verifier_kit_and_status() -> None:
    fake = FakeRedis()
    vk.redis_client = fake
    vk.signed_tenant_risk_bulletin_status = lambda tenant_code, limit=1: {"rows": [{"id": "b-1"}]}
    vk.signed_delivery_proof_status = lambda tenant_code, limit=1: {"rows": [{"id": "p-1"}]}
    vk.verify_signed_tenant_risk_bulletin_chain = lambda tenant_code, limit=100: {"valid": True}
    vk.verify_signed_delivery_proof_chain = lambda tenant_code, limit=100: {"valid": True}

    result = vk.export_tenant_verifier_kit("acb", destination_dir="./tmp/compliance/test_verifier_kit", limit=10)
    assert result["status"] == "exported"

    status = vk.tenant_verifier_kit_status("acb", limit=10)
    assert status["count"] == 1
    assert status["rows"][0]["bulletin_chain_valid"] is True
