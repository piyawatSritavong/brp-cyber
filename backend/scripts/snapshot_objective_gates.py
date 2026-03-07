from __future__ import annotations

import json

from app.db.models import Tenant
from app.db.session import SessionLocal
from app.services.enterprise.objective_gate import evaluate_and_persist_objective_gate


def main() -> None:
    db = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        rows = []
        for tenant in tenants:
            result = evaluate_and_persist_objective_gate(tenant.id)
            rows.append(
                {
                    "tenant_id": str(tenant.id),
                    "tenant_code": tenant.tenant_code,
                    "overall_pass": bool(result.get("overall_pass", False)),
                }
            )
        print(json.dumps({"count": len(rows), "rows": rows}, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
