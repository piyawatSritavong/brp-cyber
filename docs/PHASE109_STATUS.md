# Phase 109 Status

## Title
SOAR Marketplace Community/Partner Catalog Expansion

## Objective
ปิด Blue future-hardening backlog เรื่อง `richer community/partner playbook pack catalog beyond starter bundles`

## Delivered
- ขยาย marketplace metadata ต่อ pack:
  - `source_type`
  - `publisher_name`
  - `trust_tier`
  - `version`
  - `featured`
  - `community_tags`
  - `supported_connectors`
  - `install_count`
- เพิ่ม community/partner pack entries beyond starter bundles
- เพิ่ม overview summary:
  - `source_counts`
  - `trust_tier_counts`
  - `featured_pack_count`
- ขยาย API `GET /competitive/soar/marketplace/packs` ให้ filter/search ได้ด้วย:
  - `scope`
  - `source_type`
  - `trust_tier`
  - `connector_source`
  - `search`
  - `featured_only`
- ปรับหน้า `Blue Service` ให้:
  - filter marketplace catalog
  - reload catalog จาก UI
  - เห็น metadata/community tags/connectors/install counts ต่อ pack

## Validation
- `python -m compileall backend/app backend/schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_soar_marketplace_maturity.py tests/test_soar_marketplace_maturity_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

Result:
- backend compile ผ่าน
- pytest `7 passed`
- frontend typecheck ผ่าน

## Operational Note
Phase นี้ไม่มี schema/table ใหม่

ถ้าใช้ process เดิมอยู่ ให้ restart backend/frontend เพื่อโหลด query params และ UI controls ล่าสุด

## Checklist Impact
- ย้าย backlog เรื่อง `richer community/partner playbook pack catalog beyond starter bundles` ออกจาก `VIRTUAL_EXPERT_CHECKLIST.md`
- backlog ที่เหลืออยู่เป็น:
  - Blue vendor depth / deeper callback ingestion
  - Purple control-family mapping / ROI segmentation / graphical heatmap workflow
