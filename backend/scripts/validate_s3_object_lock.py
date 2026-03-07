from __future__ import annotations

import argparse
import json

from app.services.s3_object_lock_validator import validate_s3_object_lock


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate S3 Object Lock readiness")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run runtime validation against S3 (not dry-run)",
    )
    args = parser.parse_args()

    result = validate_s3_object_lock(dry_run=not args.execute)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
