from __future__ import annotations

from app.services import control_plane_regulatory_profiles as rp


def test_regulatory_scorecard_reads_signals() -> None:
    orig_pack = rp.audit_pack_status
    orig_publication = rp.publication_status
    orig_transparency = rp.transparency_status
    orig_legal = rp.legal_evidence_status
    try:
        rp.audit_pack_status = lambda limit=1: {"count": 1, "rows": [{"pack_id": "pack-1"}]}
        rp.publication_status = lambda limit=1: {"count": 1, "rows": [{"publication_id": "pub-1"}]}
        rp.transparency_status = lambda limit=1: {"count": 1, "rows": [{"entry_hash": "hash-1"}]}
        rp.legal_evidence_status = lambda limit=1: {
            "count": 1,
            "rows": [{"evidence_id": "legal-1", "notarization_profile_id": "local_integrity_only"}],
        }

        result = rp.regulatory_scorecard("soc2")
        assert result["status"] == "ok"
        assert result["framework"] == "soc2"
        assert result["readiness_score"] == 100
        assert result["coverage_ratio"] == 1.0
        assert all(row["covered"] for row in result["controls"])
    finally:
        rp.audit_pack_status = orig_pack
        rp.publication_status = orig_publication
        rp.transparency_status = orig_transparency
        rp.legal_evidence_status = orig_legal


def test_regulatory_profile_not_found() -> None:
    result = rp.regulatory_profile("unsupported")
    assert result["status"] == "not_found"
    assert "supported_frameworks" in result


def test_regulatory_scorecard_iso27001_requires_legal_evidence_profile() -> None:
    orig_pack = rp.audit_pack_status
    orig_publication = rp.publication_status
    orig_transparency = rp.transparency_status
    orig_legal = rp.legal_evidence_status
    try:
        rp.audit_pack_status = lambda limit=1: {"count": 1, "rows": [{"pack_id": "pack-1"}]}
        rp.publication_status = lambda limit=1: {"count": 1, "rows": [{"publication_id": "pub-1"}]}
        rp.transparency_status = lambda limit=1: {"count": 1, "rows": [{"entry_hash": "hash-1"}]}
        rp.legal_evidence_status = lambda limit=1: {"count": 0, "rows": []}

        result = rp.regulatory_scorecard("iso27001")
        control = next(row for row in result["controls"] if row["control_id"] == "A.18.1")
        assert control["covered"] is False
        assert result["signals"]["has_legal_evidence"] is False
        assert result["signals"]["has_notarization_compliance_profile"] is False
    finally:
        rp.audit_pack_status = orig_pack
        rp.publication_status = orig_publication
        rp.transparency_status = orig_transparency
        rp.legal_evidence_status = orig_legal
