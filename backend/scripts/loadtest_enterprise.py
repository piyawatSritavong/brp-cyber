from __future__ import annotations

import argparse
import random
import time
from typing import Any
from uuid import uuid4

import httpx


def run(base_url: str, tenant_id: str, requests_count: int, concurrency: int, emit: bool = True) -> dict[str, Any]:
    start = time.time()
    failures = 0

    with httpx.Client(timeout=10.0) as client:
        for _ in range(requests_count):
            source_ip = f"203.0.113.{random.randint(1, 254)}"
            response = client.post(
                f"{base_url}/ingest/auth-login",
                json={
                    "tenant_id": tenant_id,
                    "source_ip": source_ip,
                    "username": "admin",
                    "success": False,
                    "auth_source": "loadtest",
                },
                headers={"x-tenant-id": tenant_id},
            )
            if response.status_code >= 400:
                failures += 1

    duration = max(time.time() - start, 0.001)
    rps = requests_count / duration

    with httpx.Client(timeout=10.0) as client:
        cost_resp = client.get(f"{base_url}/enterprise/cost/{tenant_id}")
        slo_resp = client.get(f"{base_url}/enterprise/slo/{tenant_id}")

    cost = cost_resp.json() if cost_resp.status_code == 200 else {}
    slo = slo_resp.json() if slo_resp.status_code == 200 else {}

    usd = float(cost.get("usd", 0.0) or 0.0)
    est_cost_per_10k = (usd / requests_count) * 10000 if requests_count else 0.0

    summary = {
        "tenant_id": tenant_id,
        "requests": requests_count,
        "failures": failures,
        "duration_seconds": duration,
        "rps": rps,
        "estimated_cost_per_10k_events_usd": est_cost_per_10k,
        "availability": float(slo.get("availability", 0.0) or 0.0),
        "slo_snapshot": slo,
    }

    if emit:
        print("Load Test Summary")
        print(f"tenant_id={tenant_id}")
        print(f"requests={requests_count}")
        print(f"failures={failures}")
        print(f"duration_seconds={duration:.3f}")
        print(f"rps={rps:.2f}")
        print(f"estimated_cost_per_10k_events_usd={est_cost_per_10k:.6f}")
        print(f"slo_snapshot={slo}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BRP-Cyber enterprise load test harness")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--tenant-id", default=str(uuid4()))
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=1)
    args = parser.parse_args()

    run(args.base_url, args.tenant_id, args.requests, args.concurrency, emit=True)
