from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import assurance as assurance_api
from app.main import app


def test_public_assurance_endpoints() -> None:
    orig_summary = assurance_api.public_assurance_summary
    orig_transparency = assurance_api.transparency_status
    orig_frameworks = assurance_api.list_regulatory_frameworks
    orig_profile = assurance_api.regulatory_profile
    orig_scorecard = assurance_api.regulatory_scorecard
    orig_overview = assurance_api.public_assurance_regulatory_overview
    orig_orchestration = assurance_api.orchestration_objectives_status
    orig_signed = assurance_api.signed_public_assurance_status
    orig_signed_verify = assurance_api.verify_signed_public_assurance_chain
    orig_bulletin = assurance_api.signed_tenant_risk_bulletin_status
    orig_bulletin_verify = assurance_api.verify_signed_tenant_risk_bulletin_chain
    orig_delivery_proof = assurance_api.signed_delivery_proof_status
    orig_delivery_proof_verify = assurance_api.verify_signed_delivery_proof_chain
    orig_evidence_package = assurance_api.tenant_compliance_package_index_status
    orig_evidence_package_signed = assurance_api.signed_tenant_evidence_package_status
    orig_evidence_package_signed_verify = assurance_api.verify_signed_tenant_evidence_package_chain
    orig_zero_trust_status = assurance_api.zero_trust_attestation_status
    orig_zero_trust_overview = assurance_api.zero_trust_overview
    orig_verify_verifier_token = assurance_api.verify_verifier_token
    orig_import_external = assurance_api.import_external_verifier_bundle
    orig_receipt_status = assurance_api.verifier_receipt_status
    orig_receipt_verify = assurance_api.verify_verifier_receipt_chain
    orig_rollout_handoff_verify = assurance_api.verify_rollout_handoff_token
    orig_rollout_handoff_allows = assurance_api.handoff_allows_tenant
    orig_rollout_bundle = assurance_api.public_rollout_verifier_bundle
    orig_fed_digest_status = assurance_api.signed_rollout_handoff_federation_digest_status
    orig_fed_digest_verify = assurance_api.verify_signed_rollout_handoff_federation_digest_chain
    orig_fed_bundle = assurance_api.public_rollout_handoff_federation_digest_bundle
    orig_fed_bundle_verify = assurance_api.verify_signed_rollout_handoff_federation_digest_bundle
    orig_cost_report_status = assurance_api.signed_orchestration_cost_guardrail_report_status
    orig_cost_report_verify = assurance_api.verify_signed_orchestration_cost_guardrail_report_chain
    orig_cost_bundle = assurance_api.public_orchestration_cost_guardrail_report_bundle
    orig_cost_bundle_verify = assurance_api.verify_signed_orchestration_cost_guardrail_report_bundle
    try:
        assurance_api.public_assurance_summary = lambda: {"status": "ok", "latest": {}}
        assurance_api.transparency_status = lambda limit=100: {"status": "ok", "count": 1, "rows": [{"entry_hash": "h1"}]}
        assurance_api.orchestration_objectives_status = lambda limit=1000: {
            "status": "ok",
            "sample_count": 2,
            "tenant_count": 2,
            "overall_pass_rate": 0.5,
            "enterprise_readiness": {"ready": False},
            "rows": [],
        }
        assurance_api.signed_public_assurance_status = lambda limit=1: {
            "count": 1,
            "last_signature": "sig-1",
            "rows": [{"id": "1-0", "enterprise_ready": False}],
        }
        assurance_api.verify_signed_public_assurance_chain = lambda limit=1000: {"valid": True, "checked": 1}
        assurance_api.signed_tenant_risk_bulletin_status = lambda tenant_code, limit=1: {
            "tenant_code": tenant_code,
            "count": 1,
            "rows": [{"id": "1-0"}],
        }
        assurance_api.verify_signed_tenant_risk_bulletin_chain = lambda tenant_code, limit=1000: {
            "tenant_code": tenant_code,
            "valid": True,
            "checked": 1,
        }
        assurance_api.signed_delivery_proof_status = lambda tenant_code, limit=1: {
            "tenant_code": tenant_code,
            "count": 1,
            "rows": [{"id": "p-1"}],
        }
        assurance_api.verify_signed_delivery_proof_chain = lambda tenant_code, limit=1000: {
            "tenant_code": tenant_code,
            "valid": True,
            "checked": 1,
        }
        assurance_api.tenant_compliance_package_index_status = lambda tenant_code, limit=1: {
            "tenant_code": tenant_code,
            "count": 1,
            "rows": [{"id": "e-1"}],
        }
        assurance_api.signed_tenant_evidence_package_status = lambda tenant_code, limit=1: {
            "tenant_code": tenant_code,
            "count": 1,
            "rows": [{"id": "se-1"}],
        }
        assurance_api.verify_signed_tenant_evidence_package_chain = lambda tenant_code, limit=1000: {
            "tenant_code": tenant_code,
            "valid": True,
            "checked": 1,
        }
        assurance_api.zero_trust_attestation_status = lambda tenant_code, limit=1: {
            "tenant_code": tenant_code,
            "count": 1,
            "rows": [{"id": "zt-1", "trusted": True}],
        }
        assurance_api.zero_trust_overview = lambda limit=200: {
            "count": 1,
            "trusted_tenants": 1,
            "untrusted_tenants": 0,
            "rows": [{"tenant_code": "acb", "trusted": True}],
        }
        assurance_api.verify_verifier_token = lambda token, tenant_code: {"valid": token == "good-token"}
        assurance_api.import_external_verifier_bundle = lambda tenant_code, verifier_payload, source="": {
            "status": "imported",
            "tenant_code": tenant_code,
            "event_id": "1-0",
        }
        assurance_api.verifier_receipt_status = lambda tenant_code, limit=20: {
            "tenant_code": tenant_code,
            "count": 1,
            "rows": [{"id": "r-1", "valid": True}],
        }
        assurance_api.verify_verifier_receipt_chain = lambda tenant_code, limit=1000: {
            "tenant_code": tenant_code,
            "valid": True,
            "checked": 1,
        }
        assurance_api.verify_rollout_handoff_token = lambda token, source_ip="", consume=False: {
            "valid": token == "good-rollout-token",
            "tenant_scope": str("00000000-0000-0000-0000-000000000001"),
        }
        assurance_api.handoff_allows_tenant = lambda verified, tenant_id: str(tenant_id) == "00000000-0000-0000-0000-000000000001"
        assurance_api.public_rollout_verifier_bundle = lambda tenant_id, limit=1000: {
            "tenant_id": str(tenant_id),
            "verify": {"valid": True, "checked": 2, "last_signature": "sig-last"},
            "evidence_count": 2,
            "decision_count": 1,
        }
        assurance_api.signed_rollout_handoff_federation_digest_status = lambda limit=1: {
            "count": 1,
            "last_signature": "fed-sig-1",
            "rows": [{"id": "f-1", "scope": "rollout_handoff_federation_executive_digest"}],
        }
        assurance_api.verify_signed_rollout_handoff_federation_digest_chain = lambda limit=1000: {
            "valid": True,
            "checked": 1,
            "last_signature": "fed-sig-1",
        }
        assurance_api.public_rollout_handoff_federation_digest_bundle = lambda limit=1000: {
            "scope": "rollout_handoff_federation_executive_digest",
            "status": {"count": 1},
            "verify": {"valid": True, "checked": 1},
            "latest": {"id": "f-1"},
        }
        assurance_api.verify_signed_rollout_handoff_federation_digest_bundle = lambda bundle: {
            "valid": bool(bundle.get("scope")),
            "reason": "ok",
        }
        assurance_api.signed_orchestration_cost_guardrail_report_status = lambda limit=1: {
            "count": 1,
            "last_signature": "cost-sig-1",
            "rows": [{"id": "c-1", "scope": "orchestration_cost_guardrail_report"}],
        }
        assurance_api.verify_signed_orchestration_cost_guardrail_report_chain = lambda limit=1000: {
            "valid": True,
            "checked": 1,
            "last_signature": "cost-sig-1",
        }
        assurance_api.public_orchestration_cost_guardrail_report_bundle = lambda limit=1000: {
            "scope": "orchestration_cost_guardrail_report",
            "status": {"count": 1},
            "verify": {"valid": True, "checked": 1},
            "latest": {"id": "c-1"},
        }
        assurance_api.verify_signed_orchestration_cost_guardrail_report_bundle = lambda bundle: {
            "valid": bool(bundle.get("scope")),
            "reason": "ok",
        }
        assurance_api.list_regulatory_frameworks = lambda: {
            "count": 1,
            "frameworks": [{"id": "soc2", "name": "SOC2", "control_count": 3}],
        }
        assurance_api.regulatory_profile = lambda framework: (
            {"status": "not_found", "framework": framework}
            if framework == "unknown"
            else {"status": "ok", "framework": framework, "control_count": 3, "controls": []}
        )
        assurance_api.regulatory_scorecard = lambda framework: {
            "status": "ok",
            "framework": framework,
            "readiness_score": 100,
            "coverage_ratio": 1.0,
        }
        assurance_api.public_assurance_regulatory_overview = lambda: {
            "status": "ok",
            "count": 1,
            "rows": [{"framework": "soc2", "readiness_score": 100}],
        }

        with TestClient(app) as client:
            summary = client.get("/assurance/public/summary")
            assert summary.status_code == 200
            assert summary.json()["status"] == "ok"

            transparency = client.get("/assurance/public/transparency?limit=10")
            assert transparency.status_code == 200
            assert transparency.json()["count"] == 1

            objectives = client.get("/assurance/public/orchestration/objectives?limit=10")
            assert objectives.status_code == 200
            assert objectives.json()["tenant_count"] == 2

            signed = client.get("/assurance/public/signed-summary")
            assert signed.status_code == 200
            assert signed.json()["count"] == 1

            signed_verify = client.get("/assurance/public/signed-summary/verify")
            assert signed_verify.status_code == 200
            assert signed_verify.json()["valid"] is True

            bulletin = client.get("/assurance/public/tenant/acb/bulletin")
            assert bulletin.status_code == 200
            assert bulletin.json()["tenant_code"] == "acb"

            bulletin_verify = client.get("/assurance/public/tenant/acb/bulletin/verify")
            assert bulletin_verify.status_code == 200
            assert bulletin_verify.json()["valid"] is True

            delivery_proof = client.get("/assurance/public/tenant/acb/delivery-proof")
            assert delivery_proof.status_code == 200
            assert delivery_proof.json()["count"] == 1

            delivery_proof_verify = client.get("/assurance/public/tenant/acb/delivery-proof/verify")
            assert delivery_proof_verify.status_code == 200
            assert delivery_proof_verify.json()["valid"] is True

            evidence_package = client.get("/assurance/public/tenant/acb/evidence-package")
            assert evidence_package.status_code == 200
            assert evidence_package.json()["count"] == 1

            evidence_package_signed = client.get("/assurance/public/tenant/acb/evidence-package/signed")
            assert evidence_package_signed.status_code == 200
            assert evidence_package_signed.json()["count"] == 1

            evidence_package_signed_verify = client.get("/assurance/public/tenant/acb/evidence-package/signed/verify")
            assert evidence_package_signed_verify.status_code == 200
            assert evidence_package_signed_verify.json()["valid"] is True

            zero_trust = client.get("/assurance/public/tenant/acb/zero-trust-attestation")
            assert zero_trust.status_code == 200
            assert zero_trust.json()["count"] == 1

            zero_trust_overview = client.get("/assurance/public/zero-trust/overview")
            assert zero_trust_overview.status_code == 200
            assert zero_trust_overview.json()["trusted_tenants"] == 1

            verifier_denied = client.post("/assurance/public/verifier/import/acb", json={"bundle_id": "b1"})
            assert verifier_denied.status_code == 403

            verifier_import = client.post(
                "/assurance/public/verifier/import/acb",
                json={"bundle_id": "b1", "valid": True},
                headers={"X-Verifier-Token": "good-token", "X-Verifier-Source": "auditor_x"},
            )
            assert verifier_import.status_code == 200
            assert verifier_import.json()["status"] == "imported"

            receipts = client.get("/assurance/public/tenant/acb/external-verifier-receipts")
            assert receipts.status_code == 200
            assert receipts.json()["count"] == 1

            receipts_verify = client.get("/assurance/public/tenant/acb/external-verifier-receipts/verify")
            assert receipts_verify.status_code == 200
            assert receipts_verify.json()["valid"] is True

            rollout_denied = client.get("/assurance/public/orchestrator/rollout-verifier/00000000-0000-0000-0000-000000000001")
            assert rollout_denied.status_code == 403

            rollout_bundle = client.get(
                "/assurance/public/orchestrator/rollout-verifier/00000000-0000-0000-0000-000000000001",
                headers={"X-Rollout-Handoff-Token": "good-rollout-token"},
            )
            assert rollout_bundle.status_code == 200
            assert rollout_bundle.json()["verify"]["valid"] is True

            rollout_verify = client.get(
                "/assurance/public/orchestrator/rollout-verifier/00000000-0000-0000-0000-000000000001/verify",
                headers={"X-Rollout-Handoff-Token": "good-rollout-token"},
            )
            assert rollout_verify.status_code == 200
            assert rollout_verify.json()["valid"] is True

            fed_digest = client.get("/assurance/public/orchestrator/rollout-federation/digest")
            assert fed_digest.status_code == 200
            assert fed_digest.json()["count"] == 1

            fed_digest_verify = client.get("/assurance/public/orchestrator/rollout-federation/digest/verify")
            assert fed_digest_verify.status_code == 200
            assert fed_digest_verify.json()["valid"] is True

            fed_bundle = client.get("/assurance/public/orchestrator/rollout-federation/verifier-bundle")
            assert fed_bundle.status_code == 200
            assert fed_bundle.json()["scope"] == "rollout_handoff_federation_executive_digest"

            fed_bundle_verify = client.post(
                "/assurance/public/orchestrator/rollout-federation/verifier-bundle/verify",
                json={"scope": "rollout_handoff_federation_executive_digest"},
            )
            assert fed_bundle_verify.status_code == 200
            assert fed_bundle_verify.json()["valid"] is True

            cost_report = client.get("/assurance/public/orchestrator/cost-guardrail/report")
            assert cost_report.status_code == 200
            assert cost_report.json()["count"] == 1

            cost_report_verify = client.get("/assurance/public/orchestrator/cost-guardrail/report/verify")
            assert cost_report_verify.status_code == 200
            assert cost_report_verify.json()["valid"] is True

            cost_bundle = client.get("/assurance/public/orchestrator/cost-guardrail/verifier-bundle")
            assert cost_bundle.status_code == 200
            assert cost_bundle.json()["scope"] == "orchestration_cost_guardrail_report"

            cost_bundle_verify = client.post(
                "/assurance/public/orchestrator/cost-guardrail/verifier-bundle/verify",
                json={"scope": "orchestration_cost_guardrail_report"},
            )
            assert cost_bundle_verify.status_code == 200
            assert cost_bundle_verify.json()["valid"] is True

            frameworks = client.get("/assurance/public/regulatory/frameworks")
            assert frameworks.status_code == 200
            assert frameworks.json()["count"] == 1

            profile = client.get("/assurance/public/regulatory/soc2")
            assert profile.status_code == 200
            assert profile.json()["status"] == "ok"

            scorecard = client.get("/assurance/public/regulatory/soc2/scorecard")
            assert scorecard.status_code == 200
            assert scorecard.json()["readiness_score"] == 100

            scorecards = client.get("/assurance/public/regulatory-overview")
            assert scorecards.status_code == 200
            assert scorecards.json()["count"] == 1

            not_found = client.get("/assurance/public/regulatory/unknown")
            assert not_found.status_code == 200
            assert not_found.json()["status"] == "not_found"
    finally:
        assurance_api.public_assurance_summary = orig_summary
        assurance_api.transparency_status = orig_transparency
        assurance_api.list_regulatory_frameworks = orig_frameworks
        assurance_api.regulatory_profile = orig_profile
        assurance_api.regulatory_scorecard = orig_scorecard
        assurance_api.public_assurance_regulatory_overview = orig_overview
        assurance_api.orchestration_objectives_status = orig_orchestration
        assurance_api.signed_public_assurance_status = orig_signed
        assurance_api.verify_signed_public_assurance_chain = orig_signed_verify
        assurance_api.signed_tenant_risk_bulletin_status = orig_bulletin
        assurance_api.verify_signed_tenant_risk_bulletin_chain = orig_bulletin_verify
        assurance_api.signed_delivery_proof_status = orig_delivery_proof
        assurance_api.verify_signed_delivery_proof_chain = orig_delivery_proof_verify
        assurance_api.tenant_compliance_package_index_status = orig_evidence_package
        assurance_api.signed_tenant_evidence_package_status = orig_evidence_package_signed
        assurance_api.verify_signed_tenant_evidence_package_chain = orig_evidence_package_signed_verify
        assurance_api.zero_trust_attestation_status = orig_zero_trust_status
        assurance_api.zero_trust_overview = orig_zero_trust_overview
        assurance_api.verify_verifier_token = orig_verify_verifier_token
        assurance_api.import_external_verifier_bundle = orig_import_external
        assurance_api.verifier_receipt_status = orig_receipt_status
        assurance_api.verify_verifier_receipt_chain = orig_receipt_verify
        assurance_api.verify_rollout_handoff_token = orig_rollout_handoff_verify
        assurance_api.handoff_allows_tenant = orig_rollout_handoff_allows
        assurance_api.public_rollout_verifier_bundle = orig_rollout_bundle
        assurance_api.signed_rollout_handoff_federation_digest_status = orig_fed_digest_status
        assurance_api.verify_signed_rollout_handoff_federation_digest_chain = orig_fed_digest_verify
        assurance_api.public_rollout_handoff_federation_digest_bundle = orig_fed_bundle
        assurance_api.verify_signed_rollout_handoff_federation_digest_bundle = orig_fed_bundle_verify
        assurance_api.signed_orchestration_cost_guardrail_report_status = orig_cost_report_status
        assurance_api.verify_signed_orchestration_cost_guardrail_report_chain = orig_cost_report_verify
        assurance_api.public_orchestration_cost_guardrail_report_bundle = orig_cost_bundle
        assurance_api.verify_signed_orchestration_cost_guardrail_report_bundle = orig_cost_bundle_verify
