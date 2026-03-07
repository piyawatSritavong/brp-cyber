from __future__ import annotations

import argparse
import json

from app.db.models import Tenant
from app.db.session import SessionLocal
from app.services.control_plane_compliance_package_index import export_tenant_compliance_package_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Export tenant compliance evidence package index")
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--destination-dir", default="./tmp/compliance/evidence_package_index")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.tenant_code == args.tenant_code).first()
        if not tenant:
            raise SystemExit(f"tenant_not_found:{args.tenant_code}")
        result = export_tenant_compliance_package_index(
            tenant_id=tenant.id,
            tenant_code=tenant.tenant_code,
            destination_dir=args.destination_dir,
            limit=args.limit,
        )
        print(json.dumps(result, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
