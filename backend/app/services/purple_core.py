from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import UUID, uuid4

from app.core.config import settings
from app.services.event_store import persist_event
from app.services.purple_roi_dashboard import _render_pdf_bytes, _safe_filename_part
from app.services.redis_client import redis_client
from schemas.events import EventMetadata, PurpleReportEvent

SECURITY_STREAM_KEY = "security_events"
PURPLE_REPORT_STREAM_PREFIX = "purple_reports"
PURPLE_REPORT_EXPORT_STREAM_PREFIX = "purple_report_exports"


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


def _report_stream_key(tenant_id: UUID) -> str:
    return f"{PURPLE_REPORT_STREAM_PREFIX}:{tenant_id}"


def _report_export_stream_key(tenant_id: UUID) -> str:
    return f"{PURPLE_REPORT_EXPORT_STREAM_PREFIX}:{tenant_id}"


def _parse_range_value(value: datetime | str | None, *, end_of_day: bool = False) -> datetime | None:
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        dt = value
        is_date_only = False
    else:
        text = str(value).strip()
        is_date_only = len(text) == 10 and text.count("-") == 2
        normalized = text.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    if end_of_day and (is_date_only or (isinstance(value, datetime) and value.hour == 0 and value.minute == 0 and value.second == 0)):
        dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    return dt


def _resolve_window(
    *,
    report_date: datetime | str | None = None,
    date_from: datetime | str | None = None,
    date_to: datetime | str | None = None,
) -> tuple[datetime | None, datetime | None]:
    if report_date is not None and date_from is None and date_to is None:
        return _parse_range_value(report_date), _parse_range_value(report_date, end_of_day=True)
    return _parse_range_value(date_from), _parse_range_value(date_to, end_of_day=True)


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


def _events_in_window(
    events: list[dict[str, Any]],
    *,
    report_date: datetime | str | None = None,
    date_from: datetime | str | None = None,
    date_to: datetime | str | None = None,
) -> list[dict[str, Any]]:
    start, end = _resolve_window(report_date=report_date, date_from=date_from, date_to=date_to)
    if start is None and end is None:
        return events
    result = []
    for event in events:
        ts = event.get("metadata", {}).get("timestamp")
        if not ts:
            continue
        event_ts = _parse_iso(ts)
        if start is not None and event_ts < start:
            continue
        if end is not None and event_ts > end:
            continue
        result.append(event)
    return result


def _matches_text_filter(value: str, expected: str) -> bool:
    if not expected:
        return True
    return expected.strip().lower() in value.strip().lower()


def _paginate_rows(rows: list[dict[str, Any]], page: int = 1, page_size: int = 0) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    total = len(rows)
    normalized_page = max(1, int(page or 1))
    normalized_page_size = max(0, int(page_size or 0))

    if normalized_page_size <= 0:
        return rows, {
            "page": 1,
            "page_size": total,
            "returned": total,
            "total": total,
            "has_next": False,
        }

    start = (normalized_page - 1) * normalized_page_size
    end = start + normalized_page_size
    sliced = rows[start:end]
    return sliced, {
        "page": normalized_page,
        "page_size": normalized_page_size,
        "returned": len(sliced),
        "total": total,
        "has_next": end < total,
    }


def _load_reports(tenant_id: UUID, limit: int) -> list[dict[str, Any]]:
    entries = redis_client.xrevrange(_report_stream_key(tenant_id), count=max(limit, 1))
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


def _find_report(tenant_id: UUID, report_id: str, limit: int = 5000) -> dict[str, Any] | None:
    reports = _load_reports(tenant_id, limit=max(limit, 1))
    if not reports:
        return None
    if not report_id:
        return reports[0]
    for report in reports:
        if str(report.get("report_id", "")) == str(report_id):
            return report
    return None


