# BRP-Cyber Master Documentation

เอกสารนี้เป็น canonical documentation ฉบับเดียวของโปรเจกต์ ณ วันที่ `2026-03-23`
และถูกสร้างขึ้นเพื่อแทนที่ legacy docs เดิมทั้งหมดใน `docs/`

## เอกสารนี้แทนที่อะไรบ้าง

- legacy docs เดิมมีทั้งหมด `149` ไฟล์
- ในจำนวนนั้นเป็น phase logs `115` ไฟล์ (`PHASE*_STATUS.md`)
- และเป็นเอกสาร API/spec/runbook/checklist/policy/template อื่น ๆ อีก `34` ไฟล์

ปัญหาหลักของ docs เดิม:

- ข้อมูลกระจายหลายไฟล์มากเกินไป
- มี status drift ระหว่าง phase logs บางไฟล์กับ `PHASE_CHECKLIST.md`/`README.md`
- มี broken absolute path references อยู่ `17` ไฟล์
- backlog บางข้อถูกปิดไปแล้วใน phase ถัดมา แต่ไฟล์เดิมยังค้าง `[ ]`

เอกสารนี้จึงรวม 3 เรื่องหลักไว้ในที่เดียว:

1. สิ่งที่เขียนไว้แต่ยังไม่ได้ทำ
2. ระบบและ feature ทั้งหมดของโปรเจกต์
3. สิ่งที่ถูกลบ/รวมทับจาก legacy docs เดิม

## 1. สิ่งที่เขียนไว้แต่ยังไม่ได้ทำ

### 1.1 Confirmed Open Items

รายการนี้คือสิ่งที่ยังหา implementation ตรงตาม note ไม่เจอ หรือยังเป็น operational gap จริง

- ตอนนี้ไม่พบ confirmed open item จาก legacy notes เดิมแล้ว
- สิ่งที่ยังเหลือทั้งหมดอยู่ในหมวด operational validation gaps ด้านล่าง

### 1.2 Operational Validation Gaps

รายการนี้มี implementation หลักแล้ว แต่ยังมี note เรื่องการ validate ใน environment จริง

- `Execute KEDA/cluster-level e2e validation on the target Kubernetes environment`
  - cluster validator script มีแล้วใน `backend/scripts/validate_k8s_autoscaling_profile.py`
  - สิ่งที่ยังต้องทำคือรันกับ cluster จริงเพื่อยืนยัน wiring ของ Deployment/HPA/ScaledObject/CronJob และดู scale path จริง
- `Execute production-like multi-tenant concurrent benchmark against a real Redis/API/worker topology`
  - multi-tenant concurrent harness + matrix report generator มีแล้วใน `backend/scripts/loadtest_enterprise.py` และ `backend/scripts/loadtest_matrix.py`
  - สิ่งที่ยังต้องทำคือรันจริงใน prod-like environment และเก็บ evidence report/json sidecar
- `Execute Purple live Redis/API integration tests in an environment with reachable Redis`
  - implementation ของ test มีแล้ว แต่จะ `skip` อัตโนมัติถ้า Redis จริงไม่พร้อมใน environment นั้น
- `Execute Red scheduler/orchestration live Redis/API integration tests in an environment with reachable Redis`
  - implementation ของ test มีแล้ว แต่จะ `skip` อัตโนมัติถ้า Redis จริงไม่พร้อมใน environment นั้น
- `Execute unit/integration tests in CI or local env with Docker daemon enabled`
  - มาจาก Phase 1
- `Enable S3 Object Lock production validation on target bucket policy`
  - มาจาก Phase 6/7 handover
  - มี validator แล้ว แต่ note เดิมพูดถึงการ validate กับ target bucket จริง
- `Strict external IdP bootstrap validation in production rollout path`
  - phase ถัดมาทำ IdP posture และ production guardrail แล้ว
  - แต่ถ้าจะถือว่า "ปิดเต็ม operationally" ยังขึ้นกับ environment จริง

### 1.3 Closed Later But Left Open In Legacy Docs

