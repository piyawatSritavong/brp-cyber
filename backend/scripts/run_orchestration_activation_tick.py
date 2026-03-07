from __future__ import annotations

import argparse
import json

from app.services.orchestrator import run_activation_scheduler_tick


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one scheduler tick for active orchestrations")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    result = run_activation_scheduler_tick(limit=args.limit)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
