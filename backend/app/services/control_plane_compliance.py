from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.admin_auth import auth_posture
from app.services.audit_offload import offload_status
from app.services.s3_object_lock_validator import validate_s3_object_lock


def build_control_plane_compliance_evidence() -> dict[str, Any]:
    posture = auth_posture()
    s3_validation = validate_s3_object_lock(dry_run=True)
    offload = offload_status()

    controls = {
        "idp_enforced_for_production": (
            posture.get("environment") in {"prod", "production"}
            and not posture.get("local_bootstrap_available", True)
        )
        or posture.get("auth_provider") == "idp",
        "local_bootstrap_disabled": not posture.get("local_bootstrap_available", True),
        "immutable_retention_policy_flag": any(
            item.get("check") == "object_lock_policy_flag" and item.get("pass") for item in s3_validation.get("checks", [])
        ),
        "s3_object_lock_ready": bool(s3_validation.get("overall_pass", False)),
    }

    overall_pass = all(controls.values())

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_pass": overall_pass,
        "controls": controls,
        "auth_posture": posture,
        "s3_object_lock_validation": s3_validation,
        "offload_status": offload,
    }