def _report_sections(report: dict[str, Any]) -> list[dict[str, Any]]:
    kpi = report.get("kpi", {}) if isinstance(report.get("kpi", {}), dict) else {}
    rows = report.get("table", []) if isinstance(report.get("table", []), list) else []
    findings = []
    for row in rows[:20]:
        if not isinstance(row, dict):
            continue
        findings.append(
            f"{row.get('attack_type', 'unknown')} | {row.get('detection_status', 'unknown')} | "
            f"mitigation={row.get('mitigation_time_seconds', 'n/a')} | {row.get('recommendation', '')}"
        )

    return [
        {
            "section": "Executive Summary",
            "content": [
                str(report.get("summary", "")),
                f"Generated At: {report.get('generated_at', '')}",
            ],
        },
        {
            "section": "KPI",
            "content": [
                f"Detection coverage={kpi.get('detection_coverage', 0.0)}",
                f"MTTD seconds={kpi.get('mttd_seconds', 0.0)}",
                f"MTTR seconds={kpi.get('mttr_seconds', 0.0)}",
                f"Blocked before impact rate={kpi.get('blocked_before_impact_rate', 0.0)}",
                f"Attack count={kpi.get('attack_count', 0)}",
            ],
        },
        {
            "section": "Findings",
            "content": findings or ["No correlation rows available."],
        },
    ]


def _report_export_payload(report: dict[str, Any], export_format: str) -> tuple[bytes, str, str]:
    normalized = str(export_format or "json").strip().lower()
    if normalized == "pdf":
        report_id = str(report.get("report_id", "purple-report"))
        content = _render_pdf_bytes(
            title=f"Purple Daily Report: {report_id}",
            sections=_report_sections(report),
            footer_label="BRP Purple Core",
        )
        return content, "application/pdf", "pdf"

    content = json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8")
    return content, "application/json", "json"


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _filesystem_export_report(
    *,
    tenant_id: UUID,
    report_id: str,
    extension: str,
    content: bytes,
    metadata: dict[str, Any],
    destination_dir: str,
) -> dict[str, str]:
    root = Path(destination_dir or settings.purple_report_export_filesystem_dir)
    root.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    target_dir = root / day
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_report_id = _safe_filename_part(report_id)
    safe_tenant_id = _safe_filename_part(str(tenant_id))
    artifact_path = target_dir / f"{safe_tenant_id}-{safe_report_id}.{extension}"
    metadata_path = target_dir / f"{safe_tenant_id}-{safe_report_id}.metadata.json"

    artifact_path.write_bytes(content)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=True, indent=2), encoding="utf-8")
    return {"artifact_object": str(artifact_path), "metadata_object": str(metadata_path)}


def _s3_export_report(
    *,
    tenant_id: UUID,
    report_id: str,
    extension: str,
    content: bytes,
    metadata: dict[str, Any],
) -> dict[str, str]:
    import boto3

    bucket = settings.purple_report_export_s3_bucket
    if not bucket:
        raise RuntimeError("purple_report_export_s3_bucket_not_configured")

    session = boto3.session.Session(
        aws_access_key_id=settings.purple_report_export_s3_access_key or None,
        aws_secret_access_key=settings.purple_report_export_s3_secret_key or None,
        region_name=settings.purple_report_export_s3_region or None,
    )
    client = session.client("s3", endpoint_url=settings.purple_report_export_s3_endpoint_url or None)

    prefix = settings.purple_report_export_s3_prefix.strip("/")
    safe_report_id = _safe_filename_part(report_id)
    safe_tenant_id = _safe_filename_part(str(tenant_id))
    base_key = (
        f"{prefix}/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{safe_tenant_id}-{safe_report_id}"
        if prefix
        else f"purple-report/{datetime.now(timezone.utc).strftime('%Y/%m/%d')}/{safe_tenant_id}-{safe_report_id}"
    )

    artifact_key = f"{base_key}.{extension}"
    metadata_key = f"{base_key}.metadata.json"

    mime_type = "application/pdf" if extension == "pdf" else "application/json"
    client.put_object(Bucket=bucket, Key=artifact_key, Body=content, ContentType=mime_type)
    client.put_object(
        Bucket=bucket,
        Key=metadata_key,
        Body=json.dumps(metadata, ensure_ascii=True, sort_keys=True).encode("utf-8"),
        ContentType="application/json",
    )

    return {
        "artifact_object": f"s3://{bucket}/{artifact_key}",
        "metadata_object": f"s3://{bucket}/{metadata_key}",
    }


