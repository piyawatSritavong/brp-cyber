from __future__ import annotations

from typing import Any

from app.services.control_plane_audit_pack import audit_pack_status
from app.services.control_plane_audit_pack_publication import publication_status
from app.services.control_plane_legal_evidence import legal_evidence_status
from app.services.control_plane_orchestration_assurance import orchestration_objectives_status
from app.services.control_plane_regulatory_profiles import list_regulatory_frameworks, regulatory_scorecard
from app.services.control_plane_transparency import transparency_status


def public_assurance_summary() -> dict[str, Any]:
    pack = audit_pack_status(limit=1)
    publication = publication_status(limit=1)
    transparency = transparency_status(limit=1)
    legal = legal_evidence_status(limit=1)
    orchestration = orchestration_objectives_status(limit=500)

    pack_row = pack.get("rows", [{}])[0] if pack.get("rows") else {}
    publication_row = publication.get("rows", [{}])[0] if publication.get("rows") else {}
    transparency_row = transparency.get("rows", [{}])[0] if transparency.get("rows") else {}
    legal_row = legal.get("rows", [{}])[0] if legal.get("rows") else {}

    return {
        "status": "ok",
        "latest": {
            "audit_pack": {
                "available": bool(pack.get("count", 0) > 0),
                "pack_id": pack_row.get("pack_id", ""),
                "generated_at": pack_row.get("generated_at", ""),
                "overall_pass": bool(pack_row.get("overall_pass", False)),
            },
            "publication": {
                "available": bool(publication.get("count", 0) > 0),
                "publication_id": publication_row.get("publication_id", ""),
                "mode": publication_row.get("mode", ""),
                "valid": bool(publication_row.get("valid", False)),
                "published_at": publication_row.get("published_at", ""),
            },
            "transparency": {
                "available": bool(transparency.get("count", 0) > 0),
                "entry_hash": transparency_row.get("entry_hash", ""),
                "prev_hash": transparency_row.get("prev_hash", ""),
                "timestamp": transparency_row.get("timestamp", ""),
            },
            "legal_evidence": {
                "available": bool(legal.get("count", 0) > 0),
                "evidence_id": legal_row.get("evidence_id", ""),
                "path": legal_row.get("path", ""),
                "notarization_provider": legal_row.get("notarization_provider", ""),
                "notarization_provider_name": legal_row.get("notarization_provider_name", ""),
                "notarization_profile_id": legal_row.get("notarization_profile_id", ""),
                "notarization_eidas_profile": legal_row.get("notarization_eidas_profile", ""),
                "notarization_etsi_profile": legal_row.get("notarization_etsi_profile", ""),
                "generated_at": legal_row.get("generated_at", ""),
            },
            "orchestration_objectives": {
                "sample_count": orchestration.get("sample_count", 0),
                "tenant_count": orchestration.get("tenant_count", 0),
                "overall_pass_rate": orchestration.get("overall_pass_rate", 0.0),
                "enterprise_ready": bool(
                    orchestration.get("enterprise_readiness", {}).get("ready", False)
                ),
            },
        },
    }


def public_assurance_regulatory_overview() -> dict[str, Any]:
    frameworks = list_regulatory_frameworks().get("frameworks", [])
    rows = []
    for item in frameworks:
        framework_id = str(item.get("id", ""))
        score = regulatory_scorecard(framework_id)
        rows.append(
            {
                "framework": framework_id,
                "name": item.get("name", ""),
                "readiness_score": score.get("readiness_score", 0),
                "coverage_ratio": score.get("coverage_ratio", 0.0),
                "status": score.get("status", "unknown"),
            }
        )

    return {"status": "ok", "count": len(rows), "rows": rows}
