# Orchestration Pilot Mode

Phase 34 adds pilot-mode controls for user testing of autonomous Red/Blue/Purple runs.

## Pilot APIs

- `POST /orchestrator/pilot/activate`
- `POST /orchestrator/pilot/deactivate/{tenant_id}`
- `GET /orchestrator/pilot/status/{tenant_id}`
- `GET /orchestrator/pilot/sessions`

## Pilot Activation Example

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "target_asset": "acb.example.com/admin-login",
  "strategy_profile": "balanced",
  "red_scenario_name": "credential_stuffing_sim",
  "red_events_count": 30,
  "cycle_interval_seconds": 300,
  "require_objective_gate_pass": true,
  "force": false
}
```

## Report Automation

```bash
cd backend
python scripts/generate_pilot_sessions_report.py --limit 1000
```

Workflow:
- `.github/workflows/orchestration-pilot-report.yml`
