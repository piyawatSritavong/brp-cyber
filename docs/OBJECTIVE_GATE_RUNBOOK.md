# Objective Gate Remediation Runbook

ใช้ runbook นี้เมื่อ tenant ถูกบล็อก `status=blocked_by_objective_gate` ระหว่าง promote ไป `production`

## 1) Red Gate Fail
- อาการ: `gates.red.pass=false`
- ตรวจ: allowlist target และ red scenario profile
- แก้: เพิ่ม/แก้ `red_allowed_targets`, รัน orchestration อย่างน้อย 3 cycles ซ้ำ
- ยืนยัน: completion rate >= 90%, execution ratio >= 95%, ไม่มี allowlist rejection

## 2) Blue Gate Fail
- อาการ: coverage ต่ำ หรือ blocked-before-impact ต่ำ
- ตรวจ: ingest auth/WAF logs, firewall auto-block, notifier channel
- แก้: ปรับ threshold/cooldown ผ่าน policy feedback, ทดสอบ replay auth burst
- ยืนยัน: detection coverage >= threshold, mitigation event ปรากฏใน stream

## 3) Purple Gate Fail
- อาการ: ไม่มี report หรือไม่มี recommendation tracking
- ตรวจ: `purple_reports:{tenant_id}`, pending/applied actions
- แก้: trigger report generation และบันทึก recommendation adoption
- ยืนยัน: report + recommendation tracking มีข้อมูลล่าสุด

## 4) Closed-Loop Gate Fail
- อาการ: KPI trend ไม่ดีขึ้นตามสัดส่วนขั้นต่ำ
- ตรวจ: `orchestrator_kpi_trend:{tenant_id}`
- แก้: รัน multi-cycle เพิ่ม พร้อมบังคับ strategy profile ที่เหมาะสม
- ยืนยัน: improvement ratio >= threshold

## 5) Enterprise Gate Fail
- อาการ: queue lag สูงหรือค่าใช้จ่ายเกินงบ
- ตรวจ: `/enterprise/queue/stats`, `/enterprise/autoscaler/status`, `/enterprise/cost/{tenant_id}`
- แก้: reconcile autoscaler, ปรับ model routing เป็น SLM-first
- ยืนยัน: lag และ monthly cost กลับเข้า threshold

## 6) Compliance Gate Fail
- อาการ: audit entries ไม่พอ หรือมี guardrail violation
- ตรวจ: `/control-plane/audit`, objective gate snapshot
- แก้: บังคับ admin actions ผ่าน control-plane APIs เท่านั้น, แก้ policy ที่ละเมิด
- ยืนยัน: audit trail ครบและ gate ผ่าน

## Promotion Flow (แนะนำ)
1. เรียก `GET /enterprise/objective-gate/{tenant_id}`
2. ถ้าไม่ผ่าน เรียก `GET /enterprise/objective-gate-remediation/{tenant_id}`
3. แก้ตาม action list
4. snapshot gate ซ้ำ
5. ค่อยเรียก `POST /control-plane/tenant/status` เป็น `production`

## Production v1 Final Closure
- ใช้ `docs/PRODUCTION_V1_GO_LIVE_RUNBOOK.md` สำหรับ gate ปิดงานก่อน Go-Live
- ต้องผ่าน Objective Gate + Cost Guardrail + Runbook Checklist ครบพร้อมกัน
- หลัง Go-Live ให้เปิดใช้งาน Post-Go-Live Burn-Rate Guard เพื่อ auto rollback เมื่อ SLO burn-rate เกิน threshold
