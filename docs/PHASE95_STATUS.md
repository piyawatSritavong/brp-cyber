# Phase 95 Status

## Phase
`Phase 95 - AI Log Refiner Production Mode`

## Objective Alignment
- `B1` AI Log Refiner production mode
- supports Virtual Expert Blue service with persistent policy, KPI runs, operator feedback, and vendor mapping packs

## Delivered
- added site-level Blue Log Refiner policy persistence per connector source
- added refiner run history with noise-reduction KPI and estimated storage savings
- added operator feedback loop for `keep_signal`, `drop_noise`, `false_positive`, and `signal_missed`
- added vendor mapping packs for `Splunk`, `ELK`, `Cloudflare`, `CrowdStrike`, and `generic`
- added competitive APIs and Blue Service UI controls for policy, run, feedback, and mapping-pack preview

## Key Files
- [blue_log_refiner.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/blue_log_refiner.py)
- [models.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/db/models.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/api/competitive.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/schemas/competitive.py)
- [BlueTeamPanel.tsx](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/components/BlueTeamPanel.tsx)
- [api.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/api.ts)
- [types.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/types.ts)
- [test_blue_log_refiner.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_blue_log_refiner.py)
- [test_blue_log_refiner_api.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/tests/test_blue_log_refiner_api.py)

## Validation
- `cd backend && python -m compileall app schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_blue_log_refiner.py tests/test_blue_log_refiner_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

## Result
- service logic and RBAC/API tests passed
- frontend typecheck passed with Blue log refiner UI enabled

## Operational Note
- phase นี้เพิ่ม table ใหม่:
  - `blue_log_refiner_policies`
  - `blue_log_refiner_runs`
  - `blue_log_refiner_feedback`
- ต้องเรียก `POST /bootstrap/phase0/init-db` 1 ครั้งใน environment ที่ใช้งานอยู่
