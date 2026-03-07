from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_assurance_digest_signing import create_signed_assurance_executive_digest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate signed assurance executive digest")
    parser.add_argument("--destination-dir", default="./tmp/compliance/assurance_executive_digest")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = create_signed_assurance_executive_digest(db, destination_dir=args.destination_dir, limit=args.limit)
        print(json.dumps(result, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
