# Assurance Bulletin Delivery

Policy-driven customer webhook delivery for signed tenant risk bulletins.

## APIs

- `POST /control-plane/assurance/slo/{tenant_code}/distribution/upsert`
- `GET /control-plane/assurance/slo/{tenant_code}/distribution`
- `POST /control-plane/assurance/slo/{tenant_code}/bulletin/deliver`
- `GET /control-plane/assurance/slo/{tenant_code}/bulletin/receipts`
- `POST /control-plane/assurance/slo/{tenant_code}/bulletin/proof/export`
- `GET /control-plane/assurance/slo/{tenant_code}/bulletin/proof/status`
- `GET /control-plane/assurance/slo/{tenant_code}/bulletin/proof/verify`

## Policy Fields

- `enabled`
- `signed_only`
- `webhook_url`
- `auth_header`
- `timeout_seconds`
- `retry_attempts`
- `retry_backoff_seconds`

## Scripts

```bash
cd backend
python scripts/deliver_signed_tenant_bulletins.py --limit 1
python scripts/generate_bulletin_delivery_receipts_report.py --limit 100
python scripts/export_signed_delivery_proof.py --tenant-code acb --limit 100
python scripts/verify_signed_delivery_proof.py --tenant-code acb --limit 1000
```

## Receipt Tracking

Each delivery attempt writes a receipt entry with:
- timestamp
- status
- snapshot_id
- webhook target
- HTTP status / error context
