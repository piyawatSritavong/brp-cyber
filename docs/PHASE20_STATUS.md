# Phase 20 Status

- Phase: `Phase 20 - Remediation Effectiveness Scoring & Rollback Guardrails`
- Status: `Completed`
- Last Updated: `2026-03-06`

## Scope
- Measure remediation effectiveness per batch
- Add rollback guardrails when remediation worsens contract posture

## Planned Deliverables
- [x] Effectiveness scoring (`baseline`, `post`, `delta`) per remediation batch
- [x] Policy-pack controls for rollback behavior
- [x] Automatic rollback when effectiveness below threshold
- [x] Effectiveness API and reporting automation
- [x] Tests for rollback/effectiveness behavior

## Implemented APIs
- `GET /control-plane/assurance/contracts/{tenant_code}/effectiveness?limit=`

## Notes
- Effectiveness is measured from contract evaluation before and after remediation.
- Guardrail rollback is policy-driven via tenant policy pack (`rollback_on_worse_result`, `min_effectiveness_delta`).
- This improves enterprise reliability by preventing harmful automated remediations from persisting.
