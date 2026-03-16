# Phase 80 Status

## Title
Embedded Workflow API + Webhook Trigger Surface

## Objective Alignment
- `O4` SOAR playbook hub and executable one-click actions
- `O8` Purple executive product through embedded incident inputs
- `O9` Connector program and API-first external tool integration
- `O10` MSSP-ready multi-tenant operations

## Delivered
- Added site-level embedded endpoint configuration with per-endpoint shared secret, source, event kind, and default plugin config.
- Added public invoke API so external SIEM/EDR/WAF/custom tools can call AI co-workers without admin bearer tokens.
- Added invocation audit history so embedded calls are visible and traceable per site.
- Wired blue and purple endpoint invocations through the integration layer before plugin execution.
- Wired red endpoint invocations to persist embedded finding context before running exploit/template plugins.
- Added Configuration page controls to create embedded endpoints, rotate token, and copy an invoke-ready curl example.

## Files
- `backend/app/db/models.py`
- `backend/app/services/embedded_workflows.py`
- `backend/app/api/competitive.py`
- `backend/app/api/integrations.py`
- `backend/schemas/competitive.py`
- `backend/schemas/integrations.py`
- `backend/tests/test_embedded_workflows.py`
- `backend/tests/test_embedded_workflow_api.py`
- `frontend/app/configuration/page.tsx`
- `frontend/lib/api.ts`
- `frontend/lib/types.ts`

## Verification
- `cd backend && PYTHONPATH=. pytest -q tests/test_embedded_workflows.py tests/test_embedded_workflow_api.py`
- `cd backend && python -m compileall app schemas`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

## Result
The product now has a real plugin-first embedded surface. Customer tools can trigger AI co-workers through a shared-secret endpoint, while operators still manage configuration, audit trail, and rollout through the control-plane UI.