def correlate_tenant_events(
    tenant_id: UUID,
    limit: int = 5000,
    correlation_window_seconds: int | None = None,
    report_date: datetime | str | None = None,
    date_from: datetime | str | None = None,
    date_to: datetime | str | None = None,
    attack_type: str = "",
    detection_status: str = "",
    page: int = 1,
    page_size: int = 0,
) -> dict[str, Any]:
    window_seconds = correlation_window_seconds or settings.purple_correlation_window_seconds
    filter_start, filter_end = _resolve_window(report_date=report_date, date_from=date_from, date_to=date_to)
    events = _events_in_window(
        _read_tenant_events(tenant_id, limit),
        report_date=report_date,
        date_from=date_from,
        date_to=date_to,
    )

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

    filtered_rows = [
        row.as_dict()
        for row in rows
        if _matches_text_filter(row.attack_type, attack_type) and _matches_text_filter(row.detection_status, detection_status)
    ]
    paged_rows, pagination = _paginate_rows(filtered_rows, page=page, page_size=page_size)

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
        "table_total": len(filtered_rows),
        "table": paged_rows,
        "pagination": pagination,
        "applied_filters": {
            "attack_type": attack_type,
            "detection_status": detection_status,
            "date_from": filter_start.isoformat() if filter_start is not None else "",
            "date_to": filter_end.isoformat() if filter_end is not None else "",
        },
    }


def _executive_summary(correlation: dict[str, Any]) -> str:
    kpi = correlation["kpi"]
    return (
        f"Detection coverage={kpi['detection_coverage']:.2%}, "
        f"MTTD={kpi['mttd_seconds']}s, "
        f"MTTR={kpi['mttr_seconds']}s, "
        f"Mitigated={kpi['mitigated_count']}/{kpi['attack_count']}"
    )


def generate_daily_report(
    tenant_id: UUID,
    limit: int = 5000,
    report_date: datetime | str | None = None,
    date_from: datetime | str | None = None,
    date_to: datetime | str | None = None,
) -> dict[str, Any]:
    correlation = correlate_tenant_events(
        tenant_id,
        limit=limit,
        report_date=report_date,
        date_from=date_from,
        date_to=date_to,
    )
    summary = _executive_summary(correlation)

    report_id = f"purple-{tenant_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

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
        "table": correlation.get("table", []),
        "table_total": correlation.get("table_total", len(correlation.get("table", []))),
        "applied_filters": correlation.get("applied_filters", {}),
    }

    redis_client.xadd(
        _report_stream_key(tenant_id),
        {"report_id": report_id, "payload": json.dumps(payload)},
        maxlen=5000,
        approximate=True,
    )
    return payload


def list_reports(tenant_id: UUID, limit: int = 30) -> list[dict[str, Any]]:
    return query_reports(tenant_id=tenant_id, limit=limit).get("reports", [])


