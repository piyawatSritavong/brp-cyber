# Phase 6 Status

- Phase: `Phase 6 - Control Plane & Operational Readiness`
- Status: `Completed`
- Last Updated: `2026-03-06`

## Completed
- [x] Control plane onboarding API (`/control-plane/onboard`)
- [x] Tenant bootstrap flow (quota + strategy profile)
- [x] API key issuance at onboarding (hashed at rest)
- [x] Tenant detail API (`/control-plane/tenant/{tenant_id}`)
- [x] Tenant lifecycle action: suspend/reactivate (`/control-plane/tenant/status`)
- [x] Tenant API key rotation (`/control-plane/tenant/rotate-key`)
- [x] Token-based admin auth with expiry (`/control-plane/auth/token` + Bearer)
- [x] Admin token rotate/revoke/introspect endpoints
- [x] Fine-grained scope enforcement for control-plane endpoints
- [x] Tenant-scoped delegation (`tenant_scope` on admin tokens)
- [x] IdP auth provider mode (`CONTROL_PLANE_AUTH_PROVIDER=idp`)
- [x] Audit log sink for control-plane administrative actions (`/control-plane/audit`)
- [x] SIEM export endpoint and incremental export state tracking (`/control-plane/audit/export`)
- [x] Failed-batch tracking + replay recovery endpoints
- [x] Immutable signed archive chain for exported SIEM batches
- [x] Immutable store status + snapshot export + chain verification endpoints
- [x] Offload of signed archive batches to immutable store target (filesystem/S3)
- [x] DR smoke automation script (backup + restore verify + redis bgsave)
- [x] DR runbook document
- [x] Scheduled DR smoke workflow (`.github/workflows/dr-smoke.yml`)
- [x] Scheduled admin activity report workflow (`.github/workflows/admin-activity-report.yml`)
- [x] Scheduled SIEM export workflow (`.github/workflows/siem-export.yml`)
- [x] Scheduled SIEM replay workflow (`.github/workflows/siem-replay.yml`)
- [x] Scheduled archive offload workflow (`.github/workflows/audit-offload.yml`)
- [x] SIEM ack endpoint + replay backlog reconciliation endpoint/workflow

## Handover To Phase 7
- [ ] Replace bootstrap token flow with external IdP provisioning/bootstrap
- [ ] Enable S3 Object Lock production validation on target bucket policy
- [x] Connect objective-gate result to tenant production promotion controls

## Evidence
- `backend/app/api/control_plane.py`
- `backend/app/services/control_plane.py`
- `backend/app/services/admin_auth.py`
- `backend/app/services/idp_auth.py`
- `backend/app/services/audit.py`
- `backend/app/services/audit_export.py`
- `backend/app/services/audit_recovery.py`
- `backend/app/services/audit_archive.py`
- `backend/app/services/audit_immutable_store.py`
- `backend/app/services/audit_offload.py`
- `backend/schemas/control_plane.py`
- `backend/scripts/dr_backup_restore_smoke.sh`
- `backend/scripts/export_control_plane_audit.py`
- `backend/scripts/replay_control_plane_audit.py`
- `backend/scripts/reconcile_control_plane_audit.py`
- `backend/scripts/offload_control_plane_archive.py`
- `backend/scripts/generate_admin_activity_report.py`
- `docs/DR_RUNBOOK.md`
- `.github/workflows/dr-smoke.yml`
- `.github/workflows/admin-activity-report.yml`
- `.github/workflows/siem-export.yml`
- `.github/workflows/siem-replay.yml`
- `.github/workflows/audit-offload.yml`
- `.github/workflows/siem-reconcile.yml`
- `backend/tests/test_admin_auth.py`
- `backend/tests/test_audit.py`
- `backend/tests/test_audit_export.py`
- `backend/tests/test_audit_recovery.py`
- `backend/tests/test_audit_archive.py`
- `backend/tests/test_audit_offload.py`