รายการนี้ไม่ควรถือเป็น backlog ปัจจุบันแล้ว เพราะถูกปิดใน phase ถัดมา แต่ไฟล์เก่ายังไม่อัปเดต

- `Phase 1 richer suppression policy`
  - ปิดแล้วในไฟล์เดียวกัน แต่ status ยังไม่ถูก finalize
- `Phase 3 per-tenant simulation profile presets`
  - ถูกกลบ/ปิดเชิงพฤติกรรมโดย strategy profiles ใน Phase 4 (`conservative/balanced/aggressive`)
- `Phase 4 role-based authorization hooks for approve/reject`
  - ปิดแล้วผ่าน secure operator path, pilot operator auth, และ control-plane scopes
- `Phase 62 frontend role-based access split`
  - ปิดแล้วใน competitive RBAC context และ role-aware UI
- `Phase 62 delivery action panel`
  - ปิดแล้วใน Delivery Layer phases 77, 84, 85, 86
- `Phase 63 credential vault abstraction + connector health telemetry`
  - ปิดแล้วใน phases 67-71
- `Phase 64 SOAR marketplace objects + SecOps data-tier benchmark`
  - ปิดแล้วใน phases 65-67
- `Phase 9 external signature/KMS-backed attestation`
  - ปิดแล้วใน Phase 10
- `Phase 12 public transparency + notarization legal evidence integration`
  - ปิดแล้วใน phases 13-14
- `Phase 89 deeper control evidence mapping`
  - ปิดแล้วใน Phase 113
- `Phase 90 deeper external provider callback path`
  - ปิดแล้วใน Phase 99
- `Phase 92 native binary renderer`
  - ปิดแล้วใน Phase 98
- `Future hardening backlog ใน VIRTUAL_EXPERT_CHECKLIST.md`
  - ปิดแล้วใน phases 107-114

### 1.4 Status Drift ที่พบใน Legacy Docs

ไฟล์ด้านล่างยังขึ้น `In Progress` แต่ภาพรวมล่าสุดใน checklist และ README ระบุว่า complete แล้ว

- `PHASE1_STATUS.md`
- `PHASE2_STATUS.md`
- `PHASE3_STATUS.md`
- `PHASE4_STATUS.md`
- `PHASE62_STATUS.md`
- `PHASE63_STATUS.md`
- `PHASE64_STATUS.md`

สรุป: backlog ที่ควรกลับมาทำจริงมีอยู่ แต่ไม่เยอะเท่าที่ legacy docs ทำให้ดู เพราะหลายข้อถูกปิดใน phase หลังแล้ว

## 2. ระบบและ Feature ทั้งหมดของโปรเจกต์

## 2.1 Platform Foundation

- `FastAPI backend`
  - เป็น control plane, competitive engine, assurance/public API, integration API
- `PostgreSQL/Timescale + Redis`
  - persistence สำหรับ tenant/site/workflow/run history
  - Redis ใช้ทั้ง state, streams, scheduler, transient orchestration state
- `Multi-tenant isolation`
  - tenant/site/policy/credential/run history แยกตามขอบเขต
- `RBAC / scoped auth`
  - control-plane scopes
  - competitive RBAC (`viewer`, `policy_editor`, `approver`)
  - pilot operator token
- `Autonomous runtime + distributed scheduler worker`
  - runtime เป็น execution core สำหรับ scheduler loop หลายชุด
  - dedicated worker ใช้ Redis lease/status/stop control แยกจาก API process
  - API ยัง expose status/control surface ได้โดยไม่เป็น owner ของ loop เอง
- `Embedded workflow / plugin-first integration`
  - external tools เรียก AI co-workers ผ่าน shared-secret invoke surface ได้

## 2.2 Red Agent

### Red Core

- `Red Simulation Core`
  - รัน adversarial emulation แบบ authorized simulation only
  - มี scenario library, scheduling, rate guardrails, allowlist, kill-switch semantics
- `Exploit Path Simulation`
  - จำลอง exploit path เพื่อประเมินความเสี่ยงและคุณภาพการตรวจจับ
