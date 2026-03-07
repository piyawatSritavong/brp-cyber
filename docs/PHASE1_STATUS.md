# Phase 1 Status

- Phase: `Phase 1 - Blue Core (Detect + Respond)`
- Status: `In Progress`
- Last Updated: `2026-03-06`

## Completed
- [x] Auth login ingest endpoint
- [x] WAF + System Auth log adapters (3-source ingest path)
- [x] Failed login burst detection logic (threshold/window)
- [x] Allowlist suppression check
- [x] Auto-response stub: firewall block IP
- [x] Telegram alert integration (config-driven)
- [x] Security event persistence to Redis Streams
- [x] Incident timeline persistence + query endpoint
- [x] Deterministic retry/backoff for firewall/telegram failures
- [x] Dead-letter stream for response/alert failures
- [x] Test cases added for rule behavior and false-positive guardrails

## Remaining
- [x] Add richer suppression policy (username/ASN/range)
- [ ] Execute unit/integration tests in CI or local env with pytest + Docker daemon enabled

## Evidence
- `backend/app/api/ingest.py`
- `backend/app/services/blue_detection.py`
- `backend/app/services/event_store.py`
- `backend/app/services/firewall_client.py`
- `backend/app/services/notifier.py`
- `backend/app/services/dead_letter.py`
- `backend/app/services/retry.py`
- `backend/tests/test_blue_detection.py`
- `backend/tests/test_ingest_api.py`
