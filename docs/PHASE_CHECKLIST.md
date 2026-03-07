# BRP-Cyber Phase Checklist

ใช้เอกสารนี้เป็นเกณฑ์ตรวจรับงาน (`Done/Not Done`) ต่อ Phase โดยไม่อิงเวลา

## Progress Snapshot (2026-03-06)
- [x] Phase 0: Foundation & Governance (`Completed`)
- [x] Phase 1: Blue Core (`Completed`)
- [x] Phase 2: Purple Core (`Completed`)
- [x] Phase 3: Red Simulation Core (`Completed`)
- [x] Phase 4: Full Orchestration (`Completed`)
- [x] Phase 5: Enterprise-Scale Readiness (`Completed`)
- [x] Phase 6: Control Plane & Operational Readiness (`Completed`)
- [x] Phase 7: Objective Gate & Production Readiness Proof (`Completed`)
- [x] Phase 8: Identity Federation & Immutable Retention Validation (`Completed`)
- [x] Phase 9: Control Plane Governance & Policy-as-Code (`Completed`)
- [x] Phase 10: Cryptographic Hardening & External Trust (`Completed`)
- [x] Phase 11: Independent Assurance & External Audit Pack (`Completed`)
- [x] Phase 12: External Trust Anchors & Immutable Publication (`Completed`)
- [x] Phase 13: Transparency & Legal Notarization (`Completed`)
- [x] Phase 14: Public Assurance Surface & Regulatory Profiles (`Completed`)
- [x] Phase 15: Enterprise Orchestration Assurance Aggregation (`Completed`)
- [x] Phase 16: Signed Public Assurance Feed & Verification (`Completed`)
- [x] Phase 17: Customer Assurance SLA Profiles & Evidence Contracts (`Completed`)
- [x] Phase 18: Assurance Breach Auto-Remediation & Escalation (`Completed`)
- [x] Phase 19: Tenant Remediation Policy Packs & Approval Integration (`Completed`)
- [x] Phase 20: Remediation Effectiveness Scoring & Rollback Guardrails (`Completed`)
- [x] Phase 21: Cross-Tenant Risk Heatmap & Adaptive Policy Loop (`Completed`)
- [x] Phase 22: Tenant Assurance SLO, Breach Budget, and Executive Digest (`Completed`)
- [x] Phase 23: Executive Digest Signing & Customer Risk Bulletin (`Completed`)
- [x] Phase 24: Signed Bulletin Distribution Policy & Receipt Tracking (`Completed`)
- [x] Phase 25: Delivery Retry/Backoff Policy & Signed Delivery Proof (`Completed`)
- [x] Phase 26: Public Delivery-Proof Verification & Auditor Proof Index (`Completed`)
- [x] Phase 27: Tenant Verifier Kit & One-Click Evidence Package Index (`Completed`)
- [x] Phase 28: Signed Tenant Evidence Package Chain & Public Verification (`Completed`)
- [x] Phase 29: External Verifier Import & Zero-Trust Attestation (`Completed`)
- [x] Phase 30: Verifier API Keys & Signed Receipt Registry (`Completed`)
- [x] Phase 31: Verifier Policy Enforcement & Multi-Verifier Quorum (`Completed`)
- [x] Phase 32: Weighted Trust Scoring & Disagreement Guardrails (`Completed`)
- [x] Phase 33: One-Click Orchestration Activation & Auto Scheduler (`Completed`)
- [x] Phase 34: Pilot Session Hardening & Objective-Gated Start (`Completed`)
- [x] Phase 35: Self-Serve Pilot Onboarding & Scoped Operator Roles (`Completed`)
- [x] Phase 36: Pilot Safety Auto-Stop & Incident Escalation (`Completed`)
- [x] Phase 37: Multi-tenant Pilot Concurrency Guardrails & Rate Budgets (`Completed`)
- [x] Phase 38: Fairness Scheduling, Priority Tiers, and Backpressure (`Completed`)
- [x] Phase 39: Tenant Rollout Rings & Canary Orchestration Controls (`Completed`)
- [x] Phase 40: KPI-Driven Rollout Auto Promote/Demote & Rollback Signals (`Completed`)
- [x] Phase 41: Rollout Anti-Flapping Hysteresis & Cooldown Windows (`Completed`)
- [x] Phase 42: Rollout Policy Contracts & Approval Gates (`Completed`)
- [x] Phase 43: Dual-Control Rollout Approval & Signed Evidence (`Completed`)
- [x] Phase 44: Rollout Evidence Chain Verification & Integrity Ops (`Completed`)
- [x] Phase 45: Notarized Rollout Evidence Bundles & Export Ops (`Completed`)
- [x] Phase 46: Public Verifier Bundle & Third-Party Audit Hand-off (`Completed`)
- [x] Phase 47: Time-Bound Handoff Sessions, IP Allowlist, and Access Receipts (`Completed`)
- [x] Phase 48: Handoff Access Anomaly Detection & Auto-Revoke Policies (`Completed`)
- [x] Phase 49: Risk-Scored Handoff Trust Model & Adaptive Session Hardening (`Completed`)
- [x] Phase 50: Handoff Risk Governance & Auto-Containment Playbooks (`Completed`)
- [x] Phase 51: Cross-Tenant Handoff Risk Federation & Enterprise Escalation Matrix (`Completed`)
- [x] Phase 52: Handoff Federation SLO, Breach Budget, and Auto-Escalation Notifications (`Completed`)
- [x] Phase 53: Signed Federation SLO Digest Chain & Verification (`Completed`)
- [x] Phase 54: Public Federation Verifier Bundle & External Verification Surface (`Completed`)
- [x] Phase 55: Federation Policy Drift Detection & Auto-Reconciliation (`Completed`)
- [x] Phase 56: Cross-Region Orchestration Failover Resilience & Signed Drills (`Completed`)
- [x] Phase 57: Cost Guardrails & Model Routing Optimization Controls (`Completed`)
- [x] Phase 58: Runtime Cost Guardrail Enforcement & Public Verifier Surface (`Completed`)
- [x] Phase 59: Cost Anomaly Detection & Preemptive Throttling Controls (`Completed`)
- [x] Phase 60: Cost Anomaly Federation + Production v1 Final Go-Live Closure (`Completed`)
- [x] Phase 61: Post-Go-Live SLO Burn-Rate Guard & Auto Rollback Gate (`Completed`)

## Phase 0 Checklist: Foundation & Governance
- [ ] สร้าง repo structure ตามมาตรฐาน (frontend/backend/agents/infra/docs)
- [ ] กำหนด tenant data model และ RBAC model
- [ ] นิยาม event schema กลาง (`red_event`, `detection_event`, `response_event`, `purple_report_event`)
- [ ] เพิ่ม `tenant_id`, `correlation_id`, `trace_id` ในทุก event
- [ ] ตั้งค่า centralized logging + metrics baseline (Prometheus/Grafana/Loki)
- [ ] ระบุ policy ด้าน legal/ethical สำหรับ simulation-only
- [ ] เพิ่ม kill-switch สำหรับหยุด automated actions ทั้งระบบ
- [ ] เอกสาร architecture decision record (ADR) ฉบับแรกครบ

