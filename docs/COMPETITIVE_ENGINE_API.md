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

## AI Co-worker Plugins (Phase 76)
- `GET /competitive/coworker/plugins?category=&active_only=`
- `GET /competitive/sites/{site_id}/coworker/plugins?category=`
- `POST /competitive/sites/{site_id}/coworker/plugins/bindings`
- `POST /competitive/sites/{site_id}/coworker/plugins/{plugin_code}/run`
- `GET /competitive/sites/{site_id}/coworker/plugins/runs?category=&limit=`
- `POST /competitive/coworker/plugins/scheduler/run?limit=&dry_run_override=&actor=`

## AI Co-worker Delivery Layer (Phase 77)
- `GET /competitive/sites/{site_id}/coworker/delivery/profiles`
- `POST /competitive/sites/{site_id}/coworker/delivery/profiles`
- `POST /competitive/sites/{site_id}/coworker/delivery/{plugin_code}/preview`
- `POST /competitive/sites/{site_id}/coworker/delivery/{plugin_code}/dispatch`
- `GET /competitive/sites/{site_id}/coworker/delivery/events?channel=&limit=`
- `POST /competitive/sites/{site_id}/coworker/delivery/events/{event_id}/review`
- `GET /competitive/sites/{site_id}/coworker/delivery/sla?limit=&approval_sla_minutes=`
- `GET /competitive/sites/{site_id}/coworker/delivery/escalation-policy?plugin_code=`
- `POST /competitive/sites/{site_id}/coworker/delivery/escalation-policy`
- `POST /competitive/sites/{site_id}/coworker/delivery/escalation/run`
- `POST /competitive/coworker/delivery/escalation/scheduler/run?site_id=&plugin_code=&limit=&dry_run_override=&actor=`
- `GET /competitive/coworker/delivery/escalation/federation?plugin_code=&approval_sla_minutes=&limit=`

## Embedded Workflow API (Phase 80)
- `GET /competitive/sites/{site_id}/embedded/endpoints?limit=`
- `POST /competitive/sites/{site_id}/embedded/endpoints`
- `GET /competitive/sites/{site_id}/embedded/invocations?endpoint_code=&limit=`
- `GET /competitive/sites/{site_id}/embedded/invoke-packs?endpoint_code=&limit=`
- `GET /competitive/sites/{site_id}/embedded/automation-verify?endpoint_code=&limit=`
- `GET /competitive/sites/{site_id}/embedded/activation-bundles?endpoint_code=&limit=`
- `GET /competitive/embedded/federation/readiness?connector_source=&limit=`
- `POST /integrations/embedded/sites/{site_code}/{endpoint_code}/invoke`
  - Header: `X-BRP-Embed-Token: <issued token>`
  - Guardrail HTTP mapping: `403 actor_not_allowed`, `409 replay_detected`, `429 rate_limit_exceeded`, `422 payload_*`
- `GET /integrations/adapters/templates?source=`

## Blue: Managed AI Responder (Phase 81-83)
- `GET /competitive/sites/{site_id}/blue/managed-responder/policy`
- `POST /competitive/sites/{site_id}/blue/managed-responder/policy`
- `POST /competitive/sites/{site_id}/blue/managed-responder/run`
- `GET /competitive/sites/{site_id}/blue/managed-responder/runs?limit=`
- `POST /competitive/sites/{site_id}/blue/managed-responder/runs/{run_id}/review`
- `POST /competitive/sites/{site_id}/blue/managed-responder/runs/{run_id}/rollback`
- `GET /competitive/sites/{site_id}/blue/managed-responder/evidence/verify?limit=`
- `POST /competitive/blue/managed-responder/scheduler/run?limit=&dry_run_override=&actor=`
- `GET /competitive/blue/managed-responder/vendor-packs?source=`
- `GET /competitive/sites/{site_id}/blue/managed-responder/callbacks?run_id=&connector_source=&limit=`
- `POST /competitive/sites/{site_id}/blue/managed-responder/runs/{run_id}/callback`
- `POST /integrations/blue/managed-responder/sites/{site_code}/runs/{run_id}/callback`
  - Header: `X-BRP-Signature: <shared-secret-hmac>`

## Red: Exploit Path
- `POST /competitive/sites/{site_id}/red/exploit-path/simulate`
- `GET /competitive/sites/{site_id}/red/exploit-path/runs?limit=`

## Red: Exploit Autopilot (Phase 74)
- `POST /competitive/sites/{site_id}/red/exploit-autopilot/policy`
- `GET /competitive/sites/{site_id}/red/exploit-autopilot/policy`
- `POST /competitive/sites/{site_id}/red/exploit-autopilot/run`
- `GET /competitive/sites/{site_id}/red/exploit-autopilot/runs?limit=`
- `POST /competitive/red/exploit-autopilot/scheduler/run?limit=&dry_run_override=&actor=`

