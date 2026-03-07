# Assurance Contracts

Tenant-level assurance SLA/evidence contracts for enterprise customers.

## Contract Fields

- `min_samples`
- `min_overall_pass_rate`
- `min_gate_pass_rate`
- `max_enterprise_monthly_cost_usd`
- `required_gates`
- `required_frameworks`
- `min_framework_readiness_score`

## Policy Pack Fields

- `auto_apply_actions`
- `force_approval_actions`
- `blocked_actions`
- `max_auto_apply_actions_per_run`
- `notify_only`
- `rollback_on_worse_result`
- `min_effectiveness_delta`

## Control-Plane APIs

- `POST /control-plane/assurance/contracts/upsert`
- `GET /control-plane/assurance/contracts/{tenant_code}`
- `GET /control-plane/assurance/contracts/{tenant_code}/evaluate?limit=`
- `POST /control-plane/assurance/contracts/{tenant_code}/remediate?limit=&auto_apply=`
- `GET /control-plane/assurance/contracts/{tenant_code}/remediation-status?limit=`
- `POST /control-plane/assurance/policy-packs/upsert`
- `GET /control-plane/assurance/policy-packs/{tenant_code}`
- `POST /control-plane/assurance/contracts/{tenant_code}/approve`
- `GET /control-plane/assurance/contracts/{tenant_code}/effectiveness?limit=`

## Example

```bash
curl -X POST http://localhost:8000/control-plane/assurance/contracts/upsert \
  -H "Authorization: Bearer <admin_token>" \
  -H "content-type: application/json" \
  -d '{
    "tenant_code":"acb",
    "owner":"ciso-office",
    "min_samples":30,
    "min_overall_pass_rate":0.95,
    "min_gate_pass_rate":0.95,
    "max_enterprise_monthly_cost_usd":80.0,
    "required_gates":["red","blue","purple","closed_loop","enterprise","compliance"],
    "required_frameworks":["soc2","nist_csf"],
    "min_framework_readiness_score":90
  }'
```

## Automation

Run daily contract evaluation:

```bash
cd backend
python scripts/evaluate_assurance_contracts.py
```

Run daily remediation planning:

```bash
cd backend
python scripts/remediate_assurance_contracts.py --limit 200
```

Bootstrap policy packs:

```bash
cd backend
python scripts/bootstrap_assurance_policy_packs.py
```

Generate effectiveness report:

```bash
cd backend
python scripts/report_assurance_effectiveness.py
```

Cross-tenant risk loop:

```bash
cd backend
python scripts/generate_assurance_risk_report.py
python scripts/apply_assurance_risk_recommendations.py --limit 500 --max-tier high --dry-run
```