def query_reports(
    tenant_id: UUID,
    limit: int = 30,
    page: int = 1,
    page_size: int = 0,
    date_from: datetime | str | None = None,
    date_to: datetime | str | None = None,
    min_detection_coverage: float | None = None,
    max_mttr_seconds: float | None = None,
    report_id: str = "",
) -> dict[str, Any]:
    reports = _load_reports(tenant_id, limit=max(limit, 1))
    start, end = _resolve_window(date_from=date_from, date_to=date_to)

    filtered: list[dict[str, Any]] = []
    for report in reports:
        if report_id and str(report.get("report_id", "")) != str(report_id):
            continue

        generated_at = _parse_range_value(report.get("generated_at"))
        if start is not None and generated_at is not None and generated_at < start:
            continue
        if end is not None and generated_at is not None and generated_at > end:
            continue

        kpi = report.get("kpi", {}) if isinstance(report.get("kpi", {}), dict) else {}
        coverage = float(kpi.get("detection_coverage", 0.0) or 0.0)
        mttr_seconds = float(kpi.get("mttr_seconds", 0.0) or 0.0)
        if min_detection_coverage is not None and coverage < float(min_detection_coverage):
            continue
        if max_mttr_seconds is not None and mttr_seconds > float(max_mttr_seconds):
            continue

        filtered.append(report)

    paged_reports, pagination = _paginate_rows(filtered, page=page, page_size=page_size)
    return {
        "tenant_id": str(tenant_id),
        "count": len(paged_reports),
        "total_count": len(filtered),
        "reports": paged_reports,
        "pagination": pagination,
        "applied_filters": {
            "report_id": report_id,
            "date_from": start.isoformat() if start is not None else "",
            "date_to": end.isoformat() if end is not None else "",
            "min_detection_coverage": min_detection_coverage,
            "max_mttr_seconds": max_mttr_seconds,
        },
    }


def export_report_artifact(
    tenant_id: UUID,
    report_id: str = "",
    export_format: str = "json",
    destination_dir: str = "",
    limit: int = 5000,
) -> dict[str, Any]:
    report = _find_report(tenant_id, report_id=report_id, limit=max(limit, 1))
    if report is None:
        return {"status": "no_report", "tenant_id": str(tenant_id), "report_id": report_id}

    selected_report_id = str(report.get("report_id", ""))
    content, mime_type, extension = _report_export_payload(report, export_format)
    generated_at = datetime.now(timezone.utc).isoformat()
    metadata = {
        "tenant_id": str(tenant_id),
        "report_id": selected_report_id,
        "generated_at": generated_at,
        "export_format": extension,
        "mime_type": mime_type,
        "sha256": _sha256_bytes(content),
        "byte_size": len(content),
        "source_report_generated_at": str(report.get("generated_at", "")),
    }

    mode = settings.purple_report_export_mode.lower().strip()
    if mode == "s3":
        published = _s3_export_report(
            tenant_id=tenant_id,
            report_id=selected_report_id,
            extension=extension,
            content=content,
            metadata=metadata,
        )
    else:
        published = _filesystem_export_report(
            tenant_id=tenant_id,
            report_id=selected_report_id,
            extension=extension,
            content=content,
            metadata=metadata,
            destination_dir=destination_dir,
        )

    export_id = redis_client.xadd(
        _report_export_stream_key(tenant_id),
        {
            "report_id": selected_report_id,
            "generated_at": generated_at,
            "export_format": extension,
            "mode": mode,
            "artifact_object": published["artifact_object"],
            "metadata_object": published["metadata_object"],
            "sha256": metadata["sha256"],
            "byte_size": str(metadata["byte_size"]),
        },
        maxlen=5000,
        approximate=True,
    )

    return {
        "status": "exported",
        "tenant_id": str(tenant_id),
        "export_id": export_id,
        "report_id": selected_report_id,
        "mode": mode,
        "artifact_object": published["artifact_object"],
        "metadata_object": published["metadata_object"],
        "export": metadata,
    }


def purple_report_export_status(tenant_id: UUID, limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(_report_export_stream_key(tenant_id), count=max(limit, 1))
    rows: list[dict[str, Any]] = []
    for event_id, fields in entries:
        row: dict[str, Any] = {"id": event_id}
        row.update(fields)
        row["byte_size"] = int(fields.get("byte_size", "0") or 0)
        rows.append(row)
    return {"tenant_id": str(tenant_id), "count": len(rows), "rows": rows}
