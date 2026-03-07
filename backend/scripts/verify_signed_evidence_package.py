from __future__ import annotations

import argparse
import json

from app.services.control_plane_assurance_evidence_package_signing import verify_signed_tenant_evidence_package_chain


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify signed tenant evidence package chain")
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    result = verify_signed_tenant_evidence_package_chain(tenant_code=args.tenant_code, limit=args.limit)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
