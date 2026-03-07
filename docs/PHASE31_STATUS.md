# Phase 31 Status

- Phase: `Phase 31 - Verifier Policy Enforcement & Multi-Verifier Quorum`
- Status: `Completed`
- Last Updated: `2026-03-06`

## Scope
- Enforce tenant-specific external verifier policy in zero-trust attestation.
- Support multi-verifier quorum-based trust decisioning.

## Planned Deliverables
- [x] External verifier policy service (`upsert/get`) per tenant
- [x] Quorum-aware zero-trust attestation evaluation
- [x] Distinct-verifier support and allowlist policy controls
- [x] Control-plane APIs for policy lifecycle
- [x] Script/workflow support for policy automation
- [x] Tests covering quorum pass/fail behavior

## Implemented APIs
- `POST /control-plane/assurance/slo/{tenant_code}/external-verifier/policy/upsert`
- `GET /control-plane/assurance/slo/{tenant_code}/external-verifier/policy`
- `POST /control-plane/assurance/slo/{tenant_code}/zero-trust/attest?limit=&freshness_hours=`

## Notes
- Trusted decision now includes quorum requirement (`external_quorum_count >= external_min_quorum`) under tenant policy.
- Policy can restrict verifiers, enforce internal signature dependency, and require distinct verifier sources.
