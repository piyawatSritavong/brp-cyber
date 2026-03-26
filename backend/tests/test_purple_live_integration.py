from __future__ import annotations

import json
import shutil
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.main import app
from app.services import event_store, purple_core

TEST_REDIS_DB = 15


def _redis_test_url(redis_url: str, db: int = TEST_REDIS_DB) -> str:
    parts = urlsplit(redis_url)
    return urlunsplit((parts.scheme, parts.netloc, f"/{db}", parts.query, parts.fragment))


def _event(event_type: str, tenant_id: str, ts: datetime, corr_id: str, extra: dict[str, object]) -> dict[str, object]:
    payload = {
        "event_type": event_type,
        "metadata": {
            "tenant_id": tenant_id,
            "correlation_id": corr_id,
            "trace_id": str(uuid4()),
            "source": "live-redis-test",
            "timestamp": ts.isoformat(),
        },
    }
    payload.update(extra)
    return payload


def _push_event(client: Redis, payload: dict[str, object]) -> None:
    metadata = payload["metadata"]
    client.xadd(
        "security_events",
        {
            "event_type": str(payload["event_type"]),
            "tenant_id": str(metadata["tenant_id"]),
            "correlation_id": str(metadata["correlation_id"]),
            "trace_id": str(metadata["trace_id"]),
            "payload": json.dumps(payload),
        },
    )


@pytest.fixture()
def live_purple_runtime() -> tuple[Redis, Path]:
    client = Redis.from_url(_redis_test_url(settings.redis_url), decode_responses=True)
    try:
        client.ping()
        client.flushdb()
    except RedisError as exc:
        with suppress(Exception):
            client.close()
        pytest.skip(f"live redis unavailable for purple integration test: {exc}")

    orig_purple_redis = purple_core.redis_client
    orig_event_redis = event_store.redis_client
    orig_mode = purple_core.settings.purple_report_export_mode
    orig_dir = purple_core.settings.purple_report_export_filesystem_dir
    export_dir = Path("./tmp/purple_report_exports_live_test")

    purple_core.redis_client = client
    event_store.redis_client = client
    purple_core.settings.purple_report_export_mode = "filesystem"
    purple_core.settings.purple_report_export_filesystem_dir = str(export_dir)

    try:
        yield client, export_dir
    finally:
        purple_core.redis_client = orig_purple_redis
        event_store.redis_client = orig_event_redis
        purple_core.settings.purple_report_export_mode = orig_mode
        purple_core.settings.purple_report_export_filesystem_dir = orig_dir
        with suppress(RedisError):
            client.flushdb()
        with suppress(Exception):
            client.close()
        shutil.rmtree(export_dir, ignore_errors=True)


def test_purple_live_redis_api_roundtrip(live_purple_runtime: tuple[Redis, Path]) -> None:
    live_redis, _ = live_purple_runtime

    tenant_id = uuid4()
    tenant_str = str(tenant_id)
    t0 = datetime.now(timezone.utc).replace(microsecond=0)
    det_corr = str(uuid4())

    _push_event(
        live_redis,
        _event(
            "red_event",
            tenant_str,
            t0,
            str(uuid4()),
            {
                "scenario_name": "endpoint_probe_live",
                "target_asset": "admin",
                "tactic": "probe",
                "outcome": "started",
            },
        ),
    )
    _push_event(
        live_redis,
        _event(
            "detection_event",
            tenant_str,
            t0 + timedelta(seconds=15),
            det_corr,
            {
                "detector": "probe_rule",
                "severity": "medium",
                "signal_name": "probe_detected",
                "confidence": 0.88,
                "status": "confirmed",
            },
        ),
    )
    _push_event(
        live_redis,
        _event(
            "response_event",
            tenant_str,
            t0 + timedelta(seconds=40),
            det_corr,
            {
                "action": "block_ip",
                "reason_code": "probe_detected",
                "actor": "blue_auto_response",
                "target": "198.51.100.44",
                "result": "success",
            },
        ),
    )

    with TestClient(app) as client:
        correlate = client.get(
            f"/purple/correlate/{tenant_str}"
            f"?date_from={t0.date().isoformat()}&date_to={t0.date().isoformat()}"
            "&detection_status=detected&page=1&page_size=10"
        )
        assert correlate.status_code == 200
        correlate_data = correlate.json()
        assert correlate_data["event_counts"]["red"] == 1
        assert correlate_data["table_total"] == 1
        assert correlate_data["pagination"]["returned"] == 1

        report = client.post(f"/purple/report/{tenant_str}/daily?date={t0.date().isoformat()}")
        assert report.status_code == 200
        report_data = report.json()
        assert report_data["tenant_id"] == tenant_str
        assert report_data["table_total"] == 1

        report_rows = live_redis.xrevrange(f"purple_reports:{tenant_id}", count=5)
        assert len(report_rows) == 1

        listed = client.get(
            f"/purple/report/{tenant_str}"
            f"?page=1&page_size=10&min_detection_coverage=0.5"
            f"&date_from={t0.date().isoformat()}&date_to={t0.date().isoformat()}"
        )
        assert listed.status_code == 200
        listed_data = listed.json()
        assert listed_data["count"] == 1
        assert listed_data["pagination"]["returned"] == 1

        exported = client.post(f"/purple/report/{tenant_str}/export?report_id={report_data['report_id']}&export_format=json")
        assert exported.status_code == 200
        exported_data = exported.json()
        assert exported_data["status"] == "exported"
        assert exported_data["export"]["mime_type"] == "application/json"

        export_rows = live_redis.xrevrange(f"purple_report_exports:{tenant_id}", count=5)
        assert len(export_rows) == 1

        export_status = client.get(f"/purple/report/{tenant_str}/export/status?limit=10")
        assert export_status.status_code == 200
        assert export_status.json()["count"] == 1


def test_purple_live_redis_report_query_filters(live_purple_runtime: tuple[Redis, Path]) -> None:
    live_redis, _ = live_purple_runtime

    tenant_id = uuid4()
    tenant_str = str(tenant_id)
    old_report = {
        "report_id": "live-old-report",
        "tenant_id": tenant_str,
        "generated_at": "2026-03-20T10:00:00+00:00",
        "summary": "old",
        "kpi": {"detection_coverage": 0.4, "mttr_seconds": 300},
        "table": [],
        "table_total": 0,
        "applied_filters": {},
    }
    new_report = {
        "report_id": "live-new-report",
        "tenant_id": tenant_str,
        "generated_at": "2026-03-23T10:00:00+00:00",
        "summary": "new",
        "kpi": {"detection_coverage": 1.0, "mttr_seconds": 20},
        "table": [],
        "table_total": 0,
        "applied_filters": {},
    }
    live_redis.xadd(f"purple_reports:{tenant_id}", {"report_id": "live-old-report", "payload": json.dumps(old_report)})
    live_redis.xadd(f"purple_reports:{tenant_id}", {"report_id": "live-new-report", "payload": json.dumps(new_report)})

    with TestClient(app) as client:
        response = client.get(
            f"/purple/report/{tenant_str}"
            "?page=1&page_size=10"
            "&date_from=2026-03-22&date_to=2026-03-23"
            "&min_detection_coverage=0.9&max_mttr_seconds=60"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["total_count"] == 1
        assert data["reports"][0]["report_id"] == "live-new-report"