## Phase 1 Checklist: Blue Core
- [ ] รับ log จาก WAF/Auth/System ได้อย่างน้อย 3 source
- [ ] Detection rule พื้นฐานทำงานได้ (failed login burst ต่อ IP)
- [ ] Auto-response ไป firewall API ได้สำเร็จ
- [ ] ตรวจ allowlist ก่อน block ทุกครั้ง
- [ ] ส่งแจ้งเตือน Telegram/LINE พร้อม incident summary
- [ ] บันทึก audit trail ของ action ทุกเหตุการณ์
- [ ] มี dashboard แสดง incident timeline ต่อ tenant
- [ ] วัดค่า latency detect/mitigate ได้ (P50/P95)

## Phase 2 Checklist: Purple Core
- [ ] Correlate event ระหว่าง Red/Blue ได้ด้วย correlation_id/time window
- [ ] สร้าง KPI: MTTD, MTTR, coverage, block effectiveness
- [ ] สร้าง report รายวันต่อ tenant (JSON/PDF)
- [ ] แสดง gap analysis (detect miss / response delay)
- [ ] Recommendation engine สร้างข้อเสนอปรับ rule ได้
- [ ] มีสถานะติดตามว่า recommendation ถูกนำไปใช้หรือไม่
- [ ] Dashboard ผู้บริหารดูภาพรวมราย tenant ได้

## Phase 3 Checklist: Red Simulation Core
- [ ] สร้าง scenario library แบบปลอดภัย (simulation/replay/emulation)
- [ ] เพิ่ม scheduler สำหรับรัน scenario ต่อ tenant
- [ ] จำกัด rate + concurrency ตาม policy
- [ ] บังคับ target allowlist ก่อนเริ่มทุก scenario
- [ ] Tag ทุก event ว่าเป็น simulation เพื่อป้องกันสับสนกับ attack จริง
- [ ] ส่ง red activity log ไป Purple แบบ near real-time
- [ ] ทดสอบว่าไม่มี service disruption จาก simulation

## Phase 4 Checklist: Full Red/Blue/Purple Orchestration
- [ ] LangGraph orchestration flow ครบสามบทบาท
- [ ] Purple สั่งปรับ Blue threshold/rules ได้ผ่าน policy API
- [ ] Purple สั่งปรับ Red scenario profile ได้
- [ ] มี conflict resolution (priority, cooldown, approval mode)
- [ ] รัน continuous loop ต่อ tenant ได้อย่างเสถียร
- [ ] มีหลักฐาน measurable improvement อย่างน้อย 1 KPI ต่อรอบ
- [ ] มี rollback plan หาก recommendation ทำให้ระบบแย่ลง

## Phase 5 Checklist: Enterprise-Scale Readiness
- [ ] รองรับ multi-tenant onboarding แบบอัตโนมัติ
- [ ] ทดสอบ load พร้อม queue partitioning + autoscaling
- [ ] ทดสอบ data isolation (no cross-tenant leakage)
- [ ] ตั้ง per-tenant quotas (events, actions, model tokens)
- [ ] มี model routing (SLM-first, escalate to larger model)
- [ ] มี cost dashboard (`cost per tenant`, `cost per 10k events`)
- [ ] ตั้งค่า SLO/SLA monitoring + alerting
- [ ] มี DR plan และ backup/restore test ผ่าน

## Phase 6 Checklist: Control Plane & Operational Readiness
- [x] Control plane onboarding + lifecycle + key rotation ครบ
- [x] Admin auth/scopes/tenant delegation ครบ
- [x] Control-plane audit stream + listing ครบ
- [x] SIEM export incremental + failed batch replay ครบ
- [x] Immutable signed archive chain + verify ครบ
- [x] Archive offload (filesystem/S3 mode) ครบ
- [x] DR smoke + runbook + scheduled workflows ครบ
- [x] Admin activity + SIEM export/replay/offload automation ครบ

## Phase 7 Checklist: Objective Gate & Production Readiness Proof
- [x] Objective gate evaluator service (Red/Blue/Purple/Closed-loop/Enterprise/Compliance)
- [x] Enterprise API endpoint `/enterprise/objective-gate/{tenant_id}`
- [x] Enterprise APIs for gate history + remediation actions
- [x] Test coverage สำหรับ pass/fail gate baseline
- [x] ผูก objective gate เข้ากับ control-plane tenant status policy (enforce gate before prod flag)
- [x] เพิ่ม historical gate trend/report per tenant รายวัน
- [x] เพิ่ม runbook สำหรับ gate failure remediation
- [x] เพิ่ม backend APIs สำหรับ dashboard gate status + blocker reasons
- [x] เพิ่ม frontend dashboard panel for gate status and blocker reasons

## Phase 8 Checklist: Identity Federation & Immutable Retention Validation
- [x] เพิ่ม auth posture policy บังคับ production ให้ใช้ IdP
- [x] ปิด local bootstrap token issuance เมื่อ policy ไม่อนุญาต
- [x] เพิ่ม endpoint ตรวจ auth posture (`/control-plane/auth/posture`)
- [x] ขยาย IdP claim mapping (scope list/string + tenant scope fallback)
- [x] เพิ่ม S3 Object Lock validator service (dry-run + runtime validate)
- [x] เพิ่ม control-plane endpoint สำหรับ S3 Object Lock validation
- [x] เพิ่ม automation script/workflow สำหรับ S3 Object Lock validation
- [x] เพิ่ม control-plane evidence report รวม auth hardening + retention compliance

## Phase 9 Checklist: Control Plane Governance & Policy-as-Code
- [x] เพิ่ม policy-as-code service สำหรับ control-plane actions เสี่ยง
- [x] รองรับ policy mode `permissive` และ `enforce`
- [x] เพิ่ม governance dashboard summary จาก audit trail
- [x] เพิ่ม endpoints: `/control-plane/governance/policy`, `/control-plane/governance/dashboard`
- [x] เพิ่ม governance policy doc + operational rules
- [x] เพิ่ม scheduled governance report generation
- [x] เชื่อม governance panel เข้า frontend dashboard
- [x] เพิ่ม signed attestation export สำหรับ governance reports

## Phase 10 Checklist: Cryptographic Hardening & External Trust
- [x] เพิ่ม signer provider แบบเลือกได้ (`hmac`, `aws_kms`)
- [x] รองรับ detached signature bundle export
- [x] เพิ่ม verify function สำหรับ detached bundle
- [x] เพิ่ม third-party verifier CLI
- [x] เพิ่มเอกสาร attestation สำหรับ auditor

