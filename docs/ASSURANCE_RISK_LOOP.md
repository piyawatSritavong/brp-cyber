# Assurance Risk Loop

Cross-tenant risk analytics and adaptive policy recommendation loop.

## APIs

- `GET /control-plane/assurance/risk/heatmap`
- `GET /control-plane/assurance/risk/recommendations`
- `POST /control-plane/assurance/risk/recommendations/apply`

## Scripts

```bash
cd backend
python scripts/generate_assurance_risk_report.py
python scripts/apply_assurance_risk_recommendations.py --limit 500 --max-tier high --dry-run
```

## Inputs Used

- Objective gate dashboard status
- Assurance contract evaluation outcome
- Remediation effectiveness and rollback trends

## Output

- Enterprise risk tiers per tenant (`low|medium|high|critical`)
- Suggested policy-pack adjustments for higher-risk tenants
- Optional controlled apply with dry-run safeguard
