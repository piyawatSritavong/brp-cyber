from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import BlueEventLog, Site, SoarExecutionConnectorResult, SoarPlaybook, SoarPlaybookExecution, Tenant, TenantPlaybookPolicy


BUILTIN_PLAYBOOKS: list[dict[str, Any]] = [
    {
        "playbook_code": "block-ip-and-waf-tighten",
        "title": "Block IP and Tighten WAF",
        "category": "containment",
        "description": "Block a hostile IP and raise WAF sensitivity for the affected surface.",
        "version": "1.0.0",
        "scope": "private",
        "steps": ["triage_event", "block_ip", "tighten_waf_rule", "notify_team"],
        "action_policy": {"max_duration_seconds": 300, "rollback_supported": True},
        "is_active": True,
    },
    {
        "playbook_code": "isolate-host-and-reset-session",
        "title": "Isolate Host and Reset Session",
        "category": "containment",
        "description": "Contain a compromised endpoint and clear active authentication sessions.",
        "version": "1.0.0",
        "scope": "private",
        "steps": ["triage_event", "isolate_host", "clear_session", "notify_team"],
        "action_policy": {"max_duration_seconds": 300, "rollback_supported": True},
        "is_active": True,
    },
    {
        "playbook_code": "notify-and-clear-session",
        "title": "Notify Team and Clear Session",
        "category": "identity_response",
        "description": "Notify responders and revoke suspicious authentication sessions.",
        "version": "1.0.0",
        "scope": "private",
        "steps": ["triage_event", "clear_session", "notify_team"],
        "action_policy": {"max_duration_seconds": 180, "rollback_supported": True},
        "is_active": True,
    },
]