## Phase 11 Checklist: Independent Assurance & External Audit Pack
- [x] เพิ่ม external audit pack service (generate/status/verify)
- [x] รวม compliance evidence + governance report + attestation bundle
- [x] เพิ่ม manifest-based checksum verification
- [x] เพิ่ม control-plane endpoints สำหรับ audit pack
- [x] เพิ่ม scripts สำหรับ generate/verify audit pack
- [x] เพิ่ม scheduled workflow สำหรับ audit pack automation

## Phase 12 Checklist: External Trust Anchors & Immutable Publication
- [x] เพิ่ม publication pipeline สำหรับ latest audit pack
- [x] รองรับ publication mode `filesystem` และ `s3`
- [x] รองรับ policy บล็อก publish เมื่อ pack verify ไม่ผ่าน
- [x] เพิ่ม public verification metadata ใน publication artifacts
- [x] เพิ่ม control-plane endpoints สำหรับ publish/status
- [x] เพิ่ม scripts/workflow สำหรับ publication operations
- [x] เพิ่ม runbook สำหรับ publication failure handling

## Phase 13 Checklist: Transparency & Legal Notarization
- [x] เพิ่ม transparency log publication pipeline
- [x] เพิ่ม notarization adapter interface แบบ pluggable
- [x] รองรับ local_digest และ webhook notarization provider
- [x] เพิ่ม legal evidence export profile
- [x] เพิ่ม control-plane endpoints สำหรับ transparency + legal evidence
- [x] เพิ่ม scripts/workflow สำหรับ transparency + legal evidence automation

## Phase 14 Checklist: Public Assurance Surface & Regulatory Profiles
- [x] เพิ่ม public read-only assurance API surface
- [x] เพิ่ม regulatory framework templates (`SOC2`, `ISO27001`, `NIST_CSF`)
- [x] เพิ่ม per-framework scorecard จาก trust signals จริง
- [x] เพิ่ม aggregated regulatory overview endpoint
- [x] ผูก assurance endpoints เข้ากับ FastAPI main router
- [x] เพิ่ม automated tests สำหรับ assurance API + scorecard logic
- [x] อัปเดตเอกสารสถานะ Phase และ README ให้ตรงกับ API ที่ deploy

## Phase 15 Checklist: Enterprise Orchestration Assurance Aggregation
- [x] เพิ่ม global objective-gate stream สำหรับ snapshot ข้าม tenant
- [x] เพิ่ม service คำนวณ orchestration objective pass-rates ระดับองค์กร
- [x] เพิ่ม public endpoint สำหรับ orchestration readiness aggregate
- [x] ผูก orchestration readiness เข้า public assurance summary
- [x] เพิ่ม tests สำหรับ stream aggregation และ endpoint response
- [x] อัปเดตเอกสาร Phase/README/Public API ให้ตรงกับของจริง

## Phase 16 Checklist: Signed Public Assurance Feed & Verification
- [x] เพิ่ม signed public assurance snapshot service
- [x] เพิ่ม signature chain persistence + verification logic
- [x] เพิ่ม public API สำหรับ signed summary status/verify
- [x] เพิ่ม control-plane API สำหรับ sign/status/verify operations
- [x] เพิ่ม scripts สำหรับ generate และ verify signed public assurance
- [x] เพิ่ม scheduled GitHub workflow สำหรับ sign + verify
- [x] เพิ่ม tests สำหรับ signing service และ public API integration
- [x] อัปเดตเอกสาร Phase, README, และ Public Assurance API docs

