from __future__ import annotations

import argparse
import json

from app.services.autonomous_scheduler_worker import DistributedAutonomousScheduler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the distributed autonomous scheduler worker")
    parser.add_argument("--once", action="store_true", help="Run a single worker iteration and exit")
    parser.add_argument("--iterations", type=int, default=0, help="Maximum worker iterations before exit")
    parser.add_argument("--worker-id", type=str, default="", help="Optional worker identifier override")
    args = parser.parse_args()

    scheduler = DistributedAutonomousScheduler(worker_id=args.worker_id)
    limit = 1 if args.once else (args.iterations if args.iterations > 0 else None)
    result = scheduler.run_forever(max_iterations=limit)
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
