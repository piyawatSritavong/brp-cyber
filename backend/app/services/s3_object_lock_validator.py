from __future__ import annotations

from typing import Any

from app.core.config import settings


def _check(name: str, passed: bool, message: str) -> dict[str, str | bool]:
    return {
        "check": name,
        "pass": passed,
        "message": message,
    }


def validate_s3_object_lock(dry_run: bool = True) -> dict[str, Any]:
    checks: list[dict[str, str | bool]] = []

    mode_is_s3 = settings.control_plane_offload_mode.lower().strip() == "s3"
    checks.append(
        _check(
            "offload_mode",
            mode_is_s3,
            f"offload mode={settings.control_plane_offload_mode}",
        )
    )

    bucket_configured = bool(settings.control_plane_offload_s3_bucket.strip())
    checks.append(
        _check(
            "s3_bucket",
            bucket_configured,
            f"bucket={settings.control_plane_offload_s3_bucket or 'missing'}",
        )
    )

    lock_policy_enabled = bool(settings.control_plane_offload_s3_object_lock_enabled)
    checks.append(
        _check(
            "object_lock_policy_flag",
            lock_policy_enabled,
            f"CONTROL_PLANE_OFFLOAD_S3_OBJECT_LOCK_ENABLED={settings.control_plane_offload_s3_object_lock_enabled}",
        )
    )

    retention_valid = int(settings.control_plane_offload_s3_retention_days) > 0
    checks.append(
        _check(
            "retention_days",
            retention_valid,
            f"retention_days={settings.control_plane_offload_s3_retention_days}",
        )
    )

    runtime_checks: list[dict[str, str | bool]] = []

    if not dry_run and mode_is_s3 and bucket_configured:
        try:
            import boto3

            session = boto3.session.Session(
                aws_access_key_id=settings.control_plane_offload_s3_access_key or None,
                aws_secret_access_key=settings.control_plane_offload_s3_secret_key or None,
                region_name=settings.control_plane_offload_s3_region or None,
            )
            client = session.client("s3", endpoint_url=settings.control_plane_offload_s3_endpoint_url or None)

            client.head_bucket(Bucket=settings.control_plane_offload_s3_bucket)
            runtime_checks.append(_check("head_bucket", True, "bucket reachable"))

            versioning = client.get_bucket_versioning(Bucket=settings.control_plane_offload_s3_bucket)
            versioning_ok = str(versioning.get("Status", "")) == "Enabled"
            runtime_checks.append(
                _check(
                    "bucket_versioning",
                    versioning_ok,
                    f"status={versioning.get('Status', 'Unknown')}",
                )
            )

            lock_cfg = client.get_object_lock_configuration(Bucket=settings.control_plane_offload_s3_bucket)
            lock_enabled = (
                lock_cfg.get("ObjectLockConfiguration", {}).get("ObjectLockEnabled", "") == "Enabled"
            )
            runtime_checks.append(
                _check(
                    "bucket_object_lock",
                    lock_enabled,
                    f"object_lock={lock_cfg.get('ObjectLockConfiguration', {}).get('ObjectLockEnabled', 'Unknown')}",
                )
            )
        except Exception as exc:
            runtime_checks.append(_check("runtime_validation", False, f"runtime_check_failed:{exc}"))

    all_checks = checks + runtime_checks
    overall_pass = all(item.get("pass", False) for item in all_checks)

    return {
        "dry_run": dry_run,
        "overall_pass": overall_pass,
        "checks": all_checks,
        "required_next_action": (
            "Switch offload mode to s3 and enable object lock settings"
            if not mode_is_s3 or not bucket_configured
            else "Run non-dry-run validation in production path"
            if dry_run
            else "Validation completed"
        ),
    }
