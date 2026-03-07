# Phase 0 Status

- Phase: `Phase 0 - Foundation & Governance`
- Status: `Done`
- Last Updated: `2026-03-06`

## Completed
- [x] Repo structure baseline
- [x] Event schema taxonomy
- [x] Tenant/RBAC data model
- [x] Trace fields in event schema (`tenant_id`, `correlation_id`, `trace_id`)
- [x] FastAPI baseline + health endpoints
- [x] Docker Compose baseline (API, Postgres/Timescale, Redis, Prometheus, Loki, Promtail, Grafana)
- [x] DB bootstrap endpoint (`timescaledb` extension + tables)
- [x] ADR baseline document
- [x] Legal/Ethical operating policy document
- [x] Global kill-switch API

## Notes
- Structured event persistence ถูกเริ่มใน Redis Streams แล้ว และจะขยายใน Phase 1/2

## Evidence
- `backend/schemas/events.py`
- `backend/app/db/models.py`
- `backend/app/services/rbac.py`
- `backend/app/api/guardrails.py`
- `infra/docker/docker-compose.yml`
- `docs/ADR-0001-platform-baseline.md`
- `docs/LEGAL_ETHICAL_POLICY.md`
