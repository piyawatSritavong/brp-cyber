# Phase 2 Status

- Phase: `Phase 2 - Purple Core (Correlation + KPI + Reporting)`
- Status: `In Progress`
- Last Updated: `2026-03-06`

## Completed
- [x] Correlation engine จาก `security_events` stream ต่อ tenant
- [x] KPI engine (`MTTD`, `MTTR`, `detection_coverage`, `blocked_before_impact_rate`)
- [x] Executive summary + table output (`Attack Type | Detection Status | Mitigation Time | Recommendation`)
- [x] Daily report generation API + report history stream
- [x] Purple report event emission (`purple_report_event`)
- [x] Unit/API test cases สำหรับ correlation/report

## Remaining
- [ ] Report export format (PDF/JSON artifact to object storage)
- [ ] Dashboard-facing query optimization (pagination/filtering/date-range)
- [ ] Integration tests against live Redis + API runtime

## Evidence
- `backend/app/services/purple_core.py`
- `backend/app/api/purple.py`
- `backend/tests/test_purple_core.py`
- `backend/tests/test_purple_api.py`
