from __future__ import annotations

from app.services import control_plane_regulatory_profiles as rp


def test_regulatory_scorecard_reads_signals() -> None:
    orig_pack = rp.audit_pack_status
    orig_publication = rp.publication_status
    orig_transparency = rp.transparency_status
    try:
        rp.audit_pack_status = lambda limit=1: {"count": 1, "rows": [{"pack_id": "pack-1"}]}
        rp.publication_status = lambda limit=1: {"count": 1, "rows": [{"publication_id": "pub-1"}]}
        rp.transparency_status = lambda limit=1: {"count": 1, "rows": [{"entry_hash": "hash-1"}]}

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


def test_regulatory_profile_not_found() -> None:
    result = rp.regulatory_profile("unsupported")
    assert result["status"] == "not_found"
    assert "supported_frameworks" in result
