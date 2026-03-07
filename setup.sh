#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${BRP_REPO_URL:-https://github.com/piyawatSritavong/brp-cyber.git}"
BRANCH="${BRP_BRANCH:-main}"
INSTALL_DIR="${BRP_INSTALL_DIR:-$HOME/brp-cyber}"
START_STACK="${BRP_START_STACK:-true}"
INSTALL_FRONTEND_DEPS="${BRP_INSTALL_FRONTEND_DEPS:-true}"

log() {
  printf '[setup] %s\n' "$1"
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '[setup] missing required command: %s\n' "$1" >&2
    exit 1
  fi
}

detect_compose() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
    return
  fi
  if command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
    return
  fi
  printf '[setup] docker compose plugin is required\n' >&2
  exit 1
}

wait_for_api() {
  local url="$1"
  local retries=60
  local wait_seconds=2
  local i=1
  while [ "$i" -le "$retries" ]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep "$wait_seconds"
    i=$((i + 1))
  done
  return 1
}

need_cmd git
need_cmd curl
need_cmd docker

COMPOSE_CMD="$(detect_compose)"

log "repo: ${REPO_URL}"
log "branch: ${BRANCH}"
log "install_dir: ${INSTALL_DIR}"

if [ -d "${INSTALL_DIR}/.git" ]; then
  log "existing repo found, pulling latest"
  git -C "${INSTALL_DIR}" fetch --all --prune
  git -C "${INSTALL_DIR}" checkout "${BRANCH}"
  git -C "${INSTALL_DIR}" pull --ff-only origin "${BRANCH}"
else
  log "cloning repository"
  git clone --branch "${BRANCH}" --depth 1 "${REPO_URL}" "${INSTALL_DIR}"
fi

if [ ! -f "${INSTALL_DIR}/backend/.env" ] && [ -f "${INSTALL_DIR}/backend/.env.example" ]; then
  cp "${INSTALL_DIR}/backend/.env.example" "${INSTALL_DIR}/backend/.env"
  log "created backend/.env from example"
fi

if [ ! -f "${INSTALL_DIR}/frontend/.env" ] && [ -f "${INSTALL_DIR}/frontend/.env.example" ]; then
  cp "${INSTALL_DIR}/frontend/.env.example" "${INSTALL_DIR}/frontend/.env"
  log "created frontend/.env from example"
fi

if [ "${START_STACK}" = "true" ]; then
  log "starting docker stack"
  (
    cd "${INSTALL_DIR}/infra/docker"
    ${COMPOSE_CMD} up -d --build
  )

  log "waiting for API health"
  if wait_for_api "http://localhost:8000/health/live"; then
    log "API is healthy"
  else
    printf '[setup] API did not become healthy in time\n' >&2
    exit 1
  fi

  log "initializing database schema"
  curl -fsS -X POST "http://localhost:8000/bootstrap/phase0/init-db" >/dev/null
fi

if [ "${INSTALL_FRONTEND_DEPS}" = "true" ]; then
  if command -v npm >/dev/null 2>&1; then
    log "installing frontend dependencies"
    (cd "${INSTALL_DIR}/frontend" && npm ci)
  else
    log "npm not found, skip frontend dependency install"
  fi
fi

log "setup completed"
cat <<EOF

BRP-Cyber installed at:
  ${INSTALL_DIR}

Useful commands:
  cd ${INSTALL_DIR}/infra/docker && ${COMPOSE_CMD} ps
  cd ${INSTALL_DIR}/frontend && npm run dev -- --port 3001
  curl -s http://localhost:8000/health/live

Quick start URL:
  Frontend: http://localhost:3001
  API:      http://localhost:8000
EOF
