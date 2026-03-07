from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.orchestrator import get_tenant_rollout_policy, list_pending_rollout_decisions


def main() -> None:
    parser = argparse.ArgumentParser(description="Report pilot rollout policy and pending approvals")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id)
    payload = {
        "policy": get_tenant_rollout_policy(tenant_id),
        "pending": list_pending_rollout_decisions(tenant_id, limit=max(1, args.limit)),
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
