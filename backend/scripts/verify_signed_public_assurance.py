from __future__ import annotations

import argparse
import json

from app.services.control_plane_public_assurance_signing import verify_signed_public_assurance_chain


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify signed public assurance chain")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    result = verify_signed_public_assurance_chain(limit=args.limit)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
