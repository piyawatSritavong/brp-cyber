# Orchestration Activation

Phase 33 introduces one-click orchestration activation for Red/Blue/Purple loop automation.

## APIs

- `POST /orchestrator/activate`
- `POST /orchestrator/pause/{tenant_id}`
- `POST /orchestrator/deactivate/{tenant_id}`
- `GET /orchestrator/activation/{tenant_id}`
- `GET /orchestrator/activations`
- `POST /orchestrator/tick`

## Activation Request Example

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "target_asset": "acb.example.com/admin-login",
  "red_scenario_name": "credential_stuffing_sim",
  "red_events_count": 30,
  "strategy_profile": "balanced",
  "cycle_interval_seconds": 300,
  "approval_mode": false
}
```

## Automation Script

```bash
cd backend
python scripts/run_orchestration_activation_tick.py --limit 500
```

## Scheduled Workflow

- `.github/workflows/orchestration-activation-tick.yml`

This workflow executes scheduler ticks every 5 minutes to keep active tenant loops running automatically.
