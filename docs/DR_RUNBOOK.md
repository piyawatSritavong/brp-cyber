# DR Runbook (Backup/Restore)

## Objective
ยืนยันว่า backup/restore ของ PostgreSQL และ persistence trigger ของ Redis ใช้งานได้จริงแบบ smoke test

## Prerequisites
- stack ทำงานอยู่ (`infra/docker/docker-compose.yml`)
- container names: `brp-postgres`, `brp-redis`

## Smoke Test Command
```bash
cd backend
./scripts/dr_backup_restore_smoke.sh
```

## Scheduled Automation
- GitHub Actions workflow: `.github/workflows/dr-smoke.yml`
- Default schedule: every Monday at 02:00 UTC

## Audit Recovery Flow (Ops)
1. Export audit to SIEM
```bash
cd backend
python scripts/export_control_plane_audit.py --batch-size 500
```
2. Replay failed batches (if any)
```bash
python scripts/replay_control_plane_audit.py --limit 200
```
3. Offload signed archive to immutable store
```bash
python scripts/offload_control_plane_archive.py --limit 500
```

## Expected Outcome
- ได้ไฟล์ backup ใน `backend/tmp/dr_backups/`
- restore DB สำเร็จ (`brp_cyber_restore_smoke`)
- query ตาราง `tenants` ผ่าน
- Redis `BGSAVE` สำเร็จ
- audit recovery scripts return success/consistent status
