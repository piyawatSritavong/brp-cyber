# Phase 97 Status

## Phase
`Phase 97 - Connector-Native Feed Adapters & Detection-Gap Correlation`

## Objective Alignment
- `B3` Threat Intelligence Localizer completion
- closes the remaining baseline gap for vendor feed normalization and site-specific control-gap visibility

## Delivered
- added connector-native threat feed adapter templates for `Splunk`, `CrowdStrike`, `Cloudflare`, and `generic`
- added adapter import API/service that normalizes vendor payloads into the Blue threat feed model
- added detection-gap correlation that compares localized threat categories against site detection rules and enabled embedded connectors
- expanded Blue Service UI to import feed payloads via adapters, preview field mappings, and show detection-gap coverage rows in the latest threat brief
- added targeted tests for adapter normalization, RBAC, and detection-gap behavior

## Key Files
- [blue_threat_localizer.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/blue_threat_localizer.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/api/competitive.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/schemas/competitive.py)
- [BlueTeamPanel.tsx](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/components/BlueTeamPanel.tsx)
- [api.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/api.ts)
- [types.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/types.ts)
- [test_blue_threat_localizer_production.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_blue_threat_localizer_production.py)
- [test_blue_threat_localizer_api.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_blue_threat_localizer_api.py)

## Validation
- `cd backend && python -m compileall app schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_blue_threat_localizer_production.py tests/test_blue_threat_localizer_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

## Result
- adapter import and detection-gap correlation passed targeted backend tests
- frontend typecheck passed with the updated Blue localizer workflow

## Operational Note
- phase นี้ไม่มี table ใหม่
- restart backend หากมี process ค้างอยู่ เพื่อให้ route/code ใหม่ถูกโหลดครบ
