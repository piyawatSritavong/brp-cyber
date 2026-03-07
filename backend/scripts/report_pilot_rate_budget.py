from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.orchestrator import get_tenant_rate_budget, get_tenant_rate_budget_usage


def main() -> None:
    parser = argparse.ArgumentParser(description="Report pilot rate budget status for tenant")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--hour-epoch", type=int, default=None)
    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id)
    payload = {
        "rate_budget": get_tenant_rate_budget(tenant_id),
        "usage": get_tenant_rate_budget_usage(tenant_id, hour_epoch=args.hour_epoch),
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
