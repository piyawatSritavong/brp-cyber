from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
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


def _event(event_type: str, tenant_id: str, ts: datetime, corr_id: str, extra: dict[str, object]) -> dict[str, object]:
    payload = {
        "event_type": event_type,
        "metadata": {
            "tenant_id": tenant_id,
            "correlation_id": corr_id,
            "trace_id": str(uuid4()),
            "source": "test-api",
            "timestamp": ts.isoformat(),
        },
    }
    payload.update(extra)
    return payload


def test_purple_endpoints() -> None:
    fake_redis = FakeRedis()
    orig_mode = purple_core.settings.purple_report_export_mode
    orig_dir = purple_core.settings.purple_report_export_filesystem_dir
    export_dir = tempfile.mkdtemp(prefix="purple_report_exports_api_test_")
    purple_core.redis_client = fake_redis
    event_store.redis_client = fake_redis
    purple_core.persist_event = lambda event: None

    tenant_id = uuid4()
    tenant_str = str(tenant_id)
    t0 = datetime.now(timezone.utc).replace(microsecond=0)
    red_corr = str(uuid4())
    det_corr = str(uuid4())

    red = _event("red_event", tenant_str, t0, red_corr, {"scenario_name": "endpoint_probe_sim", "target_asset": "admin", "tactic": "probe", "outcome": "started"})
    det = _event("detection_event", tenant_str, t0 + timedelta(seconds=10), det_corr, {"detector": "rule", "severity": "medium", "signal_name": "probe", "confidence": 0.8, "status": "confirmed"})
    resp = _event("response_event", tenant_str, t0 + timedelta(seconds=30), det_corr, {"action": "block_ip", "reason_code": "probe", "actor": "blue", "target": "198.51.100.8", "result": "success"})

    for payload in (red, det, resp):
        fake_redis.xadd(
            "security_events",
            {
                "event_type": payload["event_type"],
                "tenant_id": tenant_str,
                "correlation_id": payload["metadata"]["correlation_id"],
                "trace_id": payload["metadata"]["trace_id"],
                "payload": json.dumps(payload),
            },
        )

    try:
        purple_core.settings.purple_report_export_mode = "filesystem"
        purple_core.settings.purple_report_export_filesystem_dir = export_dir

        with TestClient(app) as client:
            corr_resp = client.get(
                f"/purple/correlate/{tenant_str}?date_from={t0.date().isoformat()}&date_to={t0.date().isoformat()}&detection_status=detected&page=1&page_size=10"
            )
            assert corr_resp.status_code == 200
            corr_data = corr_resp.json()
            assert corr_data["event_counts"]["red"] == 1
            assert corr_data["table_total"] == 1

            report_resp = client.post(f"/purple/report/{tenant_str}/daily?date={t0.date().isoformat()}")
            assert report_resp.status_code == 200
            report_data = report_resp.json()
            assert report_data["tenant_id"] == tenant_str

            list_resp = client.get(
                f"/purple/report/{tenant_str}?page=1&page_size=10&min_detection_coverage=0.5&date_from={t0.date().isoformat()}&date_to={t0.date().isoformat()}"
            )
            assert list_resp.status_code == 200
            list_data = list_resp.json()
            assert list_data["count"] == 1
            assert list_data["pagination"]["returned"] == 1

            export_resp = client.post(f"/purple/report/{tenant_str}/export?export_format=json")
            assert export_resp.status_code == 200
            export_data = export_resp.json()
            assert export_data["status"] == "exported"
            assert export_data["export"]["mime_type"] == "application/json"

            export_status_resp = client.get(f"/purple/report/{tenant_str}/export/status?limit=10")
            assert export_status_resp.status_code == 200
            assert export_status_resp.json()["count"] == 1
    finally:
        purple_core.settings.purple_report_export_mode = orig_mode
        purple_core.settings.purple_report_export_filesystem_dir = orig_dir
        shutil.rmtree(export_dir, ignore_errors=True)
