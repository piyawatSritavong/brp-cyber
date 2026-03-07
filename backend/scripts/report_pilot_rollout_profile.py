from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.orchestrator import get_tenant_activation_state, get_tenant_rollout_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Report pilot rollout profile and runtime state")
    parser.add_argument("--tenant-id", required=True)
    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id)
    payload = {
        "rollout_profile": get_tenant_rollout_profile(tenant_id),
        "activation": get_tenant_activation_state(tenant_id),
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
