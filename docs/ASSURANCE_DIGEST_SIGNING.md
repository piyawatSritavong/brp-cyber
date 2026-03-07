# Assurance Digest Signing

Signed assurance artifacts for executive and customer communication.

## Control-Plane APIs

- `POST /control-plane/assurance/slo/executive-digest/sign`
- `GET /control-plane/assurance/slo/executive-digest/sign-status`
- `GET /control-plane/assurance/slo/executive-digest/sign-verify`
- `POST /control-plane/assurance/slo/{tenant_code}/bulletin/sign`
- `GET /control-plane/assurance/slo/{tenant_code}/bulletin/sign-status`
- `GET /control-plane/assurance/slo/{tenant_code}/bulletin/sign-verify`

## Public APIs

- `GET /assurance/public/tenant/{tenant_code}/bulletin`
- `GET /assurance/public/tenant/{tenant_code}/bulletin/verify`

## Scripts

```bash
cd backend
python scripts/generate_signed_assurance_executive_digest.py
python scripts/generate_signed_tenant_bulletins.py
python scripts/verify_signed_assurance_digests.py
```

## Security Notes

- Signature chains include `prev_signature` continuity checks.
- Bulletin stream is tenant-scoped, allowing customer-specific shareable trust artifacts.