## Phase 17 Checklist: Customer Assurance SLA Profiles & Evidence Contracts
- [x] เพิ่ม tenant-level assurance contract profile service (`upsert/get/evaluate`)
- [x] รองรับ clause สำหรับ `min_overall_pass_rate`, `min_gate_pass_rate`, `max_cost`, `required_frameworks`
- [x] ใช้ objective-gate historical evidence จริงในการประเมิน contract
- [x] เพิ่ม control-plane APIs สำหรับ contract lifecycle และ evaluation
- [x] เพิ่ม automation script/workflow สำหรับ evaluate contracts รายวัน
- [x] เพิ่ม tests สำหรับ contract pass/fail evaluation logic
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 18 Checklist: Assurance Breach Auto-Remediation & Escalation
- [x] เพิ่ม remediation engine จาก assurance contract breach (`unmet_clauses`)
- [x] รองรับ mode `pending_approval` และ `auto_apply`
- [x] เพิ่ม remediation action stream และ status API ต่อ tenant
- [x] ผูก escalation alert ผ่าน notifier channel
- [x] เพิ่ม control-plane APIs สำหรับ trigger remediation + status
- [x] เพิ่ม automation script/workflow สำหรับ remediation รอบรายวัน
- [x] เพิ่ม tests สำหรับ remediation planning และ applied path
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 19 Checklist: Tenant Remediation Policy Packs & Approval Integration
- [x] เพิ่ม tenant policy-pack service สำหรับ remediation governance
- [x] รองรับ policy knobs: `auto_apply_actions`, `force_approval_actions`, `blocked_actions`
- [x] เพิ่ม policy-aware execution path ใน remediation engine
- [x] เพิ่ม endpoint approve/reject สำหรับ assurance remediation pending actions
- [x] เพิ่ม endpoint upsert/get policy packs ผ่าน control-plane
- [x] เพิ่ม bootstrap script/workflow เพื่อสร้าง policy pack baseline
- [x] เพิ่ม tests สำหรับ policy pack และ approval integration
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 20 Checklist: Remediation Effectiveness Scoring & Rollback Guardrails
- [x] เพิ่ม baseline/post remediation contract evaluation per batch
- [x] คำนวณ effectiveness delta และบันทึก batch summary stream
- [x] เพิ่ม rollback guardrail แบบ policy-driven เมื่อผลแย่ลง
- [x] ขยาย policy pack ด้วย `rollback_on_worse_result` และ `min_effectiveness_delta`
- [x] เพิ่ม endpoint ดู effectiveness score ต่อ tenant
- [x] เพิ่ม script/workflow รายงาน effectiveness รายวัน
- [x] เพิ่ม tests สำหรับ rollback trigger และ effectiveness aggregate
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 21 Checklist: Cross-Tenant Risk Heatmap & Adaptive Policy Loop
- [x] เพิ่ม service คำนวณ cross-tenant assurance risk score
- [x] รวมสัญญาณ objective gate + contract + remediation effectiveness
- [x] เพิ่ม risk heatmap endpoint สำหรับ enterprise oversight
- [x] เพิ่ม recommendation endpoint สำหรับ adaptive policy pack tuning
- [x] เพิ่ม apply endpoint รองรับ dry-run/apply ตาม risk tier
- [x] เพิ่ม scripts/workflow สำหรับรัน risk loop อัตโนมัติ
- [x] เพิ่ม tests สำหรับ risk scoring และ recommendation apply logic
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 22 Checklist: Tenant Assurance SLO, Breach Budget, and Executive Digest
- [x] เพิ่ม assurance SLO profile service ต่อ tenant
- [x] รองรับ breach budget แบบรายวันพร้อมการหัก budget อัตโนมัติ
- [x] เพิ่ม breach history stream และ endpoint สำหรับตรวจย้อนหลัง
- [x] เพิ่ม executive digest endpoint สำหรับผู้บริหาร
- [x] รวมสัญญาณ contract/effectiveness/availability/error-rate ใน SLO evaluation
- [x] เพิ่ม script/workflow สำหรับ executive digest automation
- [x] เพิ่ม tests สำหรับ SLO evaluate และ digest summary
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 23 Checklist: Executive Digest Signing & Customer Risk Bulletin
- [x] เพิ่ม signed executive digest chain service
- [x] เพิ่ม signed tenant bulletin chain service ต่อ tenant
- [x] เพิ่ม control-plane endpoints สำหรับ sign/status/verify
- [x] เพิ่ม public read-only endpoints สำหรับ tenant bulletin
- [x] เพิ่ม scripts/workflow สำหรับ digest + bulletin signing อัตโนมัติ
- [x] เพิ่ม tests สำหรับ signing chain และ public bulletin endpoints
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 24 Checklist: Signed Bulletin Distribution Policy & Receipt Tracking
- [x] เพิ่ม tenant distribution policy สำหรับ customer bulletin delivery
- [x] เพิ่ม webhook delivery executor สำหรับ signed tenant bulletin
- [x] เพิ่ม receipt tracking stream + status API ต่อ tenant
- [x] เพิ่ม control-plane APIs สำหรับ policy upsert/get และ delivery trigger
- [x] เพิ่ม scripts/workflow สำหรับ delivery และ receipt report อัตโนมัติ
- [x] เพิ่ม tests สำหรับ distribution policy และ delivery outcomes
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 25 Checklist: Delivery Retry/Backoff Policy & Signed Delivery Proof
- [x] เพิ่ม policy knobs สำหรับ `retry_attempts` และ `retry_backoff_seconds`
- [x] ใช้ retry executor จริงใน webhook delivery path
- [x] เพิ่ม signed delivery proof bundle export service
- [x] เพิ่ม proof status/verify chain service ต่อ tenant
- [x] เพิ่ม control-plane APIs สำหรับ proof export/status/verify
- [x] เพิ่ม scripts/workflow สำหรับ proof export และ verify
- [x] เพิ่ม tests สำหรับ retry path และ proof chain verification
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 26 Checklist: Public Delivery-Proof Verification & Auditor Proof Index
- [x] เพิ่ม public endpoints สำหรับ tenant delivery-proof status/verify
- [x] เพิ่ม service สร้าง cross-tenant auditor proof index
- [x] เพิ่ม control-plane endpoints สำหรับ proof index read/export
- [x] เพิ่ม audit trail เมื่อ export proof index
- [x] เพิ่ม script/workflow สำหรับ proof index generation
- [x] เพิ่ม tests สำหรับ proof index และ public endpoint coverage
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 27 Checklist: Tenant Verifier Kit & One-Click Evidence Package Index
- [x] เพิ่ม verifier kit export/status service ต่อ tenant
- [x] เพิ่ม compliance evidence package index export/status service ต่อ tenant
- [x] เพิ่ม control-plane endpoints สำหรับ kit และ evidence package index
- [x] เพิ่ม public endpoint สำหรับ tenant evidence package status
- [x] เพิ่ม scripts/workflow สำหรับ kit/package export automation
- [x] เพิ่ม tests สำหรับ verifier kit, package index, และ public API coverage
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 28 Checklist: Signed Tenant Evidence Package Chain & Public Verification
- [x] เพิ่ม signed tenant evidence-package chain service ต่อ tenant
- [x] เพิ่ม chain verification service สำหรับ signed evidence package
- [x] เพิ่ม control-plane endpoints สำหรับ sign/status/verify operations
- [x] เพิ่ม public endpoints สำหรับ signed evidence package status/verify
- [x] เพิ่ม scripts/workflow สำหรับ signed evidence package automation
- [x] เพิ่ม tests สำหรับ signing chain และ public API coverage
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 29 Checklist: External Verifier Import & Zero-Trust Attestation
- [x] เพิ่ม service รับ import external verifier bundle ต่อ tenant
- [x] เพิ่ม tenant zero-trust attestation service จาก internal+external trust signals
- [x] เพิ่ม cross-tenant zero-trust overview aggregation
- [x] เพิ่ม control-plane APIs สำหรับ import/status/attest/overview
- [x] เพิ่ม public endpoints สำหรับ tenant zero-trust attestation และ overview
- [x] เพิ่ม scripts/workflow สำหรับ external-import + attestation automation
- [x] เพิ่ม tests สำหรับ attestation service และ public API coverage
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 30 Checklist: Verifier API Keys & Signed Receipt Registry
- [x] เพิ่ม external verifier API token registry (`issue/verify/revoke`) แยกจาก admin auth
- [x] เพิ่ม public verifier import endpoint แบบ token-scoped ต่อ tenant
- [x] เพิ่ม signed verifier receipt chain เมื่อ import external verifier bundle
- [x] เพิ่ม receipt status/verify APIs ทั้ง control-plane และ public surface
- [x] เพิ่ม scripts/workflow สำหรับ verifier token และ receipt-chain verification
- [x] เพิ่ม tests สำหรับ verifier registry + signed receipt verification + public API coverage
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 31 Checklist: Verifier Policy Enforcement & Multi-Verifier Quorum
- [x] เพิ่ม external verifier policy service ต่อ tenant (`min_quorum`, `allowed_verifiers`, `freshness_hours`)
- [x] ผูก policy enforcement เข้า zero-trust attestation path
- [x] รองรับ multi-verifier quorum evaluation และ distinct verifier policy
- [x] เพิ่ม control-plane APIs สำหรับ upsert/get external verifier policy
- [x] ขยาย attestation result ให้มี quorum evidence fields
- [x] เพิ่ม scripts/workflow สำหรับ policy upsert automation
- [x] เพิ่ม tests สำหรับ quorum pass/fail และ policy enforcement
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 32 Checklist: Weighted Trust Scoring & Disagreement Guardrails
- [x] เพิ่ม weighted trust score calculation ต่อ verifier (`verifier_weights`)
- [x] เพิ่ม policy threshold `min_weighted_score` สำหรับ zero-trust pass/fail
- [x] เพิ่ม disagreement detection จาก verifier signals ที่ขัดกัน
- [x] รองรับ policy `block_on_disagreement` สำหรับบล็อก trusted state อัตโนมัติ
- [x] ขยาย attestation payload/stream fields สำหรับ weighted + disagreement evidence
- [x] เพิ่ม script support สำหรับ upsert policy ที่มี weight/score knobs
- [x] เพิ่ม tests สำหรับ weighted-score fail/pass และ disagreement guardrail
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 33 Checklist: One-Click Orchestration Activation & Auto Scheduler
- [x] เพิ่ม one-click activation service สำหรับเปิด Red/Blue/Purple พร้อมกันต่อ tenant
- [x] เพิ่ม activation state (`active/paused/inactive`) พร้อม per-tenant runtime metadata
- [x] เพิ่ม scheduler tick service สำหรับรัน orchestration cycle อัตโนมัติเมื่อถึงเวลา
- [x] เพิ่ม endpoints สำหรับ activate/pause/deactivate/state/list/tick
- [x] เพิ่ม automation script/workflow สำหรับ scheduled orchestration ticks
- [x] เพิ่ม tests สำหรับ activation lifecycle และ scheduler execution path
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 34 Checklist: Pilot Session Hardening & Objective-Gated Start
- [x] เพิ่ม pilot session service (`running/stopped`) แยกจาก activation state
- [x] เพิ่ม objective-gate enforcement ก่อนเริ่ม pilot (พร้อม override แบบ `force`)
- [x] เพิ่ม orchestrator pilot APIs สำหรับ activate/deactivate/status/sessions
- [x] เพิ่ม pilot session report automation script/workflow
- [x] เพิ่ม tests สำหรับ objective-gate block path และ pilot lifecycle
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 35 Checklist: Self-Serve Pilot Onboarding & Scoped Operator Roles
- [x] เพิ่ม pilot operator token service (`issue/verify/revoke`) แบบ tenant-scoped
- [x] เพิ่ม secure pilot APIs ที่บังคับใช้ operator token + scope (`pilot:read`, `pilot:write`)
- [x] เพิ่ม pilot onboarding profile service (`upsert/get/checklist`)
- [x] เพิ่ม control-plane APIs สำหรับ operator token lifecycle และ onboarding profile/checklist
- [x] เพิ่ม automation script/workflow สำหรับ onboarding checklist generation
- [x] เพิ่ม tests สำหรับ operator auth, secure API path, และ onboarding checklist
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 36 Checklist: Pilot Safety Auto-Stop & Incident Escalation
- [x] เพิ่ม tenant safety policy service (`max_consecutive_failures`, objective-gate tick checks, auto-stop controls)
- [x] เพิ่ม incident stream สำหรับ pilot scheduler (`scheduler_cycle_error`, `objective_gate_warning`, `pilot_auto_stop`)
- [x] เพิ่ม auto-stop เมื่อเจอ consecutive scheduler failures ตาม policy
- [x] เพิ่ม objective-gate per-tick check พร้อมโหมด auto-stop เมื่อ gate fail
- [x] เพิ่ม orchestrator APIs สำหรับ safety policy และ incident feed (รวม secure operator read endpoint)
- [x] เพิ่ม control-plane APIs สำหรับ upsert/get pilot safety policy พร้อม audit trail
- [x] เพิ่ม automation script/workflow สำหรับ pilot safety incident reporting
- [x] เพิ่ม tests สำหรับ auto-stop logic และ secure incident API path
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 37 Checklist: Multi-tenant Pilot Concurrency Guardrails & Rate Budgets
- [x] เพิ่ม global scheduler execution cap ต่อ tick เพื่อป้องกัน worker overload
- [x] เพิ่ม tenant rate budget profile (`max_cycles_per_hour`, `max_red_events_per_hour`)
- [x] เพิ่ม usage tracking รายชั่วโมงและ reserve budget ก่อนรัน orchestration cycle
- [x] เพิ่ม guardrail auto-pause เมื่อ budget เกิน พร้อม incident escalation
- [x] เพิ่ม orchestrator APIs สำหรับ budget upsert/get/usage + secure usage read
- [x] เพิ่ม control-plane APIs สำหรับ budget governance พร้อม audit trail
- [x] เพิ่ม automation script/workflow สำหรับตรวจ budget usage
- [x] เพิ่ม tests สำหรับ global cap, budget exceed, และ usage accumulation
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 38 Checklist: Fairness Scheduling, Priority Tiers, and Backpressure
- [x] เพิ่ม tenant scheduler profile service (`priority_tier`, starvation threshold, notify toggle)
- [x] เพิ่ม scheduler ordering ที่คำนวณ effective priority จาก tier + skip streak
- [x] เพิ่ม `scheduler_skip_streak` state ต่อ tenant ใน activation metadata
- [x] เพิ่ม incident `scheduler_backpressure` เมื่อ skip streak เกิน threshold
- [x] เพิ่ม orchestrator APIs สำหรับ scheduler profile upsert/get + secure read endpoint
- [x] เพิ่ม control-plane APIs สำหรับ scheduler profile governance พร้อม audit trail
- [x] เพิ่ม automation script/workflow สำหรับ scheduler profile report
- [x] เพิ่ม tests สำหรับ tier preference, starvation mitigation, และ secure API path
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 39 Checklist: Tenant Rollout Rings & Canary Orchestration Controls
- [x] เพิ่ม tenant rollout profile service (`rollout_stage`, `canary_percent`, `hold`, `notify_on_hold`)
- [x] เพิ่ม scheduler enforcement สำหรับ rollout stage gate (`alpha/beta/ga`)
- [x] เพิ่ม canary defer logic ก่อนรัน cycle เพื่อลด blast radius
- [x] เพิ่ม rollout hold guardrail พร้อม incident และ optional notification
- [x] เพิ่ม orchestrator APIs สำหรับ rollout profile upsert/get + secure read endpoint
- [x] เพิ่ม control-plane APIs สำหรับ rollout profile governance พร้อม audit trail
- [x] เพิ่ม automation script/workflow สำหรับ rollout profile reporting
- [x] เพิ่ม tests สำหรับ rollout hold path และ canary defer/execute path
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 40 Checklist: KPI-Driven Rollout Auto Promote/Demote & Rollback Signals
- [x] เพิ่ม rollout decision engine จาก KPI trend + incident severity
- [x] เพิ่ม auto-promote rule เมื่อ KPI ดีต่อเนื่องตาม threshold
- [x] เพิ่ม auto-demote + hold rule เมื่อเจอ incident เสี่ยงสูง/auto-stop
- [x] เพิ่ม rollout decision history stream ต่อ tenant
- [x] ผูกการ evaluate rollout posture เข้ากับ scheduler หลัง cycle สำเร็จ
- [x] เพิ่ม orchestrator APIs สำหรับ evaluate และ decision history (+ secure read)
- [x] เพิ่ม control-plane APIs สำหรับ evaluate และ decision history
- [x] เพิ่ม automation script/workflow สำหรับ rollout posture evaluation
- [x] เพิ่ม tests สำหรับ promote path, demote path, และ secure decision endpoint
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 41 Checklist: Rollout Anti-Flapping Hysteresis & Cooldown Windows
- [x] เพิ่ม rollout guard state ต่อ tenant (`promote_streak`, `demote_streak`, `cooldown_until_epoch`)
- [x] เพิ่ม hysteresis logic สำหรับ promote/demote ด้วย streak thresholds
- [x] เพิ่ม cooldown block เพื่อลดการสลับ ring ถี่เกินไป (anti-flapping)
- [x] ผูก guard-state persistence เข้ากับ rollout evaluator
- [x] เพิ่ม pilot status fields สำหรับ rollout guard observability
- [x] เพิ่ม orchestrator APIs สำหรับ rollout guard state และ secure read path
- [x] เพิ่ม control-plane API สำหรับ rollout guard inspection
- [x] เพิ่ม automation script/workflow สำหรับ rollout guard report
- [x] เพิ่ม tests สำหรับ hysteresis promote และ cooldown blocked reversal
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 42 Checklist: Rollout Policy Contracts & Approval Gates
- [x] เพิ่ม rollout policy contract ต่อ tenant (`auto_promote`, `auto_demote`, `require_approval_*`)
- [x] เพิ่ม pending rollout decision store และ list API
- [x] เพิ่ม approve/reject endpoint สำหรับ pending rollout decisions
- [x] ผูก policy enforcement เข้ากับ rollout evaluator (block/pending paths)
- [x] ขยาย pilot status ให้เห็น rollout policy และ pending decisions
- [x] เพิ่ม orchestrator APIs สำหรับ rollout policy/pending/approve + secure operator paths
- [x] เพิ่ม control-plane APIs สำหรับ rollout policy governance และ approval
- [x] เพิ่ม automation script/workflow สำหรับ rollout policy + pending report
- [x] เพิ่ม tests สำหรับ policy blocked promote และ pending demote approval apply
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 43 Checklist: Dual-Control Rollout Approval & Signed Evidence
- [x] ขยาย rollout policy ด้วย dual-control flags (`require_dual_control_for_promote/demote`)
- [x] เพิ่ม multi-step approval flow สำหรับ pending rollout decisions
- [x] เพิ่ม guard ป้องกัน reviewer เดิมอนุมัติซ้ำใน decision เดียวกัน
- [x] เพิ่ม signed rollout evidence stream (HMAC-SHA256)
- [x] เพิ่ม orchestrator APIs สำหรับ rollout evidence และ staged approval
- [x] เพิ่ม secure operator APIs สำหรับ rollout evidence และ staged approval
- [x] เพิ่ม control-plane API สำหรับ rollout evidence และ dual-control policy governance
- [x] เพิ่ม automation script/workflow สำหรับ rollout evidence reporting
- [x] เพิ่ม tests สำหรับ dual-control approval path และ signed evidence presence
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 44 Checklist: Rollout Evidence Chain Verification & Integrity Ops
- [x] เพิ่ม evidence chain state (`prev_signature`) สำหรับ event linkage
- [x] เพิ่ม verify service ตรวจทั้ง signature และ prev_signature continuity
- [x] เพิ่ม orchestrator APIs สำหรับ evidence verify (standard + secure operator)
- [x] เพิ่ม control-plane API สำหรับ evidence verify
- [x] เพิ่ม automation script/workflow สำหรับ verify evidence chain
- [x] เพิ่ม tests สำหรับ evidence chain verification path
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 45 Checklist: Notarized Rollout Evidence Bundles & Export Ops
- [x] เพิ่ม service export rollout evidence bundle พร้อม notarization option
- [x] เพิ่ม bundle status stream ต่อ tenant สำหรับติดตามงาน export
- [x] เพิ่ม control-plane endpoint สำหรับ export rollout evidence bundle
- [x] เพิ่ม control-plane endpoint สำหรับดู export-status ของ bundle
- [x] เพิ่ม script/workflow สำหรับ export bundle automation
- [x] เพิ่ม tests สำหรับ bundle export + status persistence
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 46 Checklist: Public Verifier Bundle & Third-Party Audit Hand-off
- [x] เพิ่ม hand-off token service (`issue/verify/revoke`) แบบ tenant-scoped
- [x] เพิ่ม public endpoint สำหรับ rollout verifier bundle ผ่าน hand-off token
- [x] เพิ่ม public endpoint สำหรับ verifier quick-check (`/verify`) ผ่าน hand-off token
- [x] เพิ่ม control-plane endpoints สำหรับ hand-off token issue/revoke
- [x] เพิ่ม service สร้าง public verifier bundle payload สำหรับ external auditor
- [x] เพิ่ม script/workflow สำหรับ hand-off preview automation
- [x] เพิ่ม tests สำหรับ hand-off token service และ public assurance endpoint integration
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 47 Checklist: Time-Bound Handoff Sessions, IP Allowlist, and Access Receipts
- [x] เพิ่ม hand-off session controls (`session_ttl_seconds`, `max_accesses`) ต่อ token
- [x] เพิ่ม source-IP allowlist enforcement (`allowed_ip_cidrs`)
- [x] เพิ่ม consume-on-read path สำหรับ public handoff access
- [x] เพิ่ม access receipt stream สำหรับ handoff reads
- [x] เพิ่ม control-plane endpoint สำหรับอ่าน handoff receipts
- [x] เพิ่ม script/workflow สำหรับ handoff receipt reporting
- [x] เพิ่ม tests สำหรับ IP allowlist และ access-limit enforcement
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 48 Checklist: Handoff Access Anomaly Detection & Auto-Revoke Policies
- [x] เพิ่ม tenant policy สำหรับ handoff anomaly detection และ auto-revoke conditions
- [x] เพิ่ม denied-access anomaly stream ต่อ tenant
- [x] เพิ่ม auto-revoke logic เมื่อถึง threshold หรือ IP mismatch ตาม policy
- [x] เพิ่ม control-plane APIs สำหรับ policy upsert/get และ anomaly listing
- [x] เพิ่ม script/workflow สำหรับ handoff anomaly reporting
- [x] เพิ่ม tests สำหรับ policy override และ anomaly-driven revoke behavior
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 49 Checklist: Risk-Scored Handoff Trust Model & Adaptive Session Hardening
- [x] เพิ่ม trust-event stream สำหรับ handoff decision (`allowed/denied`, `risk_score`, `action_taken`)
- [x] เพิ่ม risk scoring model และ tenant risk snapshot ต่อ handoff session
- [x] เพิ่ม adaptive hardening policy (`risk_threshold_block`, `risk_threshold_harden`, `harden_session_ttl_seconds`)
- [x] เพิ่ม block-on-risk enforcement และ revoke path เมื่อเกิน threshold
- [x] เพิ่ม control-plane APIs สำหรับ risk events และ risk snapshot
- [x] เพิ่ม script/workflow สำหรับ handoff risk reporting
- [x] เพิ่ม tests สำหรับ trust events, risk snapshot, และ threshold-driven revoke/hardening
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 50 Checklist: Handoff Risk Governance & Auto-Containment Playbooks
- [x] เพิ่ม containment playbook stream พร้อม `risk_tier` และ `action_taken`
- [x] เพิ่ม governance policy knobs สำหรับ containment threshold/action ต่อ tenant
- [x] เพิ่ม auto-containment execution path (`log_only`, `harden_session`, `revoke_token`)
- [x] เพิ่ม governance snapshot service รวม risk + containment distribution
- [x] เพิ่ม control-plane APIs สำหรับ containment feed และ governance snapshot
- [x] เพิ่ม script/workflow สำหรับ handoff governance reporting
- [x] เพิ่ม tests สำหรับ containment behavior และ governance snapshot metrics
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 51 Checklist: Cross-Tenant Handoff Risk Federation & Enterprise Escalation Matrix
- [x] เพิ่ม cross-tenant handoff federation heatmap จาก governance snapshots ราย tenant
- [x] เพิ่ม enterprise escalation matrix mapping (`low/medium/high/critical`) พร้อม recommended actions
- [x] เพิ่ม apply path สำหรับ escalation matrix แบบ `dry_run` และ `apply`
- [x] เพิ่ม policy tightening automation สำหรับ tenant ที่อยู่ใน risk tier สูง
- [x] เพิ่ม control-plane APIs สำหรับ federation heatmap/escalation matrix/apply
- [x] เพิ่ม script/workflow สำหรับ federation reporting automation
- [x] เพิ่ม tests สำหรับ heatmap/matrix/apply behavior
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 52 Checklist: Handoff Federation SLO, Breach Budget, and Auto-Escalation Notifications
- [x] เพิ่ม tenant SLO profile สำหรับ handoff federation risk controls
- [x] เพิ่ม breach budget รายวันและ breach history stream สำหรับ handoff federation
- [x] เพิ่ม SLO evaluation path สำหรับ federated risk score/tier/containment pressure
- [x] เพิ่ม auto-escalation trigger จาก SLO breach พร้อม policy tightening ต่อ tenant
- [x] เพิ่ม notification trigger เมื่อเกิด SLO breach (Telegram channel)
- [x] เพิ่ม control-plane APIs สำหรับ SLO upsert/get/evaluate/breaches/executive-digest
- [x] เพิ่ม script/workflow สำหรับ SLO monitoring automation
- [x] เพิ่ม tests สำหรับ SLO profile/evaluate/budget/digest behavior
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 53 Checklist: Signed Federation SLO Digest Chain & Verification
- [x] เพิ่ม signed executive digest service สำหรับ handoff federation SLO
- [x] เพิ่ม signature-chain state (`prev_signature`) และ integrity verification
- [x] เพิ่ม control-plane APIs สำหรับ sign/status/verify ของ federation digest
- [x] เพิ่ม script สำหรับ generate/verify signed federation digest
- [x] เพิ่ม workflow automation สำหรับ federation digest signing run
- [x] เพิ่ม tests สำหรับ signed chain creation และ verification path
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 54 Checklist: Public Federation Verifier Bundle & External Verification Surface
- [x] เพิ่ม public read endpoints สำหรับ federation digest status/verify
- [x] เพิ่ม public verifier bundle endpoint สำหรับ federation digest
- [x] เพิ่ม public bundle-verify endpoint สำหรับ external re-check
- [x] เพิ่ม service function สำหรับสร้าง/ตรวจ bundle verification
- [x] เพิ่ม script/workflow สำหรับ federation verifier bundle reporting
- [x] เพิ่ม tests สำหรับ public endpoints และ bundle verify behavior
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 55 Checklist: Federation Policy Drift Detection & Auto-Reconciliation
- [x] เพิ่ม enterprise baseline policy service สำหรับ rollout handoff governance
- [x] เพิ่ม tenant drift evaluation (`drift_score`, `drift_severity`, mismatch evidence)
- [x] เพิ่ม cross-tenant drift heatmap สำหรับ enterprise oversight
- [x] เพิ่ม auto-reconciliation service (`dry_run`/`apply`) ต่อ tenant
- [x] เพิ่ม drift history stream และ high/critical notification path
- [x] เพิ่ม signed drift report chain (`sign/status/verify`) สำหรับ auditability
- [x] เพิ่ม control-plane APIs สำหรับ baseline/drift/reconcile/sign operations
- [x] เพิ่ม scripts/workflows สำหรับ drift operations automation
- [x] เพิ่ม tests สำหรับ drift logic และ signed report verification
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 56 Checklist: Cross-Region Orchestration Failover Resilience & Signed Drills
- [x] เพิ่ม tenant failover profile service (`primary/secondary region`, threshold, auto-failover)
- [x] เพิ่ม failover state tracking และ event stream ต่อ tenant
- [x] เพิ่ม health evaluation path (`health_score`, high incidents, failover recommendation)
- [x] เพิ่ม manual/auto failover drill path (`dry_run`/`apply`)
- [x] เพิ่ม enterprise failover snapshot ข้าม tenant
- [x] เพิ่ม signed failover report chain (`sign/status/verify`)
- [x] เพิ่ม control-plane APIs สำหรับ failover profile/state/health/drill/snapshot/signing
- [x] เพิ่ม scripts/workflows สำหรับ failover snapshot และ signed failover report
- [x] เพิ่ม tests สำหรับ failover logic และ signed report verification
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 57 Checklist: Cost Guardrails & Model Routing Optimization Controls
- [x] เพิ่ม tenant cost-guardrail profile service (budget/pressure/action policy)
- [x] เพิ่ม cost/usage guardrail evaluation ต่อ tenant พร้อม severity signal
- [x] เพิ่ม auto-action path (routing override + quota clamp) แบบ policy-driven
- [x] เพิ่ม tenant cost guardrail event stream และ enterprise snapshot
- [x] เพิ่ม signed cost guardrail report chain (`sign/status/verify`)
- [x] เพิ่ม control-plane APIs สำหรับ cost profile/evaluate/events/snapshot/signing
- [x] เพิ่ม scripts/workflows สำหรับ cost snapshot และ signed report automation
- [x] เพิ่ม tests สำหรับ cost guardrail service และ signing chain
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 58 Checklist: Runtime Cost Guardrail Enforcement & Public Verifier Surface
- [x] บังคับใช้ routing override (`fallback_only`) ใน model router runtime path
- [x] ผูก orchestration cycle ให้ evaluate cost guardrail และ apply actions อัตโนมัติ
- [x] เพิ่ม clear override path เมื่อ pressure ลดลงเพื่อป้องกัน fallback ค้าง
- [x] เพิ่ม public bundle helpers สำหรับ cost guardrail signed chain (`bundle/verify`)
- [x] เพิ่ม public assurance endpoints สำหรับ cost guardrail report/verify/verifier-bundle
- [x] เพิ่ม scripts/workflow สำหรับ cost guardrail verifier bundle automation
- [x] เพิ่ม tests สำหรับ runtime override enforcement และ public verifier API coverage
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 59 Checklist: Cost Anomaly Detection & Preemptive Throttling Controls
- [x] เพิ่ม anomaly policy knobs ใน cost guardrail profile (`delta/min_pressure/ema/throttle mode`)
- [x] เพิ่ม anomaly-state persistence ต่อ tenant (`ema`, `delta`, `consecutive_anomaly_count`)
- [x] เพิ่ม preemptive throttle override actions (`conservative/strict`) แบบ policy-driven
- [x] เพิ่ม clear throttle override path เมื่อ anomaly หายไป
- [x] ผูก orchestration runtime ให้ใช้ throttle override ลด red events ต่อ cycle อัตโนมัติ
- [x] เพิ่ม control-plane APIs สำหรับ throttle override และ anomaly state inspection
- [x] เพิ่ม anomaly-aware enterprise snapshot counters (`anomaly_count`) สำหรับ oversight
- [x] เพิ่ม scripts/workflow สำหรับ cost anomaly reporting automation
- [x] เพิ่ม tests สำหรับ anomaly/throttle behavior และ runtime enforcement
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 60 Checklist: Cost Anomaly Federation + Production v1 Final Go-Live Closure
- [x] เพิ่ม cross-tenant cost anomaly federation heatmap พร้อม risk tier
- [x] เพิ่ม auto policy tightening matrix สำหรับ cost guardrail profile patch ต่อ tier
- [x] เพิ่ม apply path (`dry_run`/`apply`) สำหรับ federated policy tightening
- [x] เพิ่ม Production v1 runbook service (`upsert/get`) พร้อม checklist normalization
- [x] เพิ่ม Production Readiness Final gate (Objective + Cost + Runbook)
- [x] เพิ่ม Go-Live closure path พร้อม dry-run และ promote-on-pass
- [x] เพิ่ม closure history stream สำหรับ auditability
- [x] เพิ่ม control-plane APIs สำหรับ federation + production v1 readiness/closure
- [x] เพิ่ม scripts/workflows สำหรับ cost federation และ production v1 readiness gate
- [x] เพิ่ม tests สำหรับ federation logic และ production readiness closure
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Phase 61 Checklist: Post-Go-Live SLO Burn-Rate Guard & Auto Rollback Gate
- [x] เพิ่ม production burn-rate profile service (`upsert/get`) พร้อม policy knobs
- [x] เพิ่ม burn-rate evaluator จาก SLO snapshot (`warn/rollback thresholds`)
- [x] เพิ่ม auto rollback decision gate สำหรับ tenant ที่อยู่สถานะ production
- [x] เพิ่ม cooldown guard เพื่อลด rollback flapping
- [x] เพิ่ม burn-rate event history stream สำหรับ auditability
- [x] เพิ่ม control-plane APIs สำหรับ burn-rate profile/evaluate/history
- [x] เพิ่ม script/workflow สำหรับ post-go-live burn-rate guard automation
- [x] เพิ่ม tests สำหรับ rollback execution และ cooldown-block path
- [x] อัปเดตเอกสารสถานะ Phase และ README