MARKETPLACE_PACKS: list[dict[str, Any]] = [
    {
        "pack_code": "thai_identity_containment_pack",
        "title": "Thai Identity Containment Pack",
        "audience": "soc",
        "category": "identity_response",
        "description": "Starter bundle for suspicious login, phishing, and session abuse containment.",
        "scope": "community",
        "source_type": "community",
        "publisher_name": "BRP Community Labs",
        "trust_tier": "community_reviewed",
        "version": "1.2.0",
        "featured": True,
        "community_tags": ["identity", "phishing", "thai"],
        "supported_connectors": ["splunk", "generic"],
        "install_count": 124,
        "playbooks": [
            {
                "playbook_code": "notify-and-clear-session",
                "title": "Notify Team and Clear Session",
                "category": "identity_response",
                "description": "Notify responders and revoke suspicious authentication sessions.",
                "version": "1.0.0",
                "scope": "community",
                "steps": ["triage_event", "clear_session", "notify_team"],
                "action_policy": {"max_duration_seconds": 180, "rollback_supported": True},
                "is_active": True,
            },
            {
                "playbook_code": "identity-threat-hunt-and-reset",
                "title": "Identity Threat Hunt and Reset",
                "category": "identity_response",
                "description": "Reset risky sessions, increase MFA scrutiny, and notify identity responders.",
                "version": "1.0.0",
                "scope": "community",
                "steps": ["triage_event", "increase_mfa_scrutiny", "clear_session", "notify_team"],
                "action_policy": {"max_duration_seconds": 240, "rollback_supported": True},
                "is_active": True,
            },
        ],
    },
    {
        "pack_code": "cloud_edge_containment_pack",
        "title": "Cloud Edge Containment Pack",
        "audience": "secops",
        "category": "containment",
        "description": "WAF and edge response bundle for hostile traffic bursts and credential abuse.",
        "scope": "partner",
        "source_type": "partner",
        "publisher_name": "BRP Edge Alliance",
        "trust_tier": "verified_partner",
        "version": "2.1.0",
        "featured": True,
        "community_tags": ["edge", "waf", "credential-abuse"],
        "supported_connectors": ["cloudflare", "generic"],
        "install_count": 88,
        "playbooks": [
            {
                "playbook_code": "block-ip-and-waf-tighten",
                "title": "Block IP and Tighten WAF",
                "category": "containment",
                "description": "Block a hostile IP and raise WAF sensitivity for the affected surface.",
                "version": "1.0.0",
                "scope": "partner",
                "steps": ["triage_event", "block_ip", "tighten_waf_rule", "notify_team"],
                "action_policy": {"max_duration_seconds": 300, "rollback_supported": True},
                "is_active": True,
            },
            {
                "playbook_code": "rate-limit-and-cookie-reset",
                "title": "Rate Limit and Cookie Reset",
                "category": "containment",
                "description": "Throttle abusive traffic and reset suspicious browser sessions.",
                "version": "1.0.0",
                "scope": "partner",
                "steps": ["triage_event", "rate_limit_ip", "clear_session", "notify_team"],
                "action_policy": {"max_duration_seconds": 240, "rollback_supported": True},
                "is_active": True,
            },
        ],
    },
    {
        "pack_code": "endpoint_isolation_pack",
        "title": "Endpoint Isolation Pack",
        "audience": "mssp",
        "category": "containment",
        "description": "Partner-ready response bundle for endpoint isolation and credential revocation.",
        "scope": "partner",
        "source_type": "partner",
        "publisher_name": "BRP Endpoint Partners",
        "trust_tier": "verified_partner",
        "version": "1.4.0",
        "featured": False,
        "community_tags": ["endpoint", "edr", "isolation"],
        "supported_connectors": ["crowdstrike", "generic"],
        "install_count": 64,
        "playbooks": [
            {
                "playbook_code": "isolate-host-and-reset-session",
                "title": "Isolate Host and Reset Session",
                "category": "containment",
                "description": "Contain a compromised endpoint and clear active authentication sessions.",
                "version": "1.0.0",
                "scope": "partner",
                "steps": ["triage_event", "isolate_host", "clear_session", "notify_team"],
                "action_policy": {"max_duration_seconds": 300, "rollback_supported": True},
                "is_active": True,
            },
            {
                "playbook_code": "host-quarantine-and-edr-scan",
                "title": "Host Quarantine and EDR Scan",
                "category": "containment",
                "description": "Quarantine a risky workstation and trigger follow-up EDR scan instructions.",
                "version": "1.0.0",
                "scope": "partner",
                "steps": ["triage_event", "quarantine_host", "trigger_edr_scan", "notify_team"],
                "action_policy": {"max_duration_seconds": 420, "rollback_supported": True},
                "is_active": True,
            },
        ],
    },
    {
        "pack_code": "thai_web_abuse_response_pack",
        "title": "Thai Web Abuse Response Pack",
        "audience": "mssp",
        "category": "containment",
        "description": "Expanded response bundle for Thai web abuse, bot bursts, and WAF correlation.",
        "scope": "community",
        "source_type": "community",
        "publisher_name": "BRP Community Labs",
        "trust_tier": "community_reviewed",
        "version": "1.1.0",
        "featured": False,
        "community_tags": ["web", "bot", "thai"],
        "supported_connectors": ["cloudflare", "splunk", "generic"],
        "install_count": 53,
        "playbooks": [
            {
                "playbook_code": "web-abuse-block-and-observe",
                "title": "Web Abuse Block and Observe",
                "category": "containment",
                "description": "Block hostile IPs, tighten WAF rules, and observe edge telemetry.",
                "version": "1.0.0",
                "scope": "community",
                "steps": ["triage_event", "block_ip", "tighten_waf_rule", "observe_edge_signals", "notify_team"],
                "action_policy": {"max_duration_seconds": 300, "rollback_supported": True},
                "is_active": True,
            }
        ],
    },
    {
        "pack_code": "endpoint_partner_recovery_pack",
        "title": "Endpoint Partner Recovery Pack",
        "audience": "partner",
        "category": "containment",
        "description": "Partner-ready endpoint recovery bundle with quarantine, scan, and verification callbacks.",
        "scope": "partner",
        "source_type": "partner",
        "publisher_name": "BRP MSSP Alliance",
        "trust_tier": "verified_partner",
        "version": "2.0.1",
        "featured": True,
        "community_tags": ["endpoint", "verification", "callback"],
        "supported_connectors": ["crowdstrike", "generic"],
        "install_count": 42,
        "playbooks": [
            {
                "playbook_code": "partner-endpoint-quarantine-and-verify",
                "title": "Partner Endpoint Quarantine and Verify",
                "category": "containment",
                "description": "Quarantine host, trigger scan, and verify connector callback before closure.",
                "version": "1.0.0",
                "scope": "partner",
                "steps": ["triage_event", "quarantine_host", "trigger_edr_scan", "verify_callback", "notify_team"],
                "action_policy": {"max_duration_seconds": 420, "rollback_supported": True},
                "is_active": True,
            }
        ],
    },
    {
        "pack_code": "community_identity_hunt_pack",
        "title": "Community Identity Hunt Pack",
        "audience": "soc",
        "category": "identity_response",
        "description": "Community-maintained hunt and containment bundle for suspicious identity drift and MFA fatigue.",
        "scope": "community",
        "source_type": "community",
        "publisher_name": "Thai SecOps Guild",
        "trust_tier": "community_reviewed",
        "version": "1.0.0",
        "featured": False,
        "community_tags": ["identity", "hunt", "mfa"],
        "supported_connectors": ["splunk", "crowdstrike", "generic"],
        "install_count": 37,
        "playbooks": [
            {
                "playbook_code": "identity-hunt-and-mfa-hardening",
                "title": "Identity Hunt and MFA Hardening",
                "category": "identity_response",
                "description": "Launch identity hunt, harden MFA policy, and notify identity responders.",
                "version": "1.0.0",
                "scope": "community",
                "steps": ["triage_event", "hunt_identity_signals", "increase_mfa_scrutiny", "notify_team"],
                "action_policy": {"max_duration_seconds": 240, "rollback_supported": False},
                "is_active": True,
            }
        ],
    },
]

