# Legal Evidence Export Profile

## Purpose
จัดรูปแบบ evidence สำหรับกระบวนการกฎหมาย/ตรวจสอบภายนอก โดยผสานผล verify ของ audit pack, transparency log และ notarization receipt

## Export Endpoint
- `POST /control-plane/audit-pack/legal-evidence/export?destination_dir=`

## Export Script
- `backend/scripts/export_legal_evidence_profile.py`

## Profile Content
- Audit pack reference (`pack_id`, `manifest_path`, `manifest_sha256`)
- Verification result ของ manifest
- Transparency status ล่าสุด
- Notarization receipt (provider-specific)

## Notarization Providers
- `local_digest` (default)
- `webhook` (external service)

Config:
- `CONTROL_PLANE_NOTARIZATION_PROVIDER`
- `CONTROL_PLANE_NOTARIZATION_WEBHOOK_URL`
- `CONTROL_PLANE_NOTARIZATION_API_KEY`
