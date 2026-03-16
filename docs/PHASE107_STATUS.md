# Phase 107 Status

## Title
Red Plugin External Sync & Threat-Pack Publish Bridge

## Objective
ปิด Red hardening backlog สองส่วนที่ยังเหลือ:
- external feed sync เข้า `Exploit Code Generator` / `Nuclei AI-Template Writer`
- one-click publish จาก `red_template_writer` output ไปเป็น `ThreatContentPack`

## Delivered
- เพิ่ม persistent sync source/run models:
  - `red_plugin_intelligence_sync_sources`
  - `red_plugin_intelligence_sync_runs`
- เพิ่ม service สำหรับ:
  - upsert/list sync source
  - run sync จาก external `json_feed/jsonl`
  - scheduler integration
  - publish template output ไปเป็น threat pack
- เพิ่ม competitive APIs:
  - `GET/POST /competitive/sites/{site_id}/red/plugin-intelligence/sync-sources`
  - `POST /competitive/sites/{site_id}/red/plugin-intelligence/sync`
  - `GET /competitive/sites/{site_id}/red/plugin-intelligence/sync-runs`
  - `POST /competitive/red/plugin-intelligence/scheduler/run`
  - `POST /competitive/sites/{site_id}/red/plugins/red_template_writer/publish-threat-pack`
- ผูก scheduler เข้ากับ autonomous runtime และเพิ่ม env flags
- ปรับหน้า `Red Service` ให้:
  - save sync source
  - dry-run/apply sync
  - run scheduler
  - publish threat pack
  - ดู sync source/run summary

## Validation
- `python -m compileall backend/app backend/schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_red_plugin_intelligence.py tests/test_red_plugin_intelligence_api.py tests/test_autonomous_runtime.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

Result:
- backend compile ผ่าน
- pytest `11 passed`
- frontend typecheck ผ่าน

## Operational Note
Phase นี้เพิ่มตารางใหม่:
- `red_plugin_intelligence_sync_sources`
- `red_plugin_intelligence_sync_runs`

ถ้ายังไม่ได้ sync schema ใน environment ที่ใช้อยู่:
1. restart backend
2. เรียก `POST /bootstrap/phase0/init-db` 1 ครั้ง

## Checklist Impact
- ย้ายความสามารถ `external sync source ingestion` และ `one-click publish threat pack` ออกจาก future backlog ใน `VIRTUAL_EXPERT_CHECKLIST.md`
- baseline requirement เดิมยังคง complete 100%
