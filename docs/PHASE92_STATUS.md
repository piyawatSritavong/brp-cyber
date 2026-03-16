# Phase 92 Status

## Title
ROI Executive Export Layer

## Objective Alignment
- `P2` ROI Dashboard executive mode
- `VIRTUAL_EXPERT_CHECKLIST.md` re-audit + source-of-truth correction
- Purple executive product hardening for board-facing workflow

## Delivered
- Re-audited `VIRTUAL_EXPERT_CHECKLIST.md` against current implementation and corrected status drift
- Added ROI trend view service from snapshot history with delta summary
- Added tenant portfolio roll-up service using the latest ROI snapshot per site
- Added board-pack export baseline for `pdf/ppt` content structure
- Added new competitive APIs for ROI trends, portfolio roll-up, and export pack
- Extended Purple Service UI to show trends, portfolio summary, and export preview in one panel

## Key Files
- Backend service: [purple_roi_dashboard.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/purple_roi_dashboard.py)
- Backend API: [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/api/competitive.py)
- Backend schema: [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/schemas/competitive.py)
- Frontend Purple page: [PurpleReportsPanel.tsx](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/components/PurpleReportsPanel.tsx)
- Frontend API/types: [api.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/api.ts), [types.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/types.ts)
- Checklist: [VIRTUAL_EXPERT_CHECKLIST.md](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/docs/VIRTUAL_EXPERT_CHECKLIST.md)

## Validation
- `cd backend && python -m compileall app schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_purple_roi_dashboard_executive.py tests/test_purple_roi_dashboard_api.py tests/test_virtual_expert_workflows.py tests/test_virtual_expert_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

## Result
- Backend compile passed
- Targeted pytest passed: `8 passed`
- Frontend typecheck passed

## Notes
- No schema migration/table addition in this phase
- Export is a `board-pack baseline` that returns structured sections/slides for `pdf/ppt` workflows; native binary renderer is still a remaining gap