CONNECTOR_RESULT_CONTRACTS: list[dict[str, Any]] = [
    {
        "contract_code": "cloudflare_block_result_v1",
        "connector_source": "cloudflare",
        "playbook_codes": ["block-ip-and-waf-tighten", "web-abuse-block-and-observe"],
        "required_fields": ["result.blocked_ip", "result.rule_mode", "result.edge_status"],
        "success_statuses": ["applied", "confirmed"],
        "sample_payload": {"result": {"blocked_ip": "203.0.113.10", "rule_mode": "strict", "edge_status": "confirmed"}},
        "description": "Confirms Cloudflare block and WAF mode change after containment playbooks.",
    },
    {
        "contract_code": "crowdstrike_isolate_result_v1",
        "connector_source": "crowdstrike",
        "playbook_codes": ["isolate-host-and-reset-session", "partner-endpoint-quarantine-and-verify"],
        "required_fields": ["result.host_id", "result.isolation_status", "result.scan_status"],
        "success_statuses": ["applied", "confirmed"],
        "sample_payload": {"result": {"host_id": "host-001", "isolation_status": "isolated", "scan_status": "queued"}},
        "description": "Confirms endpoint isolation and follow-up scan dispatch from CrowdStrike-like connectors.",
    },
    {
        "contract_code": "splunk_session_clear_result_v1",
        "connector_source": "splunk",
        "playbook_codes": ["notify-and-clear-session"],
        "required_fields": ["result.search_job", "result.session_status", "result.notification_status"],
        "success_statuses": ["applied", "confirmed"],
        "sample_payload": {"result": {"search_job": "sid-001", "session_status": "cleared", "notification_status": "sent"}},
        "description": "Confirms SIEM-driven identity response completion and notification delivery.",
    },
    {
        "contract_code": "generic_response_result_v1",
        "connector_source": "generic",
        "playbook_codes": [],
        "required_fields": ["result.summary"],
        "success_statuses": ["applied", "confirmed"],
        "sample_payload": {"result": {"summary": "Connector applied the requested action."}},
        "description": "Fallback contract for generic webhook-driven responses.",
    },
]


