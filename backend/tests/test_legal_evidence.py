from __future__ import annotations

from app.services import control_plane_legal_evidence as le


def test_export_legal_evidence_profile() -> None:
    le.audit_pack_status = lambda limit=1: {
        "count": 1,
        "rows": [
            {
                "pack_id": "audit-pack-1",
                "manifest_path": "./tmp/compliance/test_manifest.json",
                "manifest_sha256": "abc",
            }
        ],
    }
    le.verify_external_audit_pack = lambda manifest_path: {
        "status": "verified",
        "valid": True,
        "failure_count": 0,
    }
    le.transparency_status = lambda limit=1: {"count": 1, "rows": [{"id": "1-0"}]}
    le.notarize_payload = lambda payload: {
        "status": "notarized",
        "provider": "local_digest",
        "receipt_id": "local-1",
    }

    result = le.export_legal_evidence_profile(destination_dir="./tmp/compliance/test_legal_evidence")
    assert result["status"] == "exported"
    assert result["notarization"]["provider"] == "local_digest"
