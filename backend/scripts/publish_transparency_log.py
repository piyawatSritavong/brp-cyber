from __future__ import annotations

import argparse
import json

from app.services.control_plane_transparency import publish_transparency_entry


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish transparency log entry from latest publication")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = publish_transparency_entry(dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