- `Exploit Autopilot`
  - policy-driven scheduler สำหรับ red exploit validation
  - เลือก pack/category และรันแบบ dry-run/apply ตาม guardrails
- `Threat Content Pipeline`
  - threat-content packs
  - pipeline policy/run/scheduler
  - federation freshness view

### Red Service Features

- `24/7 Shadow Pentest`
  - passive crawl
  - page/content diff detection
  - drift-based zero-day pack assignment
  - per-site policy
  - scheduler + autonomous runtime integration
  - asset inventory baseline
  - deploy-event trigger mode
  - pack-to-asset validation chaining
- `Vulnerability Auto-Validator`
  - import findings จาก Nessus/Burp/generic
  - normalization, dedupe, exploitability verdict, false-positive scoring
  - remediation export กลับไป source tool
- `Social Engineering Simulator`
  - roster import
  - policy persistence
  - approval/reject/kill flow
  - recipient telemetry
  - callback ingestion จาก provider
  - legal/compliance template packs ตาม campaign type

### Red Plugins

- `Exploit Code Generator`
  - สร้าง PoC draft
  - รองรับ `python`, `bash`, `curl`
  - มี safety policy, lint, export, intelligence context
- `Nuclei AI-Template Writer`
  - สร้าง template draft
  - lint/validate/export ได้
  - publish เป็น threat-content pack ได้
- `Red Plugin Intelligence`
  - import intelligence (`cve/news/article`)
  - sync source/run history
  - scheduler integration

## 2.3 Blue Agent

### Blue Core

- `Blue Detect + Respond`
  - ingest logs/events
  - basic detection rules
  - response path
  - alerting
  - auditability
- `Detection Copilot`
  - tune rules, compare before/after metrics, apply tuned rules
- `Detection Autotune`
  - policy-driven scheduler สำหรับ detection tuning
  - closed-loop guardrails

### Blue Service Features

- `AI Log Refiner`
  - persistent policy ต่อ connector source
  - KPI run history
  - operator feedback loop
  - vendor mapping packs
  - direct SIEM callback ingestion
  - continuous schedule policy
- `Managed AI Responder`
  - policy persistence
  - dry-run/apply
  - approval/reject/rollback
  - evidence verify
  - vendor-aware action plans
  - vendor coverage หลายเจ้า
  - live callback ingestion
  - callback contract validation
- `Threat Intelligence Localizer`
  - localized threat brief
  - relevance/priority scoring
  - external feed ingestion
  - sector profiles
  - scheduler/digest mode
  - routing packs
  - gap promotion ไป detection autotune / SOAR follow-up

### Blue Automation and SOAR

- `SOAR Playbook Hub`
  - playbook catalog
  - execute/approve lifecycle
  - tenant policy matrix
  - delegated approvers
- `SOAR Marketplace`
  - pack catalog
  - install flow
  - community/partner metadata
  - filters/search
  - post-action verification
- `Connector Reliability`
  - connector events, health, SLA
  - DLQ backlog, replay, scheduler, federation
- `Connector Credential Governance`
  - credential vault
  - rotation events/verify
  - hygiene evaluation
  - auto-rotate
  - policy/scheduler/run history
- `Action Center`
  - Telegram/LINE routing policies
  - dispatch/events
  - SLA breach routing

## 2.4 Purple Agent

### Purple Core

- `Correlation + KPI + Reporting`
  - correlate Red/Blue events
  - KPI เช่น MTTD, MTTR, coverage, block effectiveness
  - daily reports
- `Executive Scorecard`
  - MITRE technique status
  - remediation SLA snapshot
  - federation executive rollup
- `Unified Case Graph`
  - รวม Red/Blue/SOAR/connector/replay/purple timeline
  - risk score / risk tier / recommendation

### Purple Service Features

- `Automated ISO/NIST Gap Analysis`
  - ISO 27001 gap template
  - NIST CSF gap template
  - evidence correlation จากระบบจริง
- `ROI Security Dashboard`
  - ROI snapshot generation
  - trends
  - portfolio roll-up
  - segmentation/filtering
  - board-pack export
  - native `pdf` และ `pptx`

