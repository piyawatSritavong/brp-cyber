from __future__ import annotations

import json

from app.services import control_plane_governance


def test_governance_dashboard_aggregates_policy_signals() -> None:
    control_plane_governance.list_control_plane_audit = lambda limit=1000: [
        {
            "actor": "alice",
            "action": "policy:tenant_status_update",
            "status": "denied",
            "details": json.dumps({"bypass_objective_gate": True, "new_status": "production"}),
        },
        {
            "actor": "bob",
            "action": "policy:tenant_rotate_key",
            "status": "warning",
            "details": json.dumps({"bypass_objective_gate": False}),
        },
        {
            "actor": "alice",
            "action": "tenant_status_update",
            "status": "updated",
            "details": json.dumps({"new_status": "production"}),
        },
    ]

    result = control_plane_governance.governance_dashboard(limit=100)
    assert result["summary"]["policy_denies"] == 1
    assert result["summary"]["policy_warnings"] == 1
    assert result["summary"]["production_promotions"] == 2
    assert len(result["risky_actors"]) >= 1
