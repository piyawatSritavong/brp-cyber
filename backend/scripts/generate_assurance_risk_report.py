from __future__ import annotations

import json

from app.db.session import SessionLocal
from app.services.control_plane_assurance_risk import assurance_risk_heatmap


def main() -> None:
    db = SessionLocal()
    try:
        report = assurance_risk_heatmap(db, limit=1000)
        print(json.dumps(report, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
