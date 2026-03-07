from __future__ import annotations

import argparse
import json

from app.services.control_plane_assurance_digest_signing import (
    verify_signed_assurance_executive_digest_chain,
    verify_signed_tenant_risk_bulletin_chain,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify signed assurance digest chains")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--tenant-code", default="")
    args = parser.parse_args()

    rows = {"executive_digest": verify_signed_assurance_executive_digest_chain(limit=args.limit)}
    if args.tenant_code:
        rows["tenant_bulletin"] = verify_signed_tenant_risk_bulletin_chain(args.tenant_code, limit=args.limit)
    print(json.dumps(rows, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
