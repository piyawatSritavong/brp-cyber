# SOAR + Connector API

## SOAR Playbook Hub
- `GET /competitive/auth/context`
- `POST /competitive/soar/playbooks`
- `GET /competitive/soar/playbooks?category=&scope=&active_only=&limit=`
- `GET /competitive/soar/marketplace/overview?limit=`
- `POST /competitive/soar/policies/playbook`
- `GET /competitive/soar/policies/playbook?tenant_code=`
- `POST /competitive/sites/{site_id}/soar/playbooks/{playbook_code}/execute`
- `GET /competitive/sites/{site_id}/soar/executions?status=&limit=`
- `POST /competitive/soar/executions/{execution_id}/approve`

## Connector Reliability
- `POST /competitive/connectors/events`
- `GET /competitive/connectors/events?connector_source=&status=&tenant_id=&site_id=&limit=`
- `GET /competitive/connectors/health?limit=`
- `GET /competitive/federation/action-center-sla?lookback_hours=&limit=`
- `POST /competitive/connectors/sla/profiles`
- `GET /competitive/connectors/sla/profiles?tenant_code=&connector_source=`
- `POST /competitive/connectors/sla/evaluate`
- `GET /competitive/connectors/sla/breaches?tenant_code=&connector_source=&limit=`

## Connector Reliability Replay (Phase 71)
- `POST /competitive/connectors/reliability/policies`
- `GET /competitive/connectors/reliability/policies?tenant_code=&connector_source=`
- `GET /competitive/connectors/reliability/backlog?tenant_code=&connector_source=&limit=`
- `POST /competitive/connectors/reliability/replay`
- `GET /competitive/connectors/reliability/runs?tenant_code=&limit=`
- `POST /competitive/connectors/reliability/scheduler/run?limit=&dry_run_override=&actor=`
- `GET /competitive/connectors/reliability/federation?limit=`

## Connector Credential Hardening (Phase 67)
- `POST /competitive/connectors/credentials`
- `GET /competitive/connectors/credentials?tenant_code=&connector_source=&limit=`
- `POST /competitive/connectors/credentials/rotate`
- `GET /competitive/connectors/credentials/rotation-events?tenant_code=&connector_source=&credential_name=&limit=`
- `GET /competitive/connectors/credentials/rotation-verify?tenant_code=&connector_source=&credential_name=&limit=`

## SecOps Data Tier Benchmarks (Phase 67)
- `GET /competitive/secops/data-tier/benchmark?tenant_code=&lookback_hours=&sample_limit=`
- `GET /competitive/secops/data-tier/federation?lookback_hours=&limit=`

## Credential Hygiene Governance (Phase 68)
- `GET /competitive/connectors/credentials/hygiene?tenant_code=&connector_source=&warning_days=&limit=`
- `POST /competitive/connectors/credentials/auto-rotate`
- `GET /competitive/connectors/credentials/hygiene/federation?warning_days=&limit=`

## Credential Hygiene Policy Scheduler (Phase 69)
- `POST /competitive/connectors/credentials/hygiene/policies`
- `GET /competitive/connectors/credentials/hygiene/policies?tenant_code=&connector_source=`
- `POST /competitive/connectors/credentials/hygiene/run`
- `GET /competitive/connectors/credentials/hygiene/runs?tenant_code=&limit=`
- `POST /competitive/connectors/credentials/hygiene/scheduler/run?limit=&dry_run_override=&actor=`

## Action Center
- `POST /competitive/action-center/policies`
- `GET /competitive/action-center/policies?tenant_code=`
- `POST /competitive/action-center/dispatch`
- `GET /competitive/action-center/events?tenant_code=&severity=&limit=`

## Scope Guard
- Use `POST /competitive/phases/check` at phase open/close to ensure objective alignment.