def _as_json(value: dict[str, object] | list[object]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _safe_json_load(value: str | None) -> dict[str, object] | list[object]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
        if isinstance(payload, (dict, list)):
            return payload
    except Exception:
        pass
    return {}


def _safe_json_dict(value: str | None) -> dict[str, object]:
    payload = _safe_json_load(value)
    return payload if isinstance(payload, dict) else {}


def _safe_json_list(value: str | None) -> list[object]:
    payload = _safe_json_load(value)
    return payload if isinstance(payload, list) else []


def _playbook_row(playbook: SoarPlaybook) -> dict[str, object]:
    created_at = getattr(playbook, "created_at", None)
    updated_at = getattr(playbook, "updated_at", None)
    return {
        "playbook_id": str(playbook.id),
        "playbook_code": playbook.playbook_code,
        "title": playbook.title,
        "category": playbook.category,
        "description": playbook.description,
        "version": playbook.version,
        "scope": playbook.scope,
        "steps": _safe_json_load(playbook.steps_json),
        "action_policy": _safe_json_load(playbook.action_policy_json),
        "is_active": bool(playbook.is_active),
        "created_at": created_at.isoformat() if created_at else "",
        "updated_at": updated_at.isoformat() if updated_at else "",
    }


def _find_marketplace_pack(pack_code: str) -> dict[str, Any] | None:
    normalized = str(pack_code or "").strip().lower()
    for pack in MARKETPLACE_PACKS:
        if str(pack.get("pack_code", "")).strip().lower() == normalized:
            return pack
    return None


def _marketplace_pack_row(pack: dict[str, Any]) -> dict[str, object]:
    playbooks: list[dict[str, object]] = []
    for item in pack.get("playbooks", []):
        if not isinstance(item, dict):
            continue
        playbooks.append(
            {
                "playbook_code": str(item.get("playbook_code", "")),
                "title": str(item.get("title", "")),
                "category": str(item.get("category", "")),
                "scope": str(item.get("scope", "")),
            }
        )
    return {
        "pack_code": str(pack.get("pack_code", "")),
        "title": str(pack.get("title", "")),
        "audience": str(pack.get("audience", "")),
        "category": str(pack.get("category", "")),
        "description": str(pack.get("description", "")),
        "scope": str(pack.get("scope", "")),
        "source_type": str(pack.get("source_type", "community")),
        "publisher_name": str(pack.get("publisher_name", "BRP Community")),
        "trust_tier": str(pack.get("trust_tier", "community_reviewed")),
        "version": str(pack.get("version", "1.0.0")),
        "featured": bool(pack.get("featured", False)),
        "community_tags": [str(item) for item in pack.get("community_tags", []) if str(item).strip()],
        "supported_connectors": [str(item) for item in pack.get("supported_connectors", []) if str(item).strip()],
        "install_count": int(pack.get("install_count", 0) or 0),
        "playbook_count": len(playbooks),
        "playbooks": playbooks,
    }


def upsert_playbook(
    db: Session,
    *,
    playbook_code: str,
    title: str,
    category: str,
    description: str,
    version: str,
    scope: str,
    steps: list[str],
    action_policy: dict[str, Any],
    is_active: bool,
) -> dict[str, object]:
    existing = db.scalar(select(SoarPlaybook).where(SoarPlaybook.playbook_code == playbook_code))
    now = datetime.now(timezone.utc)
    if existing:
        existing.title = title
        existing.category = category
        existing.description = description
        existing.version = version
        existing.scope = scope
        existing.steps_json = _as_json(steps)
        existing.action_policy_json = _as_json(action_policy)
        existing.is_active = is_active
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return {"status": "updated", "playbook": _playbook_row(existing)}

    row = SoarPlaybook(
        playbook_code=playbook_code,
        title=title,
        category=category,
        description=description,
        version=version,
        scope=scope,
        steps_json=_as_json(steps),
        action_policy_json=_as_json(action_policy),
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "created", "playbook": _playbook_row(row)}


def ensure_builtin_playbooks(db: Session) -> dict[str, object]:
    created_or_updated: list[str] = []
    for row in BUILTIN_PLAYBOOKS:
        result = upsert_playbook(
            db,
            playbook_code=str(row["playbook_code"]),
            title=str(row["title"]),
            category=str(row["category"]),
            description=str(row["description"]),
            version=str(row["version"]),
            scope=str(row["scope"]),
            steps=list(row["steps"]),
            action_policy=dict(row["action_policy"]),
            is_active=bool(row["is_active"]),
        )
        created_or_updated.append(str(result.get("playbook", {}).get("playbook_code", row["playbook_code"])))
    return {"count": len(created_or_updated), "rows": created_or_updated}


def list_playbooks(
    db: Session,
    *,
    category: str = "",
    scope: str = "",
    active_only: bool = True,
    limit: int = 200,
) -> dict[str, object]:
    stmt = select(SoarPlaybook).order_by(desc(SoarPlaybook.updated_at)).limit(max(1, min(limit, 2000)))
    if category:
        stmt = stmt.where(SoarPlaybook.category == category)
    if scope:
        stmt = stmt.where(SoarPlaybook.scope == scope)
    if active_only:
        stmt = stmt.where(SoarPlaybook.is_active.is_(True))

    rows = db.scalars(stmt).all()
    return {"count": len(rows), "rows": [_playbook_row(row) for row in rows]}


def soar_marketplace_overview(db: Session, *, limit: int = 500) -> dict[str, object]:
    rows = db.scalars(
        select(SoarPlaybook).order_by(desc(SoarPlaybook.updated_at)).limit(max(1, min(limit, 5000)))
    ).all()
    scope_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    trust_tier_counts: dict[str, int] = {}
    for row in rows:
        scope_counts[row.scope] = scope_counts.get(row.scope, 0) + 1
        category_counts[row.category] = category_counts.get(row.category, 0) + 1
    for pack in MARKETPLACE_PACKS:
        source_type = str(pack.get("source_type", "community")).strip().lower() or "community"
        trust_tier = str(pack.get("trust_tier", "community_reviewed")).strip().lower() or "community_reviewed"
        source_counts[source_type] = source_counts.get(source_type, 0) + 1
        trust_tier_counts[trust_tier] = trust_tier_counts.get(trust_tier, 0) + 1

    return {
        "total_playbooks": len(rows),
        "active_playbooks": len([row for row in rows if row.is_active]),
        "scope_counts": scope_counts,
        "category_counts": category_counts,
        "marketplace_pack_count": len(MARKETPLACE_PACKS),
        "source_counts": source_counts,
        "trust_tier_counts": trust_tier_counts,
        "featured_pack_count": sum(1 for pack in MARKETPLACE_PACKS if bool(pack.get("featured", False))),
    }


def list_marketplace_packs(
    *,
    category: str = "",
    audience: str = "",
    scope: str = "",
    source_type: str = "",
    trust_tier: str = "",
    connector_source: str = "",
    search: str = "",
    featured_only: bool = False,
    limit: int = 200,
) -> dict[str, object]:
    normalized_search = search.strip().lower()
    normalized_scope = scope.strip().lower()
    normalized_source_type = source_type.strip().lower()
    normalized_trust_tier = trust_tier.strip().lower()
    normalized_connector = connector_source.strip().lower()
    rows: list[dict[str, object]] = []
    for pack in MARKETPLACE_PACKS:
        if category and str(pack.get("category", "")).strip().lower() != category.strip().lower():
            continue
        if audience and str(pack.get("audience", "")).strip().lower() != audience.strip().lower():
            continue
        if normalized_scope and str(pack.get("scope", "")).strip().lower() != normalized_scope:
            continue
        if normalized_source_type and str(pack.get("source_type", "")).strip().lower() != normalized_source_type:
            continue
        if normalized_trust_tier and str(pack.get("trust_tier", "")).strip().lower() != normalized_trust_tier:
            continue
        connectors = {str(item).strip().lower() for item in pack.get("supported_connectors", []) if str(item).strip()}
        if normalized_connector and normalized_connector not in connectors:
            continue
        if featured_only and not bool(pack.get("featured", False)):
            continue
        if normalized_search:
            haystack = " ".join(
                [
                    str(pack.get("pack_code", "")),
                    str(pack.get("title", "")),
                    str(pack.get("description", "")),
                    " ".join(str(item) for item in pack.get("community_tags", [])),
                    str(pack.get("publisher_name", "")),
                ]
            ).lower()
            if normalized_search not in haystack:
                continue
        rows.append(_marketplace_pack_row(pack))
    rows.sort(key=lambda row: (not bool(row.get("featured", False)), -int(row.get("install_count", 0)), str(row.get("title", ""))))
    capped = rows[: max(1, min(limit, 500))]
    return {
        "count": len(capped),
        "rows": capped,
        "available_filters": {
            "scope": sorted({str(pack.get("scope", "")).strip().lower() for pack in MARKETPLACE_PACKS if str(pack.get("scope", "")).strip()}),
            "source_type": sorted({str(pack.get("source_type", "")).strip().lower() for pack in MARKETPLACE_PACKS if str(pack.get("source_type", "")).strip()}),
            "trust_tier": sorted({str(pack.get("trust_tier", "")).strip().lower() for pack in MARKETPLACE_PACKS if str(pack.get("trust_tier", "")).strip()}),
            "connector_source": sorted(
                {
                    str(item).strip().lower()
                    for pack in MARKETPLACE_PACKS
                    for item in pack.get("supported_connectors", [])
                    if str(item).strip()
                }
            ),
        },
    }


def list_connector_result_contracts(*, connector_source: str = "", playbook_code: str = "") -> dict[str, object]:
    source_filter = connector_source.strip().lower()
    playbook_filter = playbook_code.strip().lower()
    rows: list[dict[str, object]] = []
    for row in CONNECTOR_RESULT_CONTRACTS:
        if source_filter and str(row.get("connector_source", "")).strip().lower() != source_filter:
            continue
        playbook_codes = [str(item).strip() for item in row.get("playbook_codes", []) if str(item).strip()]
        if playbook_filter and playbook_codes and playbook_filter not in {code.lower() for code in playbook_codes}:
            continue
        rows.append(
            {
                "contract_code": str(row.get("contract_code", "")),
                "connector_source": str(row.get("connector_source", "")),
                "playbook_codes": playbook_codes,
                "required_fields": [str(item) for item in row.get("required_fields", [])],
                "success_statuses": [str(item) for item in row.get("success_statuses", [])],
                "description": str(row.get("description", "")),
                "sample_payload": row.get("sample_payload", {}),
            }
        )
    return {"status": "ok", "count": len(rows), "rows": rows}


def _find_connector_result_contract(connector_source: str, contract_code: str) -> dict[str, Any] | None:
    normalized_source = connector_source.strip().lower()
    normalized_contract = contract_code.strip().lower()
    for row in CONNECTOR_RESULT_CONTRACTS:
        if str(row.get("connector_source", "")).strip().lower() != normalized_source:
            continue
        if str(row.get("contract_code", "")).strip().lower() != normalized_contract:
            continue
        return row
    return None


def _execution_row(row: SoarPlaybookExecution) -> dict[str, object]:
    return {
        "execution_id": str(row.id),
        "site_id": str(row.site_id),
        "playbook_id": str(row.playbook_id),
        "status": row.status,
        "requested_by": row.requested_by,
        "approved_by": row.approved_by,
        "approval_required": bool(row.approval_required),
        "run_params": _safe_json_load(row.run_params_json),
        "result": _safe_json_load(row.result_json),
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    }


def _connector_result_row(row: SoarExecutionConnectorResult) -> dict[str, object]:
    return {
        "connector_result_id": str(row.id),
        "site_id": str(row.site_id),
        "execution_id": str(row.execution_id),
        "connector_source": row.connector_source,
        "contract_code": row.contract_code,
        "external_action_ref": row.external_action_ref,
        "webhook_event_id": row.webhook_event_id,
        "status": row.status,
        "actor": row.actor,
        "payload": _safe_json_dict(row.payload_json),
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


def _policy_row(row: TenantPlaybookPolicy) -> dict[str, object]:
    return {
        "policy_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "policy_version": row.policy_version,
        "owner": row.owner,
        "require_approval_by_scope": _safe_json_dict(row.require_approval_by_scope_json),
        "require_approval_by_category": _safe_json_dict(row.require_approval_by_category_json),
        "delegated_approvers": _safe_json_list(row.delegated_approvers_json),
        "blocked_playbook_codes": _safe_json_list(row.blocked_playbook_codes_json),
        "allow_partner_scope": bool(row.allow_partner_scope),
        "auto_approve_dry_run": bool(row.auto_approve_dry_run),
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    }


def _default_policy(tenant_id: UUID) -> dict[str, object]:
    return {
        "policy_id": "",
        "tenant_id": str(tenant_id),
        "policy_version": "default",
        "owner": "system",
        "require_approval_by_scope": {"partner": True, "private": True},
        "require_approval_by_category": {"containment": True},
        "delegated_approvers": [],
        "blocked_playbook_codes": [],
        "allow_partner_scope": True,
        "auto_approve_dry_run": True,
        "created_at": "",
        "updated_at": "",
    }


def _get_policy_for_tenant(db: Session, tenant_id: UUID) -> dict[str, object]:
    row = db.scalar(select(TenantPlaybookPolicy).where(TenantPlaybookPolicy.tenant_id == tenant_id))
    if row:
        return _policy_row(row)
    return _default_policy(tenant_id)


def upsert_tenant_playbook_policy(
    db: Session,
    *,
    tenant_code: str,
    policy_version: str,
    owner: str,
    require_approval_by_scope: dict[str, bool],
    require_approval_by_category: dict[str, bool],
    delegated_approvers: list[str],
    blocked_playbook_codes: list[str],
    allow_partner_scope: bool,
    auto_approve_dry_run: bool,
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}
    row = db.scalar(select(TenantPlaybookPolicy).where(TenantPlaybookPolicy.tenant_id == tenant.id))
    now = datetime.now(timezone.utc)
    if row:
        row.policy_version = policy_version
        row.owner = owner
        row.require_approval_by_scope_json = _as_json(require_approval_by_scope)
        row.require_approval_by_category_json = _as_json(require_approval_by_category)
        row.delegated_approvers_json = _as_json(delegated_approvers)
        row.blocked_playbook_codes_json = _as_json(blocked_playbook_codes)
        row.allow_partner_scope = allow_partner_scope
        row.auto_approve_dry_run = auto_approve_dry_run
        row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"status": "updated", "policy": _policy_row(row)}

    created = TenantPlaybookPolicy(
        tenant_id=tenant.id,
        policy_version=policy_version,
        owner=owner,
        require_approval_by_scope_json=_as_json(require_approval_by_scope),
        require_approval_by_category_json=_as_json(require_approval_by_category),
        delegated_approvers_json=_as_json(delegated_approvers),
        blocked_playbook_codes_json=_as_json(blocked_playbook_codes),
        allow_partner_scope=allow_partner_scope,
        auto_approve_dry_run=auto_approve_dry_run,
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"status": "created", "policy": _policy_row(created)}


def get_tenant_playbook_policy(db: Session, tenant_code: str) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}
    return {"status": "ok", "policy": _get_policy_for_tenant(db, tenant.id)}


