from __future__ import annotations

import argparse
import json

from app.db.models import Tenant
from app.db.session import SessionLocal
from app.services.control_plane_assurance_remediation import remediate_assurance_breach


def main() -> None:
    parser = argparse.ArgumentParser(description="Run assurance contract remediation across tenants")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--auto-apply", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        rows = []
        for tenant in db.query(Tenant).all():
            result = remediate_assurance_breach(
                tenant_id=tenant.id,
                tenant_code=tenant.tenant_code,
                limit=args.limit,
                auto_apply=args.auto_apply,
            )
            rows.append(
                {
                    "tenant_id": str(tenant.id),
                    "tenant_code": tenant.tenant_code,
                    "status": result.get("status", "unknown"),
                    "actions": len(result.get("actions", [])),
                }
            )
        print(json.dumps({"count": len(rows), "rows": rows}, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
