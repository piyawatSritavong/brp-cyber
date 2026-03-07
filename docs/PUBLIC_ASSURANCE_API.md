# Public Assurance API

Public endpoints for external observers, procurement teams, and independent reviewers.
All endpoints are read-only and do not require control-plane admin scopes.

## Endpoints

- `GET /assurance/public/summary`
  - Latest assurance snapshot from audit-pack, publication, transparency, and legal evidence streams.

- `GET /assurance/public/transparency?limit=100`
  - Latest transparency entries (`entry_hash`, `prev_hash`, timestamp).

- `GET /assurance/public/orchestration/objectives?limit=1000`
  - Aggregated Red/Blue/Purple objective-gate signal across recent tenant snapshots.

- `GET /assurance/public/orchestration/readiness?limit=1000`
  - Alias of orchestration objective endpoint for readiness-focused consumers.

- `GET /assurance/public/signed-summary?limit=1`
  - Latest signed public assurance snapshot metadata (signature chain status).

- `GET /assurance/public/signed-summary/verify?limit=1000`
  - Signature-chain verification result for signed assurance snapshots.

- `GET /assurance/public/tenant/{tenant_code}/bulletin?limit=1`
  - Latest signed tenant risk bulletin metadata for customer-facing sharing.

- `GET /assurance/public/tenant/{tenant_code}/bulletin/verify?limit=1000`
  - Signature-chain verification result for tenant bulletin stream.

- `GET /assurance/public/tenant/{tenant_code}/delivery-proof?limit=1`
  - Latest signed delivery-proof metadata for tenant bulletin delivery evidence.

- `GET /assurance/public/tenant/{tenant_code}/delivery-proof/verify?limit=1000`
  - Signature-chain verification result for tenant delivery-proof stream.

- `GET /assurance/public/tenant/{tenant_code}/evidence-package?limit=1`
  - Latest one-click compliance evidence package index metadata for tenant.

- `GET /assurance/public/tenant/{tenant_code}/evidence-package/signed?limit=1`
  - Latest signed evidence package metadata with tenant-specific signature chain state.

- `GET /assurance/public/tenant/{tenant_code}/evidence-package/signed/verify?limit=1000`
  - Signature-chain verification result for signed tenant evidence package stream.

- `GET /assurance/public/tenant/{tenant_code}/zero-trust-attestation?limit=1`
  - Latest tenant zero-trust attestation row combining internal/external verifier trust signals.

- `GET /assurance/public/zero-trust/overview?limit=200`
  - Cross-tenant zero-trust summary (`trusted_tenants`, `untrusted_tenants`) for external reviewers.

- `POST /assurance/public/verifier/import/{tenant_code}`
  - External verifier import endpoint requiring `X-Verifier-Token` header.

- `GET /assurance/public/tenant/{tenant_code}/external-verifier-receipts?limit=20`
  - Latest signed receipt entries generated from external verifier imports.

- `GET /assurance/public/tenant/{tenant_code}/external-verifier-receipts/verify?limit=1000`
  - Signature-chain verification result for verifier import receipt registry.

- `GET /assurance/public/orchestrator/rollout-verifier/{tenant_id}?limit=1000`
  - Rollout verifier bundle for external auditor handoff (`X-Rollout-Handoff-Token` required).

- `GET /assurance/public/orchestrator/rollout-verifier/{tenant_id}/verify?limit=1000`
  - Quick verify summary for rollout handoff verifier bundle (`X-Rollout-Handoff-Token` required).

- `GET /assurance/public/orchestrator/rollout-federation/digest?limit=1`
  - Latest signed federation executive digest metadata.

- `GET /assurance/public/orchestrator/rollout-federation/digest/verify?limit=1000`
  - Signature-chain verification result for signed federation digest stream.

- `GET /assurance/public/orchestrator/rollout-federation/verifier-bundle?limit=1000`
  - Public verifier bundle for federation digest consumers.

- `POST /assurance/public/orchestrator/rollout-federation/verifier-bundle/verify`
  - Bundle-level signature verification helper for external re-check.

- `GET /assurance/public/orchestrator/cost-guardrail/report?limit=1`
  - Latest signed orchestration cost-guardrail report metadata.

- `GET /assurance/public/orchestrator/cost-guardrail/report/verify?limit=1000`
  - Signature-chain verification result for signed cost-guardrail reports.

- `GET /assurance/public/orchestrator/cost-guardrail/verifier-bundle?limit=1000`
  - Public verifier bundle for cost-guardrail signed report consumers.

- `POST /assurance/public/orchestrator/cost-guardrail/verifier-bundle/verify`
  - Bundle-level signature verification helper for external cost report re-check.

- `GET /assurance/public/regulatory/frameworks`
  - Supported framework list and control counts.

- `GET /assurance/public/regulatory/{framework}`
  - Detailed control mapping for a framework (`soc2`, `iso27001`, `nist_csf`).

- `GET /assurance/public/regulatory/{framework}/scorecard`
  - Readiness score and control coverage ratio based on live trust signals.

- `GET /assurance/public/regulatory-overview`
  - Aggregated scorecards for all supported frameworks.

## Example

```bash
curl http://localhost:8000/assurance/public/regulatory/soc2/scorecard
```

## Enterprise Objective Alignment

This surface does not replace internal enforcement.
Enterprise readiness is still enforced by Objective Gate for Red/Blue/Purple orchestration before production promotion.
