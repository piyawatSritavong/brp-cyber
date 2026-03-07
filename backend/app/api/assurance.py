from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Header, HTTPException

from app.services.control_plane_public_assurance import (
    public_assurance_regulatory_overview,
    public_assurance_summary,
)
from app.services.control_plane_orchestration_assurance import orchestration_objectives_status
from app.services.control_plane_public_assurance_signing import (
    signed_public_assurance_status,
    verify_signed_public_assurance_chain,
)
from app.services.control_plane_assurance_digest_signing import (
    signed_tenant_risk_bulletin_status,
    verify_signed_tenant_risk_bulletin_chain,
)
from app.services.control_plane_assurance_delivery_proof import (
    signed_delivery_proof_status,
    verify_signed_delivery_proof_chain,
)
from app.services.control_plane_compliance_package_index import tenant_compliance_package_index_status
from app.services.control_plane_assurance_evidence_package_signing import (
    signed_tenant_evidence_package_status,
    verify_signed_tenant_evidence_package_chain,
)
from app.services.control_plane_external_verifier_attestation import (
    import_external_verifier_bundle,
    verifier_receipt_status,
    verify_verifier_receipt_chain,
    zero_trust_attestation_status,
    zero_trust_overview,
)
from app.services.control_plane_verifier_registry import verify_verifier_token
from app.services.control_plane_regulatory_profiles import (
    list_regulatory_frameworks,
    regulatory_profile,
    regulatory_scorecard,
)
from app.services.control_plane_rollout_handoff_federation_signing import (
    public_rollout_handoff_federation_digest_bundle,
    signed_rollout_handoff_federation_digest_status,
    verify_signed_rollout_handoff_federation_digest_bundle,
    verify_signed_rollout_handoff_federation_digest_chain,
)
from app.services.control_plane_orchestration_cost_guardrail_signing import (
    public_orchestration_cost_guardrail_report_bundle,
    signed_orchestration_cost_guardrail_report_status,
    verify_signed_orchestration_cost_guardrail_report_bundle,
    verify_signed_orchestration_cost_guardrail_report_chain,
)
from app.services.control_plane_transparency import transparency_status
from app.services.orchestrator import public_rollout_verifier_bundle
from app.services.rollout_handoff_auth import handoff_allows_tenant, verify_rollout_handoff_token

router = APIRouter(prefix="/assurance/public", tags=["assurance-public"])


@router.get("/summary")
def summary() -> dict[str, object]:
    return public_assurance_summary()


@router.get("/transparency")
def transparency(limit: int = 100) -> dict[str, object]:
    return transparency_status(limit=limit)


@router.get("/orchestration/objectives")
@router.get("/orchestration/readiness")
def orchestration_objectives(limit: int = 1000) -> dict[str, object]:
    return orchestration_objectives_status(limit=limit)


@router.get("/signed-summary")
def signed_summary(limit: int = 1) -> dict[str, object]:
    return signed_public_assurance_status(limit=limit)


@router.get("/signed-summary/verify")
def signed_summary_verify(limit: int = 1000) -> dict[str, object]:
    return verify_signed_public_assurance_chain(limit=limit)


@router.get("/tenant/{tenant_code}/bulletin")
def tenant_bulletin(tenant_code: str, limit: int = 1) -> dict[str, object]:
    return signed_tenant_risk_bulletin_status(tenant_code=tenant_code, limit=limit)


@router.get("/tenant/{tenant_code}/bulletin/verify")
def tenant_bulletin_verify(tenant_code: str, limit: int = 1000) -> dict[str, object]:
    return verify_signed_tenant_risk_bulletin_chain(tenant_code=tenant_code, limit=limit)


@router.get("/tenant/{tenant_code}/delivery-proof")
def tenant_delivery_proof(tenant_code: str, limit: int = 1) -> dict[str, object]:
    return signed_delivery_proof_status(tenant_code=tenant_code, limit=limit)


