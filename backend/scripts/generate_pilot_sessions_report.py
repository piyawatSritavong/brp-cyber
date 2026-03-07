from __future__ import annotations

import argparse
import json

from app.services.orchestrator import list_pilot_sessions


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate orchestration pilot session report")
    parser.add_argument("--limit", type=int, default=500)
    args = parser.parse_args()

    result = list_pilot_sessions(limit=args.limit)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
