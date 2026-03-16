from __future__ import annotations

import copy
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    AiCoworkerPlugin,
    RedScanRun,
    Site,
    SoarPlaybook,
    SiteEmbeddedWorkflowEndpoint,
    SiteEmbeddedWorkflowInvocation,
)
from app.services.connector_observability import record_connector_event
from app.services.coworker_plugins import (
    ensure_builtin_plugins,
    run_site_coworker_plugin,
    upsert_site_coworker_plugin_binding,
)
from app.services.integration_layer import ingest_integration_event
from app.services.integration_adapter_templates import list_adapter_invoke_templates
from app.services.redis_client import redis_client
from app.services.soar_playbook_hub import _get_policy_for_tenant, ensure_builtin_playbooks, execute_playbook


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _safe_json_dict(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _safe_iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _issue_token() -> str:
    token_id = secrets.token_hex(8)
    secret = secrets.token_urlsafe(24)
    return f"emb_{token_id}.{secret}"


def _verify_secret(token: str, secret_hash: str) -> bool:
    if not token or not secret_hash:
        return False
    return hmac.compare_digest(_hash_secret(token), secret_hash)


def _stable_payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _normalize_workflow_type(value: str) -> str:
    workflow_type = str(value or "").strip().lower()
    return workflow_type if workflow_type in {"coworker_plugin", "soar_playbook"} else "coworker_plugin"


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        candidate = str(item or "").strip()
        if not candidate or candidate in seen:
            continue
        normalized.append(candidate)
        seen.add(candidate)
    return normalized


def _normalize_endpoint_config(workflow_type: str, config: dict[str, Any] | None) -> dict[str, Any]:
    safe_config = dict(config or {})
    normalized_workflow_type = _normalize_workflow_type(workflow_type)
    if normalized_workflow_type != "soar_playbook":
        return safe_config

    playbook_code = str(
        safe_config.get("playbook_code")
        or safe_config.get("default_playbook_code")
        or ""
    ).strip()
    allowed_playbook_codes = _normalize_string_list(safe_config.get("allowed_playbook_codes", []))
    blocked_playbook_codes = _normalize_string_list(safe_config.get("blocked_playbook_codes", []))
    required_payload_fields = _normalize_string_list(safe_config.get("required_payload_fields", []))

    if playbook_code:
        safe_config["playbook_code"] = playbook_code
        safe_config["default_playbook_code"] = playbook_code
        if playbook_code not in allowed_playbook_codes:
            allowed_playbook_codes = [playbook_code, *allowed_playbook_codes]

    safe_config["allowed_playbook_codes"] = allowed_playbook_codes
    if blocked_playbook_codes:
        safe_config["blocked_playbook_codes"] = blocked_playbook_codes
    if required_payload_fields:
        safe_config["required_payload_fields"] = required_payload_fields
    safe_config["require_playbook_approval"] = bool(safe_config.get("require_playbook_approval", True))
    return safe_config


def _guardrail_decision(
    endpoint: SiteEmbeddedWorkflowEndpoint,
    *,
    actor: str,
    payload: dict[str, Any],
    webhook_event_id: str,
) -> dict[str, Any]:
    config = _safe_json_dict(endpoint.config_json)
    normalized_actor = actor.strip().lower()
    allowed_actors_raw = config.get("allowed_actors", [])
    allowed_actors = (
        {str(item).strip().lower() for item in allowed_actors_raw if str(item).strip()}
        if isinstance(allowed_actors_raw, list)
        else set()
    )
    if allowed_actors and normalized_actor not in allowed_actors:
        return {"blocked": True, "reason": "actor_not_allowed", "actor": actor}

    max_payload_keys = max(1, int(config.get("max_payload_keys", getattr(settings, "embedded_workflow_max_payload_keys", 64)) or 64))
    if len(payload) > max_payload_keys:
        return {"blocked": True, "reason": "payload_key_limit_exceeded", "payload_key_count": len(payload), "max_payload_keys": max_payload_keys}

    payload_bytes = len(json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8"))
    max_payload_bytes = max(512, int(config.get("max_payload_bytes", getattr(settings, "embedded_workflow_max_payload_bytes", 32768)) or 32768))
    if payload_bytes > max_payload_bytes:
        return {"blocked": True, "reason": "payload_size_limit_exceeded", "payload_bytes": payload_bytes, "max_payload_bytes": max_payload_bytes}

    require_webhook_event_id = bool(config.get("require_webhook_event_id", getattr(settings, "embedded_workflow_require_webhook_event_id", False)))
    if require_webhook_event_id and not webhook_event_id.strip():
        return {"blocked": True, "reason": "missing_webhook_event_id"}

    now_ts = int(_now().timestamp())
    rate_key = f"embedded_workflow:rate:{endpoint.id}"
    rate_limit = max(1, int(config.get("rate_limit_per_minute", getattr(settings, "embedded_workflow_rate_limit_per_minute", 60)) or 60))
    redis_client.zadd(rate_key, {secrets.token_hex(8): now_ts})
    redis_client.zremrangebyscore(rate_key, 0, now_ts - 60)
    current_rate = int(redis_client.zcard(rate_key) or 0)
    redis_client.expire(rate_key, 120)
    if current_rate > rate_limit:
        return {"blocked": True, "reason": "rate_limit_exceeded", "current_rate": current_rate, "rate_limit_per_minute": rate_limit}

    replay_window = max(30, int(config.get("replay_window_seconds", getattr(settings, "embedded_workflow_replay_window_seconds", 300)) or 300))
    replay_ref = webhook_event_id.strip() or _stable_payload_hash(payload)
    replay_key = f"embedded_workflow:replay:{endpoint.id}:{replay_ref}"
    if redis_client.exists(replay_key):
        return {"blocked": True, "reason": "replay_detected", "replay_ref": replay_ref}
    redis_client.set(replay_key, "1", ex=replay_window)
    return {"blocked": False, "reason": "", "replay_ref": replay_ref, "rate_limit_per_minute": rate_limit}


def _playbook_guardrail_decision(
    endpoint: SiteEmbeddedWorkflowEndpoint,
    *,
    payload: dict[str, Any],
    merged_config: dict[str, Any],
) -> dict[str, Any]:
    if _normalize_workflow_type(endpoint.workflow_type) != "soar_playbook":
        return {"blocked": False, "reason": ""}

    allowed_raw = merged_config.get("allowed_playbook_codes", [])
    blocked_raw = merged_config.get("blocked_playbook_codes", [])
    required_fields_raw = merged_config.get("required_payload_fields", [])
    allowed_codes = {str(item).strip() for item in allowed_raw if str(item).strip()} if isinstance(allowed_raw, list) else set()
    blocked_codes = {str(item).strip() for item in blocked_raw if str(item).strip()} if isinstance(blocked_raw, list) else set()
    required_fields = [str(item).strip() for item in required_fields_raw if str(item).strip()] if isinstance(required_fields_raw, list) else []

    playbook_code = str(
        payload.get("playbook_code")
        or merged_config.get("playbook_code")
        or merged_config.get("default_playbook_code")
        or ""
    ).strip()
    if not playbook_code:
        return {"blocked": True, "reason": "playbook_code_required"}
    if blocked_codes and playbook_code in blocked_codes:
        return {"blocked": True, "reason": "playbook_blocked_by_endpoint_policy", "playbook_code": playbook_code}
    if allowed_codes and playbook_code not in allowed_codes:
        return {"blocked": True, "reason": "playbook_not_allowed", "playbook_code": playbook_code}
    missing_fields = [field for field in required_fields if payload.get(field) in {None, ""}]
    if missing_fields:
        return {"blocked": True, "reason": "required_payload_fields_missing", "missing_fields": missing_fields}
    return {"blocked": False, "reason": "", "playbook_code": playbook_code, "required_payload_fields": required_fields}


def _endpoint_row(row: SiteEmbeddedWorkflowEndpoint) -> dict[str, Any]:
    return {
        "endpoint_id": str(row.id),
        "site_id": str(row.site_id),
        "endpoint_code": row.endpoint_code,
        "workflow_type": row.workflow_type,
        "plugin_code": row.plugin_code,
        "connector_source": row.connector_source,
        "default_event_kind": row.default_event_kind,
        "enabled": bool(row.enabled),
        "dry_run_default": bool(row.dry_run_default),
        "config": _safe_json_dict(row.config_json),
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _invocation_row(row: SiteEmbeddedWorkflowInvocation) -> dict[str, Any]:
    return {
        "invocation_id": str(row.id),
        "endpoint_id": str(row.endpoint_id),
        "site_id": str(row.site_id),
        "endpoint_code": row.endpoint_code,
        "workflow_type": row.workflow_type,
        "plugin_code": row.plugin_code,
        "source": row.source,
        "status": row.status,
        "dry_run": bool(row.dry_run),
        "request_summary": _safe_json_dict(row.request_summary_json),
        "response_summary": _safe_json_dict(row.response_summary_json),
        "error_message": row.error_message,
        "created_at": _safe_iso(row.created_at),
    }


def upsert_site_embedded_workflow_endpoint(
    db: Session,
    *,
    site_id: UUID,
    endpoint_code: str,
    workflow_type: str = "coworker_plugin",
    plugin_code: str,
    connector_source: str = "generic",
    default_event_kind: str = "security_event",
    enabled: bool = True,
    dry_run_default: bool = True,
    config: dict[str, Any] | None = None,
    owner: str = "security",
    rotate_secret: bool = False,
) -> dict[str, Any]:
    ensure_builtin_plugins(db)
    ensure_builtin_playbooks(db)
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    normalized_workflow_type = _normalize_workflow_type(workflow_type)
    normalized_config = _normalize_endpoint_config(normalized_workflow_type, config)
    plugin = None
    if normalized_workflow_type == "coworker_plugin":
        plugin = db.scalar(select(AiCoworkerPlugin).where(AiCoworkerPlugin.plugin_code == plugin_code))
        if not plugin:
            return {"status": "plugin_not_found", "plugin_code": plugin_code}

    code = endpoint_code.strip().lower()[:80]
    if not code:
        return {"status": "invalid_endpoint_code"}

    row = db.scalar(
        select(SiteEmbeddedWorkflowEndpoint).where(
            SiteEmbeddedWorkflowEndpoint.site_id == site.id,
            SiteEmbeddedWorkflowEndpoint.endpoint_code == code,
        )
    )
    token = ""
    now = _now()
    if row:
        row.workflow_type = normalized_workflow_type
        row.plugin_code = plugin_code if normalized_workflow_type == "coworker_plugin" else ""
        row.connector_source = connector_source.strip().lower()[:64] or "generic"
        row.default_event_kind = default_event_kind.strip().lower()[:64] or "security_event"
        row.enabled = bool(enabled)
        row.dry_run_default = bool(dry_run_default)
        row.config_json = _as_json(normalized_config)
        row.owner = owner.strip()[:64] or "security"
        row.updated_at = now
        if rotate_secret or not row.secret_hash:
            token = _issue_token()
            row.secret_hash = _hash_secret(token)
        db.commit()
        db.refresh(row)
        return {
            "status": "updated",
            "endpoint": _endpoint_row(row),
            "token": token,
            "invoke_path": f"/integrations/embedded/sites/{site.site_code}/{row.endpoint_code}/invoke",
        }

    token = _issue_token()
    created = SiteEmbeddedWorkflowEndpoint(
        site_id=site.id,
        endpoint_code=code,
        workflow_type=normalized_workflow_type,
        plugin_code=plugin_code if normalized_workflow_type == "coworker_plugin" else "",
        connector_source=connector_source.strip().lower()[:64] or "generic",
        default_event_kind=default_event_kind.strip().lower()[:64] or "security_event",
        secret_hash=_hash_secret(token),
        enabled=bool(enabled),
        dry_run_default=bool(dry_run_default),
        config_json=_as_json(normalized_config),
        owner=owner.strip()[:64] or "security",
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {
        "status": "created",
        "endpoint": _endpoint_row(created),
        "token": token,
        "invoke_path": f"/integrations/embedded/sites/{site.site_code}/{created.endpoint_code}/invoke",
    }


def list_site_embedded_workflow_endpoints(db: Session, *, site_id: UUID, limit: int = 100) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"site_id": str(site_id), "count": 0, "rows": []}
    rows = db.scalars(
        select(SiteEmbeddedWorkflowEndpoint)
        .where(SiteEmbeddedWorkflowEndpoint.site_id == site.id)
        .order_by(desc(SiteEmbeddedWorkflowEndpoint.updated_at))
        .limit(max(1, min(limit, 500)))
    ).all()
    return {"site_id": str(site.id), "count": len(rows), "rows": [_endpoint_row(row) for row in rows]}


def list_site_embedded_workflow_invocations(
    db: Session,
    *,
    site_id: UUID,
    endpoint_code: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"site_id": str(site_id), "count": 0, "rows": []}
    stmt = (
        select(SiteEmbeddedWorkflowInvocation)
        .where(SiteEmbeddedWorkflowInvocation.site_id == site.id)
        .order_by(desc(SiteEmbeddedWorkflowInvocation.created_at))
        .limit(max(1, min(limit, 500)))
    )
    if endpoint_code.strip():
        stmt = stmt.where(SiteEmbeddedWorkflowInvocation.endpoint_code == endpoint_code.strip().lower())
    rows = db.scalars(stmt).all()
    return {"site_id": str(site.id), "count": len(rows), "rows": [_invocation_row(row) for row in rows]}


def list_site_embedded_invoke_packs(
    db: Session,
    *,
    site_id: UUID,
    endpoint_code: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"site_id": str(site_id), "count": 0, "rows": []}
    stmt = (
        select(SiteEmbeddedWorkflowEndpoint)
        .where(SiteEmbeddedWorkflowEndpoint.site_id == site.id)
        .order_by(desc(SiteEmbeddedWorkflowEndpoint.updated_at))
        .limit(max(1, min(limit, 500)))
    )
    if endpoint_code.strip():
        stmt = stmt.where(SiteEmbeddedWorkflowEndpoint.endpoint_code == endpoint_code.strip().lower())
    endpoints = db.scalars(stmt).all()
    templates = list_adapter_invoke_templates()
    template_by_source = {
        str(row.get("source", "")).strip().lower(): row
        for row in templates.get("rows", [])
        if isinstance(row, dict)
    }
    rows: list[dict[str, Any]] = []
    for endpoint in endpoints:
        template = template_by_source.get(str(endpoint.connector_source or "").strip().lower(), {})
        endpoint_config = _safe_json_dict(endpoint.config_json)
        workflow_type = _normalize_workflow_type(endpoint.workflow_type)
        automation_pack = template.get("automation_pack", {}) if isinstance(template, dict) else {}
        if not isinstance(automation_pack, dict):
            automation_pack = {}
        invoke_payload = copy.deepcopy(template.get("invoke_payload", {})) if isinstance(template, dict) else {}
        if not isinstance(invoke_payload, dict):
            invoke_payload = {}
        invoke_payload["source"] = endpoint.connector_source or "generic"
        invoke_payload["event_kind"] = endpoint.default_event_kind or "security_event"
        invoke_payload["dry_run"] = bool(endpoint.dry_run_default)
        invoke_payload.setdefault("actor", f"{endpoint.connector_source or 'embedded'}_client")
        invoke_payload.setdefault(
            "payload",
            {
                "message": "sample embedded alert",
                "severity": "high",
                "source_ip": "203.0.113.20",
            },
        )
        if workflow_type == "soar_playbook":
            default_playbook_code = str(
                endpoint_config.get("playbook_code")
                or automation_pack.get("default_playbook_code")
                or ""
            ).strip()
            invoke_payload["playbook_code"] = default_playbook_code
        invoke_path = f"/integrations/embedded/sites/{site.site_code}/{endpoint.endpoint_code}/invoke"
        curl_example = (
            "curl -X POST {api_base_url}"
            + invoke_path
            + " \\\n"
            + "  -H 'Content-Type: application/json' \\\n"
            + "  -H 'X-BRP-Embed-Token: <TOKEN_FROM_CREATE_OR_ROTATE>' \\\n"
            + f"  -d '{json.dumps(invoke_payload, ensure_ascii=True, separators=(',', ':'))}'"
        )
        rows.append(
            {
                "endpoint": _endpoint_row(endpoint),
                "invoke_pack": {
                    "display_name": str(template.get("display_name", f"{endpoint.connector_source or 'generic'} embedded invoke")).strip(),
                    "vendor_preset_code": str(template.get("vendor_preset_code", f"{endpoint.connector_source or 'generic'}_preset")).strip(),
                    "notes": (
                        template.get("notes", [])
                        if isinstance(template.get("notes", []), list)
                        else ["Token is shown only during endpoint create/rotate."]
                    )
                    + ["Token is shown only during endpoint create/rotate. Store it in the customer tool secret vault."],
                    "activation_steps": template.get("activation_steps", [])
                    if isinstance(template.get("activation_steps", []), list)
                    else [],
                    "field_mapping": template.get("field_mapping", []) if isinstance(template.get("field_mapping", []), list) else [],
                    "recommended_plugin_codes": template.get("recommended_plugin_codes", [])
                    if isinstance(template.get("recommended_plugin_codes", []), list)
                    else [endpoint.plugin_code],
                    "automation_pack": {
                        "workflow_type": workflow_type,
                        "default_playbook_code": str(
                            endpoint_config.get("playbook_code")
                            or automation_pack.get("default_playbook_code")
                            or ""
                        ).strip(),
                        "allowed_playbook_codes": endpoint_config.get("allowed_playbook_codes", automation_pack.get("allowed_playbook_codes", []))
                        if isinstance(endpoint_config.get("allowed_playbook_codes", automation_pack.get("allowed_playbook_codes", [])), list)
                        else [],
                        "require_playbook_approval": bool(
                            endpoint_config.get("require_playbook_approval", automation_pack.get("require_playbook_approval", True))
                        ),
                    },
                    "guardrails": {
                        "rate_limit_per_minute": int(endpoint_config.get("rate_limit_per_minute", getattr(settings, "embedded_workflow_rate_limit_per_minute", 60)) or 60),
                        "replay_window_seconds": int(endpoint_config.get("replay_window_seconds", getattr(settings, "embedded_workflow_replay_window_seconds", 300)) or 300),
                        "require_webhook_event_id": bool(endpoint_config.get("require_webhook_event_id", getattr(settings, "embedded_workflow_require_webhook_event_id", False))),
                    },
                    "invoke_path": invoke_path,
                    "headers": {
                        "Content-Type": "application/json",
                        "X-BRP-Embed-Token": "<TOKEN_FROM_CREATE_OR_ROTATE>",
                    },
                    "invoke_payload": invoke_payload,
                    "curl_example": curl_example,
                },
            }
        )
    return {"site_id": str(site.id), "site_code": site.site_code, "count": len(rows), "rows": rows}


def verify_site_embedded_automation_packs(
    db: Session,
    *,
    site_id: UUID,
    endpoint_code: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    ensure_builtin_plugins(db)
    ensure_builtin_playbooks(db)
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id), "count": 0, "rows": []}

    stmt = (
        select(SiteEmbeddedWorkflowEndpoint)
        .where(SiteEmbeddedWorkflowEndpoint.site_id == site.id)
        .order_by(desc(SiteEmbeddedWorkflowEndpoint.updated_at))
        .limit(max(1, min(limit, 500)))
    )
    if endpoint_code.strip():
        stmt = stmt.where(SiteEmbeddedWorkflowEndpoint.endpoint_code == endpoint_code.strip().lower())
    endpoints = db.scalars(stmt).all()
    tenant_policy = _get_policy_for_tenant(db, site.tenant_id)
    blocked_playbook_codes = {
        str(item).strip()
        for item in tenant_policy.get("blocked_playbook_codes", [])
        if str(item).strip()
    }

    rows: list[dict[str, Any]] = []
    ok_count = 0
    warning_count = 0
    error_count = 0
    for endpoint in endpoints:
        normalized_workflow_type = _normalize_workflow_type(endpoint.workflow_type)
        endpoint_config = _normalize_endpoint_config(normalized_workflow_type, _safe_json_dict(endpoint.config_json))
        issues: list[dict[str, str]] = []
        recommendations: list[str] = []
        effective_approval_required = False
        playbook_code = ""

        if not bool(endpoint.enabled):
            issues.append({"level": "warning", "code": "endpoint_disabled", "message": "Endpoint is disabled and will not accept invokes."})
            recommendations.append("Enable the endpoint before handing the invoke pack to the customer tool.")

        if normalized_workflow_type == "coworker_plugin":
            plugin = db.scalar(select(AiCoworkerPlugin).where(AiCoworkerPlugin.plugin_code == endpoint.plugin_code))
            if not plugin:
                issues.append({"level": "error", "code": "plugin_not_found", "message": f"Plugin {endpoint.plugin_code or '-'} does not exist."})
                recommendations.append("Bind the endpoint to an installed AI co-worker plugin.")
            elif not bool(plugin.is_active):
                issues.append({"level": "warning", "code": "plugin_inactive", "message": f"Plugin {plugin.plugin_code} is inactive."})
                recommendations.append("Reactivate the plugin or switch the endpoint to an active plugin.")
        else:
            playbook_code = str(
                endpoint_config.get("playbook_code")
                or endpoint_config.get("default_playbook_code")
                or ""
            ).strip()
            allowed_playbook_codes = _normalize_string_list(endpoint_config.get("allowed_playbook_codes", []))
            if not playbook_code:
                issues.append({"level": "error", "code": "playbook_code_missing", "message": "No default playbook is configured for this embedded automation pack."})
                recommendations.append("Set playbook_code/default_playbook_code so vendor invokes cannot drift to an unsafe action.")
            else:
                playbook = db.scalar(select(SoarPlaybook).where(SoarPlaybook.playbook_code == playbook_code))
                if not playbook or not bool(playbook.is_active):
                    issues.append({"level": "error", "code": "playbook_not_found", "message": f"Playbook {playbook_code} is missing or inactive."})
                    recommendations.append("Seed/enable the referenced playbook before enabling direct vendor automation.")
                else:
                    if playbook_code in blocked_playbook_codes:
                        issues.append({"level": "error", "code": "playbook_blocked_by_policy", "message": f"Tenant policy blocks playbook {playbook_code}."})
                        recommendations.append("Remove the playbook from tenant blocked_playbook_codes or choose a different action.")
                    if playbook.scope == "partner" and not bool(tenant_policy.get("allow_partner_scope", True)):
                        issues.append({"level": "error", "code": "partner_scope_blocked", "message": "Tenant policy does not allow partner-scope playbooks."})
                        recommendations.append("Enable partner scope for this tenant or use a private-scope playbook.")
                    if allowed_playbook_codes and playbook_code not in allowed_playbook_codes:
                        issues.append({"level": "error", "code": "playbook_not_in_allowlist", "message": f"Endpoint allowlist does not include {playbook_code}."})
                        recommendations.append("Add the default playbook to allowed_playbook_codes to avoid runtime guardrail blocks.")
                    if not allowed_playbook_codes:
                        issues.append({"level": "warning", "code": "allowlist_missing", "message": "allowed_playbook_codes is empty; endpoint is less constrained than it should be."})
                        recommendations.append("Narrow allowed_playbook_codes to the smallest safe set for this connector.")
                    scope_requirements = tenant_policy.get("require_approval_by_scope", {})
                    if not isinstance(scope_requirements, dict):
                        scope_requirements = {}
                    category_requirements = tenant_policy.get("require_approval_by_category", {})
                    if not isinstance(category_requirements, dict):
                        category_requirements = {}
                    effective_approval_required = bool(
                        endpoint_config.get("require_playbook_approval", True)
                        or scope_requirements.get(playbook.scope, False)
                        or category_requirements.get(playbook.category, False)
                    )
            if endpoint.connector_source == "cloudflare" and not bool(endpoint_config.get("require_webhook_event_id", getattr(settings, "embedded_workflow_require_webhook_event_id", False))):
                issues.append({"level": "warning", "code": "webhook_event_id_not_required", "message": "Cloudflare preset is safer with webhook event IDs enabled for replay protection."})
                recommendations.append("Enable require_webhook_event_id for Cloudflare endpoints.")

        status = "ok"
        if any(issue["level"] == "error" for issue in issues):
            status = "error"
            error_count += 1
        elif issues:
            status = "warning"
            warning_count += 1
        else:
            ok_count += 1

        rows.append(
            {
                "endpoint": _endpoint_row(endpoint),
                "verification": {
                    "status": status,
                    "workflow_type": normalized_workflow_type,
                    "playbook_code": playbook_code,
                    "effective_approval_required": effective_approval_required,
                    "tenant_policy": {
                        "allow_partner_scope": bool(tenant_policy.get("allow_partner_scope", True)),
                        "blocked_playbook_codes": sorted(blocked_playbook_codes),
                    },
                    "issues": issues,
                    "recommendations": recommendations,
                },
            }
        )

    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "count": len(rows),
        "ok_count": ok_count,
        "warning_count": warning_count,
        "error_count": error_count,
        "rows": rows,
    }


def list_site_embedded_activation_bundles(
    db: Session,
    *,
    site_id: UUID,
    endpoint_code: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id), "count": 0, "rows": []}

    invoke_packs = list_site_embedded_invoke_packs(db, site_id=site.id, endpoint_code=endpoint_code, limit=limit)
    verification = verify_site_embedded_automation_packs(db, site_id=site.id, endpoint_code=endpoint_code, limit=limit)
    verification_by_endpoint_code = {
        str(row.get("endpoint", {}).get("endpoint_code", "")).strip().lower(): row.get("verification", {})
        for row in verification.get("rows", [])
        if isinstance(row, dict)
    }

    rows: list[dict[str, Any]] = []
    ready_count = 0
    needs_attention_count = 0
    blocked_count = 0
    for row in invoke_packs.get("rows", []):
        if not isinstance(row, dict):
            continue
        endpoint = row.get("endpoint", {})
        invoke_pack = row.get("invoke_pack", {})
        endpoint_code_key = str(endpoint.get("endpoint_code", "")).strip().lower()
        verification_row = verification_by_endpoint_code.get(endpoint_code_key, {})
        verification_status = str(verification_row.get("status", "warning") or "warning").lower()
        if verification_status not in {"ok", "warning", "error"}:
            verification_status = "warning"

        handoff_status = "ready"
        if verification_status == "error":
            handoff_status = "blocked"
            blocked_count += 1
        elif verification_status == "warning":
            handoff_status = "needs_attention"
            needs_attention_count += 1
        else:
            ready_count += 1

        issues = verification_row.get("issues", [])
        missing_items = [
            str(item.get("message", "")).strip()
            for item in issues
            if isinstance(item, dict) and str(item.get("message", "")).strip()
        ]
        checklist = [
            "Confirm the customer tool stores X-BRP-Embed-Token in its secret vault.",
            "Verify the connector payload matches the field mapping in the activation bundle.",
            "Run one dry-run invoke before switching the endpoint to production apply mode.",
        ]
        if endpoint.get("workflow_type") == "soar_playbook":
            checklist.append("Validate the referenced SOAR playbook is approved for this tenant before go-live.")
        if str(endpoint.get("connector_source", "")).strip().lower() == "cloudflare":
            checklist.append("Enable webhook event IDs for replay protection before handing the bundle to Cloudflare.")

        rows.append(
            {
                "endpoint": endpoint,
                "activation_bundle": {
                    **invoke_pack,
                    "operator_checklist": checklist,
                },
                "verification": verification_row,
                "handoff": {
                    "status": handoff_status,
                    "customer_handoff_ready": handoff_status == "ready",
                    "missing_items": missing_items,
                    "summary": (
                        "Ready to hand off to customer tool owners."
                        if handoff_status == "ready"
                        else "Review verification findings before sharing this activation bundle."
                    ),
                },
            }
        )

    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "count": len(rows),
        "ready_count": ready_count,
        "needs_attention_count": needs_attention_count,
        "blocked_count": blocked_count,
        "rows": rows,
    }


