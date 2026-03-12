# Competitive Engine API

Phase 64 APIs for objective-scoped competitive build-out.

## Objective Scope
- `GET /competitive/objectives`
- `POST /competitive/phases/check`
- `GET /competitive/phases/checks?limit=`

## Threat Content Pipeline
- `POST /competitive/threat-content/packs`
- `GET /competitive/threat-content/packs?category=&active_only=&limit=`

## Threat Content Pipeline Automation (Phase 75)
- `POST /competitive/threat-content/pipeline/policies`
- `GET /competitive/threat-content/pipeline/policies?scope=`
- `POST /competitive/threat-content/pipeline/run`
- `GET /competitive/threat-content/pipeline/runs?scope=&limit=`
- `POST /competitive/threat-content/pipeline/scheduler/run?limit=&dry_run_override=&actor=`
- `GET /competitive/threat-content/pipeline/federation?limit=&stale_after_hours=`

## Red: Exploit Path
- `POST /competitive/sites/{site_id}/red/exploit-path/simulate`
- `GET /competitive/sites/{site_id}/red/exploit-path/runs?limit=`

## Red: Exploit Autopilot (Phase 74)
- `POST /competitive/sites/{site_id}/red/exploit-autopilot/policy`
- `GET /competitive/sites/{site_id}/red/exploit-autopilot/policy`
- `POST /competitive/sites/{site_id}/red/exploit-autopilot/run`
- `GET /competitive/sites/{site_id}/red/exploit-autopilot/runs?limit=`
- `POST /competitive/red/exploit-autopilot/scheduler/run?limit=&dry_run_override=&actor=`

## Blue: Detection Copilot
- `POST /competitive/sites/{site_id}/blue/detection-copilot/tune`
- `GET /competitive/sites/{site_id}/blue/detection-copilot/rules?limit=`
- `POST /competitive/sites/{site_id}/blue/detection-copilot/rules/{rule_id}/apply`
- `GET /competitive/sites/{site_id}/blue/detection-copilot/runs?limit=`

## Blue: Detection Autotune (Phase 73)
- `POST /competitive/sites/{site_id}/blue/detection-autotune/policy`
- `GET /competitive/sites/{site_id}/blue/detection-autotune/policy`
- `POST /competitive/sites/{site_id}/blue/detection-autotune/run`
- `GET /competitive/sites/{site_id}/blue/detection-autotune/runs?limit=`
- `POST /competitive/blue/detection-autotune/scheduler/run?limit=&dry_run_override=&actor=`

## Unified Case Graph
- `GET /competitive/sites/{site_id}/case-graph?limit=`
  - Phase 72 response extensions:
    - `summary.soar_executions`, `summary.connector_events`, `summary.connector_replay_runs`
    - `summary.risk_score`, `summary.risk_tier`
    - `risk` (composite case risk metrics + recommendation)
    - `timeline` (cross-domain event chronology)

## Phase 67 Extensions (Connector + SecOps Data Tier)
- `POST /competitive/connectors/credentials`
- `GET /competitive/connectors/credentials`
- `POST /competitive/connectors/credentials/rotate`
- `GET /competitive/connectors/credentials/rotation-events`
- `GET /competitive/connectors/credentials/rotation-verify`
- `GET /competitive/secops/data-tier/benchmark`
- `GET /competitive/secops/data-tier/federation`

## Phase 68 Extensions (Credential Hygiene Auto-Rotation)
- `GET /competitive/connectors/credentials/hygiene`
- `POST /competitive/connectors/credentials/auto-rotate`
- `GET /competitive/connectors/credentials/hygiene/federation`

## Phase 69 Extensions (Credential Hygiene Policy Scheduler)
- `POST /competitive/connectors/credentials/hygiene/policies`
- `GET /competitive/connectors/credentials/hygiene/policies`
- `POST /competitive/connectors/credentials/hygiene/run`
- `GET /competitive/connectors/credentials/hygiene/runs`
- `POST /competitive/connectors/credentials/hygiene/scheduler/run`

## Phase 71 Extensions (Connector Reliability Replay Orchestration)
- `POST /competitive/connectors/reliability/policies`
- `GET /competitive/connectors/reliability/policies`
- `GET /competitive/connectors/reliability/backlog`
- `POST /competitive/connectors/reliability/replay`
- `GET /competitive/connectors/reliability/runs`
- `POST /competitive/connectors/reliability/scheduler/run`
- `GET /competitive/connectors/reliability/federation`
