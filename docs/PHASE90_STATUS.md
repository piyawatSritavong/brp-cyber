# Phase 90 Status

## Title
Social Engineering Production Path for Red Service

## Objective Alignment
- `R2` complete the Social Engineering production path from `VIRTUAL_EXPERT_CHECKLIST.md`
- strengthen the Red service so the Virtual Expert menu is backed by persisted roster, policy, approval, and telemetry workflows
- keep compatibility with the current bootstrap model by adding new tables instead of mutating old columns

## Delivered
- Added Social production models for:
  - employee roster
  - campaign policy
  - campaign execution
  - recipient telemetry
- Extended the Red Social service with:
  - roster import/list
  - policy get/upsert
  - campaign review approve/reject
  - campaign kill switch
  - recipient telemetry summary/list
- Kept the original social run table and layered execution state around it to avoid migration breakage in existing environments.
- Added competitive APIs for roster, policy, review, kill, and telemetry.
- Upgraded the `Red Service` UI so one panel now covers:
  - roster import
  - connector policy
  - campaign queue/run
  - approval/reject
  - kill latest campaign
  - telemetry view

## Validation
- `cd backend && python -m compileall app schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_red_social_engineering_production.py tests/test_red_social_engineering_api.py tests/test_virtual_expert_workflows.py tests/test_virtual_expert_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

## Result
- Backend compile passed
- Targeted pytest passed: `8 passed`
- Frontend typecheck passed

## Notes
- New tables were added. Existing environments must run `POST /bootstrap/phase0/init-db` once to create them.
- Connector types `smtp` and `webhook` are now policy-level abstractions. The baseline still uses simulated delivery unless a deeper external provider callback path is added in a later phase.
