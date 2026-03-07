from __future__ import annotations

import json
from pathlib import Path

from app.services.control_plane_governance import governance_dashboard


def main() -> None:
    report = governance_dashboard(limit=5000)
    root = Path("./tmp/compliance")
    root.mkdir(parents=True, exist_ok=True)
    target = root / "control_plane_governance_report.json"
    target.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "path": str(target), "events": report.get("summary", {}).get("events_analyzed", 0)}))


if __name__ == "__main__":
    main()
