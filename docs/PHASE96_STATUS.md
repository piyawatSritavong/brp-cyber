# Phase 96 Status

## Phase
`Phase 96 - Shadow Pentest Hardening`

## Objective Alignment
- `R1` Shadow Pentest hardening
- closes the Red service gap for passive crawl, drift detection, zero-day pack assignment, and continuous safe scheduling

## Delivered
- added site-level Shadow Pentest policy persistence and run history
- added passive crawl + page/content diff detection baseline
- added zero-day threat-pack auto-assignment from drift signals
- added manual run, scheduler run, and autonomous runtime integration
- added Red Service UI controls for policy, run, scheduler, and recent drift history

## Key Files
- [red_shadow_pentest.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/red_shadow_pentest.py)
- [models.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/db/models.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/api/competitive.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/schemas/competitive.py)
- [autonomous_runtime.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/autonomous_runtime.py)
- [config.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/core/config.py)
- [.env.example](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/.env.example)
- [RedTeamPanel.tsx](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/components/RedTeamPanel.tsx)
- [api.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/api.ts)
- [types.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/types.ts)
- [test_red_shadow_pentest.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_red_shadow_pentest.py)
- [test_red_shadow_pentest_api.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_red_shadow_pentest_api.py)
- [test_autonomous_runtime.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_autonomous_runtime.py)

## Validation
- `cd backend && python -m compileall app schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_red_shadow_pentest.py tests/test_red_shadow_pentest_api.py tests/test_autonomous_runtime.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

## Result
- service logic, RBAC/API behavior, and runtime integration tests passed
- frontend typecheck passed with Shadow Pentest UI enabled

## Operational Note
- phase นี้เพิ่ม table ใหม่:
  - `red_shadow_pentest_policies`
  - `red_shadow_pentest_runs`
- ต้องเรียก `POST /bootstrap/phase0/init-db` 1 ครั้งใน environment ที่ใช้งานอยู่
