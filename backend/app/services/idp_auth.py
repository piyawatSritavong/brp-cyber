from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


def introspect_token(token: str) -> dict[str, Any]:
    if not settings.control_plane_idp_introspection_url:
        return {"valid": False, "reason": "idp_introspection_url_not_configured"}

    data = {"token": token}
    auth = None
    if settings.control_plane_idp_client_id and settings.control_plane_idp_client_secret:
        auth = (settings.control_plane_idp_client_id, settings.control_plane_idp_client_secret)

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(settings.control_plane_idp_introspection_url, data=data, auth=auth)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        return {"valid": False, "reason": f"idp_request_failed:{exc}"}

    if not payload.get("active", False):
        return {"valid": False, "reason": "inactive"}

    raw_scope = payload.get("scope", "")
    if isinstance(raw_scope, list):
        scopes = [str(s).strip() for s in raw_scope if str(s).strip()]
    else:
        scope_raw = str(raw_scope)
        scopes = [s for s in scope_raw.split(" ") if s]

    tenant_scope = str(
        payload.get("tenant_scope")
        or payload.get("tenant")
        or payload.get("organization")
        or "*"
    ).strip()
    actor = str(payload.get("email") or payload.get("username") or payload.get("sub") or "idp-user")

    return {
        "valid": True,
        "token_id": str(payload.get("jti", "idp-token")),
        "actor": actor,
        "expires_at": int(payload.get("exp", 0) or 0),
        "scopes": scopes or ["*"],
        "tenant_scope": tenant_scope,
        "source": "idp",
    }
