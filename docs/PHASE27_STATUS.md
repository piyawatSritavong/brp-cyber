# Phase 27 Status

- Phase: `Phase 27 - Tenant Verifier Kit & One-Click Evidence Package Index`
- Status: `Completed`
- Last Updated: `2026-03-06`

## Scope
- Provide tenant-facing downloadable verifier kit
- Provide one-click compliance evidence package index per tenant

## Planned Deliverables
- [x] Verifier kit export/status service
- [x] Compliance evidence package index export/status service
- [x] Control-plane APIs for kit and package index operations
- [x] Public endpoint for tenant evidence-package index status
- [x] Scripts/workflow for scheduled kit and package export
- [x] Tests for kit/package services and public API coverage

## Implemented APIs
- `POST /control-plane/assurance/slo/{tenant_code}/verifier-kit/export?destination_dir=&limit=`
- `GET /control-plane/assurance/slo/{tenant_code}/verifier-kit/status?limit=`
- `POST /control-plane/assurance/slo/{tenant_code}/evidence-package/export?destination_dir=&limit=`
- `GET /control-plane/assurance/slo/{tenant_code}/evidence-package/status?limit=`
- `GET /assurance/public/tenant/{tenant_code}/evidence-package?limit=`

## Notes
- Verifier kit includes verification commands and latest proof metadata for customer-side validation.
- Evidence package index aggregates contract, bulletin, proof, SLO breach, and verifier-kit references in one export.
