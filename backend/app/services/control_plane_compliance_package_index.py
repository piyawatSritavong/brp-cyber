from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.control_plane_assurance_contracts import evaluate_assurance_contract
from app.services.control_plane_assurance_delivery_proof import signed_delivery_proof_status
from app.services.control_plane_assurance_digest_signing import signed_tenant_risk_bulletin_status
from app.services.control_plane_assurance_slo import assurance_slo_breach_history
from app.services.control_plane_verifier_kit import tenant_verifier_kit_status
from app.services.redis_client import redis_client

COMPLIANCE_PACKAGE_INDEX_STREAM_PREFIX = "control_plane_compliance_package_index"


def _stream_key(tenant_code: str) -> str:
    return f"{COMPLIANCE_PACKAGE_INDEX_STREAM_PREFIX}:{tenant_code.lower().strip()}"


def export_tenant_compliance_package_index(
    tenant_id: Any,
    tenant_code: str,
    destination_dir: str = "./tmp/compliance/evidence_package_index",
    limit: int = 100,
) -> dict[str, Any]:
    contract = evaluate_assurance_contract(tenant_id, tenant_code, limit=limit)
    bulletin = signed_tenant_risk_bulletin_status(tenant_code, limit=1)
    proof = signed_delivery_proof_status(tenant_code, limit=1)
    breaches = assurance_slo_breach_history(tenant_code, limit=limit)
    verifier_kit = tenant_verifier_kit_status(tenant_code, limit=1)

    package = {
        "tenant_id": str(tenant_id),
        "tenant_code": tenant_code,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "components": {
            "assurance_contract_eval": contract,
            "signed_bulletin_latest": (bulletin.get("rows", [{}]) or [{}])[0],
            "signed_delivery_proof_latest": (proof.get("rows", [{}]) or [{}])[0],
            "slo_breach_latest": (breaches.get("rows", [{}]) or [{}])[0],
            "verifier_kit_latest": (verifier_kit.get("rows", [{}]) or [{}])[0],
        },
    }

    root = Path(destination_dir)
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    target = root / f"compliance_evidence_package_index_{tenant_code}_{ts}.json"
    target.write_text(json.dumps(package, ensure_ascii=True, indent=2), encoding="utf-8")

    record = {
        "tenant_id": str(tenant_id),
        "tenant_code": tenant_code,
        "generated_at": package["generated_at"],
        "path": str(target),
    }
    event_id = redis_client.xadd(_stream_key(tenant_code), record, maxlen=50000, approximate=True)
    return {"status": "exported", "tenant_code": tenant_code, "index_id": event_id, "path": str(target), "package": package}


def tenant_compliance_package_index_status(tenant_code: str, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_stream_key(tenant_code), count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        rows.append(row)
    return {"tenant_code": tenant_code, "count": len(rows), "rows": rows}
