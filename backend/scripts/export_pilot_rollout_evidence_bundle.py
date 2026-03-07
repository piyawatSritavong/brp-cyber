from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.orchestrator import export_rollout_evidence_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Export notarized rollout evidence bundle")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--destination-dir", default="./tmp/compliance/rollout_evidence")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--no-notarize", action="store_true")
    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id)
    result = export_rollout_evidence_bundle(
        tenant_id=tenant_id,
        destination_dir=args.destination_dir,
        limit=max(1, args.limit),
        notarize=not args.no_notarize,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
