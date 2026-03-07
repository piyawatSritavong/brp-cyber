from __future__ import annotations

import argparse
import json

from app.db.models import Tenant
from app.db.session import SessionLocal
from app.services.control_plane_assurance_bulletin_delivery import bulletin_delivery_receipts


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate bulletin delivery receipts report")
    parser.add_argument("--tenant-code", default="")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        query = db.query(Tenant)
        if args.tenant_code:
            query = query.filter(Tenant.tenant_code == args.tenant_code)
        tenants = query.all()

        rows = []
        for tenant in tenants:
            data = bulletin_delivery_receipts(tenant.tenant_code, limit=args.limit)
            latest = data.get("rows", [{}])[0] if data.get("rows") else {}
            rows.append(
                {
                    "tenant_code": tenant.tenant_code,
                    "receipt_count": data.get("count", 0),
                    "latest_status": latest.get("status", ""),
                    "latest_timestamp": latest.get("timestamp", ""),
                }
            )
        print(json.dumps({"count": len(rows), "rows": rows}, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
