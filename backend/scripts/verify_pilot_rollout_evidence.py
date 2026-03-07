from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.orchestrator import verify_rollout_evidence_chain


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify pilot rollout evidence chain")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id)
    result = verify_rollout_evidence_chain(tenant_id, limit=max(1, args.limit))
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
