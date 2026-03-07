from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from app.services.audit import list_control_plane_audit
from app.services.control_plane_policy import policy_config


def _decode_details(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def governance_dashboard(limit: int = 1000) -> dict[str, Any]:
    rows = list_control_plane_audit(limit=max(1, limit))

    status_counts: dict[str, int] = defaultdict(int)
    action_counts: dict[str, int] = defaultdict(int)
    actor_risk: dict[str, int] = defaultdict(int)

    policy_warnings = 0
    policy_denies = 0
    override_actions = 0
    production_promotions = 0

    for row in rows:
        status = str(row.get("status", "unknown"))
        action = str(row.get("action", "unknown"))
        actor = str(row.get("actor", "unknown"))
        details = _decode_details(str(row.get("details", "{}")))

        status_counts[status] += 1
        action_counts[action] += 1

        if action.startswith("policy:"):
            if status == "denied":
                policy_denies += 1
                actor_risk[actor] += 2
            elif status == "warning":
                policy_warnings += 1
                actor_risk[actor] += 1

        if bool(details.get("bypass_objective_gate", False)):
            override_actions += 1
            actor_risk[actor] += 1

        if str(details.get("new_status", "")).lower() == "production":
            production_promotions += 1

    risky_actors = sorted(
        [{"actor": actor, "risk_score": score} for actor, score in actor_risk.items()],
        key=lambda item: item["risk_score"],
        reverse=True,
    )[:20]

    return {
        "policy": policy_config(),
        "summary": {
            "events_analyzed": len(rows),
            "policy_warnings": policy_warnings,
            "policy_denies": policy_denies,
            "override_actions": override_actions,
            "production_promotions": production_promotions,
        },
        "status_counts": dict(status_counts),
        "top_actions": sorted(action_counts.items(), key=lambda item: item[1], reverse=True)[:20],
        "risky_actors": risky_actors,
    }
