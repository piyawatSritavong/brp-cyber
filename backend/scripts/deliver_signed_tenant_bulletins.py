from __future__ import annotations

import argparse
import json

from app.db.models import Tenant
from app.db.session import SessionLocal
from app.services.control_plane_assurance_bulletin_delivery import deliver_signed_tenant_bulletin


def main() -> None:
    parser = argparse.ArgumentParser(description="Deliver signed tenant bulletins to customer webhooks")
    parser.add_argument("--tenant-code", default="")
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = db.query(Tenant)
        if args.tenant_code:
            query = query.filter(Tenant.tenant_code == args.tenant_code)
        tenants = query.all()

        rows = []
        for tenant in tenants:
            result = deliver_signed_tenant_bulletin(tenant_code=tenant.tenant_code, limit=args.limit)
            rows.append({"tenant_code": tenant.tenant_code, "status": result.get("status", "unknown")})

        print(json.dumps({"count": len(rows), "rows": rows}, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
