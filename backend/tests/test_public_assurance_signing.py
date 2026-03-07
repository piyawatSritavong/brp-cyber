from __future__ import annotations

from app.services import control_plane_public_assurance_signing as ps


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.strings: dict[str, str] = {}
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


def test_signed_public_assurance_snapshot_and_verify() -> None:
    fake = FakeRedis()
    ps.redis_client = fake

    orig_summary = ps.public_assurance_summary
    orig_objectives = ps.orchestration_objectives_status
    orig_sign = ps._sign_message
    orig_verify = ps._verify_signature
    try:
        ps.public_assurance_summary = lambda: {"status": "ok", "latest": {"x": 1}}
        ps.orchestration_objectives_status = lambda limit=1000: {"enterprise_readiness": {"ready": True}}
        ps._sign_message = lambda message: {
            "signature": f"sig:{message}",
            "signer_provider": "hmac",
            "signing_algorithm": "HMAC_SHA256",
            "signature_encoding": "hex",
            "key_ref": "local_hmac",
        }
        ps._verify_signature = lambda **kwargs: kwargs.get("signature", "").startswith("sig:")

        result = ps.create_signed_public_assurance_snapshot(destination_dir="./tmp/compliance/test_public_assurance", limit=10)
        assert result["status"] == "signed"

        status = ps.signed_public_assurance_status(limit=10)
        assert status["count"] == 1
        assert status["rows"][0]["enterprise_ready"] is True

        verify_chain = ps.verify_signed_public_assurance_chain(limit=10)
        assert verify_chain["valid"] is True
    finally:
        ps.public_assurance_summary = orig_summary
        ps.orchestration_objectives_status = orig_objectives
        ps._sign_message = orig_sign
        ps._verify_signature = orig_verify


def test_verify_signed_public_assurance_bundle_message_mismatch() -> None:
    result = ps.verify_signed_public_assurance_bundle(
        {
            "message": "bad",
            "message_fields": {
                "generated_at": "2026-01-01T00:00:00+00:00",
                "payload_hash": "abc",
                "prev_signature": "",
                "limit": 1,
            },
            "signature": {"value": "x", "provider": "hmac", "encoding": "hex", "algorithm": "HMAC_SHA256", "key_ref": "local_hmac"},
        }
    )
    assert result["valid"] is False
    assert result["reason"] == "message_mismatch"
