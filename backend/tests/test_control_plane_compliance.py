from __future__ import annotations

from app.services import control_plane_compliance


def test_build_control_plane_compliance_evidence_pass() -> None:
    orig_auth = control_plane_compliance.auth_posture
    orig_validate = control_plane_compliance.validate_s3_object_lock
    orig_offload = control_plane_compliance.offload_status
    try:
        control_plane_compliance.auth_posture = lambda: {
            "environment": "production",
            "auth_provider": "idp",
            "local_bootstrap_available": False,
        }
        control_plane_compliance.validate_s3_object_lock = lambda dry_run=True: {
            "overall_pass": True,
            "checks": [{"check": "object_lock_policy_flag", "pass": True}],
        }
        control_plane_compliance.offload_status = lambda: {"mode": "s3"}

        result = control_plane_compliance.build_control_plane_compliance_evidence()
        assert result["overall_pass"] is True
        assert result["controls"]["idp_enforced_for_production"] is True
    finally:
        control_plane_compliance.auth_posture = orig_auth
        control_plane_compliance.validate_s3_object_lock = orig_validate
        control_plane_compliance.offload_status = orig_offload


def test_build_control_plane_compliance_evidence_fail() -> None:
    orig_auth = control_plane_compliance.auth_posture
    orig_validate = control_plane_compliance.validate_s3_object_lock
    orig_offload = control_plane_compliance.offload_status
    try:
        control_plane_compliance.auth_posture = lambda: {
            "environment": "production",
            "auth_provider": "local",
            "local_bootstrap_available": True,
        }
        control_plane_compliance.validate_s3_object_lock = lambda dry_run=True: {
            "overall_pass": False,
            "checks": [{"check": "object_lock_policy_flag", "pass": False}],
        }
        control_plane_compliance.offload_status = lambda: {"mode": "filesystem"}

        result = control_plane_compliance.build_control_plane_compliance_evidence()
        assert result["overall_pass"] is False
        assert result["controls"]["local_bootstrap_disabled"] is False
    finally:
        control_plane_compliance.auth_posture = orig_auth
        control_plane_compliance.validate_s3_object_lock = orig_validate
        control_plane_compliance.offload_status = orig_offload
