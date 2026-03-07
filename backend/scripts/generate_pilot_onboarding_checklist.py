from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.services.orchestrator_pilot_onboarding import pilot_onboarding_checklist


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate pilot onboarding checklist for tenant")
    parser.add_argument("--tenant-id", required=True)
    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id)
    result = pilot_onboarding_checklist(tenant_id)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
