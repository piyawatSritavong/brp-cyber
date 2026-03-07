from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Tenant
from app.services.control_plane_assurance_delivery_proof import (
    signed_delivery_proof_status,
    verify_signed_delivery_proof_chain,
)


def assurance_delivery_proof_index(db: Session, limit: int = 500) -> dict[str, Any]:
    tenants = db.query(Tenant).limit(max(1, limit)).all()
    rows: list[dict[str, Any]] = []

    for tenant in tenants:
        tenant_code = tenant.tenant_code
        status = signed_delivery_proof_status(tenant_code=tenant_code, limit=1)
        latest = status.get("rows", [{}])[0] if status.get("rows") else {}
        verify = verify_signed_delivery_proof_chain(tenant_code=tenant_code, limit=1000)

        rows.append(
            {
                "tenant_id": str(tenant.id),
                "tenant_code": tenant_code,
                "has_proof": bool(status.get("count", 0) > 0),
                "latest_snapshot_id": latest.get("id", ""),
                "latest_generated_at": latest.get("generated_at", ""),
                "latest_receipt_status": latest.get("receipt_status", ""),
                "proof_chain_valid": bool(verify.get("valid", False)),
            }
        )

    rows.sort(key=lambda row: (not row["proof_chain_valid"], not row["has_proof"], row["tenant_code"]))
    valid_count = len([r for r in rows if r["proof_chain_valid"]])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "valid_chain_count": valid_count,
        "invalid_chain_count": len(rows) - valid_count,
        "rows": rows,
    }


def export_assurance_delivery_proof_index(
    db: Session,
    destination_dir: str = "./tmp/compliance/assurance_proof_index",
    limit: int = 500,
) -> dict[str, Any]:
    index = assurance_delivery_proof_index(db, limit=limit)
    root = Path(destination_dir)
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    target = root / f"assurance_delivery_proof_index_{ts}.json"
    target.write_text(json.dumps(index, ensure_ascii=True, indent=2), encoding="utf-8")
    return {"status": "exported", "path": str(target), "index": index}
