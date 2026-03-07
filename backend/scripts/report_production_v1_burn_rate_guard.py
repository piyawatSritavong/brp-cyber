from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_production_readiness import evaluate_prod_v1_burn_rate_guard


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Production v1 post-go-live burn-rate guard")
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = evaluate_prod_v1_burn_rate_guard(db, args.tenant_code, apply=args.apply)
    finally:
        db.close()

    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
