from __future__ import annotations

import argparse
import json

from app.services.control_plane_public_assurance_signing import create_signed_public_assurance_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate signed public assurance snapshot")
    parser.add_argument("--destination-dir", default="./tmp/compliance/public_assurance")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    result = create_signed_public_assurance_snapshot(destination_dir=args.destination_dir, limit=args.limit)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
