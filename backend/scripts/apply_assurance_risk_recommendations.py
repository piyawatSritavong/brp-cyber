from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_assurance_risk import apply_assurance_risk_recommendations


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply adaptive assurance risk recommendations")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--max-tier", default="critical")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = apply_assurance_risk_recommendations(
            db,
            limit=args.limit,
            max_tier=args.max_tier,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
