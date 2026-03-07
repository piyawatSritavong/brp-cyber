from __future__ import annotations

import argparse
import json

from app.db.models import Tenant
from app.db.session import SessionLocal
from app.services.control_plane_external_verifier_attestation import compute_zero_trust_attestation


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate zero-trust attestation results")
    parser.add_argument("--tenant-code", default="")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--freshness-hours", type=int, default=24)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = db.query(Tenant)
        if args.tenant_code:
            query = query.filter(Tenant.tenant_code == args.tenant_code)
        tenants = query.all()

        rows = []
        for tenant in tenants:
            result = compute_zero_trust_attestation(
                tenant_code=tenant.tenant_code,
                limit=args.limit,
                freshness_hours=args.freshness_hours,
            )
            rows.append(
                {
                    "tenant_code": tenant.tenant_code,
                    "trusted": result.get("trusted", False),
                    "status": result.get("status", "unknown"),
                }
            )

        print(json.dumps({"count": len(rows), "rows": rows}, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
