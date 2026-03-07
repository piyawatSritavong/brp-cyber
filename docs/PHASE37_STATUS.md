# Phase 37 Status

- Phase: `Phase 37 - Multi-tenant Pilot Concurrency Guardrails & Rate Budgets`
- Status: `Completed`
- Last Updated: `2026-03-06`

## Scope
- Protect shared orchestration workers when many tenants are active at once.
- Enforce per-tenant hourly pilot budgets to control blast radius and cost.

## Planned Deliverables
- [x] Global scheduler execution cap per tick
- [x] Tenant-level pilot rate budget profile (`max_cycles_per_hour`, `max_red_events_per_hour`)
- [x] Hourly usage tracking and reservation before each cycle
- [x] Auto-pause/auto-stop path when rate budget is exceeded
- [x] Incident emission for budget violations
- [x] Orchestrator APIs for budget upsert/get/usage and secure operator usage read
- [x] Control-plane APIs for budget governance and audit trail
- [x] Automation script/workflow for pilot rate-budget reporting
- [x] Tests for execution cap, budget enforcement, and secure API path

## Implemented APIs
- `POST /orchestrator/pilot/rate-budget`
- `GET /orchestrator/pilot/rate-budget/{tenant_id}`
- `GET /orchestrator/pilot/rate-budget/{tenant_id}/usage`
- `GET /orchestrator/pilot/secure/rate-budget/{tenant_id}/usage`
- `POST /control-plane/orchestrator/pilot/rate-budget/upsert`
- `GET /control-plane/orchestrator/pilot/rate-budget/{tenant_id}`
- `GET /control-plane/orchestrator/pilot/rate-budget/{tenant_id}/usage`

## Notes
- Scheduler now stops executing additional tenants when global per-tick cap is reached.
- Budget checks happen before cycle execution, so over-budget tenants are blocked before cost/impact.
