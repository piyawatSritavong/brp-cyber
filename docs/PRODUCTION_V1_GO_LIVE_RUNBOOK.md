# Production v1 Go-Live Runbook (Final Closure)

ใช้เอกสารนี้เพื่อปิดงานก่อน promote tenant ไป `production` สำหรับเวอร์ชัน 1

## Final Gate Criteria

ต้องผ่านทุกข้อพร้อมกัน:
- Objective Gate ผ่าน (`overall_pass=true`)
- Cost guardrail ไม่มี `breached` และไม่มี `anomaly`
- Runbook checklist ครบทุก item

## Runbook Checklist Items

- `dr_smoke_passed`
- `security_signoff`
- `legal_signoff`
- `rollback_validated`
- `oncall_ready`
- `observability_ready`
- `incident_playbook_ready`
- `change_ticket_linked`

## Control-Plane APIs

- `POST /control-plane/production-v1/runbook/upsert`
- `GET /control-plane/production-v1/runbook/{tenant_code}`
- `GET /control-plane/production-v1/readiness-final/{tenant_code}`
- `POST /control-plane/production-v1/go-live/close`
- `GET /control-plane/production-v1/go-live/closure-history?tenant_code=&limit=`
- `POST /control-plane/production-v1/burn-rate/profile/upsert`
- `GET /control-plane/production-v1/burn-rate/profile/{tenant_code}`
- `POST /control-plane/production-v1/burn-rate/evaluate/{tenant_code}?apply=`
- `GET /control-plane/production-v1/burn-rate/history?tenant_code=&limit=`

## Recommended Closure Flow

1. อัปเดต checklist ผ่าน `runbook/upsert`
2. ตรวจ readiness ผ่าน `readiness-final/{tenant_code}`
3. หาก `production_v1_ready=true` ให้ปิดงานด้วย `go-live/close`
4. ตรวจ `closure-history` และแนบกับ change ticket

## Script / Workflow

- Script: `backend/scripts/report_production_v1_readiness.py`
- Workflow: `.github/workflows/production-v1-readiness-gate.yml`

## Post-Go-Live Guard

หลัง Go-Live ให้ตั้ง burn-rate profile และประเมินอย่างต่อเนื่อง:
- Script: `backend/scripts/report_production_v1_burn_rate_guard.py`
- Workflow: `.github/workflows/production-v1-burn-rate-guard.yml`
