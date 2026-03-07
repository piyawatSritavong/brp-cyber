from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_rollout_handoff_policy_drift import apply_rollout_handoff_policy_drift_reconciliation


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile rollout handoff policy drift against baseline")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--min-severity", default="high")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = apply_rollout_handoff_policy_drift_reconciliation(
            db,
            limit=max(1, args.limit),
            min_severity=args.min_severity,
            dry_run=not args.apply,
        )
    finally:
        db.close()
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
