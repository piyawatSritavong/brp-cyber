from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_rollout_handoff_federation import (
    rollout_handoff_escalation_matrix,
    rollout_handoff_federation_heatmap,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Report cross-tenant rollout handoff risk federation")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        payload = {
            "heatmap": rollout_handoff_federation_heatmap(db, limit=max(1, args.limit)),
            "escalation_matrix": rollout_handoff_escalation_matrix(db, limit=max(1, args.limit)),
        }
    finally:
        db.close()

    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
