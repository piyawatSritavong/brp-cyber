from __future__ import annotations

import argparse
import json

from app.services.control_plane_audit_pack import verify_external_audit_pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify external audit pack manifest")
    parser.add_argument("--manifest-path", required=True)
    args = parser.parse_args()

    result = verify_external_audit_pack(manifest_path=args.manifest_path)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if not result.get("valid", False):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