### Purple Plugins and Exports

- `MITRE ATT&CK Heatmap`
  - run from plugin/page
  - export `markdown`, `csv`, `attack_layer_json`, `svg`
  - ATT&CK layer import/list/edit/export
  - graphical export
- `Incident Report Ghostwriter`
  - Thai incident drafts
  - template packs
  - native `pdf` / `docx`
  - final release approval workflow
- `Regulated Report Export`
  - ISO/NIST snapshot + incident context
- `Control-Family Mapping`
  - map policy/evidence across ISO 27001 and NIST CSF
  - export view/output

## 2.5 Orchestra

คำว่า Orchestra ในโปรเจกต์นี้คือ orchestration/control-plane/runtime/governance layer ที่ทำให้ Red/Blue/Purple ทำงานเป็นระบบเดียวกัน

### Orchestration Lifecycle

- `One-click activation`
  - activate, pause, deactivate
  - manual tick
  - distributed autonomous worker
- `Pilot mode`
  - pilot activate/deactivate/status/sessions
  - objective-gated start
- `Pilot onboarding`
  - onboarding profile
  - readiness checklist
  - operator token lifecycle

### Runtime Guardrails

- `Approval mode`
  - pending actions + manual approve/reject
- `Safety policy`
  - auto-stop
  - incident emission
  - escalation behavior
- `Rate budget`
  - per-tenant cycle/red-event budget
- `Fairness scheduler`
  - priority tiers
  - starvation protection
- `Rollout control`
  - rollout stage / canary / hold
  - KPI-driven promote/demote
  - hysteresis/cooldown
  - rollout policy contracts
  - dual-control approvals

### Evidence, Handoff, Federation

- `Rollout evidence chain`
  - sign, verify, export
- `Third-party handoff`
  - handoff tokens
  - IP allowlist
  - receipts
  - anomaly detection
  - risk scoring
  - containment/governance
- `Federation`
  - cross-tenant handoff risk heatmap
  - escalation matrix
  - federation SLO/digest/verifier bundle
  - policy drift detection/reconciliation

### Reliability and Cost

- `Failover`
  - failover profile/state/health/drill
  - signed failover evidence
- `Cost guardrails`
  - guardrail profile
  - routing override
  - public verifier surface
  - anomaly state
  - preemptive throttling
  - cost federation
- `Production v1 readiness`
  - runbook profile
  - integration playbook
  - final readiness gate
  - go-live closure
  - burn-rate guard + auto rollback
- `Benchmark evidence harness`
  - multi-tenant concurrent enterprise loadtest
  - tiered matrix report generator
  - queue/autoscaler evidence snapshot
- `Kubernetes autoscaling validation`
  - cluster validator สำหรับ Deployment/HPA/ScaledObject/CronJob
  - ใช้ตรวจ target cluster wiring ก่อนปิด residual risk ฝั่ง KEDA/autoscaling
- `Purple core reporting`
  - correlation filter (`attack_type`, `detection_status`)
  - report query pagination/filtering/date-range
  - report export (`json`, `pdf`) ไป filesystem/S3 object storage

## 2.6 Assurance, Public Trust, and External Verification

### Control Plane and Governance

- tenant onboarding / lifecycle / key rotation
- admin token issuance/rotate/revoke/introspect
- IdP mode and production auth posture
- audit stream, export, replay, archive, immutable offload
- DR smoke and runbooks
- governance policy-as-code
- governance attestation with `hmac` / `aws_kms`

### Assurance Layer

- assurance contracts
- remediation and policy packs
- effectiveness scoring and rollback guardrails
- risk heatmap + adaptive recommendation apply
- assurance SLO / breach budget / executive digest
- bulletin signing and delivery
- delivery proof chain
- proof index
- verifier kit
- evidence package chain
- zero-trust attestation
- external verifier token/receipts/policy/quorum/weighted trust

### Public Assurance Surface

