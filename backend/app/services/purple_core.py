from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any
from uuid import UUID, uuid4

from app.core.config import settings
from app.services.event_store import persist_event
from app.services.redis_client import redis_client
from schemas.events import EventMetadata, PurpleReportEvent

SECURITY_STREAM_KEY = "security_events"


@dataclass
class CorrelationRow:
    attack_type: str
    detection_status: str
    mitigation_time_seconds: float | None
    recommendation: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "attack_type": self.attack_type,
            "detection_status": self.detection_status,
            "mitigation_time_seconds": self.mitigation_time_seconds,
            "recommendation": self.recommendation,
        }


def _parse_iso(ts: str) -> datetime:
    normalized = ts.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _read_tenant_events(tenant_id: UUID, limit: int) -> list[dict[str, Any]]:
    entries = redis_client.xrevrange(SECURITY_STREAM_KEY, count=max(limit, 1))
    events: list[dict[str, Any]] = []
    for _, fields in reversed(entries):
        if fields.get("tenant_id") != str(tenant_id):
            continue
        payload = fields.get("payload")
        if not payload:
            continue
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            continue
        events.append(decoded)
    return events


def _events_in_day(events: list[dict[str, Any]], target_date: datetime | None) -> list[dict[str, Any]]:
    if target_date is None:
        return events

    start = target_date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    result = []
    for event in events:
        ts = event.get("metadata", {}).get("timestamp")
        if not ts:
            continue
        event_ts = _parse_iso(ts)
        if start <= event_ts < end:
            result.append(event)
    return result


def correlate_tenant_events(
    tenant_id: UUID,
    limit: int = 5000,
    correlation_window_seconds: int | None = None,
    report_date: datetime | None = None,
) -> dict[str, Any]:
    window_seconds = correlation_window_seconds or settings.purple_correlation_window_seconds
    events = _events_in_day(_read_tenant_events(tenant_id, limit), report_date)

    red_events = [e for e in events if e.get("event_type") == "red_event"]
    detection_events = [e for e in events if e.get("event_type") == "detection_event"]
    response_events = [e for e in events if e.get("event_type") == "response_event"]

    detection_events.sort(key=lambda e: e["metadata"]["timestamp"])
    response_events.sort(key=lambda e: e["metadata"]["timestamp"])

    rows: list[CorrelationRow] = []
    mttd_samples: list[float] = []
    mttr_samples: list[float] = []

    for red in red_events:
        red_ts = _parse_iso(red["metadata"]["timestamp"])
        window_end = red_ts + timedelta(seconds=window_seconds)
        red_attack_type = red.get("scenario_name") or red.get("tactic") or "unknown_attack"

        matched_detection = None
        for detection in detection_events:
            det_ts = _parse_iso(detection["metadata"]["timestamp"])
            if red_ts <= det_ts <= window_end:
                matched_detection = detection
                break

        if not matched_detection:
            rows.append(
                CorrelationRow(
                    attack_type=red_attack_type,
                    detection_status="missed",
                    mitigation_time_seconds=None,
                    recommendation="Increase detection sensitivity and add rule coverage for this pattern",
                )
            )
            continue

        det_ts = _parse_iso(matched_detection["metadata"]["timestamp"])
        mttd_samples.append((det_ts - red_ts).total_seconds())

        matched_response = None
        det_corr_id = matched_detection.get("metadata", {}).get("correlation_id")

        if det_corr_id:
            for response in response_events:
                if response.get("metadata", {}).get("correlation_id") == det_corr_id:
                    resp_ts = _parse_iso(response["metadata"]["timestamp"])
                    if resp_ts >= det_ts:
                        matched_response = response
                        break

        if not matched_response:
            for response in response_events:
                resp_ts = _parse_iso(response["metadata"]["timestamp"])
                if det_ts <= resp_ts <= det_ts + timedelta(seconds=window_seconds):
                    matched_response = response
                    break

        if matched_response:
            resp_ts = _parse_iso(matched_response["metadata"]["timestamp"])
            mitigation_seconds = (resp_ts - det_ts).total_seconds()
            mttr_samples.append(mitigation_seconds)
            recommendation = (
                "Maintain current response policy"
                if mitigation_seconds <= settings.purple_target_mttr_seconds
                else "Reduce response latency by tuning auto-response and escalation"
            )
            rows.append(
                CorrelationRow(
                    attack_type=red_attack_type,
                    detection_status="detected_and_mitigated",
                    mitigation_time_seconds=mitigation_seconds,
                    recommendation=recommendation,
                )
            )
        else:
            rows.append(
                CorrelationRow(
                    attack_type=red_attack_type,
                    detection_status="detected_not_mitigated",
                    mitigation_time_seconds=None,
                    recommendation="Add deterministic response runbook and retry policy",
                )
            )

    attack_count = len(red_events)
    detected_count = len([r for r in rows if r.detection_status != "missed"])
    mitigated_count = len([r for r in rows if r.detection_status == "detected_and_mitigated"])

    coverage = (detected_count / attack_count) if attack_count else 0.0
    mttd = mean(mttd_samples) if mttd_samples else 0.0
    mttr = mean(mttr_samples) if mttr_samples else 0.0
    blocked_before_impact = (
        len([value for value in mttr_samples if value <= settings.purple_target_mttr_seconds]) / len(mttr_samples)
        if mttr_samples
        else 0.0
    )

    return {
        "tenant_id": str(tenant_id),
        "event_counts": {
            "red": attack_count,
            "detection": len(detection_events),
            "response": len(response_events),
        },
        "kpi": {
            "mttd_seconds": round(mttd, 2),
            "mttr_seconds": round(mttr, 2),
            "detection_coverage": round(coverage, 4),
            "blocked_before_impact_rate": round(blocked_before_impact, 4),
            "mitigated_count": mitigated_count,
            "detected_count": detected_count,
            "attack_count": attack_count,
        },
        "table": [row.as_dict() for row in rows],
    }


