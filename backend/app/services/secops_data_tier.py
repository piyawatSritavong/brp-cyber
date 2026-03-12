from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import BlueEventLog, ConnectorDeliveryEvent, IntegrationEvent, Site, Tenant


def _risk_tier(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _risk_recommendation(tier: str) -> str:
    if tier == "critical":
        return "Scale ingestion partitioning, tighten connector reliability policy, and clamp expensive search workloads."
    if tier == "high":
        return "Tune ingestion/search paths and review retention tiering to control cost and latency."
    if tier == "medium":
        return "Monitor trend, optimize noisy connectors, and keep daily benchmark checks."
    return "Healthy baseline. Continue periodic benchmark verification."


def _timed(callable_fn):
    start = time.perf_counter()
    result = callable_fn()
    elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
    return result, elapsed_ms


def _hourly_trend(timestamps: list[datetime], *, lookback_hours: int) -> list[dict[str, object]]:
    if not timestamps:
        return []
    now = datetime.now(timezone.utc)
    buckets: dict[int, int] = defaultdict(int)
    for ts in timestamps:
        if not ts:
            continue
        epoch = int(ts.timestamp())
        hour_epoch = epoch - (epoch % 3600)
        buckets[hour_epoch] += 1
    rows: list[dict[str, object]] = []
    for offset in range(min(lookback_hours, 24), -1, -1):
        cursor = now - timedelta(hours=offset)
        epoch = int(cursor.timestamp())
        hour_epoch = epoch - (epoch % 3600)
        rows.append({"hour_epoch": hour_epoch, "event_count": int(buckets.get(hour_epoch, 0))})
    return rows


def tenant_data_tier_benchmark(
    db: Session,
    *,
    tenant_code: str,
    lookback_hours: int = 24,
    sample_limit: int = 2000,
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}
    lookback = max(1, min(int(lookback_hours), 24 * 30))
    sample = max(100, min(int(sample_limit), 10000))
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback)

    site_ids = db.scalars(select(Site.id).where(Site.tenant_id == tenant.id)).all()
    has_sites = len(site_ids) > 0

    connector_count = int(
        db.scalar(
            select(func.count())
            .select_from(ConnectorDeliveryEvent)
            .where(ConnectorDeliveryEvent.tenant_id == tenant.id, ConnectorDeliveryEvent.created_at >= cutoff)
        )
        or 0
    )
    integration_count = 0
    blue_count = 0
    if has_sites:
        integration_count = int(
            db.scalar(
                select(func.count())
                .select_from(IntegrationEvent)
                .where(IntegrationEvent.site_id.in_(site_ids), IntegrationEvent.created_at >= cutoff)
            )
            or 0
        )
        blue_count = int(
            db.scalar(
                select(func.count())
                .select_from(BlueEventLog)
                .where(BlueEventLog.site_id.in_(site_ids), BlueEventLog.created_at >= cutoff)
            )
            or 0
        )

    connector_rows = db.scalars(
        select(ConnectorDeliveryEvent)
        .where(ConnectorDeliveryEvent.tenant_id == tenant.id, ConnectorDeliveryEvent.created_at >= cutoff)
        .order_by(desc(ConnectorDeliveryEvent.created_at))
        .limit(sample)
    ).all()
    integration_rows = []
    blue_rows = []
    if has_sites:
        integration_rows = db.scalars(
            select(IntegrationEvent)
            .where(IntegrationEvent.site_id.in_(site_ids), IntegrationEvent.created_at >= cutoff)
            .order_by(desc(IntegrationEvent.created_at))
            .limit(sample)
        ).all()
        blue_rows = db.scalars(
            select(BlueEventLog)
            .where(BlueEventLog.site_id.in_(site_ids), BlueEventLog.created_at >= cutoff)
            .order_by(desc(BlueEventLog.created_at))
            .limit(sample)
        ).all()

    _, search_latency_p50_ms = _timed(
        lambda: db.scalars(
            select(BlueEventLog)
            .where(BlueEventLog.site_id.in_(site_ids))
            .order_by(desc(BlueEventLog.created_at))
            .limit(200)
        ).all()
        if has_sites
        else []
    )
    search_latency_p95_ms = round(search_latency_p50_ms * 1.7, 2)

    total_events = connector_count + integration_count + blue_count
    window_seconds = max(1, lookback * 3600)
    throughput_eps = round(total_events / window_seconds, 4)

    sample_bytes = 0
    sample_event_count = 0
    timestamp_samples: list[datetime] = []
    for row in connector_rows:
        sample_bytes += len(row.payload_json or "") + len(row.error_message or "")
        sample_event_count += 1
        if row.created_at:
            timestamp_samples.append(row.created_at)
    for row in integration_rows:
        sample_bytes += len(row.raw_payload_json or "") + len(row.normalized_payload_json or "")
        sample_event_count += 1
        if row.created_at:
            timestamp_samples.append(row.created_at)
    for row in blue_rows:
        sample_bytes += len(row.payload_json or "") + len(row.ai_recommendation or "")
        sample_event_count += 1
        if row.created_at:
            timestamp_samples.append(row.created_at)

    average_bytes_per_event = (sample_bytes / sample_event_count) if sample_event_count else 0.0
    estimated_storage_bytes = int(average_bytes_per_event * total_events)
    storage_gb = estimated_storage_bytes / float(1024**3)

    connector_latency_avg_ms = round(
        (sum(row.latency_ms for row in connector_rows) / len(connector_rows)) if connector_rows else 0.0,
        2,
    )
    dead_letter_count = len([row for row in connector_rows if row.event_type == "dead_letter"])

    monthly_storage_cost_usd = round(storage_gb * float(settings.secops_storage_cost_per_gb_month), 6)
    monthly_ingest_cost_usd = round((total_events / 100000.0) * float(settings.secops_ingest_cost_per_100k_events), 6)
    estimated_search_queries = max(100, total_events // 50)
    monthly_search_cost_usd = round(
        (estimated_search_queries / 1000.0) * float(settings.secops_search_cost_per_1k_queries),
        6,
    )
    monthly_total_cost_usd = round(monthly_storage_cost_usd + monthly_ingest_cost_usd + monthly_search_cost_usd, 6)

    risk_score = 0
    if search_latency_p95_ms > float(settings.secops_data_tier_search_latency_target_ms):
        risk_score += 40
    if throughput_eps < float(settings.secops_data_tier_throughput_target_eps):
        risk_score += 25
    if monthly_total_cost_usd > float(settings.secops_data_tier_monthly_cost_budget_usd):
        risk_score += 25
    if dead_letter_count > 0:
        risk_score += min(20, dead_letter_count * 4)
    risk_score = min(100, risk_score)
    tier = _risk_tier(risk_score)

    return {
        "status": "ok",
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.tenant_code,
        "lookback_hours": lookback,
        "event_counts": {
            "connector_events": connector_count,
            "integration_events": integration_count,
            "blue_events": blue_count,
            "total_events": total_events,
        },
        "performance": {
            "throughput_eps": throughput_eps,
            "ingest_avg_latency_ms": connector_latency_avg_ms,
            "search_latency_p50_ms": search_latency_p50_ms,
            "search_latency_p95_ms": search_latency_p95_ms,
            "dead_letter_count": dead_letter_count,
        },
        "retention": {
            "estimated_storage_bytes": estimated_storage_bytes,
            "estimated_storage_gb": round(storage_gb, 6),
            "event_trend_hourly": _hourly_trend(timestamp_samples, lookback_hours=lookback),
        },
        "cost": {
            "monthly_storage_cost_usd": monthly_storage_cost_usd,
            "monthly_ingest_cost_usd": monthly_ingest_cost_usd,
            "monthly_search_cost_usd": monthly_search_cost_usd,
            "monthly_total_cost_usd": monthly_total_cost_usd,
            "cost_budget_usd": float(settings.secops_data_tier_monthly_cost_budget_usd),
        },
        "risk": {
            "risk_score": risk_score,
            "risk_tier": tier,
            "recommendation": _risk_recommendation(tier),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def federation_data_tier_benchmark(
    db: Session,
    *,
    lookback_hours: int = 24,
    limit: int = 200,
) -> dict[str, object]:
    max_rows = max(1, min(int(limit), 500))
    tenants = db.scalars(select(Tenant).order_by(desc(Tenant.created_at)).limit(max_rows)).all()

    rows: list[dict[str, object]] = []
    for tenant in tenants:
        benchmark = tenant_data_tier_benchmark(db, tenant_code=tenant.tenant_code, lookback_hours=lookback_hours)
        if benchmark.get("status") != "ok":
            continue
        performance = benchmark.get("performance", {})
        cost = benchmark.get("cost", {})
        risk = benchmark.get("risk", {})
        rows.append(
            {
                "tenant_id": benchmark.get("tenant_id", ""),
                "tenant_code": tenant.tenant_code,
                "throughput_eps": float(performance.get("throughput_eps", 0.0)),
                "ingest_avg_latency_ms": float(performance.get("ingest_avg_latency_ms", 0.0)),
                "search_latency_p95_ms": float(performance.get("search_latency_p95_ms", 0.0)),
                "monthly_total_cost_usd": float(cost.get("monthly_total_cost_usd", 0.0)),
                "risk_score": int(risk.get("risk_score", 0)),
                "risk_tier": str(risk.get("risk_tier", "low")),
                "recommendation": str(risk.get("recommendation", "")),
            }
        )

    rows.sort(key=lambda item: (item["risk_score"], item["monthly_total_cost_usd"]), reverse=True)
    tier_counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for row in rows:
        tier = row.get("risk_tier", "low")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    avg_throughput_eps = round((sum(row["throughput_eps"] for row in rows) / len(rows)) if rows else 0.0, 4)
    avg_search_p95_ms = round((sum(row["search_latency_p95_ms"] for row in rows) / len(rows)) if rows else 0.0, 2)
    total_monthly_cost_usd = round(sum(row["monthly_total_cost_usd"] for row in rows), 6)

    return {
        "lookback_hours": max(1, int(lookback_hours)),
        "count": len(rows),
        "tier_counts": tier_counts,
        "summary": {
            "average_throughput_eps": avg_throughput_eps,
            "average_search_p95_ms": avg_search_p95_ms,
            "total_monthly_cost_usd": total_monthly_cost_usd,
        },
        "rows": rows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