def _simulate_playbook_result(site: Site, playbook: SoarPlaybook, params: dict[str, Any], dry_run: bool) -> dict[str, object]:
    steps = _safe_json_load(playbook.steps_json)
    if not isinstance(steps, list):
        steps = []
    action_policy = _safe_json_load(playbook.action_policy_json)
    if not isinstance(action_policy, dict):
        action_policy = {}
    return {
        "site_code": site.site_code,
        "playbook_code": playbook.playbook_code,
        "dry_run": dry_run,
        "executed_steps": steps[:10],
        "policy": action_policy,
        "params": params,
        "summary": f"Playbook {playbook.playbook_code} simulated for {site.site_code}.",
    }


def _resolve_target_event(db: Session, *, site: Site, params: dict[str, Any]) -> BlueEventLog | None:
    event_id = params.get("event_id")
    if event_id:
        try:
            row = db.get(BlueEventLog, UUID(str(event_id)))
            if row is not None:
                return row
        except Exception:
            pass
    return db.scalar(
        select(BlueEventLog)
        .where(BlueEventLog.site_id == site.id)
        .order_by(desc(BlueEventLog.created_at))
        .limit(1)
    )


def _list_execution_connector_result_rows(db: Session, *, execution_id: UUID, limit: int = 20) -> list[SoarExecutionConnectorResult]:
    return db.scalars(
        select(SoarExecutionConnectorResult)
        .where(SoarExecutionConnectorResult.execution_id == execution_id)
        .order_by(desc(SoarExecutionConnectorResult.created_at))
        .limit(max(1, min(limit, 200)))
    ).all()


