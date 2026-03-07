from __future__ import annotations

import json

from app.db.models import Tenant
from app.db.session import SessionLocal
from app.services.control_plane_assurance_policy_packs import upsert_assurance_policy_pack


def main() -> None:
    db = SessionLocal()
    try:
        rows = []
        for tenant in db.query(Tenant).all():
            result = upsert_assurance_policy_pack(
                tenant.tenant_code,
                {
                    "owner": "security",
                    "auto_apply_actions": ["tighten_blue_threshold"],
                    "force_approval_actions": ["enable_approval_mode"],
                    "blocked_actions": [],
                    "max_auto_apply_actions_per_run": 1,
                    "notify_only": False,
                },
            )
            rows.append(
                {
                    "tenant_id": str(tenant.id),
                    "tenant_code": tenant.tenant_code,
                    "status": result.get("status", "unknown"),
                }
            )
        print(json.dumps({"count": len(rows), "rows": rows}, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
