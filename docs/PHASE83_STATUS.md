# Phase 83 Status

## Title
Embedded Invoke Packs, Blue Response Evidence Chain, and Approval/Rollback Controls

## Objective Alignment
- `O4` SOAR/playbook operationalization
- `O7` autonomous blue guardrails with approval + rollback
- `O9` connector program / embedded workflow usability
- `O10` MSSP-ready operational safety and auditability

## Delivered
- Added endpoint-specific embedded invoke packs under the competitive admin surface.
- Added HMAC-linked evidence chain for `blue_managed_responder_runs` using immutable signed payload snapshots in `details_json`.
- Added evidence verification endpoint for managed responder history.
- Added approval review API for pending managed responder runs.
- Added rollback API to restore Blue event state and cancel/relabel linked playbook executions.
- Improved SOAR approval handling so playbook approval prefers the exact `event_id` from run params.
- Updated Blue Service UI to review/rollback responder runs and display evidence summaries.
- Updated Configuration UI to show invoke packs per configured embedded endpoint.

## Validation
- `cd backend && python -m compileall app schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_blue_managed_responder.py tests/test_blue_managed_responder_api.py tests/test_embedded_workflow_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

## Result
- Backend compile passed
- Targeted pytest passed: `11 passed`
- Frontend typecheck passed

## Notes
- Evidence chain is stored in `details_json` to avoid a new migration and keep rollout friction low.
- Embedded invoke packs intentionally expose a token placeholder only; the real token is still shown once at create/rotate time.
