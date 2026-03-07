from __future__ import annotations

from uuid import uuid4

from app.services import control_plane_assurance_evidence_package_signing as ep


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
        event_id = f"{self.counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]

    def xrange(self, key: str, min: str = "-", max: str = "+", count: int = 100):
        return list(self.streams.get(key, []))[:count]


def test_signed_tenant_evidence_package_chain() -> None:
    fake = FakeRedis()
    ep.redis_client = fake
    ep.export_tenant_compliance_package_index = lambda tenant_id, tenant_code, destination_dir="", limit=100: {
        "status": "exported",
        "index_id": "idx-1",
        "path": "./tmp/compliance/test_evidence.json",
        "package": {"tenant_code": tenant_code, "generated_at": "2026-01-01T00:00:00+00:00"},
    }
    ep._sign_message = lambda message: {
        "signature": f"sig:{message}",
        "signer_provider": "hmac",
        "signing_algorithm": "HMAC_SHA256",
        "signature_encoding": "hex",
        "key_ref": "local_hmac",
    }
    ep._verify_signature = lambda **kwargs: str(kwargs.get("signature", "")).startswith("sig:")

    signed = ep.create_signed_tenant_evidence_package(
        tenant_id=uuid4(),
        tenant_code="acb",
        destination_dir="./tmp/compliance/test_signed_evidence_package",
        limit=10,
    )
    assert signed["status"] == "signed"

    status = ep.signed_tenant_evidence_package_status("acb", limit=10)
    assert status["count"] == 1

    verify = ep.verify_signed_tenant_evidence_package_chain("acb", limit=10)
    assert verify["valid"] is True
