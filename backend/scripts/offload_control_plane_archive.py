from __future__ import annotations

import argparse
import json

from app.services.audit_offload import offload_archive_batches, offload_status


def main() -> None:
    parser = argparse.ArgumentParser(description="Offload signed control-plane archive batches")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    result = offload_archive_batches(limit=max(1, args.limit))
    status = offload_status()
    print(json.dumps({"result": result, "status": status}, indent=2))


if __name__ == "__main__":
    main()
