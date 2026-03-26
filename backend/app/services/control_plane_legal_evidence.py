from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.control_plane_audit_pack import audit_pack_status, verify_external_audit_pack
from app.services.control_plane_notarization import notarize_payload
from app.services.control_plane_transparency import transparency_status
from app.services.redis_client import redis_client

LEGAL_EVIDENCE_STREAM_KEY = "control_plane_legal_evidence"


def export_legal_evidence_profile(
    destination_dir: str = "./tmp/compliance/legal_evidence",
) -> dict[str, Any]:
    packs = audit_pack_status(limit=1)
    rows = packs.get("rows", [])
    if not rows:
        return {"status": "no_audit_pack"}

    latest = rows[0]
    manifest_path = str(latest.get("manifest_path", ""))
    verification = verify_external_audit_pack(manifest_path=manifest_path)
    transparency = transparency_status(limit=1)

    profile = {
        "profile_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "audit_pack": {
            "pack_id": latest.get("pack_id", ""),
            "manifest_path": manifest_path,
            "manifest_sha256": latest.get("manifest_sha256", ""),
            "verification": verification,
        },
        "transparency": transparency,
    }

    notarization = notarize_payload(profile)
    profile["notarization"] = notarization
    compliance_profile = notarization.get("compliance_profile", {})
    if not isinstance(compliance_profile, dict):
        compliance_profile = {}

    root = Path(destination_dir)
    root.mkdir(parents=True, exist_ok=True)
    target = root / f"legal_evidence_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
    target.write_text(json.dumps(profile, ensure_ascii=True, indent=2), encoding="utf-8")

    evidence_id = f"legal-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    stream_persisted = True
    try:
        redis_client.xadd(
            LEGAL_EVIDENCE_STREAM_KEY,
            {
                "evidence_id": evidence_id,
                "pack_id": str(latest.get("pack_id", "")),
                "path": str(target),
                "generated_at": profile["generated_at"],
                "notarization_provider": str(notarization.get("provider", "")),
                "notarization_provider_name": str(notarization.get("provider_name", "")),
                "notarization_receipt_id": str(notarization.get("receipt_id", "")),
                "notarization_profile_id": str(compliance_profile.get("profile_id", "")),
                "notarization_eidas_profile": str(
                    (compliance_profile.get("eidas", {}) if isinstance(compliance_profile.get("eidas", {}), dict) else {}).get("profile", "")
                ),
                "notarization_etsi_profile": str(
                    (compliance_profile.get("etsi", {}) if isinstance(compliance_profile.get("etsi", {}), dict) else {}).get("profile", "")
                ),
            },
            maxlen=50000,
            approximate=True,
        )
    except Exception:
        stream_persisted = False

    return {
        "status": "exported",
        "path": str(target),
        "pack_id": str(latest.get("pack_id", "")),
        "evidence_id": evidence_id,
        "notarization": notarization,
        "stream_persisted": stream_persisted,
    }


def legal_evidence_status(limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(LEGAL_EVIDENCE_STREAM_KEY, count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"count": len(rows), "rows": rows}
