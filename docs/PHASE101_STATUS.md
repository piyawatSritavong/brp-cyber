# Phase 101 Status

## Phase
`Phase 101 - Shadow Pentest Asset Inventory & Deploy Trigger`

## Objective Alignment
- `R1` Shadow Pentest hardening completion
- closes the remaining baseline gap for deploy-aware drift validation and lightweight asset inventory visibility

## Delivered
- added asset inventory baseline derived from passive shadow crawl pages
- added API to retrieve the latest asset inventory summary and rows for a site
- added deploy-event trigger service/API that forces a shadow scan from CI/CD or release workflow context
- attached deploy trigger context into Shadow Pentest run details for traceability
- expanded Red Service UI with deploy trigger controls and asset inventory view
- added targeted tests for asset inventory summary, deploy trigger service, and API permission behavior

## Key Files
- [red_shadow_pentest.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/red_shadow_pentest.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/api/competitive.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/schemas/competitive.py)
- [RedTeamPanel.tsx](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/components/RedTeamPanel.tsx)
- [api.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/api.ts)
- [types.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/types.ts)
- [test_red_shadow_pentest.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_red_shadow_pentest.py)
- [test_red_shadow_pentest_api.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_red_shadow_pentest_api.py)

## Validation
- `cd backend && python -m compileall app schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_red_shadow_pentest.py tests/test_red_shadow_pentest_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

## Result
- asset inventory and deploy-trigger flows passed targeted backend tests
- frontend typecheck passed with Red Service deploy trigger and asset inventory controls enabled

## Operational Note
- phase นี้ไม่มี table ใหม่
- restart backend หากมี process ค้างอยู่ เพื่อให้ Shadow Pentest routes ใหม่ถูกโหลดครบ
