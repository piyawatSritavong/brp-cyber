from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_rollout_handoff_federation import (
    evaluate_rollout_handoff_federation_slo,
    rollout_handoff_federation_executive_digest,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Report rollout handoff federation SLO and breach budget")
    parser.add_argument("--tenant-code", default="acb")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--dry-run-escalation", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        payload = {
            "tenant_evaluation": evaluate_rollout_handoff_federation_slo(
                db,
                tenant_code=args.tenant_code,
                limit=max(1, args.limit),
                dry_run_escalation=args.dry_run_escalation,
            ),
            "executive_digest": rollout_handoff_federation_executive_digest(db, limit=max(1, args.limit)),
        }
    finally:
        db.close()

    print(json.dumps(payload, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
