from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.services.redis_client import redis_client

ASSURANCE_POLICY_PACK_PREFIX = "control_plane_assurance_policy_pack"


def _key(tenant_code: str) -> str:
    return f"{ASSURANCE_POLICY_PACK_PREFIX}:{tenant_code.lower().strip()}"


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except json.JSONDecodeError:
            return []
    return []


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
    max_auto = payload.get("max_auto_apply_actions_per_run", 1)
    try:
        max_auto = int(max_auto)
    except (TypeError, ValueError):
        max_auto = 1
    max_auto = min(100, max(0, max_auto))

    return {
        "pack_version": str(payload.get("pack_version", "1.0")),
        "owner": str(payload.get("owner", "security")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "auto_apply_actions": _as_list(payload.get("auto_apply_actions", [])),
        "force_approval_actions": _as_list(payload.get("force_approval_actions", [])),
        "blocked_actions": _as_list(payload.get("blocked_actions", [])),
        "max_auto_apply_actions_per_run": max_auto,
        "notify_only": bool(payload.get("notify_only", False)),
        "rollback_on_worse_result": bool(payload.get("rollback_on_worse_result", True)),
        "min_effectiveness_delta": float(payload.get("min_effectiveness_delta", 0.0) or 0.0),
    }


def upsert_assurance_policy_pack(tenant_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize(payload)
    redis_client.set(_key(tenant_code), json.dumps(normalized, ensure_ascii=True, sort_keys=True))
    return {"status": "upserted", "tenant_code": tenant_code, "policy_pack": normalized}


def get_assurance_policy_pack(tenant_code: str) -> dict[str, Any]:
    raw = redis_client.get(_key(tenant_code))
    if not raw:
        return {
            "status": "default",
            "tenant_code": tenant_code,
            "policy_pack": _normalize({}),
        }
    try:
        pack = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "corrupted", "tenant_code": tenant_code}
    return {"status": "ok", "tenant_code": tenant_code, "policy_pack": _normalize(pack)}