def _build_post_action_verification(
    db: Session,
    *,
    site: Site,
    playbook: SoarPlaybook,
    params: dict[str, Any],
    actor: str,
) -> dict[str, object]:
    target_event = _resolve_target_event(db, site=site, params=params)
    execution_id = params.get("execution_id")
    connector_results: list[dict[str, object]] = []
    if execution_id:
        try:
            connector_results = [_connector_result_row(row) for row in _list_execution_connector_result_rows(db, execution_id=UUID(str(execution_id)), limit=10)]
        except Exception:
            connector_results = []
    action_policy = _safe_json_dict(getattr(playbook, "action_policy_json", None))
    target_event_id = ""
    event_status = ""
    action_taken = ""
    if target_event is not None:
        target_event_id = str(target_event.id)
        event_status = str(target_event.status or "").strip()
        action_taken = str(target_event.action_taken or "").strip()
    action_reflected = bool(action_taken and playbook.playbook_code in [part.strip() for part in action_taken.split(",") if part.strip()])
    connector_callback_confirmed = any(str(row.get("status", "")).strip().lower() in {"applied", "confirmed"} for row in connector_results)
    verified = bool((target_event_id and event_status == "applied" and action_reflected) or connector_callback_confirmed)
    issues: list[str] = []
    if not target_event_id:
        issues.append("target_event_not_found")
    if target_event_id and event_status != "applied":
        issues.append(f"event_status={event_status or 'unknown'}")
    if target_event_id and not action_reflected:
        issues.append("playbook_action_not_reflected")
    recommendations: list[str] = []
    if "target_event_not_found" in issues:
        recommendations.append("bind a concrete event_id when dispatching the playbook")
    if "playbook_action_not_reflected" in issues:
        recommendations.append("confirm connector result callback or attach post-action adapter feedback")
    if any(item.startswith("event_status=") for item in issues):
        recommendations.append("re-run verification after connector side-effect is confirmed")
    if not connector_callback_confirmed:
        recommendations.append("attach connector-native callback contract if vendor confirmation is available")
    return {
        "status": "verified" if verified else "warning",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "verified_by": actor,
        "target_event_id": target_event_id,
        "event_status": event_status,
        "action_taken": action_taken,
        "action_reflected": action_reflected,
        "connector_callback_confirmed": connector_callback_confirmed,
        "connector_results": connector_results,
        "rollback_supported": bool(action_policy.get("rollback_supported", False)),
        "issues": issues,
        "recommendations": recommendations,
    }


def _attach_post_action_verification(
    db: Session,
    *,
    row: SoarPlaybookExecution,
    site: Site,
    playbook: SoarPlaybook,
    params: dict[str, Any],
    actor: str,
) -> dict[str, object]:
    current_result = _safe_json_load(row.result_json)
    if not isinstance(current_result, dict):
        current_result = {}
    verification = _build_post_action_verification(db, site=site, playbook=playbook, params=params, actor=actor)
    current_result["post_action_verification"] = verification
    row.result_json = _as_json(current_result)
    return verification


