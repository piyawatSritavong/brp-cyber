from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.rollout_handoff_auth import get_rollout_handoff_policy, rollout_handoff_anomalies


def main() -> None:
    parser = argparse.ArgumentParser(description="Report rollout handoff anomalies")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id)
    payload = {
        "policy": get_rollout_handoff_policy(tenant_id),
        "anomalies": rollout_handoff_anomalies(tenant_id, limit=max(1, args.limit)),
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
