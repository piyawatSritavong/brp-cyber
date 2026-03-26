from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import uuid4

import httpx

from scripts import loadtest_enterprise, loadtest_matrix


def _build_transport() -> tuple[httpx.MockTransport, dict[str, int]]:
    counters = {"ingest": 0, "reconcile": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/ingest/auth-login" and request.method == "POST":
            counters["ingest"] += 1
            return httpx.Response(200, json={"status": "ok"})
        if path.startswith("/enterprise/cost/") and request.method == "GET":
            return httpx.Response(200, json={"usd": 1.25})
        if path.startswith("/enterprise/slo/") and request.method == "GET":
            return httpx.Response(200, json={"availability": 0.995})
        if path == "/enterprise/queue/stats" and request.method == "GET":
            return httpx.Response(200, json={"total_lag": 17, "total_length": 44, "partitions": []})
        if path == "/enterprise/autoscaler/status" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "current_workers": 2,
                    "target_workers": 4,
                    "desired_workers": 4,
                    "scale_delta": 2,
                    "total_lag": 17,
                    "cooldown_active": "0",
                },
            )
        if path == "/enterprise/autoscaler/history" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "count": 3,
                    "history": [
                        {"id": "3-0", "current_workers": "2", "desired_workers": "4", "action": "scale_up", "total_lag": "17"},
                        {"id": "2-0", "current_workers": "4", "desired_workers": "4", "action": "noop", "total_lag": "8"},
                        {"id": "1-0", "current_workers": "4", "desired_workers": "6", "action": "noop", "total_lag": "22"},
                    ],
                },
            )
        if path == "/enterprise/autoscaler/reconcile" and request.method == "POST":
            counters["reconcile"] += 1
            return httpx.Response(200, json={"action": "scale_up", "desired_workers": 4})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    return httpx.MockTransport(handler), counters


def test_run_multi_tenant_collects_concurrent_summary() -> None:
    transport, counters = _build_transport()
    tenant_ids = [str(uuid4()), str(uuid4())]

    summary = loadtest_enterprise.run_multi_tenant(
        "http://example.test",
        tenant_ids=tenant_ids,
        requests_count=10,
        concurrency=4,
        emit=False,
        transport=transport,
        reconcile_autoscaler=True,
    )

    assert counters["ingest"] == 10
    assert counters["reconcile"] == 1
    assert summary["tenant_count"] == 2
    assert summary["requests"] == 10
    assert summary["concurrency"] == 4
    assert len(summary["tenant_summaries"]) == 2
    assert {row["requests"] for row in summary["tenant_summaries"]} == {5}
    assert summary["queue_snapshot"]["total_lag"] == 17
    assert summary["autoscaler_history_summary"]["peak_desired_workers"] == 6
    assert summary["autoscaler_history_summary"]["scale_actions"] == 1
    assert summary["autoscaler_history_summary"]["suppressed_scale_actions"] == 1


def test_run_multi_tenant_attributes_failures_to_the_right_tenant() -> None:
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        tenant_id = request.headers.get("x-tenant-id", "")
        if path == "/ingest/auth-login" and request.method == "POST":
            status_code = 503 if tenant_id == tenant_b else 200
            return httpx.Response(status_code, json={"tenant_id": tenant_id})
        if path.startswith("/enterprise/cost/") and request.method == "GET":
            return httpx.Response(200, json={"usd": 1.25})
        if path.startswith("/enterprise/slo/") and request.method == "GET":
            return httpx.Response(200, json={"availability": 0.995})
        if path == "/enterprise/queue/stats" and request.method == "GET":
            return httpx.Response(200, json={"total_lag": 0, "total_length": 0, "partitions": []})
        if path == "/enterprise/autoscaler/status" and request.method == "GET":
            return httpx.Response(200, json={"current_workers": 1, "desired_workers": 1, "total_lag": 0})
        if path == "/enterprise/autoscaler/history" and request.method == "GET":
            return httpx.Response(200, json={"count": 0, "history": []})
        raise AssertionError(f"unexpected request: {request.method} {path}")

    summary = loadtest_enterprise.run_multi_tenant(
        "http://example.test",
        tenant_ids=[tenant_a, tenant_b],
        requests_count=8,
        concurrency=4,
        emit=False,
        transport=httpx.MockTransport(handler),
    )

    by_tenant = {row["tenant_id"]: row for row in summary["tenant_summaries"]}
    assert summary["failures"] == 4
    assert by_tenant[tenant_a]["failures"] == 0
    assert by_tenant[tenant_b]["failures"] == 4


def test_loadtest_matrix_writes_markdown_and_json_reports(tmp_path: Path, monkeypatch) -> None:
    output_path = tmp_path / "matrix_report.md"

    def fake_run_multi_tenant(*_args, **kwargs):
        requests = int(kwargs["requests_count"])
        concurrency = int(kwargs["concurrency"])
        tenant_ids = list(kwargs["tenant_ids"])
        return {
            "tenant_count": len(tenant_ids),
            "tenant_ids": tenant_ids,
            "requests": requests,
            "concurrency": concurrency,
            "failures": 0,
            "failure_rate": 0.0,
            "duration_seconds": 1.0,
            "rps": float(requests),
            "avg_latency_seconds": 0.01,
            "p95_latency_seconds": 0.02,
            "availability_floor": 0.99,
            "availability_average": 0.995,
            "tenant_summaries": [
                {
                    "tenant_id": tenant_id,
                    "requests": requests // len(tenant_ids),
                    "failures": 0,
                    "estimated_cost_per_10k_events_usd": 0.123,
                    "availability": 0.99,
                }
                for tenant_id in tenant_ids
            ],
            "queue_snapshot": {"total_length": 88},
            "autoscaler_history_summary": {
                "peak_total_lag": 17,
                "peak_desired_workers": concurrency,
                "scale_actions": 2,
                "suppressed_scale_actions": 1,
            },
        }

    monkeypatch.setattr(loadtest_matrix, "run_multi_tenant", fake_run_multi_tenant)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "loadtest_matrix.py",
            "--base-url",
            "http://example.test",
            "--tenant-id",
            str(uuid4()),
            "--tenant-id",
            str(uuid4()),
            "--environment",
            "staging",
            "--out",
            str(output_path),
        ],
    )

    loadtest_matrix.main()

    markdown = output_path.read_text(encoding="utf-8")
    assert "# Load Test Evidence Report" in markdown
    assert "| T1 | 10000 | 4 | multi-tenant concurrent profile |" in markdown
    assert "Cooldown or suppressed scale actions: 1" in markdown

    json_payload = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert json_payload["environment"] == "staging"
    assert len(json_payload["tiers"]) == 3
