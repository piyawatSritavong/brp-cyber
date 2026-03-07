from __future__ import annotations

import argparse
import json

from app.services.control_plane_orchestration_cost_guardrail_signing import (
    public_orchestration_cost_guardrail_report_bundle,
    verify_signed_orchestration_cost_guardrail_report_bundle,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Report/verify orchestration cost guardrail verifier bundle")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    bundle = public_orchestration_cost_guardrail_report_bundle(limit=max(1, args.limit))
    verify = verify_signed_orchestration_cost_guardrail_report_bundle(bundle)
    print(json.dumps({"bundle": bundle, "verify_bundle": verify}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
