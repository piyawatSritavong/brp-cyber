# Phase 89 Status

## Title
ISO/NIST Gap Baseline Completion for Purple Service

## Objective Alignment
- `O8` expand the Purple executive/compliance product from ISO-only to ISO + NIST baseline coverage
- `O10` keep the compliance workflow usable across sites from the existing multi-site dashboard and service pages

## Delivered
- Added shared Purple compliance context generation in `site_ops` for framework-driven gap analysis.
- Added `NIST Cybersecurity Framework 2.0` gap template generation based on actual Red/Blue/Purple evidence.
- Added new site API endpoint `GET /sites/{site_id}/purple/nist-csf-gap-template?limit=`.
- Updated Purple Service UI to trigger both `ISO 27001 Gap` and `NIST CSF Gap` from the same compliance panel.
- Updated the Virtual Expert checklist to mark `Automated ISO/NIST Gap Analysis` as implemented baseline.

## Validation
- `cd backend && python -m compileall app schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_purple_executive_site_ops.py tests/test_blue_managed_responder.py tests/test_red_vulnerability_validator.py tests/test_red_vulnerability_validator_api.py tests/test_virtual_expert_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

## Result
- Backend compile passed
- Targeted pytest passed: `16 passed`
- Frontend typecheck passed

## Notes
- The compliance baseline now covers both ISO and NIST templates, but exportable audit packs and deeper control evidence mapping remain future work.
