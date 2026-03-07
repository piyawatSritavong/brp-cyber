# Control Plane Governance Attestation

## Purpose
สร้างหลักฐาน cryptographic chain สำหรับ governance reports เพื่อให้ตรวจสอบย้อนหลังได้ว่า report ไม่ถูกแก้ไข

## Signer Providers
- `hmac` (default): เซ็นด้วย HMAC-SHA256
- `aws_kms`: เซ็นด้วย AWS KMS asymmetric signing key

Config ที่เกี่ยวข้อง:
- `CONTROL_PLANE_GOVERNANCE_SIGNER_PROVIDER`
- `CONTROL_PLANE_GOVERNANCE_ATTESTATION_HMAC_KEY`
- `CONTROL_PLANE_GOVERNANCE_SIGNER_KMS_KEY_ID`
- `CONTROL_PLANE_GOVERNANCE_SIGNER_KMS_SIGNING_ALGORITHM`
- `CONTROL_PLANE_GOVERNANCE_SIGNER_KMS_REGION`
- `CONTROL_PLANE_GOVERNANCE_SIGNER_KMS_ENDPOINT_URL`

## Endpoints
- `POST /control-plane/governance/attest?limit=`
- `GET /control-plane/governance/attestation-status?limit=`
- `GET /control-plane/governance/attestation-verify?limit=`
- `POST /control-plane/governance/attestation-export?destination_dir=`

## Detached Bundle
การ export จะได้ detached bundle JSON ที่มี:
- `message_fields`
- `message`
- `signature` (provider/algorithm/encoding/key_ref)
- `artifacts.report_hash`

## Third-Party Verification CLI
- `backend/scripts/verify_governance_attestation_bundle.py --bundle <path>`
- สำหรับ provider `hmac` สามารถส่ง `--hmac-key` เพื่อ verify แบบ offline
- สำหรับ provider `aws_kms` ใช้ KMS verify ผ่าน credential ที่ runtime

## Automation
- Generate: `backend/scripts/generate_signed_governance_attestation.py`
- Verify bundle: `backend/scripts/verify_governance_attestation_bundle.py`
- Workflow: `.github/workflows/control-plane-governance-attestation.yml`
