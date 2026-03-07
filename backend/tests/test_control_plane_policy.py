from __future__ import annotations

from app.core.config import settings
from app.services.control_plane_policy import evaluate_policy


def test_policy_enforce_denies_production_without_ticket() -> None:
    orig_mode = settings.control_plane_policy_mode
    orig_ticket_prod = settings.control_plane_policy_require_change_ticket_for_production
    try:
        settings.control_plane_policy_mode = "enforce"
        settings.control_plane_policy_require_change_ticket_for_production = True

        decision = evaluate_policy(
            action="tenant_status_update",
            admin={"scopes": ["control_plane:write"]},
            context={"status": "production", "bypass_objective_gate": False, "change_ticket": ""},
        )
        assert decision["allowed"] is False
        assert decision["severity"] == "deny"
    finally:
        settings.control_plane_policy_mode = orig_mode
        settings.control_plane_policy_require_change_ticket_for_production = orig_ticket_prod


def test_policy_permissive_warns_key_rotate_without_reason() -> None:
    orig_mode = settings.control_plane_policy_mode
    orig_reason = settings.control_plane_policy_require_reason_for_key_rotation
    try:
        settings.control_plane_policy_mode = "permissive"
        settings.control_plane_policy_require_reason_for_key_rotation = True

        decision = evaluate_policy(
            action="tenant_rotate_key",
            admin={"scopes": ["control_plane:write"]},
            context={"reason": "", "change_ticket": "CHG-1"},
        )
        assert decision["allowed"] is True
        assert decision["has_violations"] is True
        assert decision["severity"] == "warning"
    finally:
        settings.control_plane_policy_mode = orig_mode
        settings.control_plane_policy_require_reason_for_key_rotation = orig_reason
