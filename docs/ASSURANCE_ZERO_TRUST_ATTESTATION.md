# Assurance Zero-Trust Attestation

Phase 29 introduces external verifier ingestion and zero-trust attestation on top of signed tenant evidence packages.

## Control-Plane APIs

- `POST /control-plane/assurance/slo/{tenant_code}/external-verifier/import`
- `GET /control-plane/assurance/slo/{tenant_code}/external-verifier/status`
- `POST /control-plane/assurance/slo/{tenant_code}/zero-trust/attest`
- `GET /control-plane/assurance/slo/{tenant_code}/zero-trust/status`
- `GET /control-plane/assurance/zero-trust/overview`

## Public APIs

- `GET /assurance/public/tenant/{tenant_code}/zero-trust-attestation`
- `GET /assurance/public/zero-trust/overview`

## Scripts

```bash
cd backend
python scripts/import_external_verifier_bundle.py --tenant-code acb --source auditor_x --valid --bundle-id vb-1 --snapshot-id s-1
python scripts/generate_zero_trust_attestation.py --tenant-code acb --freshness-hours 24
```

## Zero-Trust Trusted Criteria

- Internal signed evidence package chain verifies successfully.
- External verifier quorum meets policy (`min_quorum`).
- External verifier weighted score meets policy (`min_weighted_score` with `verifier_weights`).
- External verifier result is fresh within configured window (`freshness_hours`).
- Optional disagreement guardrail (`block_on_disagreement`) does not trigger.
