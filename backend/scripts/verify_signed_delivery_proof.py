from __future__ import annotations

import argparse
import json

from app.services.control_plane_assurance_delivery_proof import verify_signed_delivery_proof_chain


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify signed delivery proof chain for tenant")
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    result = verify_signed_delivery_proof_chain(args.tenant_code, limit=args.limit)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
