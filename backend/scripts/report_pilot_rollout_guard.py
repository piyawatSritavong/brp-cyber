from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.orchestrator import get_rollout_guard_state, rollout_decision_history


def main() -> None:
    parser = argparse.ArgumentParser(description="Report pilot rollout guard state")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id)
    payload = {
        "guard": get_rollout_guard_state(tenant_id),
        "decisions": rollout_decision_history(tenant_id, limit=max(1, args.limit)),
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
