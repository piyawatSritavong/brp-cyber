from __future__ import annotations

import json

from app.db.models import Tenant
from app.db.session import SessionLocal
from app.services.control_plane_assurance_contracts import evaluate_assurance_contract


def main() -> None:
    db = SessionLocal()
    try:
        rows = []
        for tenant in db.query(Tenant).all():
            result = evaluate_assurance_contract(tenant.id, tenant.tenant_code, limit=200)
            rows.append(
                {
                    "tenant_id": str(tenant.id),
                    "tenant_code": tenant.tenant_code,
                    "status": result.get("status", "unknown"),
                    "contract_pass": bool(result.get("evaluation", {}).get("contract_pass", False)),
                }
            )
        print(json.dumps({"count": len(rows), "rows": rows}, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
