from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_orchestration_failover import orchestration_failover_enterprise_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Report orchestration failover enterprise snapshot")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = orchestration_failover_enterprise_snapshot(db, limit=max(1, args.limit))
    finally:
        db.close()
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
