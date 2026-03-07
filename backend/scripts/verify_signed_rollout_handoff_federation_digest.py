from __future__ import annotations

import argparse
import json

from app.services.control_plane_rollout_handoff_federation_signing import verify_signed_rollout_handoff_federation_digest_chain


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify signed rollout handoff federation digest chain")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    result = verify_signed_rollout_handoff_federation_digest_chain(limit=max(1, args.limit))
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
