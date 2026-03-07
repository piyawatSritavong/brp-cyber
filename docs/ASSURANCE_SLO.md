# Assurance SLO

Tenant assurance SLO profile, breach budget, and executive digest.

## APIs

- `POST /control-plane/assurance/slo/upsert`
- `GET /control-plane/assurance/slo/{tenant_code}`
- `GET /control-plane/assurance/slo/{tenant_code}/evaluate`
- `GET /control-plane/assurance/slo/{tenant_code}/breaches`
- `GET /control-plane/assurance/slo/executive-digest`
- `POST /control-plane/assurance/slo/executive-digest/sign`
- `GET /control-plane/assurance/slo/executive-digest/sign-status`
- `GET /control-plane/assurance/slo/executive-digest/sign-verify`
- `POST /control-plane/assurance/slo/{tenant_code}/bulletin/sign`

## Signals Included

- Contract overall pass-rate
- Remediation effectiveness delta
- Rollback batch trend
- API availability and error-rate

## Scripts

```bash
cd backend
python scripts/generate_assurance_executive_digest.py
```
