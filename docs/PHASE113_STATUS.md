# Phase 113 Status

## Title
Purple Control-Family Policy/Evidence Mapping

## Completed
- Added control-family mapping service across ISO 27001 and NIST CSF
- Added policy/evidence references from Blue/Purple operational artifacts
- Added control-family map view/export APIs
- Added control-family map preview/export UI to `PurpleReportsPanel`

## Validation
- `python -m compileall backend/app backend/schemas`
- `PYTHONPATH=. pytest -q tests/test_purple_control_mapping.py tests/test_purple_control_mapping_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`
