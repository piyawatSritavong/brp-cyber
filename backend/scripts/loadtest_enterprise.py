from __future__ import annotations

import argparse
import math
import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

import httpx


def _partition_requests(tenant_ids: list[str], requests_count: int) -> list[str]:
    normalized_tenants = [tenant_id.strip() for tenant_id in tenant_ids if tenant_id.strip()]
    if not normalized_tenants:
        normalized_tenants = [str(uuid4())]
    return [normalized_tenants[index % len(normalized_tenants)] for index in range(max(0, requests_count))]


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1, math.ceil((percentile / 100.0) * len(ordered)) - 1))
    return ordered[rank]


def _safe_json(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = client.request(method, url, params=params, json=json_body)
    if response.status_code >= 400:
        return {}
    payload = response.json()
    return payload if isinstance(payload, dict) else {}


def _worker_run(
    *,
    base_url: str,
    assignments: list[tuple[int, str]],
    timeout_seconds: float,
    transport: httpx.BaseTransport | None,
) -> dict[str, Any]:
    request_results: list[tuple[str, float, bool]] = []

    with httpx.Client(timeout=timeout_seconds, transport=transport) as client:
        for request_index, tenant_id in assignments:
            rng = random.Random(f"{tenant_id}:{request_index}")
            source_ip = f"203.0.113.{rng.randint(1, 254)}"
            username = ["admin", "root", "ops"][request_index % 3]
            started = time.perf_counter()
            success = False
            try:
                response = client.post(
                    f"{base_url}/ingest/auth-login",
                    json={
                        "tenant_id": tenant_id,
                        "source_ip": source_ip,
                        "username": username,
                        "success": False,
                        "auth_source": "loadtest",
                    },
                    headers={"x-tenant-id": tenant_id},
                )
                success = response.status_code < 400
            except httpx.HTTPError:
                success = False
            latency = max(time.perf_counter() - started, 0.0)
            request_results.append((tenant_id, latency, success))

    return {"request_results": request_results}


def _tenant_metrics(
    *,
    client: httpx.Client,
    base_url: str,
    tenant_id: str,
    request_count: int,
    failure_count: int,
    latencies: list[float],
) -> dict[str, Any]:
    cost = _safe_json(client, "GET", f"{base_url}/enterprise/cost/{tenant_id}")
    slo = _safe_json(client, "GET", f"{base_url}/enterprise/slo/{tenant_id}")
    usd = float(cost.get("usd", 0.0) or 0.0)
    return {
        "tenant_id": tenant_id,
        "requests": request_count,
        "failures": failure_count,
        "failure_rate": (failure_count / request_count) if request_count else 0.0,
        "avg_latency_seconds": statistics.mean(latencies) if latencies else 0.0,
        "p95_latency_seconds": _percentile(latencies, 95.0),
        "estimated_cost_per_10k_events_usd": (usd / request_count) * 10000 if request_count else 0.0,
        "availability": float(slo.get("availability", 0.0) or 0.0),
        "slo_snapshot": slo,
        "cost": cost,
    }


def _autoscaler_history_summary(history_payload: dict[str, Any]) -> dict[str, Any]:
    rows = history_payload.get("history", [])
    if not isinstance(rows, list):
        rows = []
    desired_values = [int(row.get("desired_workers", 0) or 0) for row in rows if isinstance(row, dict)]
    total_lag_values = [int(row.get("total_lag", 0) or 0) for row in rows if isinstance(row, dict)]
    scale_actions = 0
    suppressed_scale_actions = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        action = str(row.get("action", "") or "")
        current_workers = int(row.get("current_workers", 0) or 0)
        desired_workers = int(row.get("desired_workers", 0) or 0)
        if action in {"scale_up", "scale_down"}:
            scale_actions += 1
        elif action == "noop" and desired_workers != current_workers:
            suppressed_scale_actions += 1
    return {
        "count": len(rows),
        "peak_desired_workers": max(desired_values) if desired_values else 0,
        "peak_total_lag": max(total_lag_values) if total_lag_values else 0,
        "scale_actions": scale_actions,
        "suppressed_scale_actions": suppressed_scale_actions,
    }


def run_multi_tenant(
    base_url: str,
    tenant_ids: list[str],
    requests_count: int,
    concurrency: int,
    *,
    emit: bool = True,
    timeout_seconds: float = 10.0,
    transport: httpx.BaseTransport | None = None,
    reconcile_autoscaler: bool = False,
) -> dict[str, Any]:
    normalized_concurrency = max(1, int(concurrency or 1))
    request_plan = _partition_requests(tenant_ids, requests_count)
    assignments: list[list[tuple[int, str]]] = [[] for _ in range(normalized_concurrency)]
    for index, tenant_id in enumerate(request_plan):
        assignments[index % normalized_concurrency].append((index, tenant_id))

    started = time.perf_counter()
    worker_results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=normalized_concurrency) as executor:
        futures = [
            executor.submit(
                _worker_run,
                base_url=base_url,
                assignments=bucket,
                timeout_seconds=timeout_seconds,
                transport=transport,
            )
            for bucket in assignments
            if bucket
        ]
        for future in futures:
            worker_results.append(future.result())
    duration = max(time.perf_counter() - started, 0.001)

    tenant_latencies: dict[str, list[float]] = {}
    tenant_request_counts: dict[str, int] = {}
    tenant_failures: dict[str, int] = {}
    for worker_result in worker_results:
        for tenant_id, latency, success in worker_result.get("request_results", []):
            tenant_latencies.setdefault(tenant_id, []).append(float(latency))
            tenant_request_counts[tenant_id] = int(tenant_request_counts.get(tenant_id, 0) or 0) + 1
            tenant_failures.setdefault(tenant_id, 0)
            if not success:
                tenant_failures[tenant_id] = int(tenant_failures.get(tenant_id, 0) or 0) + 1
    tenant_summaries: list[dict[str, Any]] = []
    with httpx.Client(timeout=timeout_seconds, transport=transport) as client:
        queue_snapshot = _safe_json(client, "GET", f"{base_url}/enterprise/queue/stats")
        autoscaler_status = _safe_json(client, "GET", f"{base_url}/enterprise/autoscaler/status")
        autoscaler_reconcile_result = (
            _safe_json(client, "POST", f"{base_url}/enterprise/autoscaler/reconcile") if reconcile_autoscaler else {}
        )
        autoscaler_history = _safe_json(client, "GET", f"{base_url}/enterprise/autoscaler/history", params={"limit": 100})

        for tenant_id in sorted(tenant_request_counts):
            tenant_summaries.append(
                _tenant_metrics(
                    client=client,
                    base_url=base_url,
                    tenant_id=tenant_id,
                    request_count=tenant_request_counts.get(tenant_id, 0),
                    failure_count=tenant_failures.get(tenant_id, 0),
                    latencies=tenant_latencies.get(tenant_id, []),
                )
            )

    all_latencies = [latency for latencies in tenant_latencies.values() for latency in latencies]
    total_failures = sum(int(summary.get("failures", 0) or 0) for summary in tenant_summaries)
    total_requests = sum(int(summary.get("requests", 0) or 0) for summary in tenant_summaries)
    availability_values = [float(summary.get("availability", 0.0) or 0.0) for summary in tenant_summaries]

    summary = {
        "tenant_count": len(tenant_summaries),
        "tenant_ids": [summary["tenant_id"] for summary in tenant_summaries],
        "requests": total_requests,
        "concurrency": normalized_concurrency,
        "failures": total_failures,
        "failure_rate": (total_failures / total_requests) if total_requests else 0.0,
        "duration_seconds": duration,
        "rps": total_requests / duration if duration else 0.0,
        "avg_latency_seconds": statistics.mean(all_latencies) if all_latencies else 0.0,
        "p95_latency_seconds": _percentile(all_latencies, 95.0),
        "availability_floor": min(availability_values) if availability_values else 0.0,
        "availability_average": statistics.mean(availability_values) if availability_values else 0.0,
        "tenant_summaries": tenant_summaries,
        "queue_snapshot": queue_snapshot,
        "autoscaler_status": autoscaler_status,
        "autoscaler_history_summary": _autoscaler_history_summary(autoscaler_history),
        "autoscaler_reconcile": autoscaler_reconcile_result,
    }

    if emit:
        print("Load Test Summary")
        print(f"tenant_count={summary['tenant_count']}")
        print(f"requests={summary['requests']}")
        print(f"concurrency={summary['concurrency']}")
        print(f"failures={summary['failures']}")
        print(f"failure_rate={summary['failure_rate']:.6f}")
        print(f"duration_seconds={summary['duration_seconds']:.3f}")
        print(f"rps={summary['rps']:.2f}")
        print(f"avg_latency_seconds={summary['avg_latency_seconds']:.6f}")
        print(f"p95_latency_seconds={summary['p95_latency_seconds']:.6f}")
        print(f"availability_floor={summary['availability_floor']:.6f}")
        print(f"queue_snapshot={summary['queue_snapshot']}")
        print(f"autoscaler_status={summary['autoscaler_status']}")
        print(f"autoscaler_history_summary={summary['autoscaler_history_summary']}")

    return summary


