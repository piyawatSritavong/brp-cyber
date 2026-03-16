# Phase 108 Status

## Title
Red Multi-Language Exploit Output & Social Compliance Packs

## Objective
ปิด Red future-hardening backlog ที่เหลือ 2 ส่วน:
- multi-language exploit output สำหรับ `Exploit Code Generator`
- richer legal/compliance template packs ต่อ social campaign type

## Delivered
- ขยาย `red_exploit_code_generator` ให้สร้าง script preview หลายภาษา:
  - `python`
  - `bash`
  - `curl`
- เพิ่ม `target_language` ใน plugin binding config และ input summary
- เพิ่ม language-aware lint/export ใน `red_plugin_intelligence.py`
  - lint kind แยกตามภาษา
  - export extension แยก `.py/.sh/.txt`
- เพิ่ม social template-pack catalog สำหรับ campaign type:
  - `awareness`
  - `hr_notice`
  - `finance_notice`
  - `brand_protection`
- เพิ่ม route:
  - `GET /competitive/red/social-simulator/template-packs`
- ขยาย social policy/run payload ให้รองรับ:
  - `campaign_type`
  - `template_pack_code`
  - `evidence_retention_days`
  - `legal_ack_required`
- ปรับหน้า `Red Service` ให้:
  - เลือก exploit output language
  - preview legal notice/compliance controls ของ selected template pack
  - save policy พร้อม retention / legal-ack / approval state ตาม template pack
- แก้ execution approval flag ให้สอดคล้องกับทั้ง site policy และ template-pack approval requirement

## Validation
- `python -m compileall backend/app backend/schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_coworker_plugins.py tests/test_red_plugin_intelligence.py tests/test_red_social_engineering_production.py tests/test_red_social_engineering_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

Result:
- backend compile ผ่าน
- pytest `20 passed`
- frontend typecheck ผ่าน

## Operational Note
Phase นี้ไม่มี schema/table ใหม่

ถ้าใช้ backend/frontend process เดิมอยู่ ให้ restart process เพื่อโหลด code ล่าสุด

## Checklist Impact
- ย้าย Red backlog item ต่อไปนี้ออกจาก `Future Hardening Backlog`:
  - multi-language exploit output นอกเหนือจาก Python draft
  - richer legal/compliance template packs ต่อ social campaign type
- ฝั่ง Red ใน `VIRTUAL_EXPERT_CHECKLIST.md` ไม่มี backlog ค้างแล้ว
