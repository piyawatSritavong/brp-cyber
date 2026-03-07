from __future__ import annotations

import argparse
import json

from app.services.audit_recovery import replay_failed_batches, recovery_status


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay failed control-plane audit SIEM batches")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    result = replay_failed_batches(limit=max(1, args.limit))
    status = recovery_status(limit=100)
    print(json.dumps({"result": result, "status": status}, indent=2))


if __name__ == "__main__":
    main()
