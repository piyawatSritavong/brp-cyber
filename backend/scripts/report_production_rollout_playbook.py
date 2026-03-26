from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_production_rollout_playbook import production_rollout_integration_playbook


def main() -> None:
    parser = argparse.ArgumentParser(description="Report the production rollout integration playbook for a tenant")
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--max-monthly-cost-usd", type=float, default=50.0)
    parser.add_argument("--handoff-limit", type=int, default=200)
    parser.add_argument("--closure-limit", type=int, default=20)
    parser.add_argument("--burn-rate-limit", type=int, default=20)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = production_rollout_integration_playbook(
            db,
            args.tenant_code,
            max_monthly_cost_usd=args.max_monthly_cost_usd,
            handoff_limit=args.handoff_limit,
            closure_limit=args.closure_limit,
            burn_rate_limit=args.burn_rate_limit,
        )
    finally:
        db.close()

    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
