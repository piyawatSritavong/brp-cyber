# Assurance Verifier Kit

Tenant-facing verifier kit and compliance evidence package index.

## Control-Plane APIs

- `POST /control-plane/assurance/slo/{tenant_code}/verifier-kit/export`
- `GET /control-plane/assurance/slo/{tenant_code}/verifier-kit/status`
- `POST /control-plane/assurance/slo/{tenant_code}/evidence-package/export`
- `GET /control-plane/assurance/slo/{tenant_code}/evidence-package/status`
- `POST /control-plane/assurance/slo/{tenant_code}/evidence-package/sign`
- `GET /control-plane/assurance/slo/{tenant_code}/evidence-package/sign-status`
- `GET /control-plane/assurance/slo/{tenant_code}/evidence-package/sign-verify`

## Public API

- `GET /assurance/public/tenant/{tenant_code}/evidence-package`
- `GET /assurance/public/tenant/{tenant_code}/evidence-package/signed`
- `GET /assurance/public/tenant/{tenant_code}/evidence-package/signed/verify`

## Scripts

```bash
cd backend
python scripts/export_verifier_kit.py --tenant-code acb --limit 1000
python scripts/export_compliance_evidence_package_index.py --tenant-code acb --limit 100
python scripts/generate_signed_evidence_package.py --tenant-code acb --limit 100
python scripts/verify_signed_evidence_package.py --tenant-code acb --limit 1000
```

## Kit Contents

- `README.md` with verifier commands
- `verifier_kit_index.json` with latest bulletin/proof validity signals
- package index export referencing contract, SLO breach, bulletin, delivery proof, and kit metadata
