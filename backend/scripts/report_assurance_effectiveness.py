from __future__ import annotations

import json

from app.db.models import Tenant
from app.db.session import SessionLocal
from app.services.control_plane_assurance_remediation import assurance_remediation_effectiveness


def main() -> None:
    db = SessionLocal()
    try:
        rows = []
        for tenant in db.query(Tenant).all():
            score = assurance_remediation_effectiveness(tenant.tenant_code, limit=500)
            rows.append(
                {
                    "tenant_id": str(tenant.id),
                    "tenant_code": tenant.tenant_code,
                    "count": int(score.get("count", 0)),
                    "average_effectiveness_delta": float(score.get("average_effectiveness_delta", 0.0)),
                    "rollback_batches": int(score.get("rollback_batches", 0)),
                }
            )
        print(json.dumps({"count": len(rows), "rows": rows}, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