## Red: Shadow Pentest (Phase 96)
- `POST /competitive/sites/{site_id}/red/shadow-pentest/policy`
- `GET /competitive/sites/{site_id}/red/shadow-pentest/policy`
- `POST /competitive/sites/{site_id}/red/shadow-pentest/run`
- `GET /competitive/sites/{site_id}/red/shadow-pentest/runs?limit=`
- `POST /competitive/red/shadow-pentest/scheduler/run?limit=&dry_run_override=&actor=`

## Red: Vulnerability Auto-Validator (Phase 87)
- `POST /competitive/sites/{site_id}/red/vuln-validator/import`
- `GET /competitive/sites/{site_id}/red/vuln-validator/findings?source_tool=&verdict=&limit=`
- `POST /competitive/sites/{site_id}/red/vuln-validator/run`
- `GET /competitive/sites/{site_id}/red/vuln-validator/runs?limit=`
- `GET /competitive/sites/{site_id}/red/vuln-validator/remediation-export?source_tool=&verdict=&limit=`

## Red: Social Engineering Production Path (Phase 90)
- `POST /competitive/sites/{site_id}/red/social-simulator/roster/import`
- `GET /competitive/sites/{site_id}/red/social-simulator/roster?active_only=&limit=`
- `GET /competitive/red/social-simulator/template-packs?campaign_type=&jurisdiction=`
- `POST /competitive/sites/{site_id}/red/social-simulator/policy`
- `GET /competitive/sites/{site_id}/red/social-simulator/policy`
- `POST /competitive/sites/{site_id}/red/social-simulator/run`
- `GET /competitive/sites/{site_id}/red/social-simulator/runs?limit=`
- `POST /competitive/sites/{site_id}/red/social-simulator/{run_id}/review`
- `POST /competitive/sites/{site_id}/red/social-simulator/{run_id}/kill`
- `GET /competitive/sites/{site_id}/red/social-simulator/telemetry?run_id=&limit=`
- `POST /competitive/sites/{site_id}/red/social-simulator/provider-callback`
  - policy/run payload extensions:
    - `campaign_type`
    - `template_pack_code`
    - `evidence_retention_days`
    - `legal_ack_required`

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

## Blue: Threat Intelligence Localizer External Feeds (Phase 91/97)
- `POST /competitive/sites/{site_id}/blue/threat-localizer/run`
- `GET /competitive/sites/{site_id}/blue/threat-localizer/runs?limit=`
- `GET /competitive/sites/{site_id}/blue/threat-localizer/policy`
- `POST /competitive/sites/{site_id}/blue/threat-localizer/policy`
- `POST /competitive/blue/threat-localizer/feed-items/import`
- `POST /competitive/blue/threat-localizer/feed-adapters/import`
- `GET /competitive/blue/threat-localizer/feed-items?focus_region=&sector=&category=&active_only=&limit=`
- `GET /competitive/blue/threat-localizer/feed-adapters?source=`
- `GET /competitive/blue/threat-localizer/sector-profiles`
- `POST /competitive/blue/threat-localizer/scheduler/run?limit=&dry_run_override=&actor=`
- `GET /competitive/sites/{site_id}/blue/threat-localizer/routing-policy`
- `POST /competitive/sites/{site_id}/blue/threat-localizer/routing-policy`
- `GET /competitive/sites/{site_id}/blue/threat-localizer/promotion-runs?limit=`
- `POST /competitive/sites/{site_id}/blue/threat-localizer/promote-gap`

## Purple: ROI Executive Export Layer (Phase 92/98)
- `POST /competitive/sites/{site_id}/purple/roi-dashboard/generate`
- `GET /competitive/sites/{site_id}/purple/roi-dashboard/snapshots?limit=`
- `GET /competitive/sites/{site_id}/purple/roi-dashboard/trends?limit=&metric_focus=&min_automation_coverage_pct=&min_noise_reduction_pct=`
- `GET /competitive/purple/roi-dashboard/portfolio?tenant_code=&site_code=&status=&min_automation_coverage_pct=&min_noise_reduction_pct=&sort_by=&limit=`
- `GET /competitive/purple/roi-dashboard/template-packs?audience=`
- `POST /competitive/sites/{site_id}/purple/roi-dashboard/export`

## SOAR Marketplace & Verification (Phase 100)
- `GET /competitive/soar/marketplace/overview?limit=`
- `GET /competitive/soar/marketplace/packs?category=&audience=&scope=&source_type=&trust_tier=&connector_source=&search=&featured_only=&limit=`
- `POST /competitive/soar/marketplace/packs/{pack_code}/install`
- `POST /competitive/soar/executions/{execution_id}/verify`
- `GET /competitive/soar/contracts/results?connector_source=`
- `POST /competitive/sites/{site_id}/soar/executions/{execution_id}/connector-result`
- `GET /competitive/sites/{site_id}/soar/executions/{execution_id}/connector-results?limit=`
- `POST /integrations/soar/sites/{site_code}/executions/{execution_id}/callback`

