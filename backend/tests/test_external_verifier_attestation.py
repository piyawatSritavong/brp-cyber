from __future__ import annotations

from app.services import control_plane_external_verifier_attestation as zv


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.strings: dict[str, str] = {}
        self.hashes: dict[str, dict[str, str]] = {}
        self.counter = 0

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self.counter += 1
        event_id = f"{self.counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]

    def xrange(self, key: str, min: str = "-", max: str = "+", count: int = 100):
        return list(self.streams.get(key, []))[:count]

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

    def set(self, key: str, value: str) -> bool:
        self.strings[key] = value
        return True

    def hset(self, key: str, mapping: dict[str, str]) -> int:
        self.hashes.setdefault(key, {}).update(mapping)
        return len(mapping)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key, {}))


def test_external_verifier_import_and_zero_trust_attestation() -> None:
    fake = FakeRedis()
    zv.redis_client = fake
    zv.verify_signed_tenant_evidence_package_chain = lambda tenant_code, limit=100: {
        "tenant_code": tenant_code,
        "valid": True,
        "checked": 1,
    }
    zv._sign_message = lambda message: {
        "signature": f"sig:{message}",
        "signer_provider": "hmac",
        "signing_algorithm": "HMAC_SHA256",
        "signature_encoding": "hex",
        "key_ref": "local_hmac",
    }
    zv._verify_signature = lambda **kwargs: str(kwargs.get("signature", "")).startswith("sig:")

    imported = zv.import_external_verifier_bundle(
        tenant_code="acb",
        verifier_payload={
            "bundle_id": "vb-1",
            "snapshot_id": "s-1",
            "valid": True,
            "signature": "sig-x",
            "reported_at": "2026-03-06T10:00:00+00:00",
        },
        source="auditor_x",
    )
    assert imported["status"] == "imported"
    assert imported["valid"] is True
    assert imported["receipt_id"] != ""

    status = zv.external_verifier_status("acb", limit=10)
    assert status["count"] == 1
    assert status["rows"][0]["valid"] is True

    attested = zv.compute_zero_trust_attestation("acb", limit=10, freshness_hours=24)
    assert attested["status"] == "attested"
    assert attested["trusted"] is True

    tenant_status = zv.zero_trust_attestation_status("acb", limit=10)
    assert tenant_status["count"] == 1
    assert tenant_status["rows"][0]["trusted"] is True

    overview = zv.zero_trust_overview(limit=10)
    assert overview["count"] == 1
    assert overview["trusted_tenants"] == 1

    receipts = zv.verifier_receipt_status("acb", limit=10)
    assert receipts["count"] == 1
    assert receipts["rows"][0]["valid"] is True

    receipt_verify = zv.verify_verifier_receipt_chain("acb", limit=10)
    assert receipt_verify["valid"] is True


def test_zero_trust_quorum_policy_enforcement() -> None:
    fake = FakeRedis()
    zv.redis_client = fake
    zv.verify_signed_tenant_evidence_package_chain = lambda tenant_code, limit=100: {
        "tenant_code": tenant_code,
        "valid": True,
        "checked": 1,
    }
    zv._sign_message = lambda message: {
        "signature": f"sig:{message}",
        "signer_provider": "hmac",
        "signing_algorithm": "HMAC_SHA256",
        "signature_encoding": "hex",
        "key_ref": "local_hmac",
    }
    zv._verify_signature = lambda **kwargs: str(kwargs.get("signature", "")).startswith("sig:")

    policy = zv.upsert_external_verifier_policy(
        tenant_code="acb",
        payload={"min_quorum": 2, "allowed_verifiers": ["auditor_a", "auditor_b"], "freshness_hours": 24},
    )
    assert policy["status"] == "upserted"
    assert policy["policy"]["min_quorum"] == 2

    zv.import_external_verifier_bundle(
        tenant_code="acb",
        verifier_payload={"bundle_id": "v1", "snapshot_id": "s1", "valid": True, "verifier": "auditor_a"},
        source="auditor_a",
    )
    first = zv.compute_zero_trust_attestation("acb", limit=10, freshness_hours=24)
    assert first["external_quorum_met"] is False
    assert first["trusted"] is False

    zv.import_external_verifier_bundle(
        tenant_code="acb",
        verifier_payload={"bundle_id": "v2", "snapshot_id": "s2", "valid": True, "verifier": "auditor_b"},
        source="auditor_b",
    )
    second = zv.compute_zero_trust_attestation("acb", limit=10, freshness_hours=24)
    assert second["external_quorum_met"] is True
    assert second["trusted"] is True


def test_weighted_score_and_disagreement_policy() -> None:
    fake = FakeRedis()
    zv.redis_client = fake
    zv.verify_signed_tenant_evidence_package_chain = lambda tenant_code, limit=100: {
        "tenant_code": tenant_code,
        "valid": True,
        "checked": 1,
    }
    zv._sign_message = lambda message: {
        "signature": f"sig:{message}",
        "signer_provider": "hmac",
        "signing_algorithm": "HMAC_SHA256",
        "signature_encoding": "hex",
        "key_ref": "local_hmac",
    }
    zv._verify_signature = lambda **kwargs: str(kwargs.get("signature", "")).startswith("sig:")

    zv.upsert_external_verifier_policy(
        tenant_code="acb",
        payload={
            "min_quorum": 1,
            "min_weighted_score": 0.8,
            "allowed_verifiers": ["auditor_a", "auditor_b"],
            "verifier_weights": {"auditor_a": 0.2, "auditor_b": 1.0},
            "block_on_disagreement": True,
        },
    )

    zv.import_external_verifier_bundle(
        tenant_code="acb",
        verifier_payload={"bundle_id": "va", "snapshot_id": "sa", "valid": True, "verifier": "auditor_a"},
        source="auditor_a",
    )
    zv.import_external_verifier_bundle(
        tenant_code="acb",
        verifier_payload={"bundle_id": "vb", "snapshot_id": "sb", "valid": False, "verifier": "auditor_b"},
        source="auditor_b",
    )

    first = zv.compute_zero_trust_attestation("acb", limit=10, freshness_hours=24)
    assert first["external_quorum_met"] is True
    assert first["external_weighted_pass"] is False
    assert first["external_disagreement_detected"] is True
    assert first["trusted"] is False

    zv.import_external_verifier_bundle(
        tenant_code="acb",
        verifier_payload={"bundle_id": "vb2", "snapshot_id": "sb2", "valid": True, "verifier": "auditor_b"},
        source="auditor_b",
    )
    second = zv.compute_zero_trust_attestation("acb", limit=10, freshness_hours=24)
    assert second["external_weighted_pass"] is True
    assert second["external_disagreement_detected"] is False
    assert second["trusted"] is True
