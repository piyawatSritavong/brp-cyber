# BRP-Cyber: MVP Phase Plan (Cost-Optimized, Enterprise-Ready)

## 1) Scope และข้อจำกัด (สำคัญ)
- โหมด Red Team ในระบบนี้ใช้ **Attack Simulation / Adversarial Emulation** ภายในขอบเขตที่อนุญาตเท่านั้น
- ไม่ใช้ workflow ที่เป็นการเจาะระบบจริงนอกขอบเขตใบอนุญาตของลูกค้า
- เป้าหมาย MVP: พิสูจน์ว่า Red/Blue/Purple orchestration ทำงานครบวงจร, วัดผลได้, และ scale ได้ระดับ enterprise

## 2) Free-First Technology Baseline (เริ่มแบบประหยัด)
- Frontend: Next.js + Tailwind + shadcn/ui
- Backend API: FastAPI (Python)
- Queue/Broker (เริ่มฟรีก่อน): Redis Streams (แทน Kafka ช่วงแรก)
- Database: PostgreSQL + TimescaleDB extension
- Cache/Rate limit: Redis
- Object storage (dev): MinIO (S3-compatible)
- Detection stack: Wazuh + Suricata (OSS)
- Reverse proxy/WAF ingest: Cloudflare logs (free tier เท่าที่มี)
- Orchestration engine: LangGraph
- Notifications: Telegram Bot API (ฟรี) + LINE Notify/LINE Messaging API (ตาม tier ที่ใช้ได้)
- Infra local/staging: Docker Compose
- Infra scale-out phase: Kubernetes (k3s ใน lab, production ไป EKS/GKE ภายหลัง)
- Observability: Prometheus + Grafana + Loki

## 3) Non-Negotiable Enterprise Objectives (ต้องผ่านทุกข้อ)
1. Tenant isolation: แยกข้อมูล, policy, secret ต่อ tenant อย่างเข้มงวด
2. High-throughput ingestion: รับ event จำนวนมากโดยไม่ตกหล่น
3. Deterministic response: Blue ตอบสนองตาม policy อัตโนมัติแบบตรวจสอบย้อนหลังได้
4. Closed-loop learning: Purple สรุป gap แล้วปรับ red simulation + blue rule ได้เป็นวงรอบ
5. Auditability: ทุก action trace ได้ (who/what/when/why)
6. Safety & legal guardrails: allowlist, block safeguards, approval mode สำหรับ action เสี่ยง

## 4) MVP Phases (ไม่ผูกเวลา)

## Phase 0: Foundation & Governance
**Objective:** วางสถาปัตยกรรมและ guardrails ให้พร้อมใช้งานจริงตั้งแต่วันแรก

### Deliverables
- Monorepo structure (frontend/backend/agents/infra/docs)
- Tenant model + RBAC model + secrets policy
- Event taxonomy กลาง (red_event, detection_event, response_event, purple_report_event)
- Legal-safe operating policy (simulation only)

### Exit Criteria
- ทุกทีมใช้ event schema เดียวกันได้
- ทุก service มี correlation_id, tenant_id, trace_id ในทุก log
- มี risk controls พื้นฐานครบ

---

## Phase 1: Blue Core (Detect + Respond)
**Objective:** ทำ Blue Team ให้สร้างคุณค่าจริงก่อน (monitoring + auto response + alert)

### Deliverables
- Ingest logs จาก WAF/Auth/System เข้าสู่ pipeline
- Detection rules พื้นฐาน (เช่น failed login burst ต่อ IP)
- Response engine: firewall API integration + account hardening action
- Telegram/LINE alert pipeline พร้อม template มาตรฐาน
- Incident timeline view (UI)

### Exit Criteria
- เหตุการณ์เข้า-ตรวจจับ-ตอบสนองครบ loop เดียวกันได้
- ลด false positive ด้วย allowlist + suppression policy
- มี audit log ของ action ทุกเคส

---

## Phase 2: Purple Core (Correlation + KPI + Reporting)
**Objective:** เปลี่ยนข้อมูลดิบให้เป็นการตัดสินใจเชิงกลยุทธ์

