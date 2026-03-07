from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.control_plane_assurance_delivery_proof import (
    signed_delivery_proof_status,
    verify_signed_delivery_proof_chain,
)
from app.services.control_plane_assurance_digest_signing import (
    signed_tenant_risk_bulletin_status,
    verify_signed_tenant_risk_bulletin_chain,
)
from app.services.redis_client import redis_client

VERIFIER_KIT_STREAM_PREFIX = "control_plane_verifier_kit"


def _stream_key(tenant_code: str) -> str:
    return f"{VERIFIER_KIT_STREAM_PREFIX}:{tenant_code.lower().strip()}"


def _build_readme(tenant_code: str, payload: dict[str, Any]) -> str:
    generated_at = payload.get("generated_at", "")
    return "\n".join(
        [
            f"# Verifier Kit: {tenant_code}",
            "",
            f"- Generated At (UTC): {generated_at}",
            f"- Tenant Code: {tenant_code}",
            "",
            "## Verification Commands",
            "```bash",
            f"cd backend && python scripts/verify_signed_assurance_digests.py --tenant-code {tenant_code}",
            f"cd backend && python scripts/verify_signed_delivery_proof.py --tenant-code {tenant_code}",
            "```",
            "",
            "## Snapshot",
            f"- Bulletin chain valid: {payload.get('bulletin_chain_valid', False)}",
            f"- Delivery proof chain valid: {payload.get('delivery_proof_chain_valid', False)}",
        ]
    )


def export_tenant_verifier_kit(
    tenant_code: str,
    destination_dir: str = "./tmp/compliance/verifier_kits",
    limit: int = 1000,
) -> dict[str, Any]:
    bulletin_status = signed_tenant_risk_bulletin_status(tenant_code, limit=1)
    proof_status = signed_delivery_proof_status(tenant_code, limit=1)
    bulletin_verify = verify_signed_tenant_risk_bulletin_chain(tenant_code, limit=max(1, limit))
    proof_verify = verify_signed_delivery_proof_chain(tenant_code, limit=max(1, limit))

    payload = {
        "tenant_code": tenant_code,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bulletin_latest": (bulletin_status.get("rows", [{}]) or [{}])[0],
        "delivery_proof_latest": (proof_status.get("rows", [{}]) or [{}])[0],
        "bulletin_chain_valid": bool(bulletin_verify.get("valid", False)),
        "delivery_proof_chain_valid": bool(proof_verify.get("valid", False)),
        "commands": [
            f"python scripts/verify_signed_assurance_digests.py --tenant-code {tenant_code}",
            f"python scripts/verify_signed_delivery_proof.py --tenant-code {tenant_code}",
        ],
    }

    root = Path(destination_dir)
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    kit_dir = root / f"verifier_kit_{tenant_code}_{ts}"
    kit_dir.mkdir(parents=True, exist_ok=True)

    index_path = kit_dir / "verifier_kit_index.json"
    readme_path = kit_dir / "README.md"
    index_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    readme_path.write_text(_build_readme(tenant_code, payload), encoding="utf-8")

    record = {
        "tenant_code": tenant_code,
        "generated_at": payload["generated_at"],
        "kit_dir": str(kit_dir),
        "index_path": str(index_path),
        "readme_path": str(readme_path),
        "bulletin_chain_valid": "1" if payload["bulletin_chain_valid"] else "0",
        "delivery_proof_chain_valid": "1" if payload["delivery_proof_chain_valid"] else "0",
    }
    event_id = redis_client.xadd(_stream_key(tenant_code), record, maxlen=50000, approximate=True)

    return {
        "status": "exported",
        "tenant_code": tenant_code,
        "kit_id": event_id,
        "kit_dir": str(kit_dir),
        "index_path": str(index_path),
        "readme_path": str(readme_path),
        "bulletin_chain_valid": payload["bulletin_chain_valid"],
        "delivery_proof_chain_valid": payload["delivery_proof_chain_valid"],
    }


def tenant_verifier_kit_status(tenant_code: str, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_stream_key(tenant_code), count=max(1, limit))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row: dict[str, Any] = {"id": event_id}
        row.update(fields)
        row["bulletin_chain_valid"] = str(fields.get("bulletin_chain_valid", "0")) == "1"
        row["delivery_proof_chain_valid"] = str(fields.get("delivery_proof_chain_valid", "0")) == "1"
        rows.append(row)
    return {"tenant_code": tenant_code, "count": len(rows), "rows": rows}
