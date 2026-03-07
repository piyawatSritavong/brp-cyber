from __future__ import annotations

import argparse
import json

from app.services.control_plane_legal_evidence import export_legal_evidence_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Export legal evidence profile")
    parser.add_argument("--destination-dir", default="./tmp/compliance/legal_evidence")
    args = parser.parse_args()

    result = export_legal_evidence_profile(destination_dir=args.destination_dir)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
