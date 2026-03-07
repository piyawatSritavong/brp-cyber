from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.orchestrator import evaluate_tenant_rollout_posture, rollout_decision_history


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate pilot rollout posture for tenant")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id)
    decision = evaluate_tenant_rollout_posture(tenant_id, apply=args.apply)
    history = rollout_decision_history(tenant_id, limit=max(1, args.limit))
    payload = {"decision": decision, "history": history}
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
