from __future__ import annotations

import argparse
import json

from app.services.control_plane_audit_pack_publication import publish_latest_audit_pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish latest external audit pack")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = publish_latest_audit_pack(dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
