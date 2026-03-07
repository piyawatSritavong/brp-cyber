from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_rollout_handoff_policy_drift import (
    get_rollout_handoff_policy_drift_baseline,
    rollout_handoff_policy_drift_heatmap,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Report rollout handoff policy drift heatmap")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--notify", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        payload = {
            "baseline": get_rollout_handoff_policy_drift_baseline(),
            "heatmap": rollout_handoff_policy_drift_heatmap(db, limit=max(1, args.limit), notify=args.notify),
        }
    finally:
        db.close()
    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