def run(
    base_url: str,
    tenant_id: str,
    requests_count: int,
    concurrency: int,
    emit: bool = True,
    *,
    timeout_seconds: float = 10.0,
    transport: httpx.BaseTransport | None = None,
    reconcile_autoscaler: bool = False,
) -> dict[str, Any]:
    summary = run_multi_tenant(
        base_url=base_url,
        tenant_ids=[tenant_id],
        requests_count=requests_count,
        concurrency=concurrency,
        emit=emit,
        timeout_seconds=timeout_seconds,
        transport=transport,
        reconcile_autoscaler=reconcile_autoscaler,
    )
    first_tenant = summary["tenant_summaries"][0] if summary.get("tenant_summaries") else {}
    flattened = dict(summary)
    flattened.update(first_tenant)
    flattened["tenant_id"] = tenant_id
    return flattened


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BRP-Cyber enterprise load test harness")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--tenant-id", action="append", dest="tenant_ids")
    parser.add_argument("--tenant-count", type=int, default=1)
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--reconcile-autoscaler", action="store_true")
    args = parser.parse_args()

    cli_tenants = list(args.tenant_ids or [])
    if not cli_tenants:
        cli_tenants = [str(uuid4()) for _ in range(max(1, args.tenant_count))]

    run_multi_tenant(
        args.base_url,
        tenant_ids=cli_tenants,
        requests_count=args.requests,
        concurrency=args.concurrency,
        emit=True,
        timeout_seconds=args.timeout_seconds,
        reconcile_autoscaler=args.reconcile_autoscaler,
    )