def install_marketplace_pack(
    db: Session,
    *,
    pack_code: str,
    actor: str = "marketplace_installer",
    scope_override: str = "",
) -> dict[str, object]:
    pack = _find_marketplace_pack(pack_code)
    if pack is None:
        return {"status": "pack_not_found", "pack_code": pack_code}
    effective_scope = scope_override.strip() or str(pack.get("scope", "community"))
    installed_playbooks: list[dict[str, object]] = []
    for item in pack.get("playbooks", []):
        if not isinstance(item, dict):
            continue
        result = upsert_playbook(
            db,
            playbook_code=str(item.get("playbook_code", "")),
            title=str(item.get("title", "")),
            category=str(item.get("category", "response")),
            description=str(item.get("description", "")),
            version=str(item.get("version", "1.0.0")),
            scope=effective_scope,
            steps=[str(step) for step in item.get("steps", []) if str(step).strip()],
            action_policy=dict(item.get("action_policy", {})),
            is_active=bool(item.get("is_active", True)),
        )
        installed_playbooks.append(result.get("playbook", {}))
    return {
        "status": "installed",
        "pack": _marketplace_pack_row({**pack, "scope": effective_scope}),
        "installed_count": len(installed_playbooks),
        "installed_playbooks": installed_playbooks,
        "actor": actor,
    }


