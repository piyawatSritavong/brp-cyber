from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.control_plane_governance_attestation import verify_detached_attestation_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify detached governance attestation bundle")
    parser.add_argument("--bundle", required=True, help="Path to detached bundle JSON")
    parser.add_argument(
        "--hmac-key",
        default=None,
        help="Optional HMAC key override for bundles signed with provider=hmac",
    )
    args = parser.parse_args()

    bundle_path = Path(args.bundle)
    if not bundle_path.exists():
        raise SystemExit(f"bundle_not_found:{bundle_path}")

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    result = verify_detached_attestation_bundle(bundle=bundle, hmac_key_override=args.hmac_key)
    print(json.dumps(result, ensure_ascii=True, indent=2))

    if not result.get("valid", False):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
