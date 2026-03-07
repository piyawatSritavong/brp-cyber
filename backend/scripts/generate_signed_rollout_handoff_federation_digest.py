from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_rollout_handoff_federation_signing import create_signed_rollout_handoff_federation_digest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate signed rollout handoff federation executive digest")
    parser.add_argument("--destination-dir", default="./tmp/compliance/rollout_handoff_federation_digest")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = create_signed_rollout_handoff_federation_digest(
            db,
            destination_dir=args.destination_dir,
            limit=max(1, args.limit),
        )
    finally:
        db.close()

    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
