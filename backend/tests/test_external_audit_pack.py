from __future__ import annotations

import json
from pathlib import Path

from app.services import control_plane_audit_pack as ap


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


def test_generate_and_verify_external_audit_pack() -> None:
    fake = FakeRedis()
    orig_redis = ap.redis_client
    ap.redis_client = fake

    orig_build = ap.build_control_plane_compliance_evidence
    orig_governance = ap.governance_dashboard
    orig_create = ap.create_governance_attestation
    orig_export = ap.export_latest_governance_attestation
    orig_verify_bundle = ap.verify_detached_attestation_bundle
    orig_create_manifest_attestation = ap.create_audit_pack_manifest_attestation
    orig_verify_manifest_attestation = ap.verify_audit_pack_manifest_attestation_bundle
    try:
        ap.build_control_plane_compliance_evidence = lambda: {"overall_pass": True, "controls": {"a": True}}
        ap.governance_dashboard = lambda limit=5000: {"summary": {"events_analyzed": 1}}
        ap.create_governance_attestation = lambda limit=5000: {"status": "success"}

        def _fake_export(destination_dir=""):
            root = Path(destination_dir)
            root.mkdir(parents=True, exist_ok=True)
            bundle_path = root / "bundle.json"
            bundle_path.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
            return {
                "status": "exported",
                "path": str(bundle_path),
                "bundle": {
                    "message_fields": {
                        "generated_at": "2026-01-01T00:00:00+00:00",
                        "report_hash": "abc",
                        "prev_signature": "",
                        "limit": 1,
                    },
                    "message": "2026-01-01T00:00:00+00:00|abc||1",
                    "signature": {
                        "value": "sig",
                        "provider": "hmac",
                        "algorithm": "HMAC_SHA256",
                        "encoding": "hex",
                        "key_ref": "local_hmac",
                    },
                },
            }

        def _fake_manifest_attestation(pack_id: str, manifest_path: str):
            target = Path(manifest_path)
            bundle_path = target.parent / "manifest_attestation_bundle.json"
            bundle = {
                "attestation_id": "1-0",
                "message_fields": {
                    "generated_at": "2026-01-01T00:00:00+00:00",
                    "pack_id": pack_id,
                    "manifest_sha256": ap._sha256_file(target),
                    "prev_signature": "",
                },
                "message": f"2026-01-01T00:00:00+00:00|{pack_id}|{ap._sha256_file(target)}|",
                "signature": {
                    "value": "sig",
                    "provider": "hmac",
                    "algorithm": "HMAC_SHA256",
                    "encoding": "hex",
                    "key_ref": "local_hmac",
                },
                "artifacts": {
                    "pack_id": pack_id,
                    "manifest_path": str(target),
                    "manifest_sha256": ap._sha256_file(target),
                },
            }
            bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
            return {
                "status": "attested",
                "attestation_id": "1-0",
                "path": str(bundle_path),
                "bundle": bundle,
            }

        ap.export_latest_governance_attestation = _fake_export
        ap.verify_detached_attestation_bundle = lambda bundle: {"valid": True}
        ap.create_audit_pack_manifest_attestation = _fake_manifest_attestation
        ap.verify_audit_pack_manifest_attestation_bundle = lambda bundle, expected_manifest_path=None: {"valid": True}

        result = ap.generate_external_audit_pack(limit=10, destination_dir="./tmp/compliance/test_audit_packs")
        assert result["status"] == "success"
        assert result["manifest_attestation_valid"] is True

        verify = ap.verify_external_audit_pack(result["manifest_path"])
        assert verify["valid"] is True
        assert verify["manifest_attestation_valid"] is True

        status = ap.audit_pack_status(limit=10)
        assert status["count"] == 1
        assert status["rows"][0]["manifest_attestation_valid"] is True
    finally:
        ap.redis_client = orig_redis
        ap.build_control_plane_compliance_evidence = orig_build
        ap.governance_dashboard = orig_governance
        ap.create_governance_attestation = orig_create
        ap.export_latest_governance_attestation = orig_export
        ap.verify_detached_attestation_bundle = orig_verify_bundle
        ap.create_audit_pack_manifest_attestation = orig_create_manifest_attestation
        ap.verify_audit_pack_manifest_attestation_bundle = orig_verify_manifest_attestation


def test_verify_external_audit_pack_requires_manifest_attestation() -> None:
    base = Path("./tmp/compliance/test_audit_packs_missing_attestation")
    pack_dir = base / "audit-pack-1"
    pack_dir.mkdir(parents=True, exist_ok=True)

    evidence = pack_dir / "evidence.json"
    evidence.write_text(json.dumps({"ok": True}), encoding="utf-8")

    manifest_path = pack_dir / "manifest.json"
    manifest = {
        "pack_id": "audit-pack-1",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "overall_pass": True,
        "artifacts": [
            {
                "name": evidence.name,
                "path": str(evidence),
                "sha256": ap._sha256_file(evidence),
                "size_bytes": evidence.stat().st_size,
            }
        ],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    verify = ap.verify_external_audit_pack(str(manifest_path))
    assert verify["valid"] is False
    assert any(item["reason"] == "manifest_attestation_missing" for item in verify["failures"])
