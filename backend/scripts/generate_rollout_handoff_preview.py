from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.orchestrator import public_rollout_verifier_bundle
from app.services.rollout_handoff_auth import issue_rollout_handoff_token


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate rollout handoff token and preview bundle")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--auditor-name", default="external_auditor")
    parser.add_argument("--ttl-seconds", type=int, default=86400)
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id)
    token = issue_rollout_handoff_token(
        tenant_id=tenant_id,
        actor="script",
        auditor_name=args.auditor_name,
        ttl_seconds=max(60, args.ttl_seconds),
    )
    bundle = public_rollout_verifier_bundle(tenant_id=tenant_id, limit=max(1, args.limit))
    print(json.dumps({"token": token, "bundle_preview": bundle}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
