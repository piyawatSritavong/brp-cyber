# Phase 114 Status

## Title
Purple Graphical Heatmap Export & ATT&CK Layer Workflow

## Completed
- Added SVG export support for Purple MITRE heatmap
- Added `purple_attack_layer_workspaces` persistence
- Added ATT&CK layer list/import/edit/export APIs
- Added live graphical export endpoint from current executive heatmap evidence
- Added ATT&CK layer editor/import/export UI to `PurpleReportsPanel`

## Validation
- `python -m compileall backend/app backend/schemas`
- `PYTHONPATH=. pytest -q tests/test_purple_attack_layer_workflows.py tests/test_purple_attack_layer_workflows_api.py tests/test_purple_plugin_exports.py tests/test_purple_plugin_exports_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`
