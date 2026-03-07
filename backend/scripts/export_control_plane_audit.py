from __future__ import annotations

import argparse
import json

from app.services.audit_export import export_control_plane_audit_to_siem, get_export_status


def main() -> None:
    parser = argparse.ArgumentParser(description="Export control-plane audit events to SIEM")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on failed export")
    args = parser.parse_args()

    result = export_control_plane_audit_to_siem(batch_size=max(1, args.batch_size))
    status = get_export_status()

    print(json.dumps({"result": result, "status": status}, indent=2))

    if args.strict and result.get("status") == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
