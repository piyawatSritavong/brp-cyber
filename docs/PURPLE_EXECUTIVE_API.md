# Purple Executive API

## Site Executive Scorecard
- `GET /sites/{site_id}/purple/executive-scorecard?lookback_runs=&lookback_events=&sla_target_seconds=`

Returns:
- MITRE ATT&CK technique heatmap rows (`technique_id`, detection status, mitigation proxy)
- remediation SLA snapshot (`estimated_mttr_seconds`, `apply_rate`, `sla_status`)
- executive summary metrics for board-level tracking

## Federation Executive Rollup
- `GET /sites/purple/executive-federation?limit=&lookback_runs=&lookback_events=&sla_target_seconds=`

Returns:
- site-level executive rows ranked by risk
- `passing_sites` / `at_risk_sites` counters
- coverage and SLA trend indicators for MSSP / multi-tenant oversight
