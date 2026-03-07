# Phase 63 Status

- Phase: `Phase 63 - Universal Integration Layer & ISO Gap Automation`
- Status: `In Progress`
- Last Updated: `2026-03-07`

## Scope
- Build API-first adapter layer so external tools can send security telemetry into one normalized schema.
- Add webhook ingestion path with optional HMAC verification for production-safe integration.
- Generate Purple-side ISO/IEC 27001 gap template directly from real Red/Blue evidence.

## Planned Deliverables
- [x] Integration data model for raw + normalized events (`integration_events`)
- [x] Adapter service for OCSF-compatible normalization (Cloudflare/Wazuh/Splunk/CrowdStrike/Generic)
- [x] API endpoints for adapters/webhook ingestion/event listing
- [x] Auto-route normalized external events into Blue event stream
- [x] Purple endpoint for ISO/IEC 27001 gap template generation by site
- [x] Frontend updates: adapter visibility + sample external-event ingest action
- [x] Frontend updates: Purple panel ISO gap summary rendering
- [x] Unit tests for adapter normalization + webhook signature checks
- [ ] Add per-integration credential vault abstraction (token/key rotation by connector)
- [ ] Add connector health telemetry + retry/dead-letter dashboard widget

## Implemented APIs (Phase 63 scope)
- `GET /integrations/adapters`
- `POST /integrations/events`
- `POST /integrations/webhooks/{source}`
- `GET /integrations/events`
- `GET /sites/{site_id}/purple/iso27001-gap-template?limit=`

## Notes
- Red behavior remains simulation-safe and authorized validation only.
- Webhook signature verification is controlled by `INTEGRATION_WEBHOOK_HMAC_SECRET`.
- Normalized schema is OCSF-compatible for cross-tool ingestion consistency.
