from __future__ import annotations

import argparse
import json

from app.services.control_plane_rollout_handoff_federation_signing import (
    public_rollout_handoff_federation_digest_bundle,
    verify_signed_rollout_handoff_federation_digest_bundle,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Report/verify rollout handoff federation verifier bundle")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    bundle = public_rollout_handoff_federation_digest_bundle(limit=max(1, args.limit))
    verify = verify_signed_rollout_handoff_federation_digest_bundle(bundle)
    print(json.dumps({"bundle": bundle, "verify_bundle": verify}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
