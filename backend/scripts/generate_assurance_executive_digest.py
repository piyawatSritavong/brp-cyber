from __future__ import annotations

import json

from app.db.session import SessionLocal
from app.services.control_plane_assurance_slo import assurance_executive_risk_digest


def main() -> None:
    db = SessionLocal()
    try:
        digest = assurance_executive_risk_digest(db, limit=1000)
        print(json.dumps(digest, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
