from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_assurance_digest_signing as ds


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


def test_signed_assurance_executive_digest_chain() -> None:
    fake = FakeRedis()
    ds.redis_client = fake
    ds.assurance_executive_risk_digest = lambda db, limit=200: {"count": 1, "rows": [{"tenant_code": "acb"}]}
    ds._sign_message = lambda message: {
        "signature": f"sig:{message}",
        "signer_provider": "hmac",
        "signing_algorithm": "HMAC_SHA256",
        "signature_encoding": "hex",
        "key_ref": "local_hmac",
    }
    ds._verify_signature = lambda **kwargs: str(kwargs.get("signature", "")).startswith("sig:")

    signed = ds.create_signed_assurance_executive_digest(db=None, destination_dir="./tmp/compliance/test_exec_digest", limit=10)
    assert signed["status"] == "signed"

    status = ds.signed_assurance_executive_digest_status(limit=10)
    assert status["count"] == 1

    verify = ds.verify_signed_assurance_executive_digest_chain(limit=10)
    assert verify["valid"] is True


def test_signed_tenant_bulletin_chain() -> None:
    fake = FakeRedis()
    ds.redis_client = fake
    ds.evaluate_assurance_slo = lambda tenant_id, tenant_code, limit=200: {"status": "ok", "breach": False}
    ds.evaluate_assurance_contract = lambda tenant_id, tenant_code, limit=200: {"status": "ok"}
    ds.assurance_remediation_effectiveness = lambda tenant_code, limit=200: {"count": 0}
    ds._sign_message = lambda message: {
        "signature": f"sig:{message}",
        "signer_provider": "hmac",
        "signing_algorithm": "HMAC_SHA256",
        "signature_encoding": "hex",
        "key_ref": "local_hmac",
    }
    ds._verify_signature = lambda **kwargs: str(kwargs.get("signature", "")).startswith("sig:")

    signed = ds.create_signed_tenant_risk_bulletin(
        tenant_id=uuid4(),
        tenant_code="acb",
        destination_dir="./tmp/compliance/test_tenant_bulletin",
        limit=10,
    )
    assert signed["status"] == "signed"

    status = ds.signed_tenant_risk_bulletin_status("acb", limit=10)
    assert status["count"] == 1

    verify = ds.verify_signed_tenant_risk_bulletin_chain("acb", limit=10)
    assert verify["valid"] is True
