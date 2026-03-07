from __future__ import annotations

import argparse
import json

from app.services.control_plane_external_verifier_attestation import verify_verifier_receipt_chain


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify external verifier signed receipt chain")
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    result = verify_verifier_receipt_chain(tenant_code=args.tenant_code, limit=args.limit)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
