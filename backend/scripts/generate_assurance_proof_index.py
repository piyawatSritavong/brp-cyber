from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_assurance_proof_index import assurance_delivery_proof_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate cross-tenant assurance delivery proof index")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = assurance_delivery_proof_index(db, limit=args.limit)
        print(json.dumps(report, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
