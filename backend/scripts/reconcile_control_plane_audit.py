from __future__ import annotations

import argparse
import json

from app.services.audit_recovery import reconcile_failed_batches


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile failed SIEM batches against replay/ack states")
    parser.add_argument("--limit", type=int, default=2000)
    args = parser.parse_args()

    result = reconcile_failed_batches(limit=max(1, args.limit))
    print(json.dumps(result, indent=2))

    if result.get("unresolved_count", 0) > 0:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
