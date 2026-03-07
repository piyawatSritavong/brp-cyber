# Objective Gate Dashboard API

ใช้ API กลุ่มนี้สำหรับหน้า Dashboard ที่ต้องการแสดงสถานะ orchestration readiness แบบ enterprise

## 1) Tenant Gate Snapshot
`GET /enterprise/objective-gate/{tenant_id}`
- ประเมิน gate ล่าสุดของ tenant
- โดย default จะ persist snapshot ลง history

## 2) Tenant Blockers
`GET /enterprise/objective-gate-blockers/{tenant_id}`
- คืนค่า blocker reason ที่อ่านง่ายสำหรับ UI
- เหมาะกับ side panel หรือ tenant detail card

## 3) Tenant History
`GET /enterprise/objective-gate-history/{tenant_id}?limit=100`
- คืน snapshot history ของ gate ต่อ tenant
- ใช้ทำ trend chart รายวัน

## 4) Cross-Tenant Overview
`GET /enterprise/objective-gate-dashboard?limit=100`
- สรุป tenant ที่ผ่าน/ไม่ผ่าน
- เรียง tenant ที่ fail ก่อน

### Response Shape (overview)
```json
{
  "total_tenants": 120,
  "passing_tenants": 90,
  "failing_tenants": 30,
  "rows": [
    {
      "tenant_id": "...",
      "overall_pass": false,
      "failed_gate_count": 2,
      "blockers": [
        {"gate": "blue", "reason": "detect_or_mitigate_below_threshold"},
        {"gate": "compliance", "reason": "auditability_or_guardrail_check_failed"}
      ]
    }
  ]
}
```

## UI Notes
- ใช้สี `green/red` ตาม `overall_pass`
- แสดง badge ตาม `failed_gate_count`
- คลิก tenant card แล้วดึง blockers + remediation ต่อ
