# Orchestration Pilot Onboarding

Phase 35 adds self-serve onboarding and scoped operator roles for pilot users.

## Control-Plane APIs

- `POST /control-plane/orchestrator/pilot/operators/issue`
- `POST /control-plane/orchestrator/pilot/operators/revoke`
- `POST /control-plane/orchestrator/pilot/onboarding/upsert`
- `GET /control-plane/orchestrator/pilot/onboarding/{tenant_id}`
- `GET /control-plane/orchestrator/pilot/onboarding/{tenant_id}/checklist`

## Orchestrator Secure APIs

- `POST /orchestrator/pilot/secure/activate`
- `POST /orchestrator/pilot/secure/deactivate/{tenant_id}`
- `GET /orchestrator/pilot/secure/status/{tenant_id}`

Required headers for secure APIs:
- `Authorization: Bearer opt_*`
- `X-Tenant-Code: <tenant_code>`

## Checklist Script

```bash
cd backend
python scripts/generate_pilot_onboarding_checklist.py --tenant-id 00000000-0000-0000-0000-000000000001
```

## Workflow

- `.github/workflows/orchestration-pilot-onboarding-checklist.yml`
