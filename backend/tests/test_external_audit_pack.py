from __future__ import annotations

import json
from pathlib import Path

from app.services import control_plane_audit_pack as ap


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.counter = 0

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self.counter += 1
        event_id = f"{self.counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]


def test_generate_and_verify_external_audit_pack() -> None:
    fake = FakeRedis()
    ap.redis_client = fake

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
                "signature": {"value": "sig", "provider": "hmac", "algorithm": "HMAC_SHA256", "encoding": "hex", "key_ref": "local_hmac"},
            },
        }

    ap.export_latest_governance_attestation = _fake_export
    ap.verify_detached_attestation_bundle = lambda bundle: {"valid": True}

    result = ap.generate_external_audit_pack(limit=10, destination_dir="./tmp/compliance/test_audit_packs")
    assert result["status"] == "success"

    verify = ap.verify_external_audit_pack(result["manifest_path"])
    assert verify["valid"] is True

    status = ap.audit_pack_status(limit=10)
    assert status["count"] == 1
