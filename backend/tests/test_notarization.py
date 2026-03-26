from __future__ import annotations

from app.core.config import settings
from app.services import control_plane_notarization as notarization


def test_notarize_payload_local_digest_includes_compliance_profile() -> None:
    orig_provider = settings.control_plane_notarization_provider
    try:
        settings.control_plane_notarization_provider = "local_digest"
        result = notarization.notarize_payload({"hello": "world"})
        assert result["status"] == "notarized"
        assert result["provider"] == "local_digest"
        assert result["compliance_profile"]["profile_id"] == "local_integrity_only"
        assert result["compliance_profile"]["eidas"]["profile"] == "not_supported"
        assert result["compliance_profile"]["etsi"]["profile"] == "none"
    finally:
        settings.control_plane_notarization_provider = orig_provider


def test_resolve_notarization_compliance_profile_webhook_declared_timestamp() -> None:
    orig_profiles = settings.control_plane_notarization_compliance_profiles
    try:
        settings.control_plane_notarization_compliance_profiles = ""
        result = notarization.resolve_notarization_compliance_profile(
            {
                "provider": "webhook",
                "provider_name": "eu-qtsp",
                "receipt_id": "receipt-1",
                "reference": {"compliance": {"profile_id": "qualified_timestamp"}},
            }
        )
        assert result["profile_id"] == "eidas_qualified_timestamp"
        assert result["provider_name"] == "eu-qtsp"
        assert result["eidas"]["qualified"] is True
        assert result["etsi"]["profile"] == "timestamp_service"
    finally:
        settings.control_plane_notarization_compliance_profiles = orig_profiles
