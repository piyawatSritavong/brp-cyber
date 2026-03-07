# Phase 18 Status

- Phase: `Phase 18 - Assurance Breach Auto-Remediation & Escalation`
- Status: `Completed`
- Last Updated: `2026-03-06`

## Scope
- Trigger remediation plan automatically when tenant assurance contract is breached
- Support escalation path (`pending_approval` vs `auto_apply`) with audit trail

## Planned Deliverables
- [x] Assurance remediation service from contract breach signals
- [x] Control-plane APIs for remediation trigger/status
- [x] Automated remediation script + scheduled workflow
- [x] Test coverage for remediation planning and execution

## Implemented APIs
- `POST /control-plane/assurance/contracts/{tenant_code}/remediate?limit=&auto_apply=`
- `GET /control-plane/assurance/contracts/{tenant_code}/remediation-status?limit=`

## Notes
- Remediation actions are derived from `unmet_clauses` of assurance contract evaluation.
- Default behavior creates `pending_approval` actions; `auto_apply=true` applies changes immediately.
- Escalation notification is sent through existing notifier channel.
