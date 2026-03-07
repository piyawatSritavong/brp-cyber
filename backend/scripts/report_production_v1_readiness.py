from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_production_readiness import (
    close_prod_v1_go_live,
    evaluate_prod_v1_readiness_final,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate/close Production v1 readiness gate")
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--max-monthly-cost-usd", type=float, default=50.0)
    parser.add_argument("--close", action="store_true")
    parser.add_argument("--approved-by", type=str, default="ciso-ai")
    parser.add_argument("--change-ticket", type=str, default="CHG-PROD-V1")
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        readiness = evaluate_prod_v1_readiness_final(
            db,
            args.tenant_code,
            max_monthly_cost_usd=args.max_monthly_cost_usd,
        )
        close_result = None
        if args.close:
            close_result = close_prod_v1_go_live(
                db,
                args.tenant_code,
                approved_by=args.approved_by,
                change_ticket=args.change_ticket,
                dry_run=not args.promote,
                promote_on_pass=args.promote,
                max_monthly_cost_usd=args.max_monthly_cost_usd,
            )
    finally:
        db.close()

    print(json.dumps({"readiness": readiness, "close_result": close_result}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
