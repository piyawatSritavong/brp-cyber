#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/dr_backup_restore_smoke.sh
# Requirements:
#   - docker-compose stack running from infra/docker
#   - brp-postgres container available

BACKUP_DIR="${BACKUP_DIR:-./tmp/dr_backups}"
TS="$(date +%Y%m%d_%H%M%S)"
DUMP_FILE="${BACKUP_DIR}/brp_cyber_${TS}.dump"
RESTORE_DB="brp_cyber_restore_smoke"

mkdir -p "${BACKUP_DIR}"

echo "[1/5] Creating pg_dump backup -> ${DUMP_FILE}"
docker exec brp-postgres pg_dump -U brp -d brp_cyber -Fc > "${DUMP_FILE}"

echo "[2/5] Preparing restore database: ${RESTORE_DB}"
docker exec brp-postgres psql -U brp -d postgres -c "DROP DATABASE IF EXISTS ${RESTORE_DB};"
docker exec brp-postgres psql -U brp -d postgres -c "CREATE DATABASE ${RESTORE_DB};"

echo "[3/5] Restoring backup into ${RESTORE_DB}"
cat "${DUMP_FILE}" | docker exec -i brp-postgres pg_restore -U brp -d "${RESTORE_DB}" --no-owner --no-privileges

echo "[4/5] Running restore verification"
docker exec brp-postgres psql -U brp -d "${RESTORE_DB}" -c "SELECT count(*) AS tenants_count FROM tenants;"

echo "[5/5] Redis persistence check"
docker exec brp-redis redis-cli BGSAVE

echo "DR smoke test completed successfully"
