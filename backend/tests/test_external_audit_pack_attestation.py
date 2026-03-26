from __future__ import annotations

import json
from pathlib import Path

from app.services import control_plane_audit_pack_attestation as att


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


def test_create_and_verify_audit_pack_manifest_attestation() -> None:
    fake = FakeRedis()
    orig_redis = att.redis_client
    att.redis_client = fake

    orig_sign = att._sign_message
    orig_verify = att._verify_signature
    try:
        att._sign_message = lambda message: {
            "signature": f"sig:{message}",
            "signer_provider": "hmac",
            "signing_algorithm": "HMAC_SHA256",
            "signature_encoding": "hex",
            "key_ref": "local_hmac",
        }
        att._verify_signature = lambda **kwargs: kwargs.get("signature", "").startswith("sig:")

        root = Path("./tmp/compliance/test_audit_pack_attestation")
        root.mkdir(parents=True, exist_ok=True)
        manifest_path = root / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "pack_id": "audit-pack-1",
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "scope": "control_plane_external_audit_pack",
                    "artifacts": [],
                },
                ensure_ascii=True,
                indent=2,
            ),
            encoding="utf-8",
        )

        created = att.create_audit_pack_manifest_attestation(
            pack_id="audit-pack-1",
            manifest_path=str(manifest_path),
        )
        assert created["status"] == "attested"

        status = att.audit_pack_manifest_attestation_status(limit=10)
        assert status["count"] == 1

        verify_chain = att.verify_audit_pack_manifest_attestation_chain(limit=10)
        assert verify_chain["valid"] is True

        bundle = json.loads(Path(created["path"]).read_text(encoding="utf-8"))
        verified = att.verify_audit_pack_manifest_attestation_bundle(
            bundle=bundle,
            expected_manifest_path=str(manifest_path),
        )
        assert verified["valid"] is True
    finally:
        att.redis_client = orig_redis
        att._sign_message = orig_sign
        att._verify_signature = orig_verify


def test_verify_audit_pack_manifest_attestation_bundle_message_mismatch() -> None:
    result = att.verify_audit_pack_manifest_attestation_bundle(
        {
            "message": "bad",
            "message_fields": {
                "generated_at": "2026-01-01T00:00:00+00:00",
                "pack_id": "audit-pack-1",
                "manifest_sha256": "abc",
                "prev_signature": "",
            },
            "signature": {
                "value": "x",
                "provider": "hmac",
                "encoding": "hex",
                "algorithm": "HMAC_SHA256",
                "key_ref": "local_hmac",
            },
            "artifacts": {
                "pack_id": "audit-pack-1",
                "manifest_path": "./tmp/compliance/test_audit_pack_attestation/manifest.json",
                "manifest_sha256": "abc",
            },
        }
    )
    assert result["valid"] is False
    assert result["reason"] == "message_mismatch"
