from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.services.control_plane_orchestration_cost_guardrail import orchestration_cost_guardrail_enterprise_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Report orchestration cost guardrail anomalies")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--apply-actions", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        snapshot = orchestration_cost_guardrail_enterprise_snapshot(
            db,
            limit=max(1, args.limit),
            apply_actions=args.apply_actions,
        )
    finally:
        db.close()

    anomaly_rows = [row for row in snapshot.get("rows", []) if bool(row.get("anomaly", False))]
    report = {
        "count": len(anomaly_rows),
        "anomaly_count": int(snapshot.get("anomaly_count", 0) or 0),
        "pressure_count": int(snapshot.get("pressure_count", 0) or 0),
        "breached_count": int(snapshot.get("breached_count", 0) or 0),
        "rows": anomaly_rows,
    }
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
