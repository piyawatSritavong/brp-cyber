from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_orchestration_failover_signing import create_signed_orchestration_failover_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate signed orchestration failover report")
    parser.add_argument("--destination-dir", default="./tmp/compliance/orchestration_failover")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = create_signed_orchestration_failover_report(
            db,
            destination_dir=args.destination_dir,
            limit=max(1, args.limit),
        )
    finally:
        db.close()
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
