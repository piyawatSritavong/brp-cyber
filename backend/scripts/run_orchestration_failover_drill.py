from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.control_plane_orchestration_failover import trigger_orchestration_failover_drill


def main() -> None:
    parser = argparse.ArgumentParser(description="Run orchestration failover drill")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--reason", default="manual_drill")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    result = trigger_orchestration_failover_drill(
        UUID(args.tenant_id),
        tenant_code=args.tenant_code,
        reason=args.reason,
        dry_run=not args.apply,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
