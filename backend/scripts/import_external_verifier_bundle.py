from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.control_plane_external_verifier_attestation import import_external_verifier_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Import external verifier result bundle for a tenant")
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--source", default="external_auditor")
    parser.add_argument("--payload-file", default="")
    parser.add_argument("--valid", action="store_true")
    parser.add_argument("--bundle-id", default="")
    parser.add_argument("--snapshot-id", default="")
    args = parser.parse_args()

    payload: dict[str, object]
    if args.payload_file:
        payload = json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    else:
        payload = {
            "valid": args.valid,
            "bundle_id": args.bundle_id,
            "snapshot_id": args.snapshot_id,
            "verifier": args.source,
        }

    result = import_external_verifier_bundle(
        tenant_code=args.tenant_code,
        verifier_payload=payload,
        source=args.source,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
