from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.control_plane_audit_pack_attestation import (
    MANIFEST_ATTESTATION_BUNDLE_NAME,
    create_audit_pack_manifest_attestation,
    verify_audit_pack_manifest_attestation_bundle,
)
from app.services.control_plane_compliance import build_control_plane_compliance_evidence
from app.services.control_plane_governance import governance_dashboard
from app.services.control_plane_governance_attestation import (
    create_governance_attestation,
    export_latest_governance_attestation,
    verify_detached_attestation_bundle,
)
from app.services.redis_client import redis_client

AUDIT_PACK_STREAM_KEY = "control_plane_external_audit_pack"


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> tuple[str, int]:
    encoded = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
    path.write_bytes(encoded)
    return _sha256_bytes(encoded), len(encoded)


def generate_external_audit_pack(
    limit: int = 5000,
    destination_dir: str = "./tmp/compliance/audit_packs",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    pack_id = f"audit-pack-{now.strftime('%Y%m%d%H%M%S')}"

    root = Path(destination_dir)
    pack_dir = root / pack_id
    pack_dir.mkdir(parents=True, exist_ok=True)

    compliance = build_control_plane_compliance_evidence()
    governance = governance_dashboard(limit=limit)

    # Ensure attestation chain grows and export detached bundle for external verification.
    create_governance_attestation(limit=limit)
    exported = export_latest_governance_attestation(destination_dir=str(pack_dir))

    compliance_path = pack_dir / "control_plane_compliance_evidence.json"
    governance_path = pack_dir / "control_plane_governance_report.json"

    compliance_hash, compliance_size = _write_json(compliance_path, compliance)
    governance_hash, governance_size = _write_json(governance_path, governance)

    attestation_path = Path(str(exported.get("path", ""))) if exported.get("status") == "exported" else None
    if attestation_path is None or not attestation_path.exists():
        return {"status": "failed", "reason": "attestation_export_failed"}

    attestation_hash = _sha256_file(attestation_path)
    attestation_size = attestation_path.stat().st_size

    bundle = exported.get("bundle", {}) if isinstance(exported.get("bundle"), dict) else {}
    verify_bundle = verify_detached_attestation_bundle(bundle=bundle) if bundle else {"valid": False}

    files = [
        {
            "name": compliance_path.name,
            "path": str(compliance_path),
            "sha256": compliance_hash,
            "size_bytes": compliance_size,
        },
        {
            "name": governance_path.name,
            "path": str(governance_path),
            "sha256": governance_hash,
            "size_bytes": governance_size,
        },
        {
            "name": attestation_path.name,
            "path": str(attestation_path),
            "sha256": attestation_hash,
            "size_bytes": attestation_size,
        },
    ]

    manifest = {
        "pack_id": pack_id,
        "generated_at": now.isoformat(),
        "scope": "control_plane_external_audit_pack",
        "overall_pass": bool(compliance.get("overall_pass", False)) and bool(verify_bundle.get("valid", False)),
        "checks": {
            "compliance_overall_pass": bool(compliance.get("overall_pass", False)),
            "attestation_bundle_valid": bool(verify_bundle.get("valid", False)),
        },
        "artifacts": files,
    }

    manifest_path = pack_dir / "manifest.json"
    manifest_hash, manifest_size = _write_json(manifest_path, manifest)

    manifest_attestation = create_audit_pack_manifest_attestation(pack_id=pack_id, manifest_path=str(manifest_path))
    if manifest_attestation.get("status") != "attested":
        return {
            "status": "failed",
            "reason": "manifest_attestation_failed",
            "manifest_path": str(manifest_path),
            "details": manifest_attestation,
        }

    manifest_attestation_path = Path(str(manifest_attestation.get("path", "")))
    if not manifest_attestation_path.exists():
        return {
            "status": "failed",
            "reason": "manifest_attestation_export_failed",
            "manifest_path": str(manifest_path),
        }

    manifest_attestation_bundle = (
        manifest_attestation.get("bundle", {}) if isinstance(manifest_attestation.get("bundle"), dict) else {}
    )
    verify_manifest_attestation = (
        verify_audit_pack_manifest_attestation_bundle(
            bundle=manifest_attestation_bundle,
            expected_manifest_path=str(manifest_path),
        )
        if manifest_attestation_bundle
        else {"valid": False, "reason": "bundle_missing"}
    )
    if not verify_manifest_attestation.get("valid", False):
        return {
            "status": "failed",
            "reason": "manifest_attestation_invalid",
            "manifest_path": str(manifest_path),
            "details": verify_manifest_attestation,
        }

    manifest_attestation_hash = _sha256_file(manifest_attestation_path)
    manifest_attestation_size = manifest_attestation_path.stat().st_size
    overall_pass = bool(manifest["overall_pass"]) and bool(verify_manifest_attestation.get("valid", False))

    summary = {
        "status": "success",
        "pack_id": pack_id,
        "pack_dir": str(pack_dir),
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_hash,
        "manifest_size_bytes": manifest_size,
        "manifest_attestation_id": manifest_attestation.get("attestation_id", ""),
        "manifest_attestation_path": str(manifest_attestation_path),
        "manifest_attestation_sha256": manifest_attestation_hash,
        "manifest_attestation_size_bytes": manifest_attestation_size,
        "manifest_attestation_valid": bool(verify_manifest_attestation.get("valid", False)),
        "overall_pass": overall_pass,
    }

    redis_client.xadd(
        AUDIT_PACK_STREAM_KEY,
        {
            "pack_id": pack_id,
            "generated_at": manifest["generated_at"],
            "pack_dir": str(pack_dir),
            "manifest_path": str(manifest_path),
            "manifest_sha256": manifest_hash,
            "manifest_attestation_id": str(manifest_attestation.get("attestation_id", "")),
            "manifest_attestation_path": str(manifest_attestation_path),
            "manifest_attestation_sha256": manifest_attestation_hash,
            "manifest_attestation_valid": "1" if verify_manifest_attestation.get("valid", False) else "0",
            "overall_pass": "1" if overall_pass else "0",
        },
        maxlen=50000,
        approximate=True,
    )

    return summary


def audit_pack_status(limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(AUDIT_PACK_STREAM_KEY, count=max(1, limit))
    rows: list[dict[str, Any]] = []

    for event_id, fields in entries:
        row = {"id": event_id}
        row.update(fields)
        row["overall_pass"] = str(fields.get("overall_pass", "0")) == "1"
        row["manifest_attestation_valid"] = str(fields.get("manifest_attestation_valid", "0")) == "1"
        rows.append(row)

    return {"count": len(rows), "rows": rows}


def verify_external_audit_pack(manifest_path: str) -> dict[str, Any]:
    target = Path(manifest_path)
    if not target.exists():
        return {"status": "not_found", "manifest_path": manifest_path}

    try:
        manifest = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "status": "failed",
            "manifest_path": manifest_path,
            "valid": False,
            "failure_count": 1,
            "failures": [{"file": manifest_path, "reason": "manifest_json_invalid"}],
        }

    artifacts = manifest.get("artifacts", []) if isinstance(manifest, dict) else []

    failures: list[dict[str, str]] = []
    for artifact in artifacts:
        file_path = Path(str(artifact.get("path", "")))
        expected_hash = str(artifact.get("sha256", ""))

        if not file_path.exists():
            failures.append({"file": str(file_path), "reason": "missing"})
            continue

        actual_hash = _sha256_file(file_path)
        if actual_hash != expected_hash:
            failures.append({"file": str(file_path), "reason": "sha256_mismatch"})

    attestation_path = target.parent / MANIFEST_ATTESTATION_BUNDLE_NAME
    manifest_attestation_valid = False
    manifest_attestation_sha256 = ""

    if not attestation_path.exists():
        failures.append({"file": str(attestation_path), "reason": "manifest_attestation_missing"})
    else:
        manifest_attestation_sha256 = _sha256_file(attestation_path)
        try:
            bundle = json.loads(attestation_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            failures.append({"file": str(attestation_path), "reason": "manifest_attestation_json_invalid"})
        else:
            manifest_attestation_result = verify_audit_pack_manifest_attestation_bundle(
                bundle=bundle,
                expected_manifest_path=str(target),
            )
            manifest_attestation_valid = bool(manifest_attestation_result.get("valid", False))
            if not manifest_attestation_valid:
                failures.append(
                    {
                        "file": str(attestation_path),
                        "reason": f"manifest_attestation_{manifest_attestation_result.get('reason', 'invalid')}",
                    }
                )

    manifest_hash = _sha256_file(target)
    return {
        "status": "verified" if not failures else "failed",
        "manifest_path": str(target),
        "manifest_sha256": manifest_hash,
        "manifest_attestation_path": str(attestation_path),
        "manifest_attestation_sha256": manifest_attestation_sha256,
        "manifest_attestation_valid": manifest_attestation_valid,
        "valid": len(failures) == 0,
        "failure_count": len(failures),
        "failures": failures,
    }