@router.get("/tenant/{tenant_code}/delivery-proof/verify")
def tenant_delivery_proof_verify(tenant_code: str, limit: int = 1000) -> dict[str, object]:
    return verify_signed_delivery_proof_chain(tenant_code=tenant_code, limit=limit)


@router.get("/tenant/{tenant_code}/evidence-package")
def tenant_evidence_package(tenant_code: str, limit: int = 1) -> dict[str, object]:
    return tenant_compliance_package_index_status(tenant_code=tenant_code, limit=limit)


@router.get("/tenant/{tenant_code}/evidence-package/signed")
def tenant_evidence_package_signed(tenant_code: str, limit: int = 1) -> dict[str, object]:
    return signed_tenant_evidence_package_status(tenant_code=tenant_code, limit=limit)


@router.get("/tenant/{tenant_code}/evidence-package/signed/verify")
def tenant_evidence_package_signed_verify(tenant_code: str, limit: int = 1000) -> dict[str, object]:
    return verify_signed_tenant_evidence_package_chain(tenant_code=tenant_code, limit=limit)


@router.get("/tenant/{tenant_code}/zero-trust-attestation")
def tenant_zero_trust_attestation(tenant_code: str, limit: int = 1) -> dict[str, object]:
    return zero_trust_attestation_status(tenant_code=tenant_code, limit=limit)


@router.get("/zero-trust/overview")
def zero_trust_summary(limit: int = 200) -> dict[str, object]:
    return zero_trust_overview(limit=limit)


@router.post("/verifier/import/{tenant_code}")
def verifier_import(
    tenant_code: str,
    payload: dict[str, object] = Body(default_factory=dict),
    x_verifier_token: str = Header(default="", alias="X-Verifier-Token"),
    x_verifier_source: str = Header(default="", alias="X-Verifier-Source"),
) -> dict[str, object]:
    verified = verify_verifier_token(token=x_verifier_token, tenant_code=tenant_code)
    if not verified.get("valid"):
        raise HTTPException(status_code=403, detail=f"forbidden_verifier:{verified.get('reason', 'invalid')}")
    source = x_verifier_source.strip() or str(verified.get("verifier_name", "external_verifier"))
    return import_external_verifier_bundle(tenant_code=tenant_code, verifier_payload=payload, source=source)


@router.get("/tenant/{tenant_code}/external-verifier-receipts")
def tenant_external_verifier_receipts(tenant_code: str, limit: int = 20) -> dict[str, object]:
    return verifier_receipt_status(tenant_code=tenant_code, limit=limit)


@router.get("/tenant/{tenant_code}/external-verifier-receipts/verify")
def tenant_external_verifier_receipts_verify(tenant_code: str, limit: int = 1000) -> dict[str, object]:
    return verify_verifier_receipt_chain(tenant_code=tenant_code, limit=limit)


@router.get("/orchestrator/rollout-verifier/{tenant_id}")
def orchestrator_rollout_verifier_bundle(
    tenant_id: UUID,
    limit: int = 1000,
    x_rollout_handoff_token: str = Header(default="", alias="X-Rollout-Handoff-Token"),
    x_forwarded_for: str = Header(default="", alias="X-Forwarded-For"),
) -> dict[str, object]:
    verified = verify_rollout_handoff_token(
        x_rollout_handoff_token,
        source_ip=x_forwarded_for,
        consume=True,
    )
    if not verified.get("valid"):
        raise HTTPException(status_code=403, detail=f"forbidden_rollout_handoff:{verified.get('reason', 'invalid')}")
    if not handoff_allows_tenant(verified, tenant_id):
        raise HTTPException(status_code=403, detail="forbidden_rollout_handoff:tenant_scope")
    return public_rollout_verifier_bundle(tenant_id=tenant_id, limit=limit)


