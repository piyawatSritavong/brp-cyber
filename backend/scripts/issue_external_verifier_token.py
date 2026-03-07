from __future__ import annotations

import argparse
import json

from app.services.control_plane_verifier_registry import issue_verifier_token


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue external verifier API token")
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--verifier-name", default="external_auditor")
    parser.add_argument("--ttl-seconds", type=int, default=86400)
    args = parser.parse_args()

    result = issue_verifier_token(
        tenant_code=args.tenant_code,
        verifier_name=args.verifier_name,
        ttl_seconds=args.ttl_seconds,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
