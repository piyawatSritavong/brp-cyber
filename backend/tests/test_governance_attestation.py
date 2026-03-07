from __future__ import annotations

from app.services import control_plane_governance_attestation as att


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

    def xrange(self, key: str, min: str = "-", max: str = "+", count: int = 1000):
        return list(self.streams.get(key, []))[:count]


def _setup_hmac_mode(fake: FakeRedis) -> None:
    att.redis_client = fake
    att.governance_dashboard = lambda limit=1000: {
        "policy": {"mode": "enforce"},
        "summary": {"events_analyzed": 10, "policy_warnings": 1, "policy_denies": 0, "override_actions": 0, "production_promotions": 1},
    }


def test_create_and_verify_governance_attestation_chain_hmac() -> None:
    fake = FakeRedis()
    _setup_hmac_mode(fake)

    created = att.create_governance_attestation(limit=100)
    assert created["status"] == "success"
    assert created["signer_provider"] == "hmac"

    status = att.governance_attestation_status(limit=10)
    assert status["count"] == 1

    verify = att.verify_governance_attestation_chain(limit=100)
    assert verify["valid"] is True


def test_export_and_verify_detached_bundle_hmac() -> None:
    fake = FakeRedis()
    _setup_hmac_mode(fake)

    att.create_governance_attestation(limit=200)
    exported = att.export_latest_governance_attestation(destination_dir="./tmp/compliance/test_exports")
    assert exported["status"] == "exported"

    bundle = exported["bundle"]
    verified = att.verify_detached_attestation_bundle(bundle=bundle)
    assert verified["valid"] is True

    bundle["message_fields"]["limit"] = 999
    invalid = att.verify_detached_attestation_bundle(bundle=bundle)
    assert invalid["valid"] is False
