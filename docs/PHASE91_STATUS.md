# Phase 91 Status

## Title
Threat Intelligence Localizer External Feeds & Digest Scheduler

## Objective Alignment
- `B3` Threat Intelligence Localizer upgrade
- `O9/O10` plugin-first embedded and multi-site operations baseline
- `VIRTUAL_EXPERT_CHECKLIST.md` source-of-truth closure for Blue service gap

## Delivered
- Added threat localizer policy persistence per site
- Added external threat feed item ingestion/listing baseline for Thai/SEA content
- Added sector profile library and site impact scoring in localizer runs
- Added recurring digest scheduler and autonomous runtime integration
- Extended Blue Service UI with policy save, feed import, sector profile display, and scheduler controls
- Added targeted tests for service logic, route RBAC, workflow regression, and runtime integration

## Key Files
- Backend service: [blue_threat_localizer.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/blue_threat_localizer.py)
- Backend API: [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/api/competitive.py)
- Backend models: [models.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/db/models.py)
- Runtime integration: [autonomous_runtime.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/autonomous_runtime.py)
- Frontend Blue page: [BlueTeamPanel.tsx](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/components/BlueTeamPanel.tsx)
- Frontend API/types: [api.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/api.ts), [types.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/types.ts)
- Tests: [test_blue_threat_localizer_production.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_blue_threat_localizer_production.py), [test_blue_threat_localizer_api.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_blue_threat_localizer_api.py)

## Validation
- `cd backend && python -m compileall app schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_blue_threat_localizer_production.py tests/test_blue_threat_localizer_api.py tests/test_virtual_expert_workflows.py tests/test_virtual_expert_api.py tests/test_autonomous_runtime.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

## Result
- Backend compile passed
- Targeted pytest passed: `10 passed`
- Frontend typecheck passed

## Operational Note
- This phase adds new tables:
  - `blue_threat_localizer_policies`
  - `blue_threat_feed_items`
- Run `POST /bootstrap/phase0/init-db` once on the active environment before using the new policy/feed features.
