# Phase 110 Status

## Title
Purple ROI Segmentation & Portfolio Filters

## Objective
ปิด Purple future-hardening backlog เรื่อง `finer ROI segmentation/filtering ระดับ tenant/site/portfolio`

## Delivered
- ขยาย ROI trends API ให้ filter ได้ด้วย:
  - `metric_focus`
  - `min_automation_coverage_pct`
  - `min_noise_reduction_pct`
- ขยาย ROI portfolio API ให้ filter/sort ได้ด้วย:
  - `site_code`
  - `status`
  - `min_automation_coverage_pct`
  - `min_noise_reduction_pct`
  - `sort_by`
- เพิ่ม summary fields สำหรับ:
  - filtered counts
  - total before filter
  - applied filter set
- ปรับหน้า `Purple Service` ให้:
  - เลือก trend metric focus
  - ตั้ง threshold สำหรับ automation/noise
  - filter portfolio ด้วย site/status
  - sort portfolio rows ตาม metric สำคัญ
  - reload ROI slice จากหน้าเดียว

## Validation
- `python -m compileall backend/app backend/schemas`
- `cd backend && PYTHONPATH=. pytest -q tests/test_purple_roi_dashboard_executive.py tests/test_purple_roi_dashboard_api.py`
- `cd frontend && ./node_modules/.bin/tsc --noEmit`

Result:
- backend compile ผ่าน
- pytest `8 passed`
- frontend typecheck ผ่าน

## Operational Note
Phase นี้ไม่มี schema/table ใหม่

restart backend/frontend หากมี process เดิมค้างอยู่เพื่อโหลด query params และ UI controls ล่าสุด

## Checklist Impact
- ย้าย backlog เรื่อง `finer ROI segmentation/filtering ระดับ tenant/site/portfolio` ออกจาก `VIRTUAL_EXPERT_CHECKLIST.md`
- backlog ที่เหลืออยู่:
  - Blue deeper vendor coverage
  - Blue deeper live connector callback ingestion
  - Purple deeper control-family mapping
  - Purple graphical heatmap export + ATT&CK layer import/edit workflow
