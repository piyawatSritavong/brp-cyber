from __future__ import annotations

import argparse
import json

from app.services.control_plane_audit_pack_publication import publication_status


def main() -> None:
    parser = argparse.ArgumentParser(description="External audit pack publication status")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    result = publication_status(limit=max(1, args.limit))
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
