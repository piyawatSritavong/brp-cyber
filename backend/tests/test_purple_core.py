from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.services import event_store, purple_core


class FakeRedis:
    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self._counter = 0

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self._counter += 1
        event_id = f"{self._counter}-0"
        self.streams.setdefault(key, []).append((event_id, fields))
        return event_id

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]


def _make_event(event_type: str, tenant_id: str, ts: datetime, correlation_id: str, extra: dict[str, object]):
    payload = {
        "event_type": event_type,
        "metadata": {
            "tenant_id": tenant_id,
            "correlation_id": correlation_id,
            "trace_id": str(uuid4()),
            "source": "test",
            "timestamp": ts.isoformat(),
        },
    }
    payload.update(extra)
    return payload


def test_purple_correlation_and_report_generation() -> None:
    fake_redis = FakeRedis()
    orig_mode = purple_core.settings.purple_report_export_mode
    orig_dir = purple_core.settings.purple_report_export_filesystem_dir
    export_dir = tempfile.mkdtemp(prefix="purple_report_exports_test_")
    purple_core.redis_client = fake_redis
    event_store.redis_client = fake_redis

    captured = []
    purple_core.persist_event = lambda event: captured.append(event.event_type)

    tenant_id = uuid4()
    tenant_str = str(tenant_id)

    t0 = datetime.now(timezone.utc).replace(microsecond=0)

    red_payload = _make_event(
        "red_event",
        tenant_str,
        t0,
        str(uuid4()),
        {"scenario_name": "credential_stuffing_sim", "target_asset": "login", "tactic": "auth_burst", "outcome": "started"},
    )
    detection_corr = str(uuid4())
    det_payload = _make_event(
        "detection_event",
        tenant_str,
        t0 + timedelta(seconds=30),
        detection_corr,
        {
            "detector": "failed_login_burst",
            "severity": "high",
            "signal_name": "brute_force_suspected",
            "confidence": 0.95,
            "status": "confirmed",
        },
    )
    resp_payload = _make_event(
        "response_event",
        tenant_str,
        t0 + timedelta(seconds=50),
        detection_corr,
        {
            "action": "block_ip",
            "reason_code": "brute_force_suspected",
            "actor": "blue_auto_response",
            "target": "198.51.100.10",
            "result": "success",
        },
    )

    fake_redis.xadd(
        "security_events",
        {
            "event_type": "red_event",
            "tenant_id": tenant_str,
            "correlation_id": red_payload["metadata"]["correlation_id"],
            "trace_id": red_payload["metadata"]["trace_id"],
            "payload": json.dumps(red_payload),
        },
    )
    fake_redis.xadd(
        "security_events",
        {
            "event_type": "detection_event",
            "tenant_id": tenant_str,
            "correlation_id": detection_corr,
            "trace_id": det_payload["metadata"]["trace_id"],
            "payload": json.dumps(det_payload),
        },
    )
    fake_redis.xadd(
        "security_events",
        {
            "event_type": "response_event",
            "tenant_id": tenant_str,
            "correlation_id": detection_corr,
            "trace_id": resp_payload["metadata"]["trace_id"],
            "payload": json.dumps(resp_payload),
        },
    )

    correlation = purple_core.correlate_tenant_events(tenant_id, limit=100)
    assert correlation["event_counts"]["red"] == 1
    assert correlation["kpi"]["mttd_seconds"] == 30.0
    assert correlation["kpi"]["mttr_seconds"] == 20.0
    assert correlation["kpi"]["detection_coverage"] == 1.0
    assert correlation["table"][0]["detection_status"] == "detected_and_mitigated"

    report = purple_core.generate_daily_report(tenant_id, limit=100)
    assert report["tenant_id"] == tenant_str
    assert "Detection coverage" in report["summary"]
    assert captured[-1] == "purple_report_event"

    reports = purple_core.list_reports(tenant_id, limit=10)
    assert len(reports) == 1
    assert reports[0]["report_id"] == report["report_id"]

    filtered = purple_core.correlate_tenant_events(
        tenant_id,
        limit=100,
        attack_type="credential",
        detection_status="detected",
        page=1,
        page_size=1,
    )
    assert filtered["table_total"] == 1
    assert filtered["pagination"]["returned"] == 1

    queried = purple_core.query_reports(
        tenant_id=tenant_id,
        limit=10,
        page=1,
        page_size=1,
        min_detection_coverage=0.9,
    )
    assert queried["count"] == 1
    assert queried["total_count"] == 1

    try:
        purple_core.settings.purple_report_export_mode = "filesystem"
        purple_core.settings.purple_report_export_filesystem_dir = export_dir
        exported = purple_core.export_report_artifact(
            tenant_id=tenant_id,
            report_id=report["report_id"],
            export_format="pdf",
        )
        assert exported["status"] == "exported"
        assert exported["export"]["mime_type"] == "application/pdf"
        status = purple_core.purple_report_export_status(tenant_id, limit=10)
        assert status["count"] == 1
    finally:
        purple_core.settings.purple_report_export_mode = orig_mode
        purple_core.settings.purple_report_export_filesystem_dir = orig_dir
        shutil.rmtree(export_dir, ignore_errors=True)


def test_purple_query_reports_filters_date_range() -> None:
    fake_redis = FakeRedis()
    purple_core.redis_client = fake_redis

    tenant_id = uuid4()
    tenant_str = str(tenant_id)
    old_report = {
        "report_id": "old-report",
        "tenant_id": tenant_str,
        "generated_at": "2026-03-20T10:00:00+00:00",
        "summary": "old",
        "kpi": {"detection_coverage": 0.5, "mttr_seconds": 300},
        "table": [],
    }
    new_report = {
        "report_id": "new-report",
        "tenant_id": tenant_str,
        "generated_at": "2026-03-23T10:00:00+00:00",
        "summary": "new",
        "kpi": {"detection_coverage": 1.0, "mttr_seconds": 20},
        "table": [],
    }
    fake_redis.xadd(f"purple_reports:{tenant_id}", {"report_id": "old-report", "payload": json.dumps(old_report)})
    fake_redis.xadd(f"purple_reports:{tenant_id}", {"report_id": "new-report", "payload": json.dumps(new_report)})

    queried = purple_core.query_reports(
        tenant_id=tenant_id,
        limit=10,
        date_from="2026-03-22",
        date_to="2026-03-23",
    )
    assert queried["count"] == 1
    assert queried["reports"][0]["report_id"] == "new-report"
