from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.orchestrator import get_tenant_safety_policy, pilot_incidents


def main() -> None:
    parser = argparse.ArgumentParser(description="Report pilot incidents for tenant")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id)
    payload = {
        "safety_policy": get_tenant_safety_policy(tenant_id),
        "incidents": pilot_incidents(tenant_id, limit=max(1, args.limit)),
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
