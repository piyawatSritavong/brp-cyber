from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import BlueEventLog, Site, SoarPlaybook, SoarPlaybookExecution, Tenant, TenantPlaybookPolicy


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
        "created_at": playbook.created_at.isoformat() if playbook.created_at else "",
        "updated_at": playbook.updated_at.isoformat() if playbook.updated_at else "",
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
    for row in rows:
        scope_counts[row.scope] = scope_counts.get(row.scope, 0) + 1
        category_counts[row.category] = category_counts.get(row.category, 0) + 1

    return {
        "total_playbooks": len(rows),
        "active_playbooks": len([row for row in rows if row.is_active]),
        "scope_counts": scope_counts,
        "category_counts": category_counts,
    }


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
    row.result_json = _as_json(current_result)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return {"status": row.status, "execution": _execution_row(row)}


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
