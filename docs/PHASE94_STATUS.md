# Phase 94 Status

## Phase
`Phase 94 - Purple Plugin Export Layer`

## Objective Alignment
- `P3` Purple plugin export layer
- supports Virtual Expert Purple plugins with export surfaces that operators can use directly from the Purple page

## Delivered
- added backend service for Purple export template packs
- added MITRE heatmap export baseline in `markdown`, `csv`, and `attack_layer_json`
- added incident report export baseline with company, board, and Thai regulator template packs
- added regulated report export baseline with ISO 27001 + NIST CSF evidence snapshots
- added competitive APIs for Purple export listing and export generation
- added Purple Service UI controls and preview blocks for MITRE, incident, and regulated exports

## Key Files
- [purple_plugin_exports.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/purple_plugin_exports.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/api/competitive.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/schemas/competitive.py)
- [PurpleReportsPanel.tsx](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/components/PurpleReportsPanel.tsx)
- [api.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/api.ts)
- [types.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/types.ts)
- [test_purple_plugin_exports.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_purple_plugin_exports.py)
- [test_purple_plugin_exports_api.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_purple_plugin_exports_api.py)
- [VIRTUAL_EXPERT_CHECKLIST.md](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/docs/VIRTUAL_EXPERT_CHECKLIST.md)

## Validation
- `cd backend && python -m compileall app schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_purple_plugin_exports.py tests/test_purple_plugin_exports_api.py tests/test_virtual_expert_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

## Result
- Purple export services passed targeted tests
- RBAC behavior for export endpoints passed
- frontend typecheck passed with Purple export UI enabled

## Operational Note
- phase นี้ไม่มี table/schema ใหม่
- ไม่ต้องเรียก `POST /bootstrap/phase0/init-db` สำหรับ Phase 94