def _executive_summary(correlation: dict[str, Any]) -> str:
    kpi = correlation["kpi"]
    return (
        f"Detection coverage={kpi['detection_coverage']:.2%}, "
        f"MTTD={kpi['mttd_seconds']}s, "
        f"MTTR={kpi['mttr_seconds']}s, "
        f"Mitigated={kpi['mitigated_count']}/{kpi['attack_count']}"
    )


def generate_daily_report(tenant_id: UUID, limit: int = 5000, report_date: datetime | None = None) -> dict[str, Any]:
    correlation = correlate_tenant_events(tenant_id, limit=limit, report_date=report_date)
    summary = _executive_summary(correlation)

    report_id = f"purple-{tenant_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    metadata = EventMetadata(
        tenant_id=tenant_id,
        correlation_id=uuid4(),
        trace_id=uuid4(),
        source="purple_reporting_engine",
        timestamp=datetime.now(timezone.utc),
    )
    report_event = PurpleReportEvent(
        metadata=metadata,
        report_id=report_id,
        summary=summary,
        mttd_seconds=correlation["kpi"]["mttd_seconds"],
        mttr_seconds=correlation["kpi"]["mttr_seconds"],
        recommendation_count=len(correlation["table"]),
    )
    persist_event(report_event)

    payload = {
        "report_id": report_id,
        "tenant_id": str(tenant_id),
        "generated_at": metadata.timestamp.isoformat(),
        "summary": summary,
        "kpi": correlation["kpi"],
        "table": correlation["table"],
    }

    redis_client.xadd(
        f"purple_reports:{tenant_id}",
        {"report_id": report_id, "payload": json.dumps(payload)},
        maxlen=5000,
        approximate=True,
    )
    return payload


def list_reports(tenant_id: UUID, limit: int = 30) -> list[dict[str, Any]]:
    entries = redis_client.xrevrange(f"purple_reports:{tenant_id}", count=max(limit, 1))
    reports: list[dict[str, Any]] = []
    for _, fields in entries:
        payload = fields.get("payload")
        if not payload:
            continue
        try:
            reports.append(json.loads(payload))
        except json.JSONDecodeError:
            continue
    return reports
