from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_orchestration_cost_federation import (
    apply_orchestration_cost_policy_tightening_matrix,
    orchestration_cost_anomaly_federation_heatmap,
    orchestration_cost_policy_tightening_matrix,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Report orchestration cost anomaly federation and policy matrix")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--min-tier", type=str, default="high")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        heatmap = orchestration_cost_anomaly_federation_heatmap(db, limit=max(1, args.limit))
        matrix = orchestration_cost_policy_tightening_matrix(db, limit=max(1, args.limit))
        apply_result = apply_orchestration_cost_policy_tightening_matrix(
            db,
            limit=max(1, args.limit),
            min_tier=args.min_tier,
            dry_run=not args.apply,
        )
    finally:
        db.close()

    print(
        json.dumps(
            {
                "heatmap": heatmap,
                "policy_matrix": matrix,
                "apply_result": apply_result,
            },
            ensure_ascii=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
