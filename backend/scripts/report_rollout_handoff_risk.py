from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.rollout_handoff_auth import rollout_handoff_risk_snapshot, rollout_handoff_trust_events


def main() -> None:
    parser = argparse.ArgumentParser(description="Report rollout handoff trust/risk summary")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id)
    payload = {
        "risk_snapshot": rollout_handoff_risk_snapshot(tenant_id, limit=max(1, args.limit)),
        "trust_events": rollout_handoff_trust_events(tenant_id, limit=max(1, args.limit)),
    }
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
