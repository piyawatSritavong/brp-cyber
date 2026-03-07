from __future__ import annotations

import argparse
import json

from app.services.control_plane_verifier_kit import export_tenant_verifier_kit


def main() -> None:
    parser = argparse.ArgumentParser(description="Export tenant verifier kit")
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--destination-dir", default="./tmp/compliance/verifier_kits")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    result = export_tenant_verifier_kit(
        tenant_code=args.tenant_code,
        destination_dir=args.destination_dir,
        limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
