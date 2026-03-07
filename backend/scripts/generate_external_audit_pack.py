from __future__ import annotations

import argparse
import json

from app.services.control_plane_audit_pack import generate_external_audit_pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate external audit pack")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--destination-dir", default="./tmp/compliance/audit_packs")
    args = parser.parse_args()

    result = generate_external_audit_pack(limit=max(1, args.limit), destination_dir=args.destination_dir)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
