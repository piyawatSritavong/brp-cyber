from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.services.admin_auth import token_has_scope


def policy_config() -> dict[str, Any]:
    return {
        "mode": settings.control_plane_policy_mode.lower().strip(),
        "require_change_ticket_for_override": settings.control_plane_policy_require_change_ticket_for_override,
        "require_change_ticket_for_production": settings.control_plane_policy_require_change_ticket_for_production,
        "require_reason_for_key_rotation": settings.control_plane_policy_require_reason_for_key_rotation,
    }


def evaluate_policy(action: str, admin: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {}
    cfg = policy_config()
    mode = cfg["mode"]

    violations: list[dict[str, str]] = []

    if action == "tenant_status_update":
        new_status = str(context.get("status", "")).lower().strip()
        bypass = bool(context.get("bypass_objective_gate", False))
        change_ticket = str(context.get("change_ticket", "")).strip()

        if bypass and not token_has_scope(admin, "control_plane:override"):
            violations.append({"code": "override_scope_required", "message": "override scope required for bypass"})

        if bypass and cfg["require_change_ticket_for_override"] and not change_ticket:
            violations.append({"code": "change_ticket_required_for_override", "message": "change ticket required for bypass override"})

        if new_status == "production" and cfg["require_change_ticket_for_production"] and not change_ticket:
            violations.append({"code": "change_ticket_required_for_production", "message": "change ticket required for production promotion"})

    if action == "tenant_rotate_key":
        reason = str(context.get("reason", "")).strip()
        if cfg["require_reason_for_key_rotation"] and len(reason) < 8:
            violations.append({"code": "rotation_reason_required", "message": "key rotation reason must be provided"})

    has_violations = len(violations) > 0
    allowed = not has_violations or mode != "enforce"

    return {
        "action": action,
        "mode": mode,
        "allowed": allowed,
        "has_violations": has_violations,
        "severity": "warning" if has_violations and mode != "enforce" else "deny" if has_violations else "pass",
        "violations": violations,
    }
