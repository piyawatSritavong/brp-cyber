# Phase 28 Status

- Phase: `Phase 28 - Signed Tenant Evidence Package Chain & Public Verification`
- Status: `Completed`
- Last Updated: `2026-03-06`

## Scope
- Add tamper-evident signature chain for tenant evidence package exports
- Expose control-plane and public verification surfaces for signed evidence packages

## Planned Deliverables
- [x] Signed tenant evidence package service (`sign/status/verify`)
- [x] Control-plane APIs for signed evidence package operations
- [x] Public APIs for signed evidence package status + verification
- [x] Scripts/workflow for daily sign + verify automation
- [x] Tests for signing chain and assurance public endpoints

## Implemented APIs
- `POST /control-plane/assurance/slo/{tenant_code}/evidence-package/sign?destination_dir=&limit=`
- `GET /control-plane/assurance/slo/{tenant_code}/evidence-package/sign-status?limit=`
- `GET /control-plane/assurance/slo/{tenant_code}/evidence-package/sign-verify?limit=`
- `GET /assurance/public/tenant/{tenant_code}/evidence-package/signed?limit=`
- `GET /assurance/public/tenant/{tenant_code}/evidence-package/signed/verify?limit=`

## Notes
- Signed chain scope is tenant-specific (`assurance_tenant_evidence_package:{tenant_code}`).
- Signature chain uses canonical message + existing signing provider abstraction.