def embedded_automation_federation_snapshot(
    db: Session,
    *,
    connector_source: str = "",
    limit: int = 200,
) -> dict[str, Any]:
    max_rows = max(1, min(limit, 500))
    normalized_connector_source = str(connector_source or "").strip().lower()
    sites = db.scalars(
        select(Site)
        .order_by(desc(Site.updated_at), desc(Site.created_at))
        .limit(max_rows)
    ).all()

    rows: list[dict[str, Any]] = []
    total_endpoints = 0
    total_ready_endpoints = 0
    total_warning_endpoints = 0
    total_error_endpoints = 0
    ready_sites = 0
    warning_sites = 0
    error_sites = 0
    not_configured_sites = 0

    for site in sites:
        verification = verify_site_embedded_automation_packs(db, site_id=site.id, limit=500)
        invoke_packs = list_site_embedded_invoke_packs(db, site_id=site.id, limit=500)
        verification_rows = [
            row
            for row in verification.get("rows", [])
            if isinstance(row, dict)
            and (
                not normalized_connector_source
                or str(row.get("endpoint", {}).get("connector_source", "")).strip().lower() == normalized_connector_source
            )
        ]
        invoke_pack_rows = [
            row
            for row in invoke_packs.get("rows", [])
            if isinstance(row, dict)
            and (
                not normalized_connector_source
                or str(row.get("endpoint", {}).get("connector_source", "")).strip().lower() == normalized_connector_source
            )
        ]

        endpoint_count = len(verification_rows)
        if endpoint_count == 0:
            rows.append(
                {
                    "site_id": str(site.id),
                    "site_code": site.site_code,
                    "tenant_code": getattr(site, "tenant_code", "") or getattr(getattr(site, "tenant", None), "tenant_code", ""),
                    "status": "not_configured",
                    "endpoint_count": 0,
                    "ready_endpoint_count": 0,
                    "warning_endpoint_count": 0,
                    "error_endpoint_count": 0,
                    "plugin_endpoint_count": 0,
                    "playbook_endpoint_count": 0,
                    "approval_required_count": 0,
                    "connector_sources": [],
                    "vendor_preset_codes": [],
                    "recommended_action": (
                        f"Create at least one {normalized_connector_source} embedded endpoint for this site."
                        if normalized_connector_source
                        else "Create an embedded endpoint or vendor activation bundle for this site."
                    ),
                }
            )
            not_configured_sites += 1
            continue

        ready_endpoint_count = sum(
            1 for row in verification_rows if str(row.get("verification", {}).get("status", "")).lower() == "ok"
        )
        warning_endpoint_count = sum(
            1 for row in verification_rows if str(row.get("verification", {}).get("status", "")).lower() == "warning"
        )
        error_endpoint_count = sum(
            1 for row in verification_rows if str(row.get("verification", {}).get("status", "")).lower() == "error"
        )
        plugin_endpoint_count = sum(
            1 for row in verification_rows if str(row.get("endpoint", {}).get("workflow_type", "")) == "coworker_plugin"
        )
        playbook_endpoint_count = sum(
            1 for row in verification_rows if str(row.get("endpoint", {}).get("workflow_type", "")) == "soar_playbook"
        )
        approval_required_count = sum(
            1 for row in verification_rows if bool(row.get("verification", {}).get("effective_approval_required", False))
        )
        connector_sources = sorted(
            {
                str(row.get("endpoint", {}).get("connector_source", "")).strip().lower()
                for row in verification_rows
                if str(row.get("endpoint", {}).get("connector_source", "")).strip()
            }
        )
        vendor_preset_codes = sorted(
            {
                str(row.get("invoke_pack", {}).get("vendor_preset_code", "")).strip()
                for row in invoke_pack_rows
                if str(row.get("invoke_pack", {}).get("vendor_preset_code", "")).strip()
            }
        )

        status = "ready"
        if error_endpoint_count > 0:
            status = "error"
            error_sites += 1
        elif warning_endpoint_count > 0:
            status = "warning"
            warning_sites += 1
        else:
            ready_sites += 1

        recommended_action = "Maintain the current embedded automation posture."
        if status == "error":
            recommended_action = "Resolve playbook/plugin policy blockers before handing bundles to customer tools."
        elif status == "warning":
            recommended_action = "Tighten allowlists and approval requirements before switching this site to steady-state automation."

        rows.append(
            {
                "site_id": str(site.id),
                "site_code": site.site_code,
                "tenant_code": getattr(site, "tenant_code", "") or getattr(getattr(site, "tenant", None), "tenant_code", ""),
                "status": status,
                "endpoint_count": endpoint_count,
                "ready_endpoint_count": ready_endpoint_count,
                "warning_endpoint_count": warning_endpoint_count,
                "error_endpoint_count": error_endpoint_count,
                "plugin_endpoint_count": plugin_endpoint_count,
                "playbook_endpoint_count": playbook_endpoint_count,
                "approval_required_count": approval_required_count,
                "connector_sources": connector_sources,
                "vendor_preset_codes": vendor_preset_codes,
                "recommended_action": recommended_action,
            }
        )

        total_endpoints += endpoint_count
        total_ready_endpoints += ready_endpoint_count
        total_warning_endpoints += warning_endpoint_count
        total_error_endpoints += error_endpoint_count

    return {
        "status": "ok",
        "generated_at": _now().isoformat(),
        "connector_source": normalized_connector_source,
        "count": len(rows),
        "summary": {
            "total_sites": len(rows),
            "ready_sites": ready_sites,
            "warning_sites": warning_sites,
            "error_sites": error_sites,
            "not_configured_sites": not_configured_sites,
            "total_endpoints": total_endpoints,
            "ready_endpoints": total_ready_endpoints,
            "warning_endpoints": total_warning_endpoints,
            "error_endpoints": total_error_endpoints,
        },
        "rows": rows,
    }


