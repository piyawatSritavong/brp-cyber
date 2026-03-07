from __future__ import annotations

import argparse
import json

from app.services.control_plane_assurance_delivery_proof import export_signed_delivery_proof_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Export signed delivery proof bundle for a tenant")
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--destination-dir", default="./tmp/compliance/assurance_delivery_proofs")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    result = export_signed_delivery_proof_bundle(
        tenant_code=args.tenant_code,
        destination_dir=args.destination_dir,
        limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
