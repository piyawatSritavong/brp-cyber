# Phase 3 Status

- Phase: `Phase 3 - Red Simulation Core (Safe Adversarial Emulation)`
- Status: `In Progress`
- Last Updated: `2026-03-06`

## Completed
- [x] Red scenario library (credential stuffing sim / slow bruteforce sim / admin probe sim)
- [x] Target allowlist guardrail (`RED_ALLOWED_TARGETS`)
- [x] Rate and volume guardrails (`RED_MAX_EVENTS_PER_RUN`, `RED_MIN_DELAY_MS`)
- [x] Red simulation run API
- [x] Scheduler API (schedule + tick)
- [x] Replay protection for scheduled jobs (job status key)
- [x] Streamed red events for Purple correlation (`red_event` in security stream)
- [x] Closed-loop pressure to Blue via simulated auth failures
- [x] Unit tests for run/schedule/guardrail flow

## Remaining
- [ ] Add per-tenant simulation profile presets (conservative/balanced/aggressive)
- [ ] Add distributed scheduler worker (instead of API-triggered tick)
- [ ] Add integration tests against live Redis/API runtime

## Evidence
- `backend/app/services/red_simulator.py`
- `backend/app/api/red_sim.py`
- `backend/schemas/red_sim.py`
- `backend/tests/test_red_simulator.py`