## Objective Gate: Ensure Red/Blue/Purple Orchestration for Enterprise
เกณฑ์นี้ต้องผ่านก่อนประกาศว่า “พร้อม enterprise-scale”
- [x] Red objective: scenario coverage ครบตาม profile และปลอดภัยตาม policy (evaluated by gate service)
- [x] Blue objective: detect + respond อัตโนมัติและตรวจสอบย้อนหลังได้ (evaluated by gate service)
- [x] Purple objective: correlate + feedback + report ทำงานครบวงจร (evaluated by gate service)
- [x] Closed-loop objective: KPI ดีขึ้นต่อเนื่องทุก iteration (evaluated by gate service)
- [x] Enterprise objective: throughput ผ่านเกณฑ์และต้นทุนต่อ tenant อยู่ในงบ (evaluated by gate service)
- [x] Compliance objective: มี auditability + guardrails ครบ (evaluated by gate service)

## Phase 62 Checklist: Autonomous Team Console & Operator UX
- [x] เพิ่ม runtime autonomous tick loop ใน API startup (ไม่ต้องรัน script tick เอง)
- [x] เพิ่ม runtime config knobs สำหรับ autonomous orchestration/schedule limits
- [x] เพิ่ม API endpoints สำหรับ autonomous runtime status/start/stop/run-once
- [x] เพิ่ม Configuration menu/หน้าใหม่ สำหรับตั้งค่าและเพิ่มลูกค้าแบบ Site พร้อมบันทึกลง DB
- [x] เพิ่ม Site operations APIs (`/sites`) สำหรับ list/upsert/red scan/blue logs/actions/purple reports
- [x] เพิ่ม Red Team panel ให้แสดงรายการ Site และยิง scan case ต่อ Site พร้อม AI summary
- [x] เพิ่ม Blue Team panel ให้ monitor event logs ต่อ Site พร้อม AI severity + recommendation + apply action
- [x] เพิ่ม Purple Team panel ให้รวมผล Red/Blue ต่อ Site พร้อม AI analysis report
- [x] ผูกหน้า dashboard หลักให้แสดง Red/Blue/Purple panels แบบ site-centric
- [x] เพิ่ม test coverage สำหรับ autonomous runtime service
- [ ] เพิ่ม role-based UI control แยกสิทธิ์ Red/Blue/Purple operator
- [ ] เพิ่ม incident/report outbound action center (Telegram/Line routing control)

## Phase 63 Checklist: Universal Integration Layer & ISO Gap Automation
- [x] เพิ่ม integration event model สำหรับ raw + normalized payload persistence
- [x] เพิ่ม adapter normalization service แบบ OCSF-compatible (generic/cloudflare/wazuh/splunk/crowdstrike)
- [x] เพิ่ม webhook signature verification สำหรับ inbound connector events
- [x] เพิ่ม integration APIs (`/integrations/adapters`, `/integrations/events`, `/integrations/webhooks/{source}`)
- [x] เพิ่ม auto-route จาก normalized integration event ไป Blue event stream
- [x] เพิ่ม Purple ISO/IEC 27001 gap template endpoint ต่อ site
- [x] เพิ่ม Configuration UI ให้เห็น adapter list และ ingest sample external event
- [x] เพิ่ม Purple UI ให้เรียก/แสดง ISO gap summary ได้จาก evidence จริง
- [x] เพิ่ม tests สำหรับ adapter normalization และ webhook signature verification
- [ ] เพิ่ม connector credential vault abstraction + key rotation policy ต่อ connector
- [ ] เพิ่ม connector health telemetry/retry/dead-letter UI สำหรับ production operations
