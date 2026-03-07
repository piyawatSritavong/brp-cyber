# Assurance External Verifier

Phase 30 adds a dedicated verifier trust boundary and signed import receipts.

## Control-Plane APIs

- `POST /control-plane/assurance/slo/{tenant_code}/external-verifier/tokens/issue`
- `POST /control-plane/assurance/slo/{tenant_code}/external-verifier/tokens/revoke`
- `POST /control-plane/assurance/slo/{tenant_code}/external-verifier/policy/upsert`
- `GET /control-plane/assurance/slo/{tenant_code}/external-verifier/policy`
- `GET /control-plane/assurance/slo/{tenant_code}/external-verifier/status`
- `GET /control-plane/assurance/slo/{tenant_code}/external-verifier/receipts`
- `GET /control-plane/assurance/slo/{tenant_code}/external-verifier/receipts/verify`

## Public APIs

- `POST /assurance/public/verifier/import/{tenant_code}` (`X-Verifier-Token` required)
- `GET /assurance/public/tenant/{tenant_code}/external-verifier-receipts`
- `GET /assurance/public/tenant/{tenant_code}/external-verifier-receipts/verify`

## Scripts

```bash
cd backend
python scripts/issue_external_verifier_token.py --tenant-code acb --verifier-name auditor_x
python scripts/upsert_external_verifier_policy.py --tenant-code acb --min-quorum 2 --allowed-verifiers auditor_x,auditor_y --freshness-hours 24
python scripts/import_external_verifier_bundle.py --tenant-code acb --source auditor_x --valid --bundle-id vb-1 --snapshot-id s-1
python scripts/verify_external_verifier_receipts.py --tenant-code acb --limit 1000
```

## Security Model

- Verifier tokens are tenant-scoped and cannot be reused across tenants.
- Verifier tokens are revocable and short-lived (`ttl_seconds` policy).
- Every import emits signed receipt-chain entry for independent replay verification.
- Zero-trust attestation can require multi-verifier quorum with distinct sources based on tenant policy.
- Zero-trust policy also supports weighted trust thresholds (`min_weighted_score`, `verifier_weights`) and disagreement blocking (`block_on_disagreement`).