@router.get("/orchestrator/rollout-verifier/{tenant_id}/verify")
def orchestrator_rollout_verifier_verify(
    tenant_id: UUID,
    limit: int = 1000,
    x_rollout_handoff_token: str = Header(default="", alias="X-Rollout-Handoff-Token"),
    x_forwarded_for: str = Header(default="", alias="X-Forwarded-For"),
) -> dict[str, object]:
    verified = verify_rollout_handoff_token(
        x_rollout_handoff_token,
        source_ip=x_forwarded_for,
        consume=True,
    )
    if not verified.get("valid"):
        raise HTTPException(status_code=403, detail=f"forbidden_rollout_handoff:{verified.get('reason', 'invalid')}")
    if not handoff_allows_tenant(verified, tenant_id):
        raise HTTPException(status_code=403, detail="forbidden_rollout_handoff:tenant_scope")
    bundle = public_rollout_verifier_bundle(tenant_id=tenant_id, limit=limit)
    return {
        "tenant_id": str(tenant_id),
        "valid": bool(bundle.get("verify", {}).get("valid", False)),
        "checked": int(bundle.get("verify", {}).get("checked", 0) or 0),
        "last_signature": str(bundle.get("verify", {}).get("last_signature", "")),
    }


@router.get("/orchestrator/rollout-federation/digest")
def orchestrator_rollout_federation_digest(limit: int = 1) -> dict[str, object]:
    return signed_rollout_handoff_federation_digest_status(limit=limit)


@router.get("/orchestrator/rollout-federation/digest/verify")
def orchestrator_rollout_federation_digest_verify(limit: int = 1000) -> dict[str, object]:
    return verify_signed_rollout_handoff_federation_digest_chain(limit=limit)


@router.get("/orchestrator/rollout-federation/verifier-bundle")
def orchestrator_rollout_federation_verifier_bundle(limit: int = 1000) -> dict[str, object]:
    return public_rollout_handoff_federation_digest_bundle(limit=limit)


@router.post("/orchestrator/rollout-federation/verifier-bundle/verify")
def orchestrator_rollout_federation_verifier_bundle_verify(payload: dict[str, object] = Body(default_factory=dict)) -> dict[str, object]:
    return verify_signed_rollout_handoff_federation_digest_bundle(dict(payload))


@router.get("/orchestrator/cost-guardrail/report")
def orchestrator_cost_guardrail_report(limit: int = 1) -> dict[str, object]:
    return signed_orchestration_cost_guardrail_report_status(limit=limit)


@router.get("/orchestrator/cost-guardrail/report/verify")
def orchestrator_cost_guardrail_report_verify(limit: int = 1000) -> dict[str, object]:
    return verify_signed_orchestration_cost_guardrail_report_chain(limit=limit)


@router.get("/orchestrator/cost-guardrail/verifier-bundle")
def orchestrator_cost_guardrail_verifier_bundle(limit: int = 1000) -> dict[str, object]:
    return public_orchestration_cost_guardrail_report_bundle(limit=limit)


@router.post("/orchestrator/cost-guardrail/verifier-bundle/verify")
def orchestrator_cost_guardrail_verifier_bundle_verify(payload: dict[str, object] = Body(default_factory=dict)) -> dict[str, object]:
    return verify_signed_orchestration_cost_guardrail_report_bundle(dict(payload))


@router.get("/frameworks")
@router.get("/regulatory/frameworks")
def frameworks() -> dict[str, object]:
    return list_regulatory_frameworks()


@router.get("/regulatory/{framework}")
def framework_profile(framework: str) -> dict[str, object]:
    return regulatory_profile(framework)


@router.get("/scorecard/{framework}")
@router.get("/regulatory/{framework}/scorecard")
def framework_scorecard(framework: str) -> dict[str, object]:
    return regulatory_scorecard(framework)


@router.get("/scorecards")
@router.get("/regulatory-overview")
def scorecards() -> dict[str, object]:
    return public_assurance_regulatory_overview()
