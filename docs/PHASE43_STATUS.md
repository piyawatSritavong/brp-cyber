# Phase 43 Status

- Phase: `Phase 43 - Dual-Control Rollout Approval & Signed Evidence`
- Status: `Completed`
- Last Updated: `2026-03-06`

## Scope
- Enforce dual-control approval for rollout changes when required by tenant policy.
- Persist signed evidence for approval/rejection operations to strengthen audit trust.

## Planned Deliverables
- [x] Rollout policy extension with dual-control toggles
- [x] Pending-decision approval flow supporting multi-step approvers
- [x] Duplicate-reviewer protection for dual-control enforcement
- [x] Signed rollout evidence stream (`HMAC-SHA256`)
- [x] Evidence APIs for orchestrator and secure operator access
- [x] Control-plane evidence API + policy dual-control governance
- [x] Script/workflow for rollout evidence reporting
- [x] Tests for dual-control behavior and evidence output

## Implemented APIs
- `GET /orchestrator/pilot/rollout/evidence/{tenant_id}`
- `GET /orchestrator/pilot/secure/rollout/evidence/{tenant_id}`
- `POST /orchestrator/pilot/rollout-policy/upsert` (supports dual-control flags)
- `POST /orchestrator/pilot/rollout/pending/approve` (supports staged approvals)
- `POST /orchestrator/pilot/secure/rollout/pending/approve`
- `GET /control-plane/orchestrator/pilot/rollout/evidence/{tenant_id}`
- `POST /control-plane/orchestrator/pilot/rollout-policy/upsert` (supports dual-control flags)

## Notes
- Rollout evidence entries are signed for tamper-evident audit workflows.
- When dual control is enabled, a second distinct reviewer is mandatory before apply.
