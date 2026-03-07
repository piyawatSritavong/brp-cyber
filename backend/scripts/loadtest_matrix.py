from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from scripts.loadtest_enterprise import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multi-tier load test and generate markdown evidence")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--out", default="../docs/loadtest/reports/latest_matrix_report.md")
    args = parser.parse_args()

    tiers = [
        ("T1", 10_000),
        ("T2", 50_000),
        ("T3", 100_000),
    ]

    rows = []
    for tier, requests_count in tiers:
        summary = run(args.base_url, args.tenant_id, requests_count=requests_count, concurrency=1, emit=False)
        rows.append((tier, summary))

    lines = []
    lines.append("# Load Test Matrix Report")
    lines.append("")
    lines.append(f"- Generated At: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Tenant: {args.tenant_id}")
    lines.append("")
    lines.append("| Tier | Requests | RPS | Failures | Cost/10k Events (USD) | Availability |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    for tier, summary in rows:
        lines.append(
            f"| {tier} | {summary['requests']} | {summary['rps']:.2f} | {summary['failures']} | {summary['estimated_cost_per_10k_events_usd']:.6f} | {summary['availability']:.6f} |"
        )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"report_written={out_path}")


if __name__ == "__main__":
    main()
