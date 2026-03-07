# External Audit Pack

## Objective
สร้างแพ็กหลักฐานที่พร้อมส่ง auditor ภายนอก โดยรวม evidence ที่สำคัญและ hash manifest สำหรับตรวจสอบความสมบูรณ์

## Included Artifacts
- `control_plane_compliance_evidence.json`
- `control_plane_governance_report.json`
- `governance_attestation_bundle_*.json`
- `manifest.json` (รวม checksum ของ artifacts)

## APIs
- `POST /control-plane/audit-pack/generate?limit=&destination_dir=`
- `GET /control-plane/audit-pack/status?limit=`
- `POST /control-plane/audit-pack/verify?manifest_path=`
- `POST /control-plane/audit-pack/publish?dry_run=`
- `GET /control-plane/audit-pack/publication-status?limit=`

## Scripts
- Generate: `backend/scripts/generate_external_audit_pack.py`
- Verify: `backend/scripts/verify_external_audit_pack.py`
- Publish latest: `backend/scripts/publish_external_audit_pack.py`
- Publication status: `backend/scripts/external_audit_publication_status.py`

## Automation
- Pack workflow: `.github/workflows/external-audit-pack.yml`
- Publication workflow: `.github/workflows/external-audit-pack-publication.yml`

## Verification Model
- ทุก artifact ใน pack จะถูกระบุใน `manifest.json`
- `verify_external_audit_pack` จะคำนวณ SHA256 ใหม่เทียบกับค่าใน manifest
- หาก mismatch/missing จะ report รายการ failures

## Public Verification Metadata
- publication metadata จะระบุ:
  - `manifest_sha256`
  - verification status (`valid`, `failure_count`)
  - trust anchor ของ governance attestation (provider/algorithm/key_ref)
