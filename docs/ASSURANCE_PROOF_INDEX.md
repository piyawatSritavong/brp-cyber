# Assurance Proof Index

Cross-tenant index for auditor review of signed delivery-proof chains.

## APIs

- `GET /control-plane/assurance/proof-index`
- `POST /control-plane/assurance/proof-index/export`

## Public Verification

- `GET /assurance/public/tenant/{tenant_code}/delivery-proof`
- `GET /assurance/public/tenant/{tenant_code}/delivery-proof/verify`

## Script

```bash
cd backend
python scripts/generate_assurance_proof_index.py --limit 500
```

## Index Fields

- `tenant_code`
- `has_proof`
- `latest_snapshot_id`
- `latest_generated_at`
- `latest_receipt_status`
- `proof_chain_valid`
