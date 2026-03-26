from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

try:
    from scripts.loadtest_enterprise import run_multi_tenant
except ImportError:  # pragma: no cover - allows direct file execution without PYTHONPATH=backend
    from loadtest_enterprise import run_multi_tenant


DEFAULT_TIERS = [
    ("T1", 10_000, 4),
    ("T2", 50_000, 12),
    ("T3", 100_000, 24),
]


def _render_markdown(
    *,
    environment: str,
    tenant_ids: list[str],
    rows: list[tuple[str, dict[str, object]]],
) -> str:
    lines = []
    lines.append("# Load Test Evidence Report")
    lines.append("")
    lines.append(f"- Date: {datetime.now(timezone.utc).date().isoformat()}")
    lines.append(f"- Environment: {environment}")
    lines.append(f"- Generated At: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Tenants: {', '.join(tenant_ids)}")
    lines.append("")
    lines.append("## Traffic Tiers")
    lines.append("| Tier | Requests | Workers | Notes |")
    lines.append("|---|---:|---:|---|")
    for tier, summary in rows:
        lines.append(
            f"| {tier} | {int(summary.get('requests', 0) or 0)} | {int(summary.get('concurrency', 0) or 0)} | multi-tenant concurrent profile |"
        )
    lines.append("")
    lines.append("## Results")
    lines.append("| Tier | Throughput (RPS) | Failure Rate | Avg Latency (s) | P95 Latency (s) | Cost/10k Events (USD) | Availability |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for tier, summary in rows:
        tenant_summaries = summary.get("tenant_summaries", [])
        costs = [
            float(row.get("estimated_cost_per_10k_events_usd", 0.0) or 0.0)
            for row in tenant_summaries
            if isinstance(row, dict)
        ]
        avg_cost = sum(costs) / len(costs) if costs else 0.0
        lines.append(
            f"| {tier} | {float(summary.get('rps', 0.0) or 0.0):.2f} | {float(summary.get('failure_rate', 0.0) or 0.0):.6f} | "
            f"{float(summary.get('avg_latency_seconds', 0.0) or 0.0):.6f} | {float(summary.get('p95_latency_seconds', 0.0) or 0.0):.6f} | "
            f"{avg_cost:.6f} | {float(summary.get('availability_floor', 0.0) or 0.0):.6f} |"
        )
    lines.append("")
    lines.append("## Queue + Autoscaling")
    for tier, summary in rows:
        queue_snapshot = summary.get("queue_snapshot", {}) if isinstance(summary.get("queue_snapshot", {}), dict) else {}
        autoscaler_history = summary.get("autoscaler_history_summary", {}) if isinstance(summary.get("autoscaler_history_summary", {}), dict) else {}
        lines.append(f"### {tier}")
        lines.append(f"- Queue total lag peak: {int(autoscaler_history.get('peak_total_lag', 0) or 0)}")
        lines.append(f"- Queue total length: {int(queue_snapshot.get('total_length', 0) or 0)}")
        lines.append(f"- Desired workers peak: {int(autoscaler_history.get('peak_desired_workers', 0) or 0)}")
        lines.append(f"- Scale actions count: {int(autoscaler_history.get('scale_actions', 0) or 0)}")
        lines.append(f"- Cooldown or suppressed scale actions: {int(autoscaler_history.get('suppressed_scale_actions', 0) or 0)}")
    lines.append("")
    lines.append("## Observations")
    for tier, summary in rows:
        lines.append(
            f"1. {tier}: tenants={int(summary.get('tenant_count', 0) or 0)} rps={float(summary.get('rps', 0.0) or 0.0):.2f} "
            f"p95={float(summary.get('p95_latency_seconds', 0.0) or 0.0):.6f}s failure_rate={float(summary.get('failure_rate', 0.0) or 0.0):.6f}"
        )
    lines.append("")
    lines.append("## Action Items")
    lines.append("1. Run this matrix against a prod-like environment with real Redis/API/worker topology and capture the emitted JSON sidecar.")
    lines.append("2. Compare autoscaler queue lag and desired worker peaks against the target Kubernetes rollout profile before closing Phase 5 residual risks.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multi-tenant load test matrix and generate markdown evidence")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--tenant-id", action="append", dest="tenant_ids")
    parser.add_argument("--tenant-count", type=int, default=3)
    parser.add_argument("--environment", default="prod-like")
    parser.add_argument("--out", default="./tmp/loadtest/latest_matrix_report.md")
    parser.add_argument("--reconcile-autoscaler", action="store_true")
    args = parser.parse_args()

    tenant_ids = list(args.tenant_ids or [])
    if not tenant_ids:
        tenant_ids = [str(uuid4()) for _ in range(max(1, args.tenant_count))]

    rows: list[tuple[str, dict[str, object]]] = []
    for tier, requests_count, concurrency in DEFAULT_TIERS:
        summary = run_multi_tenant(
            args.base_url,
            tenant_ids=tenant_ids,
            requests_count=requests_count,
            concurrency=concurrency,
            emit=False,
            reconcile_autoscaler=args.reconcile_autoscaler,
        )
        rows.append((tier, summary))

    markdown = _render_markdown(environment=args.environment, tenant_ids=tenant_ids, rows=rows)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")

    json_path = out_path.with_suffix(".json")
    json_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "environment": args.environment,
                "tenant_ids": tenant_ids,
                "tiers": [{"tier": tier, "summary": summary} for tier, summary in rows],
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"report_written={out_path}")
    print(f"json_written={json_path}")


if __name__ == "__main__":
    main()