def _persist_embedded_red_context(
    db: Session,
    *,
    site: Site,
    source: str,
    payload: dict[str, Any],
    event_kind: str,
) -> dict[str, Any]:
    message = str(payload.get("message") or payload.get("title") or payload.get("cve") or event_kind or "embedded finding")
    summary = f"Embedded finding from {source}: {message}"
    scan = RedScanRun(
        site_id=site.id,
        scan_type="embedded_finding",
        status="completed",
        findings_json=_as_json(payload),
        ai_summary=summary,
        created_at=_now(),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return {"scan_id": str(scan.id), "scan_type": scan.scan_type, "ai_summary": scan.ai_summary}


def _preprocess_payload(
    db: Session,
    *,
    site: Site,
    workflow_type: str,
    plugin_code: str,
    source: str,
    event_kind: str,
    payload: dict[str, Any],
    webhook_event_id: str,
) -> dict[str, Any]:
    if not payload:
        return {"status": "skipped", "reason": "empty_payload"}
    if _normalize_workflow_type(workflow_type) == "soar_playbook":
        ingested = ingest_integration_event(
            db,
            source=source,
            event_kind=event_kind,
            payload=payload,
            site_id=site.id,
            tenant_code="",
            site_code=site.site_code,
            webhook_event_id=webhook_event_id,
        )
        return {
            "status": "integration_ingested",
            "integration_event_id": ingested.get("integration_event_id", ""),
            "blue_event_id": ingested.get("blue_event_id", ""),
        }
    if plugin_code.startswith("red_"):
        context = _persist_embedded_red_context(db, site=site, source=source, payload=payload, event_kind=event_kind)
        return {"status": "red_context_persisted", **context}
    if plugin_code.startswith("blue_") or plugin_code.startswith("purple_"):
        ingested = ingest_integration_event(
            db,
            source=source,
            event_kind=event_kind,
            payload=payload,
            site_id=site.id,
            tenant_code="",
            site_code=site.site_code,
            webhook_event_id=webhook_event_id,
        )
        return {
            "status": "integration_ingested",
            "integration_event_id": ingested.get("integration_event_id", ""),
            "blue_event_id": ingested.get("blue_event_id", ""),
        }
    return {"status": "skipped", "reason": "unknown_plugin_category"}


def invoke_site_embedded_workflow(
    db: Session,
    *,
    site_code: str,
    endpoint_code: str,
    token: str,
    source: str = "",
    event_kind: str = "security_event",
    payload: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    dry_run: bool | None = None,
    actor: str = "embedded_client",
    webhook_event_id: str = "",
) -> dict[str, Any]:
    site = db.scalar(select(Site).where(Site.site_code == site_code.strip()))
    if not site:
        return {"status": "site_not_found", "site_code": site_code}
    endpoint = db.scalar(
        select(SiteEmbeddedWorkflowEndpoint).where(
            SiteEmbeddedWorkflowEndpoint.site_id == site.id,
            SiteEmbeddedWorkflowEndpoint.endpoint_code == endpoint_code.strip().lower(),
        )
    )
    if not endpoint:
        return {"status": "endpoint_not_found", "site_code": site.site_code, "endpoint_code": endpoint_code}
    if not endpoint.enabled:
        return {"status": "endpoint_disabled", "site_code": site.site_code, "endpoint_code": endpoint.endpoint_code}
    if not _verify_secret(token, endpoint.secret_hash):
        return {"status": "forbidden", "reason": "invalid_embed_token"}

    request_payload = payload or {}
    resolved_source = source.strip().lower() or endpoint.connector_source or "generic"
    resolved_event_kind = event_kind.strip().lower() or endpoint.default_event_kind or "security_event"
    resolved_dry_run = endpoint.dry_run_default if dry_run is None else bool(dry_run)
    resolved_workflow_type = _normalize_workflow_type(endpoint.workflow_type)
    merged_config = {**_safe_json_dict(endpoint.config_json), **(config or {})}
    guardrails = _guardrail_decision(
        endpoint,
        actor=actor,
        payload=request_payload,
        webhook_event_id=webhook_event_id,
    )
    playbook_guardrails = _playbook_guardrail_decision(
        endpoint,
        payload=request_payload,
        merged_config=merged_config,
    )
    if not bool(guardrails.get("blocked")) and bool(playbook_guardrails.get("blocked")):
        guardrails = playbook_guardrails

    request_summary = {
        "workflow_type": resolved_workflow_type,
        "source": resolved_source,
        "event_kind": resolved_event_kind,
        "payload_keys": sorted(list(request_payload.keys()))[:50],
        "actor": actor,
        "dry_run": resolved_dry_run,
        "guardrails": guardrails,
    }

    if bool(guardrails.get("blocked")):
        invocation = SiteEmbeddedWorkflowInvocation(
            endpoint_id=endpoint.id,
            site_id=site.id,
            endpoint_code=endpoint.endpoint_code,
            workflow_type=endpoint.workflow_type,
            plugin_code=endpoint.plugin_code,
            source=resolved_source,
            status="guardrail_blocked",
            dry_run=resolved_dry_run,
            request_summary_json=_as_json(request_summary),
            response_summary_json=_as_json({"guardrails": guardrails}),
            error_message=str(guardrails.get("reason", "guardrail_blocked")),
            created_at=_now(),
        )
        db.add(invocation)
        record_connector_event(
            db,
            connector_source=resolved_source or "embedded",
            event_type="delivery_attempt",
            status="guardrail_blocked",
            site_id=site.id,
            latency_ms=0,
            attempt=1,
            payload={
                "endpoint_code": endpoint.endpoint_code,
                "plugin_code": endpoint.plugin_code,
                "workflow_type": endpoint.workflow_type,
                "guardrail_reason": guardrails.get("reason", ""),
            },
            error_message=str(guardrails.get("reason", "")),
        )
        db.commit()
        db.refresh(invocation)
        return {
            "status": "guardrail_blocked",
            "reason": str(guardrails.get("reason", "guardrail_blocked")),
            "site_code": site.site_code,
            "endpoint": _endpoint_row(endpoint),
            "guardrails": guardrails,
            "invocation": _invocation_row(invocation),
        }

    preprocess = _preprocess_payload(
        db,
        site=site,
        workflow_type=resolved_workflow_type,
        plugin_code=endpoint.plugin_code,
        source=resolved_source,
        event_kind=resolved_event_kind,
        payload=request_payload,
        webhook_event_id=webhook_event_id,
    )

    try:
        if resolved_workflow_type == "soar_playbook":
            playbook_code = str(
                request_payload.get("playbook_code")
                or merged_config.get("playbook_code")
                or merged_config.get("default_playbook_code")
                or ""
            ).strip()
            workflow_result = execute_playbook(
                db,
                site_id=site.id,
                playbook_code=playbook_code,
                actor=actor,
                require_approval=bool(merged_config.get("require_playbook_approval", True)),
                dry_run=resolved_dry_run,
                params={
                    **request_payload,
                    "source": resolved_source,
                    "event_kind": resolved_event_kind,
                    "webhook_event_id": webhook_event_id,
                },
            )
            response_summary = {
                "preprocess": preprocess,
                "playbook_result": workflow_result,
            }
            result_status = str(workflow_result.get("status", "ok"))
        else:
            upsert_site_coworker_plugin_binding(
                db,
                site_id=site.id,
                plugin_code=endpoint.plugin_code,
                enabled=True,
                auto_run=False,
                schedule_interval_minutes=60,
                notify_channels=[],
                config=merged_config,
                owner=endpoint.owner or "embedded_workflow",
            )
            workflow_result = run_site_coworker_plugin(
                db,
                site_id=site.id,
                plugin_code=endpoint.plugin_code,
                dry_run=resolved_dry_run,
                force=True,
                actor=actor,
            )
            response_summary = {
                "preprocess": preprocess,
                "plugin_run": workflow_result.get("run", {}),
                "alert": workflow_result.get("alert", {}),
            }
            result_status = str(workflow_result.get("status", "ok"))

        invocation = SiteEmbeddedWorkflowInvocation(
            endpoint_id=endpoint.id,
            site_id=site.id,
            endpoint_code=endpoint.endpoint_code,
            workflow_type=endpoint.workflow_type,
            plugin_code=endpoint.plugin_code,
            source=resolved_source,
            status=result_status,
            dry_run=resolved_dry_run,
            request_summary_json=_as_json(request_summary),
            response_summary_json=_as_json(response_summary),
            error_message="",
            created_at=_now(),
        )
        db.add(invocation)
        connector_status = "success" if result_status in {"ok", "dry_run", "pending_approval", "applied"} else "failed"
        record_connector_event(
            db,
            connector_source=resolved_source or "embedded",
            event_type="delivery_attempt",
            status=connector_status,
            site_id=site.id,
            latency_ms=0,
            attempt=1,
            payload={
                "endpoint_code": endpoint.endpoint_code,
                "plugin_code": endpoint.plugin_code,
                "workflow_type": endpoint.workflow_type,
            },
        )
        db.commit()
        db.refresh(invocation)
        result_payload = {
            "status": result_status,
            "site_code": site.site_code,
            "endpoint": _endpoint_row(endpoint),
            "preprocess": preprocess,
            "invocation": _invocation_row(invocation),
        }
        if resolved_workflow_type == "soar_playbook":
            result_payload["playbook_result"] = workflow_result
        else:
            result_payload["plugin_run"] = workflow_result
        return result_payload
    except Exception as exc:
        invocation = SiteEmbeddedWorkflowInvocation(
            endpoint_id=endpoint.id,
            site_id=site.id,
            endpoint_code=endpoint.endpoint_code,
            workflow_type=endpoint.workflow_type,
            plugin_code=endpoint.plugin_code,
            source=resolved_source,
            status="error",
            dry_run=resolved_dry_run,
            request_summary_json=_as_json(request_summary),
            response_summary_json=_as_json({"preprocess": preprocess}),
            error_message=str(exc),
            created_at=_now(),
        )
        db.add(invocation)
        record_connector_event(
            db,
            connector_source=resolved_source or "embedded",
            event_type="delivery_attempt",
            status="failed",
            site_id=site.id,
            latency_ms=0,
            attempt=1,
            payload={
                "endpoint_code": endpoint.endpoint_code,
                "plugin_code": endpoint.plugin_code,
                "workflow_type": endpoint.workflow_type,
            },
            error_message=str(exc),
        )
        db.commit()
        db.refresh(invocation)
        return {
            "status": "error",
            "site_code": site.site_code,
            "endpoint": _endpoint_row(endpoint),
            "preprocess": preprocess,
            "invocation": _invocation_row(invocation),
            "error": str(exc),
        }
