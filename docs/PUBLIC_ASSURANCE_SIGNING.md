# Public Assurance Signing

This document describes signing and verification flow for public assurance snapshots.

## Generate Snapshot

```bash
cd backend
python scripts/generate_signed_public_assurance.py --destination-dir ./tmp/compliance/public_assurance --limit 1000
```

## Verify Signature Chain

```bash
cd backend
python scripts/verify_signed_public_assurance.py --limit 1000
```

## API Surface

- Public read-only:
  - `GET /assurance/public/signed-summary`
  - `GET /assurance/public/signed-summary/verify`
- Control-plane operational:
  - `POST /control-plane/audit-pack/public-assurance/sign`
  - `GET /control-plane/audit-pack/public-assurance/sign-status`
  - `GET /control-plane/audit-pack/public-assurance/sign-verify`

## Security Notes

- Signature chain includes `prev_signature` to prevent silent record replacement or reordering.
- Snapshot payload includes assurance summary plus orchestration objective readiness aggregate.
- This feed provides external trust evidence and does not replace internal objective-gate enforcement.
