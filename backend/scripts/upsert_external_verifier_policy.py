from __future__ import annotations

import argparse
import json

from app.services.control_plane_external_verifier_attestation import upsert_external_verifier_policy


def main() -> None:
    parser = argparse.ArgumentParser(description="Upsert external verifier quorum policy")
    parser.add_argument("--tenant-code", required=True)
    parser.add_argument("--min-quorum", type=int, default=1)
    parser.add_argument("--freshness-hours", type=int, default=24)
    parser.add_argument("--min-weighted-score", type=float, default=0.0)
    parser.add_argument("--allowed-verifiers", default="")
    parser.add_argument("--verifier-weights", default="")
    parser.add_argument("--allow-missing-internal-signature", action="store_true")
    parser.add_argument("--no-distinct", action="store_true")
    parser.add_argument("--block-on-disagreement", action="store_true")
    args = parser.parse_args()

    allowed = [item.strip() for item in args.allowed_verifiers.split(",") if item.strip()]
    weights: dict[str, float] = {}
    if args.verifier_weights.strip():
        for part in args.verifier_weights.split(","):
            text = part.strip()
            if not text or ":" not in text:
                continue
            name, raw_weight = text.split(":", 1)
            name = name.strip().lower()
            if not name:
                continue
            try:
                weights[name] = max(0.0, float(raw_weight.strip()))
            except ValueError:
                continue
    result = upsert_external_verifier_policy(
        tenant_code=args.tenant_code,
        payload={
            "min_quorum": args.min_quorum,
            "freshness_hours": args.freshness_hours,
            "min_weighted_score": args.min_weighted_score,
            "allowed_verifiers": allowed,
            "verifier_weights": weights,
            "require_internal_signature": not args.allow_missing_internal_signature,
            "require_distinct_verifiers": not args.no_distinct,
            "block_on_disagreement": args.block_on_disagreement,
        },
    )
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