- public summary
- public transparency
- public orchestration objective readiness
- signed public assurance snapshots
- public tenant bulletin / delivery proof / evidence package / zero-trust views
- public rollout verifier bundle
- public federation verifier bundle
- public cost-guardrail verifier bundle
- regulatory framework/scorecard endpoints

## 2.7 Plugin-First Product Surface

- `AI Co-worker catalog`
  - per-site plugin binding
  - run history
  - scheduler
- `Delivery Layer`
  - Telegram
  - LINE
  - Teams
  - webhook
  - preview, dispatch, review SLA, escalation scheduler, federation posture
- `Embedded workflow API`
  - public invoke surface
  - adapter templates
  - vendor presets
  - activation bundles
- `Frontend service pages`
  - Red Service
  - Blue Service
  - Purple Service
  - Configuration
  - Delivery Layer
  - dashboard/federation/control surfaces

## 2.8 Source of Truth in Code

หลังจากลบ split docs เดิมแล้ว source of truth เชิง implementation คือโค้ดชุดนี้

- Backend APIs: `backend/app/api/`
- Core orchestration: `backend/app/services/orchestrator.py`
- Autonomous runtime: `backend/app/services/autonomous_runtime.py`
- Distributed worker control: `backend/app/services/autonomous_scheduler_worker.py`
- Worker entrypoint: `backend/app/workers/autonomous_scheduler_worker.py`, `backend/scripts/run_autonomous_scheduler_worker.py`
- Red services: `backend/app/services/red_*`
- Blue services: `backend/app/services/blue_*`
- Purple services: `backend/app/services/purple_*`
- SOAR/connector services: `backend/app/services/soar_*`, `connector_*`, `action_center.py`
- Assurance/control-plane services: `backend/app/services/control_plane_*`
- Frontend panels:
  - `frontend/components/RedTeamPanel.tsx`
  - `frontend/components/BlueTeamPanel.tsx`
  - `frontend/components/PurpleReportsPanel.tsx`
  - `frontend/components/CoworkerDeliveryPanel.tsx`
  - `frontend/app/configuration/page.tsx`

## 3. สิ่งที่ถูกลบ/รวมทับจาก Legacy Docs

## 3.1 หลักการ Cleanup

legacy docs เดิมถูกลบเพราะ:

- ซ้ำกันหลายชั้น
- แยก feature เดียวออกเป็นหลายเอกสารเกินไป
- มีข้อมูลขัดกันเอง
- มี phase history ที่มีค่าทาง audit แต่ไม่ควรเป็น current product documentation

canonical docs ใหม่จึงเหลือไฟล์เดียวคือไฟล์นี้

## 3.2 กลุ่มไฟล์ที่ถูกลบ

### A. Phase History Logs

- `PHASE0_STATUS.md` ถึง `PHASE114_STATUS.md`
- รวม `115` ไฟล์
- ถือเป็น development history, implementation snapshots, and handover notes
- ถูกแทนที่ด้วย:
  - Section 1 ของเอกสารนี้สำหรับ backlog/open items
  - Section 2 สำหรับ system/feature map

### B. Planning / Checklist / Template Docs

- `MVP_PHASE_PLAN.md`
- `PHASE_CHECKLIST.md`
- `PHASE_STATUS_TEMPLATE.md`
- `ADR-0001-platform-baseline.md`

เหตุผล:

- มีประโยชน์ช่วง build-out
- แต่ตอน consolidate แล้วข้อมูลหลักถูกดูดซึมเข้า master doc นี้แล้ว

### C. Assurance / Control Plane / Trust Docs

- `ASSURANCE_BULLETIN_DELIVERY.md`
- `ASSURANCE_CONTRACTS.md`
- `ASSURANCE_DIGEST_SIGNING.md`
- `ASSURANCE_EXTERNAL_VERIFIER.md`
- `ASSURANCE_PROOF_INDEX.md`
- `ASSURANCE_RISK_LOOP.md`
- `ASSURANCE_SLO.md`
- `ASSURANCE_VERIFIER_KIT.md`
- `ASSURANCE_ZERO_TRUST_ATTESTATION.md`
- `CONTROL_PLANE_GOVERNANCE_ATTESTATION.md`
- `CONTROL_PLANE_GOVERNANCE_POLICY.md`
- `EXTERNAL_AUDIT_PACK.md`
- `EXTERNAL_AUDIT_PUBLICATION_RUNBOOK.md`
- `LEGAL_ETHICAL_POLICY.md`
- `LEGAL_EVIDENCE_PROFILE.md`
- `PUBLIC_ASSURANCE_API.md`
- `PUBLIC_ASSURANCE_SIGNING.md`

