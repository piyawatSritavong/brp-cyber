# Phase 35 Status

- Phase: `Phase 35 - Self-Serve Pilot Onboarding & Scoped Operator Roles`
- Status: `Completed`
- Last Updated: `2026-03-06`

## Scope
- Add tenant-scoped pilot operator credentials for real user pilot operations.
- Add self-serve onboarding profile and readiness checklist before pilot launch.

## Planned Deliverables
- [x] Pilot operator token service (`issue/verify/revoke`)
- [x] Secure pilot APIs requiring operator token and scoped permissions
- [x] Pilot onboarding profile and readiness checklist service
- [x] Control-plane endpoints for onboarding and operator token lifecycle
- [x] Automation script/workflow for onboarding checklist
- [x] Tests for operator auth, secure API, and onboarding logic

## Implemented APIs
- `POST /control-plane/orchestrator/pilot/operators/issue`
- `POST /control-plane/orchestrator/pilot/operators/revoke`
- `POST /control-plane/orchestrator/pilot/onboarding/upsert`
- `GET /control-plane/orchestrator/pilot/onboarding/{tenant_id}`
- `GET /control-plane/orchestrator/pilot/onboarding/{tenant_id}/checklist`
- `POST /orchestrator/pilot/secure/activate` (`Authorization: Bearer opt_*`, `X-Tenant-Code`)
- `POST /orchestrator/pilot/secure/deactivate/{tenant_id}`
- `GET /orchestrator/pilot/secure/status/{tenant_id}`

## Notes
- Operator tokens are tenant-scoped and limited to `pilot:read`/`pilot:write` scopes.
- Secure pilot endpoints enforce both token scope and tenant matching.
