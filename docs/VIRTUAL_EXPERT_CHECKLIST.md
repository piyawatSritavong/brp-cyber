# Virtual Expert Checklist

สถานะอ้างอิงจาก implementation จริงใน codebase ปัจจุบัน ไม่ใช่ marketing roadmap

อัปเดตหลัง re-audit implementation จริงล่าสุดเมื่อ `2026-03-16`

หมายเหตุรอบนี้:
- re-audit code + API + UI + tests จริงอีกครั้งหลังปิด Phase 102-107
- แยก `baseline acceptance` ออกจาก `future hardening backlog` ให้ชัด
- เป้าหมายของ checklist นี้คือยืนยันว่า Service Menu และ Plugin Catalog ตาม requirement ของผู้ใช้ “ครบ baseline แล้ว”

## Status Legend
- `[x] Implemented baseline` ใช้งานได้จริงผ่าน API/UI และมี persistence/history ตาม baseline requirement

## Baseline Acceptance Summary
- `[x]` Red Service Category ครบ baseline
- `[x]` Blue Service Category ครบ baseline
- `[x]` Purple Service Category ครบ baseline
- `[x]` Red/Blue/Purple Plugin Catalog ครบ baseline
- `[x]` Supporting plugin-first platform capabilities ครบ baseline

## Red Service Category

### Service Menu
- `[x] 24/7 Shadow Pentest`
  - มีแล้ว:
    - passive shadow crawl แบบ non-intrusive ต่อ site
    - page/content diff detection เทียบ baseline ล่าสุด
    - per-site shadow policy (`crawl_depth/max_pages/change_threshold/schedule`)
    - zero-day pack auto-assignment baseline จาก drift signal
    - scheduler + autonomous runtime integration
    - deeper asset inventory baseline จาก passive crawl
    - deploy-event trigger mode สำหรับ CI/CD หรือ release pipeline
    - pack-to-asset validation chaining baseline จาก latest drift + selected threat pack
    - Red scan flow (`baseline_scan`, `vuln_scan`, `pentest_sim`)
    - exploit path simulation
    - red exploit autopilot policy/run/scheduler
    - threat content pipeline + federation freshness

- `[x] Social Engineering Simulator`
  - มีแล้ว:
    - Thai phishing simulation run/history
    - risk score / click-rate estimate / Thai subject lines / lure suggestions
    - dry-run/simulated campaign mode
    - employee roster import
    - connector policy abstraction (`simulated` / `smtp` / `webhook`)
    - delivery/open/click/report telemetry baseline ต่อ recipient
    - campaign approval / reject / kill switch flow
    - external provider callback ingestion baseline สำหรับ delivery/open/click/report feedback

- `[x] Vulnerability Auto-Validator`
  - มีแล้ว:
    - exploit-path validation baseline
    - red scan finding summaries
    - risk-tiered validation outputs
    - import จาก Nessus/Burp/generic payload โดยตรง
    - finding normalization / dedupe / exploitability verdict ต่อ finding
    - false-positive scoring ต่อ finding
    - remediation export กลับไปหา scanner/source tool

### Plugins
- `[x] Exploit Code Generator`
  - มีแล้ว:
    - generate Python PoC draft จาก finding ล่าสุด
    - run ได้จาก Red page และเก็บ plugin run history
    - import CVE/news/article intelligence baseline ต่อ site
    - external intelligence sync source + sync run history baseline
    - exploit safety policy per target type
    - lint/export baseline ผ่าน Red page และ competitive API

- `[x] Nuclei AI-Template Writer`
  - มีแล้ว:
    - generate YAML template draft จาก scan/finding ล่าสุด
    - run ได้จาก Red page และเก็บ plugin run history
    - import CVE/news/article intelligence baseline ต่อ site
    - external intelligence sync source + scheduler baseline
    - template lint/validation/export baseline
    - one-click publish เป็น threat-content pack baseline

## Blue Service Category

### Service Menu
- `[x] AI Log Refiner (The Noise Killer)`
  - มีแล้ว:
    - plugin `blue_log_refiner`
    - signal/noise summary
    - Thai delivery / embedded invoke path / plugin scheduler
    - pre-ingest/post-ingest policy baseline ต่อ site/source connector
    - noise-reduction KPI และ estimated storage savings ต่อ run
    - operator feedback loop สำหรับ false positive / signal missed
    - vendor mapping packs สำหรับ `Splunk`, `ELK`, `Cloudflare`, `CrowdStrike`, `generic`
    - source-SIEM callback ingestion
    - continuous refinement scheduler policy ต่อ connector

- `[x] Managed AI Responder`
  - มีแล้ว:
    - policy persistence
    - dry-run/apply run
    - approval / reject / rollback
    - evidence chain verify
    - scheduler + autonomous runtime integration
    - embedded workflow + SOAR/playbook path
    - vendor-aware direct action plan/confirmation สำหรับ `Cloudflare`, `CrowdStrike`, `Splunk`, `generic`
    - connector action status / confirmation status / rollback status ใน run history
    - connector rollback confirmation baseline

