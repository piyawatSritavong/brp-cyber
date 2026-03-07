from __future__ import annotations

from app.core.config import settings
from app.services.s3_object_lock_validator import validate_s3_object_lock


def test_s3_object_lock_dry_run_fails_when_not_s3_mode() -> None:
    orig_mode = settings.control_plane_offload_mode
    orig_bucket = settings.control_plane_offload_s3_bucket
    orig_lock = settings.control_plane_offload_s3_object_lock_enabled
    orig_retention = settings.control_plane_offload_s3_retention_days

    try:
        settings.control_plane_offload_mode = "filesystem"
        settings.control_plane_offload_s3_bucket = ""
        settings.control_plane_offload_s3_object_lock_enabled = False
        settings.control_plane_offload_s3_retention_days = 30

        result = validate_s3_object_lock(dry_run=True)
        assert result["overall_pass"] is False
        assert any(c["check"] == "offload_mode" and c["pass"] is False for c in result["checks"])
    finally:
        settings.control_plane_offload_mode = orig_mode
        settings.control_plane_offload_s3_bucket = orig_bucket
        settings.control_plane_offload_s3_object_lock_enabled = orig_lock
        settings.control_plane_offload_s3_retention_days = orig_retention


def test_s3_object_lock_dry_run_passes_with_required_flags() -> None:
    orig_mode = settings.control_plane_offload_mode
    orig_bucket = settings.control_plane_offload_s3_bucket
    orig_lock = settings.control_plane_offload_s3_object_lock_enabled
    orig_retention = settings.control_plane_offload_s3_retention_days

    try:
        settings.control_plane_offload_mode = "s3"
        settings.control_plane_offload_s3_bucket = "acb-audit-immutable"
        settings.control_plane_offload_s3_object_lock_enabled = True
        settings.control_plane_offload_s3_retention_days = 30

        result = validate_s3_object_lock(dry_run=True)
        assert result["overall_pass"] is True
    finally:
        settings.control_plane_offload_mode = orig_mode
        settings.control_plane_offload_s3_bucket = orig_bucket
        settings.control_plane_offload_s3_object_lock_enabled = orig_lock
        settings.control_plane_offload_s3_retention_days = orig_retention