def execute_playbook(
    db: Session,
    *,
    site_id: UUID,
    playbook_code: str,
    actor: str,
    require_approval: bool,
    dry_run: bool,
    params: dict[str, Any],
) -> dict[str, object]:
    ensure_builtin_playbooks(db)
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    playbook = db.scalar(select(SoarPlaybook).where(SoarPlaybook.playbook_code == playbook_code))
    if not playbook or not playbook.is_active:
        return {"status": "playbook_not_found", "playbook_code": playbook_code}

    policy = _get_policy_for_tenant(db, site.tenant_id)
    blocked_codes = {str(code).strip() for code in policy.get("blocked_playbook_codes", []) if str(code).strip()}
    if playbook.playbook_code in blocked_codes:
        return {
            "status": "blocked_by_policy",
            "reason": f"playbook_code={playbook.playbook_code} blocked for tenant policy",
            "policy": policy,
        }
    if playbook.scope == "partner" and not bool(policy.get("allow_partner_scope", True)):
        return {
            "status": "blocked_by_policy",
            "reason": "partner_scope_not_allowed",
            "policy": policy,
        }

    scope_map = policy.get("require_approval_by_scope", {})
    if not isinstance(scope_map, dict):
        scope_map = {}
    category_map = policy.get("require_approval_by_category", {})
    if not isinstance(category_map, dict):
        category_map = {}
    scope_approval = bool(scope_map.get(playbook.scope, False))
    category_approval = bool(category_map.get(playbook.category, False))
    approval_required = bool(require_approval or scope_approval or category_approval)
    if dry_run and bool(policy.get("auto_approve_dry_run", True)):
        approval_required = False

    result = _simulate_playbook_result(site, playbook, params, dry_run)
    connector_source = str(params.get("connector_source", "generic") or "generic").strip().lower()
    result["connector_result_contracts"] = list_connector_result_contracts(
        connector_source=connector_source,
        playbook_code=playbook.playbook_code,
    ).get("rows", [])
    if dry_run:
        status = "dry_run"
    elif approval_required:
        status = "pending_approval"
    else:
        status = "applied"

    row = SoarPlaybookExecution(
        site_id=site.id,
        playbook_id=playbook.id,
        status=status,
        requested_by=actor,
        approved_by="",
        approval_required=approval_required,
        run_params_json=_as_json(params),
        result_json=_as_json(result),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(row)

    if status == "applied":
        candidate_event = db.scalar(
            select(BlueEventLog)
            .where(BlueEventLog.site_id == site.id, BlueEventLog.status == "open")
            .order_by(desc(BlueEventLog.created_at))
            .limit(1)
        )
        if candidate_event:
            candidate_event.status = "applied"
            candidate_event.action_taken = playbook.playbook_code
        result["post_action_verification"] = _build_post_action_verification(
            db,
            site=site,
            playbook=playbook,
            params=params,
            actor=actor,
        )

    db.commit()
    db.refresh(row)
    return {
        "status": status,
        "execution": _execution_row(row),
        "playbook": _playbook_row(playbook),
        "policy_decision": {
            "approval_required": approval_required,
            "scope_approval": scope_approval,
            "category_approval": category_approval,
        },
    }


def approve_playbook_execution(
    db: Session,
    *,
    execution_id: UUID,
    approve: bool,
    approver: str,
    note: str,
) -> dict[str, object]:
    row = db.get(SoarPlaybookExecution, execution_id)
    if not row:
        return {"status": "not_found"}
    if row.status not in {"pending_approval"}:
        return {"status": "no_op", "execution": _execution_row(row)}

    site = db.get(Site, row.site_id)
    if not site:
        return {"status": "site_not_found", "execution": _execution_row(row)}
    policy = _get_policy_for_tenant(db, site.tenant_id)
    delegated = {str(actor).strip().lower() for actor in policy.get("delegated_approvers", []) if str(actor).strip()}
    allowed = delegated | {"security_lead", "ciso_ai"}
    if delegated and approver.strip().lower() not in allowed:
        return {
            "status": "approver_not_authorized",
            "required_approvers": sorted(delegated),
            "execution": _execution_row(row),
        }

    row.status = "applied" if approve else "rejected"
    row.approved_by = approver
    current_result = _safe_json_load(row.result_json)
    if not isinstance(current_result, dict):
        current_result = {}
    current_result["approval_note"] = note
    current_result["approved"] = bool(approve)
    if approve:
        params = _safe_json_load(row.run_params_json)
        if not isinstance(params, dict):
            params = {}
        playbook_obj = row.playbook if getattr(row, "playbook", None) is not None else db.get(SoarPlaybook, row.playbook_id)
        target_event = None
        event_id = params.get("event_id")
        if event_id:
            try:
                target_event = db.get(BlueEventLog, UUID(str(event_id)))
            except Exception:
                target_event = None
        if target_event is None:
            target_event = db.scalar(
                select(BlueEventLog)
                .where(BlueEventLog.site_id == site.id, BlueEventLog.status == "open")
                .order_by(desc(BlueEventLog.created_at))
                .limit(1)
            )
        if target_event:
            target_event.status = "applied"
            action_taken = str(target_event.action_taken or "").strip()
            if not action_taken:
                target_event.action_taken = playbook_obj.playbook_code if playbook_obj is not None else ""
            elif playbook_obj is not None and playbook_obj.playbook_code not in action_taken.split(","):
                target_event.action_taken = f"{action_taken},{playbook_obj.playbook_code}"[:64]
        if playbook_obj is not None:
            current_result["post_action_verification"] = _build_post_action_verification(
                db,
                site=site,
                playbook=playbook_obj,
                params=params,
                actor=approver,
            )
    row.result_json = _as_json(current_result)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return {"status": row.status, "execution": _execution_row(row)}


def verify_playbook_execution(
    db: Session,
    *,
    execution_id: UUID,
    actor: str = "soar_verifier",
) -> dict[str, object]:
    row = db.get(SoarPlaybookExecution, execution_id)
    if not row:
        return {"status": "not_found"}
    site = db.get(Site, row.site_id)
    if not site:
        return {"status": "site_not_found", "execution": _execution_row(row)}
    playbook = row.playbook if getattr(row, "playbook", None) is not None else db.get(SoarPlaybook, row.playbook_id)
    if playbook is None:
        return {"status": "playbook_not_found", "execution": _execution_row(row)}
    params = _safe_json_load(row.run_params_json)
    if not isinstance(params, dict):
        params = {}
    params["execution_id"] = str(row.id)
    verification = _attach_post_action_verification(db, row=row, site=site, playbook=playbook, params=params, actor=actor)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return {"status": str(verification.get("status", "warning")), "execution": _execution_row(row), "verification": verification}


def ingest_playbook_connector_result(
    db: Session,
    *,
    execution_id: UUID,
    site_id: UUID | None = None,
    connector_source: str,
    contract_code: str,
    external_action_ref: str = "",
    webhook_event_id: str = "",
    status: str = "received",
    payload: dict[str, Any] | None = None,
    actor: str = "connector_callback",
) -> dict[str, object]:
    execution = db.get(SoarPlaybookExecution, execution_id)
    if not execution:
        return {"status": "execution_not_found"}
    if site_id and execution.site_id != site_id:
        return {"status": "site_mismatch", "execution": _execution_row(execution)}
    contract = _find_connector_result_contract(connector_source, contract_code)
    if contract is None:
        return {"status": "contract_not_found", "connector_source": connector_source, "contract_code": contract_code}
    row = SoarExecutionConnectorResult(
        site_id=execution.site_id,
        execution_id=execution.id,
        connector_source=connector_source,
        contract_code=contract_code,
        external_action_ref=external_action_ref[:255],
        webhook_event_id=webhook_event_id[:255],
        status=str(status or "received")[:32],
        actor=str(actor or "connector_callback")[:128],
        payload_json=_as_json(payload or {}),
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    current_result = _safe_json_dict(execution.result_json)
    current_result["connector_result_contract"] = {
        "connector_source": connector_source,
        "contract_code": contract_code,
        "external_action_ref": external_action_ref,
        "status": row.status,
    }
    current_result["connector_result_callback"] = {
        "webhook_event_id": webhook_event_id,
        "received_at": row.created_at.isoformat(),
        "payload": payload or {},
    }
    execution.result_json = _as_json(current_result)
    if row.status.lower() in {item.lower() for item in contract.get("success_statuses", [])} and execution.status in {"pending_approval", "applied", "dry_run"}:
        execution.status = "verified"
    execution.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    db.refresh(execution)
    return {
        "status": "ok",
        "execution": _execution_row(execution),
        "connector_result": _connector_result_row(row),
        "contract": {
            "contract_code": contract["contract_code"],
            "connector_source": contract["connector_source"],
            "required_fields": contract["required_fields"],
            "success_statuses": contract["success_statuses"],
        },
    }


def list_playbook_connector_results(
    db: Session,
    *,
    execution_id: UUID,
    site_id: UUID | None = None,
    limit: int = 20,
) -> dict[str, object]:
    execution = db.get(SoarPlaybookExecution, execution_id)
    if not execution:
        return {"status": "execution_not_found"}
    if site_id and execution.site_id != site_id:
        return {"status": "site_mismatch", "execution": _execution_row(execution)}
    rows = _list_execution_connector_result_rows(db, execution_id=execution.id, limit=limit)
    return {"status": "ok", "count": len(rows), "rows": [_connector_result_row(row) for row in rows], "execution": _execution_row(execution)}


def list_playbook_executions(
    db: Session,
    *,
    site_id: UUID | None = None,
    status: str = "",
    limit: int = 200,
) -> dict[str, object]:
    stmt = select(SoarPlaybookExecution).order_by(desc(SoarPlaybookExecution.updated_at)).limit(max(1, min(limit, 2000)))
    if site_id:
        stmt = stmt.where(SoarPlaybookExecution.site_id == site_id)
    if status:
        stmt = stmt.where(SoarPlaybookExecution.status == status)
    rows = db.scalars(stmt).all()
    return {"count": len(rows), "rows": [_execution_row(row) for row in rows]}
