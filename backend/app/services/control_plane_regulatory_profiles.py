from __future__ import annotations

from typing import Any

from app.services.control_plane_audit_pack import audit_pack_status
from app.services.control_plane_audit_pack_publication import publication_status
from app.services.control_plane_legal_evidence import legal_evidence_status
from app.services.control_plane_transparency import transparency_status

REGULATORY_TEMPLATES: dict[str, dict[str, Any]] = {
    "soc2": {
        "name": "SOC 2 Trust Services Criteria",
        "controls": [
            {
                "control_id": "CC7.2",
                "title": "Monitor system components and security events",
                "evidence_refs": ["control_plane_governance_report", "objective_gate_dashboard"],
            },
            {
                "control_id": "CC8.1",
                "title": "Change management and controlled deployments",
                "evidence_refs": ["control_plane_policy_audit", "governance_attestation_bundle"],
            },
            {
                "control_id": "A1.2",
                "title": "Availability and incident handling",
                "evidence_refs": ["dr_smoke", "external_audit_pack"],
            },
        ],
    },
    "iso27001": {
        "name": "ISO/IEC 27001 Annex A",
        "controls": [
            {
                "control_id": "A.12.4",
                "title": "Logging and monitoring",
                "evidence_refs": ["control_plane_audit_stream", "siem_export"],
            },
            {
                "control_id": "A.16.1",
                "title": "Incident management",
                "evidence_refs": ["blue_detection_response", "purple_gap_reports"],
            },
            {
                "control_id": "A.18.1",
                "title": "Compliance with legal and contractual requirements",
                "evidence_refs": ["legal_evidence_profile", "transparency_log"],
            },
        ],
    },
    "nist_csf": {
        "name": "NIST Cybersecurity Framework",
        "controls": [
            {
                "control_id": "DE.CM",
                "title": "Continuous security monitoring",
                "evidence_refs": ["objective_gate_kpi", "control_plane_governance"],
            },
            {
                "control_id": "RS.MI",
                "title": "Mitigation and response improvements",
                "evidence_refs": ["purple_recommendations", "policy_feedback_loop"],
            },
            {
                "control_id": "RC.RP",
                "title": "Recovery planning",
                "evidence_refs": ["dr_runbook", "audit_pack_publication"],
            },
        ],
    },
}


def list_regulatory_frameworks() -> dict[str, Any]:
    return {
        "count": len(REGULATORY_TEMPLATES),
        "frameworks": [
            {"id": key, "name": value["name"], "control_count": len(value["controls"])}
            for key, value in REGULATORY_TEMPLATES.items()
        ],
    }


def regulatory_profile(framework: str) -> dict[str, Any]:
    key = framework.lower().strip()
    template = REGULATORY_TEMPLATES.get(key)
    if not template:
        return {
            "status": "not_found",
            "framework": framework,
            "supported_frameworks": sorted(REGULATORY_TEMPLATES.keys()),
        }

    return {
        "status": "ok",
        "framework": key,
        "name": template["name"],
        "control_count": len(template["controls"]),
        "controls": template["controls"],
    }


def regulatory_scorecard(framework: str) -> dict[str, Any]:
    profile = regulatory_profile(framework)
    if profile.get("status") != "ok":
        return profile

    pack = audit_pack_status(limit=1)
    publication = publication_status(limit=1)
    transparency = transparency_status(limit=1)
    legal = legal_evidence_status(limit=1)

    has_pack = pack.get("count", 0) > 0
    has_publication = publication.get("count", 0) > 0
    has_transparency = transparency.get("count", 0) > 0
    has_legal_evidence = legal.get("count", 0) > 0
    legal_row = legal.get("rows", [{}])[0] if legal.get("rows") else {}
    has_notarization_profile = bool(legal_row.get("notarization_profile_id", ""))

    readiness = 0
    readiness += 35 if has_pack else 0
    readiness += 35 if has_publication else 0
    readiness += 30 if has_transparency else 0

    coverage = []
    for control in profile["controls"]:
        covered = has_pack and has_publication
        if "legal_evidence_profile" in control["evidence_refs"]:
            covered = covered and has_transparency and has_legal_evidence and has_notarization_profile
        if "transparency_log" in control["evidence_refs"]:
            covered = covered and has_transparency
        coverage.append(
            {
                "control_id": control["control_id"],
                "title": control["title"],
                "covered": covered,
                "evidence_refs": control["evidence_refs"],
            }
        )

    covered_count = len([c for c in coverage if c["covered"]])

    return {
        "status": "ok",
        "framework": profile["framework"],
        "name": profile["name"],
        "readiness_score": readiness,
        "covered_controls": covered_count,
        "total_controls": len(coverage),
        "coverage_ratio": round((covered_count / len(coverage)) if coverage else 0.0, 4),
        "signals": {
            "has_audit_pack": has_pack,
            "has_publication": has_publication,
            "has_transparency": has_transparency,
            "has_legal_evidence": has_legal_evidence,
            "has_notarization_compliance_profile": has_notarization_profile,
        },
        "controls": coverage,
    }
