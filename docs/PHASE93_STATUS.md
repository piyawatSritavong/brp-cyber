# Phase 93 Status

## Phase
`Phase 93 - Red Plugin Intelligence Upgrade`

## Objective Alignment
- `R4` Red plugin intelligence upgrade
- supports Virtual Expert Red plugins so checklist status is backed by implementation, not labels

## Delivered
- added persistent site-level red plugin intelligence items for `cve/news/article`
- added persistent exploit safety policy per `target_type`
- upgraded `Exploit Code Generator` to consume intelligence context and safety policy
- upgraded `Nuclei AI-Template Writer` to consume intelligence context
- added lint/export baseline for both Red plugins
- added competitive APIs and Red Service UI controls for intelligence import, safety policy, lint, and export

## Key Files
- [red_plugin_intelligence.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/red_plugin_intelligence.py)
- [coworker_plugins.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/coworker_plugins.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/api/competitive.py)
- [models.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/db/models.py)
- [competitive.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/schemas/competitive.py)
- [RedTeamPanel.tsx](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/components/RedTeamPanel.tsx)
- [api.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/api.ts)
- [types.ts](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/lib/types.ts)
- [VIRTUAL_EXPERT_CHECKLIST.md](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/docs/VIRTUAL_EXPERT_CHECKLIST.md)

## Validation
- `cd backend && python -m compileall app schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_red_plugin_intelligence.py tests/test_red_plugin_intelligence_api.py tests/test_coworker_plugins.py`
- `cd backend && PYTHONPATH=. pytest -q tests/test_virtual_expert_workflows.py tests/test_virtual_expert_api.py tests/test_red_vulnerability_validator.py tests/test_red_social_engineering_production.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

## Result
- new Phase 93 tests passed
- Red/Virtual Expert regression tests passed
- frontend typecheck passed

## Operational Note
- phase นี้เพิ่ม table ใหม่:
  - `red_plugin_intelligence_items`
  - `red_plugin_safety_policies`
- ต้องเรียก `POST /bootstrap/phase0/init-db` 1 ครั้งใน environment ที่ใช้งานอยู่
