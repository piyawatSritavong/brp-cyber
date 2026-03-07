from __future__ import annotations

import argparse
import json

from app.services.control_plane_governance_attestation import (
    create_governance_attestation,
    export_latest_governance_attestation,
    verify_detached_attestation_bundle,
    verify_governance_attestation_chain,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate signed governance attestation")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--export", action="store_true", help="Export latest signed attestation")
    parser.add_argument("--destination-dir", default="./tmp/compliance/exports")
    args = parser.parse_args()

    created = create_governance_attestation(limit=max(1, args.limit))
    verify_chain = verify_governance_attestation_chain(limit=1000)

    output = {
        "created": created,
        "verify_chain": verify_chain,
    }

    if args.export:
        export = export_latest_governance_attestation(destination_dir=args.destination_dir)
        output["export"] = export
        bundle = export.get("bundle")
        if isinstance(bundle, dict):
            output["verify_bundle"] = verify_detached_attestation_bundle(bundle=bundle)

    print(json.dumps(output, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
