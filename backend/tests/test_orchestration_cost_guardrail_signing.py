from __future__ import annotations

from app.services import control_plane_orchestration_cost_guardrail_signing as sig


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


def test_signed_orchestration_cost_guardrail_report_chain() -> None:
    fake = FakeRedis()
    sig.redis_client = fake
    sig.orchestration_cost_guardrail_enterprise_snapshot = lambda db, limit=200, apply_actions=False: {
        "count": 1,
        "rows": [{"tenant_code": "acb"}],
    }
    sig._sign_message = lambda message: {
        "signature": f"sig:{message}",
        "signer_provider": "hmac",
        "signing_algorithm": "HMAC_SHA256",
        "signature_encoding": "hex",
        "key_ref": "local_hmac",
    }
    sig._verify_signature = lambda **kwargs: str(kwargs.get("signature", "")).startswith("sig:")

    created = sig.create_signed_orchestration_cost_guardrail_report(
        db=None,
        destination_dir="./tmp/compliance/test_orchestration_cost_guardrail",
        limit=10,
    )
    assert created["status"] == "signed"

    status = sig.signed_orchestration_cost_guardrail_report_status(limit=10)
    assert status["count"] == 1

    verify = sig.verify_signed_orchestration_cost_guardrail_report_chain(limit=10)
    assert verify["valid"] is True

    bundle = sig.public_orchestration_cost_guardrail_report_bundle(limit=10)
    assert bundle["scope"] == "orchestration_cost_guardrail_report"
    assert bundle["verify"]["valid"] is True

    bundle_verify = sig.verify_signed_orchestration_cost_guardrail_report_bundle(bundle)
    assert bundle_verify["valid"] is True
