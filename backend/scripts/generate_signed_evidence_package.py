from __future__ import annotations

import argparse
import json

from app.db.models import Tenant
from app.db.session import SessionLocal
from app.services.control_plane_assurance_evidence_package_signing import create_signed_tenant_evidence_package


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate signed tenant evidence package bundles")
    parser.add_argument("--destination-dir", default="./tmp/compliance/assurance_tenant_evidence_package_signed")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--tenant-code", default="")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = db.query(Tenant)
        if args.tenant_code:
            query = query.filter(Tenant.tenant_code == args.tenant_code)
        tenants = query.all()

        rows = []
        for tenant in tenants:
            result = create_signed_tenant_evidence_package(
                tenant_id=tenant.id,
                tenant_code=tenant.tenant_code,
                destination_dir=args.destination_dir,
                limit=args.limit,
            )
            rows.append({
                "tenant_code": tenant.tenant_code,
                "status": result.get("status", "unknown"),
                "snapshot_id": result.get("snapshot_id", ""),
            })

        print(json.dumps({"count": len(rows), "rows": rows}, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
