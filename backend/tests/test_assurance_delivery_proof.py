from __future__ import annotations

from app.services import control_plane_assurance_delivery_proof as dp


class FakeRedis:
    def __init__(self) -> None:
        self.strings: dict[str, str] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.counter = 0

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

    def set(self, key: str, value: str) -> bool:
        self.strings[key] = value
        return True

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self.counter += 1
        eid = f"{self.counter}-0"
        self.streams.setdefault(key, []).append((eid, fields))
        return eid

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]

    def xrange(self, key: str, min: str = "-", max: str = "+", count: int = 100):
        return list(self.streams.get(key, []))[:count]


def test_export_and_verify_delivery_proof() -> None:
    fake = FakeRedis()
    dp.redis_client = fake

    dp.bulletin_delivery_receipts = lambda tenant_code, limit=100: {
        "tenant_code": tenant_code,
        "rows": [{"id": "1-0", "status": "delivered", "timestamp": "2026-01-01T00:00:00+00:00"}],
    }
    dp.signed_tenant_risk_bulletin_status = lambda tenant_code, limit=1: {
        "tenant_code": tenant_code,
        "rows": [{"id": "1-0", "signature": "sig", "scope": "assurance_tenant_bulletin:acb"}],
    }
    dp.verify_signed_tenant_risk_bulletin_chain = lambda tenant_code, limit=100: {"valid": True, "checked": 1}
    dp._sign_message = lambda message: {
        "signature": f"sig:{message}",
        "signer_provider": "hmac",
        "signing_algorithm": "HMAC_SHA256",
        "signature_encoding": "hex",
        "key_ref": "local_hmac",
    }
    dp._verify_signature = lambda **kwargs: str(kwargs.get("signature", "")).startswith("sig:")

    result = dp.export_signed_delivery_proof_bundle("acb", destination_dir="./tmp/compliance/test_delivery_proof", limit=10)
    assert result["status"] == "exported"

    status = dp.signed_delivery_proof_status("acb", limit=10)
    assert status["count"] == 1

    verify = dp.verify_signed_delivery_proof_chain("acb", limit=10)
    assert verify["valid"] is True
