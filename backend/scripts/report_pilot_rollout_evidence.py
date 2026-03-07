from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.orchestrator import rollout_evidence_history


def main() -> None:
    parser = argparse.ArgumentParser(description="Report pilot rollout evidence history")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id)
    payload = rollout_evidence_history(tenant_id, limit=max(1, args.limit))
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