- `[x] Threat Intelligence Localizer`
  - มีแล้ว:
    - Thai localized threat brief
    - relevance / priority score ต่อ site
    - recommended actions + run history
    - external threat feed ingestion baseline สำหรับไทย/SEA
    - sector profile library
    - recurring digest/subscription mode + scheduler
    - site impact scoring + feed match summary ต่อ run
    - connector-native feed adapters สำหรับ `Splunk`, `CrowdStrike`, `Cloudflare`, `generic`
    - detection-gap correlation baseline เทียบ threat categories กับ detection rules + embedded connectors ของ site
    - stakeholder routing pack ไปกลุ่ม `soc_l1`, `threat_hunting`, `security_lead`
    - gap promotion loop ไปสู่ detection autotune / playbook dispatch baseline

### Plugins
- `[x] Thai Alert Translator & Summarizer`
  - มีแล้ว:
    - plugin run ได้จริง
    - Thai incident summary
    - embedded endpoint trigger ได้
    - delivery channel integration ได้

- `[x] Auto-Playbook Executor (Webhook)`
  - มีแล้ว:
    - plugin generates action payload
    - SOAR playbook dispatch path
    - embedded endpoint presets สำหรับ CrowdStrike/Cloudflare
    - SOAR marketplace content packs baseline
    - post-action verification baseline ต่อ SOAR execution
    - connector-native webhook/result contracts
    - vendor callback ingestion กลับเข้า execution summary

## Purple Service Category

### Service Menu
- `[x] Automated ISO/NIST Gap Analysis`
  - มีแล้ว:
    - ISO 27001 gap template
    - NIST CSF gap template
    - unified evidence correlation
    - executive scorecard / case graph
    - regulated report export baseline ที่รวม ISO/NIST snapshot + incident context

- `[x] ROI Security Dashboard`
  - มีแล้ว:
    - ROI snapshot generation
    - automation coverage
    - noise reduction
    - estimated analyst hours saved / cost saved
    - snapshot history
    - trend view จาก snapshot history
    - tenant portfolio roll-up baseline
    - board-pack export baseline (`pdf/ppt`)
    - native binary `pdf/pptx` renderer baseline
    - board template packs สำหรับ `board`, `risk_committee`, `mssp_monthly`

### Plugins
- `[x] MITRE ATT&CK Heatmap Generator`
  - มีแล้ว:
    - plugin run ได้จริง
    - MITRE/evidence correlation baseline
    - executive scorecard/federation support
    - export baseline (`markdown`, `csv`, `attack_layer_json`)

- `[x] Incident Report Ghostwriter`
  - มีแล้ว:
    - plugin run ได้จริง
    - Thai incident draft จาก Blue/Purple evidence
    - delivery/report flow รองรับ
    - company/board/regulator template packs
    - regulated report output baseline สำหรับ compliance handoff
    - native `pdf/docx` export baseline
    - final report release approval workflow

## Supporting Platform Already Present
- `[x] Plugin catalog + per-site binding`
- `[x] Embedded workflow API + shared-secret invoke`
- `[x] Vendor presets for Splunk / CrowdStrike / Cloudflare`
- `[x] Delivery layer for Telegram / LINE / Teams / webhook`
- `[x] Delivery approval SLA + escalation scheduler`
- `[x] Embedded activation bundles + federation readiness posture`
- `[x] Multi-site federation views for Purple / delivery / embedded readiness`

## Acceptance Result
- `[x]` Baseline requirement จาก Service Menu + Plugin Catalog ตาม user requirement ปิดครบแล้ว
- `[x]` Checklist baseline ถือว่า complete 100%

## Future Hardening Backlog
รายการนี้ไม่ใช่ blocker ของ baseline acceptance แต่เป็น maturity backlog ระยะถัดไป

### Red
- multi-language exploit output นอกเหนือจาก Python draft
- richer legal/compliance template packs ต่อ social campaign type

### Blue
- deeper vendor coverage สำหรับ Managed AI Responder มากกว่าชุด baseline ปัจจุบัน
- live connector callback ingestion ที่ลึกกว่าระดับ orchestration baseline
- richer community/partner playbook pack catalog beyond starter bundles

### Purple
- policy/evidence mapping ที่ลงลึกขึ้นต่อ control family
- finer ROI segmentation/filtering ระดับ tenant/site/portfolio
- graphical heatmap export และ richer ATT&CK layer import/edit workflow

## Source of Truth in Code
- Red service: [RedTeamPanel.tsx](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/components/RedTeamPanel.tsx)
- Blue service: [BlueTeamPanel.tsx](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/components/BlueTeamPanel.tsx)
- Purple service: [PurpleReportsPanel.tsx](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/frontend/components/PurpleReportsPanel.tsx)
- Plugin catalog/runtime: [coworker_plugins.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/coworker_plugins.py)
- Social simulator: [red_social_engineering.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/red_social_engineering.py)
- Vulnerability auto-validator: [red_vulnerability_validator.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/red_vulnerability_validator.py)
- Red plugin intelligence: [red_plugin_intelligence.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/red_plugin_intelligence.py)
- Shadow pentest: [red_shadow_pentest.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/red_shadow_pentest.py)
- Threat localizer: [blue_threat_localizer.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/blue_threat_localizer.py)
- Threat localizer promotion: [blue_threat_localizer_promotion.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/blue_threat_localizer_promotion.py)
- Blue log refiner: [blue_log_refiner.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/blue_log_refiner.py)
- SOAR playbook hub: [soar_playbook_hub.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/soar_playbook_hub.py)
- Purple exports: [purple_plugin_exports.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/purple_plugin_exports.py)
- ROI dashboard: [purple_roi_dashboard.py](/Users/gustyle/Documents/networkmanGithub/BRP-Cyber/backend/app/services/purple_roi_dashboard.py)