เหตุผล:

- endpoint และ policy surface เหล่านี้ถูกรวมสรุปไว้แล้วใน Section 2
- ของเดิมเป็น split API/runbook docs ที่มี overlap สูง

### D. Orchestration / Ops Docs

- `OBJECTIVE_GATE_DASHBOARD_API.md`
- `OBJECTIVE_GATE_RUNBOOK.md`
- `ORCHESTRATION_ACTIVATION.md`
- `ORCHESTRATION_PILOT_MODE.md`
- `ORCHESTRATION_PILOT_ONBOARDING.md`
- `PRODUCTION_V1_GO_LIVE_RUNBOOK.md`
- `DR_RUNBOOK.md`

เหตุผล:

- เป็นเอกสารเฉพาะ flow
- เนื้อหาหลักถูกรวมในหมวด Orchestra แล้ว
- ถ้าจะมี playbook/runbook รอบใหม่ควรเขียนจาก canonical doc นี้เป็นฐาน

### E. Competitive/Product Docs

- `COMPETITIVE_ENGINE_API.md`
- `SOAR_CONNECTOR_API.md`
- `PURPLE_EXECUTIVE_API.md`
- `VIRTUAL_EXPERT_CHECKLIST.md`

เหตุผล:

- เป็น source ของ feature map เดิม
- แต่มี overlap กันสูงมาก
- และ `VIRTUAL_EXPERT_CHECKLIST.md` เดิมมี backlog/closure references จำนวนมากที่ควรรวมเป็น summary เดียวแทน

### F. Load Test Docs

- `loadtest/README.md`
- `loadtest/reports/BASELINE_EVIDENCE_TEMPLATE.md`

เหตุผล:

- ตอนนี้ถูกยุบให้เป็นส่วนหนึ่งของ operational/open-item summary
- benchmark details ที่ยังต้องทำจริงถูกรวมไว้ใน Section 1 แล้ว

## 3.3 ปัญหาเอกสารที่ถูกแก้ด้วยการ Consolidate

- phase status `In Progress` ค้างอยู่ `7` ไฟล์ ทั้งที่ภาพรวมล่าสุดปิดแล้ว
- มี broken absolute path references `17` ไฟล์ ชี้ไป path `BRP-Cyber` ที่ไม่ตรงกับ repo ปัจจุบัน `brp-cyber`
- backlog บางชุดถูกปิดไปแล้วใน phase ถัดมา แต่ legacy docs ยังทำให้ดูเหมือนค้าง

## 3.4 Current Documentation Rule

หลัง cleanup นี้ ให้ถือ rule ดังนี้:

- เอกสาร product/project canonical มีไฟล์เดียว: `docs/MASTER_DOCUMENTATION.md`
- source of truth เชิง behavior ให้ดูจาก code/tests ก่อนเอกสารเสมอ
- ถ้ามี feature ใหม่ในอนาคต:
  - อัปเดตไฟล์นี้โดยตรง
  - ถ้าต้องมี runbook เฉพาะเรื่อง ให้สร้างเพิ่มเฉพาะเมื่อเป็น operational artifact ที่แยกออกมาแล้วคุ้มค่า

## 3.5 Recommended Next Work Order

ถ้าจะกลับมาทำ backlog ที่เหลือ แนะนำลำดับดังนี้:

1. ทำ target-cluster KEDA e2e validation บน Kubernetes environment จริง
2. รัน multi-tenant concurrent benchmark matrix ใน prod-like environment และเก็บ evidence report/json sidecar
3. รัน live Redis/API integration suites ใน environment ที่มี Redis จริงเข้าถึงได้