### Deliverables
- Correlation engine: จับคู่ Red/Blue event ตามช่วงเวลาและเป้าหมาย
- KPI engine: MTTD, MTTR, detection coverage, blocked-before-impact rate
- Daily executive report per tenant (JSON + PDF)
- Recommendation engine: policy tuning suggestions

### Exit Criteria
- รายงานรายวันแยก tenant อัตโนมัติ
- มีข้อเสนอแนะที่นำไปตั้งค่าระบบได้จริง
- ผู้ใช้เห็น timeline "attack -> detect -> mitigate" ได้ชัดเจน

---

## Phase 3: Red Simulation Core (Safe Adversarial Emulation)
**Objective:** สร้างแรงกดดันเชิงทดสอบให้ Blue/Purple โดยไม่ผิดกฎหมาย

### Deliverables
- Scenario library (credential stuffing simulation, endpoint probing simulation, suspicious auth pattern replay)
- Red agent scheduler (policy-driven, bounded rate)
- Safety controls: target allowlist, max-rate, kill-switch, simulation boundary tags
- Real-time stream ไป Purple โดยตรง

### Exit Criteria
- Red สร้าง event simulation ต่อเนื่องได้โดยไม่กระทบ production stability
- Blue ตรวจจับได้ตาม KPI ขั้นต่ำที่กำหนด
- Purple เห็น gap ระหว่าง expected vs actual detection

---

## Phase 4: Full Orchestration Loop (Red <-> Blue <-> Purple)
**Objective:** ปิดวงจรอัตโนมัติและวัดผลการพัฒนาในแต่ละรอบ

### Deliverables
- LangGraph state machine ครบ 3 ทีม
- Policy feedback loop: Purple ปรับ threshold/rules และสั่ง Red เปลี่ยน scenario
- Conflict resolver (priority + cooldown + human-approval mode)
- Per-tenant strategy profile (conservative/balanced/aggressive)

### Exit Criteria
- สามารถรัน continuous cycle ต่อ tenant ได้
- ทุก loop มี measurable improvement อย่างน้อย 1 KPI
- ไม่มี action ที่หลุด guardrail

---

## Phase 5: Enterprise Scale Readiness
**Objective:** ยกระดับจาก MVP ไป platform สำหรับลูกค้าจำนวนมาก

### Deliverables
- Multi-tenant control plane + self-serve onboarding
- Queue partitioning strategy + worker autoscaling
- Cost controls: model routing (SLM-first), token budget per tenant
- SLO/SLA dashboards (latency, event loss, response success)
- DR/Backup + incident runbooks

### Exit Criteria
- ผ่าน load test ตามเป้าหมาย throughput ที่กำหนด
- ระบบไม่ cross-tenant data leak
- ค่าใช้จ่ายต่อ tenant อยู่ในงบที่รับได้

## 5) KPI Framework (ใช้ตัดสินผ่าน/ไม่ผ่าน phase)
- Detection latency (P50/P95)
- Mitigation latency (P50/P95)
- False positive rate / False negative proxy
- Incident containment rate
- Red scenario coverage
- Purple recommendation adoption rate
- Event loss rate
- Cost per 10k events

## 6) Recommended Repo Structure (เริ่มทันที)
```text
BRP-Cyber/
  frontend/
  backend/
    app/
    agents/
      blue/
      purple/
      red_sim/
    schemas/
    workers/
  infra/
    docker/
    k8s/
    terraform/
  docs/
    MVP_PHASE_PLAN.md
    PHASE_CHECKLIST.md
```

## 7) Governance Rules (บังคับใช้ตั้งแต่ Phase 0)
- ทุก event ต้องมี tenant_id + correlation_id
- ทุก automated response ต้องมี reason_code
- ทุก block action ต้องผ่าน allowlist check ก่อน
- ทุก recommendation ต้อง track ว่าถูกนำไปใช้หรือไม่
- ทุก phase ต้องมี rollback strategy
