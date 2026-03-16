# Phase 105 Status

## Phase
`Phase 105 - Purple Binary Export & Final Report Release Workflow`

## Objective Alignment
- closes the remaining Purple baseline gap for native incident/regulatory binary export and final release approval

## Delivered
- expanded Purple incident and regulatory exports to support native `pdf` and `docx`
- added final report release workflow with request/list/review lifecycle
- added release approval surface in Purple Service UI
- added download links for binary export artifacts from the Purple page

## Key Files
- [purple_plugin_exports.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/purple_plugin_exports.py)
- [models.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/db/models.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/api/competitive.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/schemas/competitive.py)
- [PurpleReportsPanel.tsx](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/components/PurpleReportsPanel.tsx)
- [api.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/api.ts)
- [types.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/types.ts)
- [test_purple_plugin_exports.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_purple_plugin_exports.py)
- [test_purple_plugin_exports_api.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_purple_plugin_exports_api.py)

## Validation
- `cd backend && python -m compileall app schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_purple_plugin_exports.py tests/test_purple_plugin_exports_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

## Result
- native binary export and release-approval flows passed targeted backend tests
- frontend typecheck passed with Purple final release UI enabled

## Operational Note
- phase นี้เพิ่ม table ใหม่:
  - `purple_report_releases`
- ต้องเรียก `POST /bootstrap/phase0/init-db` 1 ครั้งใน environment ที่ใช้งานอยู่