## Red: Shadow Pentest Asset Inventory & Deploy Trigger (Phase 101)
- `GET /competitive/sites/{site_id}/red/shadow-pentest/assets?limit=`
- `POST /competitive/sites/{site_id}/red/shadow-pentest/deploy-event`
- `GET /competitive/sites/{site_id}/red/shadow-pentest/pack-validation?limit=`

## Red: Plugin Intelligence Upgrade (Phase 93)
- `POST /competitive/sites/{site_id}/red/plugin-intelligence/import`
- `GET /competitive/sites/{site_id}/red/plugin-intelligence?source_type=&limit=`
- `GET /competitive/sites/{site_id}/red/plugin-intelligence/sync-sources?limit=`
- `POST /competitive/sites/{site_id}/red/plugin-intelligence/sync-sources`
- `POST /competitive/sites/{site_id}/red/plugin-intelligence/sync`
- `GET /competitive/sites/{site_id}/red/plugin-intelligence/sync-runs?limit=`
- `POST /competitive/red/plugin-intelligence/scheduler/run?limit=&dry_run_override=&actor=`
- `GET /competitive/sites/{site_id}/red/plugin-safety-policy?target_type=`
- `POST /competitive/sites/{site_id}/red/plugin-safety-policy`
- `POST /competitive/sites/{site_id}/red/plugins/{plugin_code}/lint`
- `POST /competitive/sites/{site_id}/red/plugins/{plugin_code}/export`
- `POST /competitive/sites/{site_id}/red/plugins/red_template_writer/publish-threat-pack`
  - `red_exploit_code_generator` รองรับ `target_language=python|bash|curl`

## Purple: Plugin Export Layer (Phase 94)
- `GET /competitive/purple/export/template-packs?kind=&audience=`
- `POST /competitive/sites/{site_id}/purple/mitre-heatmap/export`
- `POST /competitive/sites/{site_id}/purple/incident-report/export`
- `POST /competitive/sites/{site_id}/purple/regulatory-report/export`
  - `incident-report` และ `regulatory-report` รองรับ `markdown|json|pdf|docx`
- `mitre-heatmap` รองรับ `markdown|csv|attack_layer_json|svg`
- `GET /competitive/sites/{site_id}/purple/report-releases?limit=`
- `POST /competitive/sites/{site_id}/purple/report-releases`
- `POST /competitive/purple/report-releases/{release_id}/review`

## Purple: Control-Family Mapping & ATT&CK Layer Workflow (Phase 113/114)
- `GET /competitive/sites/{site_id}/purple/control-family-map?framework=`
- `POST /competitive/sites/{site_id}/purple/control-family-map/export`
- `GET /competitive/sites/{site_id}/purple/mitre-heatmap/layers?limit=`
- `POST /competitive/sites/{site_id}/purple/mitre-heatmap/layers/import`
- `POST /competitive/sites/{site_id}/purple/mitre-heatmap/layers/{layer_id}/edit`
- `POST /competitive/sites/{site_id}/purple/mitre-heatmap/layers/{layer_id}/export`
- `POST /competitive/sites/{site_id}/purple/mitre-heatmap/graphical-export`

## Blue: AI Log Refiner Production Mode (Phase 95)
- `GET /competitive/blue/log-refiner/mapping-packs?source=`
- `GET /competitive/sites/{site_id}/blue/log-refiner/policy?connector_source=`
- `POST /competitive/sites/{site_id}/blue/log-refiner/policy`
- `POST /competitive/sites/{site_id}/blue/log-refiner/run`
- `GET /competitive/sites/{site_id}/blue/log-refiner/runs?connector_source=&limit=`
- `POST /competitive/sites/{site_id}/blue/log-refiner/feedback`
- `GET /competitive/sites/{site_id}/blue/log-refiner/feedback?connector_source=&limit=`
- `GET /competitive/sites/{site_id}/blue/log-refiner/schedule-policy?connector_source=`
- `POST /competitive/sites/{site_id}/blue/log-refiner/schedule-policy`
- `POST /competitive/blue/log-refiner/scheduler/run?site_id=&connector_source=&limit=&dry_run_override=&actor=`
- `POST /competitive/sites/{site_id}/blue/log-refiner/callback`
- `GET /competitive/sites/{site_id}/blue/log-refiner/callbacks?connector_source=&limit=`
- `POST /integrations/blue/log-refiner/sites/{site_code}/callback`

## Unified Case Graph
- `GET /competitive/sites/{site_id}/case-graph?limit=`
  - Phase 72 response extensions:
    - `summary.soar_executions`, `summary.connector_events`, `summary.connector_replay_runs`
    - `summary.risk_score`, `summary.risk_tier`
    - `risk` (composite case risk metrics + recommendation)
    - `timeline` (cross-domain event chronology)

## Purple Compliance Templates
- `GET /sites/{site_id}/purple/iso27001-gap-template?limit=`
- `GET /sites/{site_id}/purple/nist-csf-gap-template?limit=`

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
