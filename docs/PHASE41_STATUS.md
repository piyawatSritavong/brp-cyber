# Phase 41 Status

- Phase: `Phase 41 - Rollout Anti-Flapping Hysteresis & Cooldown Windows`
- Status: `Completed`
- Last Updated: `2026-03-06`

## Scope
- Prevent rollout ring flapping (promote/demote oscillation) under noisy signals.
- Add hysteresis and cooldown guardrails for enterprise-safe rollout automation.

## Planned Deliverables
- [x] Rollout guard state store per tenant (`promote_streak`, `demote_streak`, `cooldown_until_epoch`)
- [x] Hysteresis rules for promote/demote streak thresholds
- [x] Cooldown blocking for immediate reversal decisions
- [x] Guard-state persistence integrated into rollout evaluator
- [x] Pilot status extension with rollout guard state
- [x] Orchestrator APIs for rollout guard read (+ secure read)
- [x] Control-plane API for rollout guard inspection
- [x] Script/workflow for rollout guard reporting
- [x] Tests for hysteresis promote behavior and cooldown block behavior

## Implemented APIs
- `GET /orchestrator/pilot/rollout/guard/{tenant_id}`
- `GET /orchestrator/pilot/secure/rollout/guard/{tenant_id}`
- `GET /control-plane/orchestrator/pilot/rollout/guard/{tenant_id}`

## Notes
- Auto-promote now requires sustained KPI quality across consecutive evaluations.
- Cooldown windows reduce rollback churn and protect ring stability during transient incidents.
