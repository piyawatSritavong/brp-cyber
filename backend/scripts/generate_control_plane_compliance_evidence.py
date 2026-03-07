from __future__ import annotations

import json
from pathlib import Path

from app.services.control_plane_compliance import build_control_plane_compliance_evidence


def main() -> None:
    report = build_control_plane_compliance_evidence()
    root = Path("./tmp/compliance")
    root.mkdir(parents=True, exist_ok=True)
    target = root / "control_plane_compliance_evidence.json"
    target.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "path": str(target), "overall_pass": report.get("overall_pass", False)}))


if __name__ == "__main__":
    main()
