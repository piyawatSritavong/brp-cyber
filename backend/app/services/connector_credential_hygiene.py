from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import ConnectorCredentialHygienePolicy, ConnectorCredentialHygieneRun, Tenant
from app.db.session import SessionLocal
from app.services.action_center import dispatch_manual_alert
from app.services.connector_credential_vault import auto_rotate_due_credentials, evaluate_connector_credential_hygiene


def _as_json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _safe_json_load(value: str | None) -> dict[str, object]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _normalize_source(connector_source: str) -> str:
    source = (connector_source or "").strip().lower()
    return source if source else "*"


def _default_policy(tenant_id: str, connector_source: str) -> dict[str, object]:
    source = _normalize_source(connector_source)
    return {
        "policy_id": "",
        "tenant_id": tenant_id,
        "connector_source": source,
        "warning_days": 7,
        "max_rotate_per_run": 20,
        "auto_apply": False,
        "route_alert": True,
        "schedule_interval_minutes": 60,
        "enabled": True,
        "owner": "system",
        "created_at": "",
        "updated_at": "",
    }


def _policy_row(row: ConnectorCredentialHygienePolicy) -> dict[str, object]:
    return {
        "policy_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "connector_source": row.connector_source,
        "warning_days": int(row.warning_days),
        "max_rotate_per_run": int(row.max_rotate_per_run),
        "auto_apply": bool(row.auto_apply),
        "route_alert": bool(row.route_alert),
        "schedule_interval_minutes": int(row.schedule_interval_minutes),
        "enabled": bool(row.enabled),
        "owner": row.owner,
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    }


def _run_row(row: ConnectorCredentialHygieneRun) -> dict[str, object]:
    return {
        "run_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "connector_source": row.connector_source,
        "dry_run": bool(row.dry_run),
        "status": row.status,
        "candidate_count": int(row.candidate_count),
        "selected_count": int(row.selected_count),
        "planned_count": int(row.planned_count),
        "executed_count": int(row.executed_count),
        "failed_count": int(row.failed_count),
        "risk_score": int(row.risk_score),
        "risk_tier": row.risk_tier,
        "alert_routed": bool(row.alert_routed),
        "details": _safe_json_load(row.details_json),
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


def _resolve_policy(db: Session, tenant_id, connector_source: str) -> ConnectorCredentialHygienePolicy | None:
    source = _normalize_source(connector_source)
    row = db.scalar(
        select(ConnectorCredentialHygienePolicy).where(
            ConnectorCredentialHygienePolicy.tenant_id == tenant_id,
            ConnectorCredentialHygienePolicy.connector_source == source,
        )
    )
    if row:
        return row
    if source != "*":
        row = db.scalar(
            select(ConnectorCredentialHygienePolicy).where(
                ConnectorCredentialHygienePolicy.tenant_id == tenant_id,
                ConnectorCredentialHygienePolicy.connector_source == "*",
            )
        )
    return row


def upsert_credential_hygiene_policy(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str = "*",
    warning_days: int = 7,
    max_rotate_per_run: int = 20,
    auto_apply: bool = False,
    route_alert: bool = True,
    schedule_interval_minutes: int = 60,
    enabled: bool = True,
    owner: str = "security",
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}

    source = _normalize_source(connector_source)
    now = datetime.now(timezone.utc)
    row = db.scalar(
        select(ConnectorCredentialHygienePolicy).where(
            ConnectorCredentialHygienePolicy.tenant_id == tenant.id,
            ConnectorCredentialHygienePolicy.connector_source == source,
        )
    )
    if row:
        row.warning_days = max(1, min(int(warning_days), 90))
        row.max_rotate_per_run = max(1, min(int(max_rotate_per_run), 200))
        row.auto_apply = bool(auto_apply)
        row.route_alert = bool(route_alert)
        row.schedule_interval_minutes = max(5, min(int(schedule_interval_minutes), 24 * 60))
        row.enabled = bool(enabled)
        row.owner = owner[:64] or "security"
        row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"status": "updated", "policy": _policy_row(row)}

    created = ConnectorCredentialHygienePolicy(
        tenant_id=tenant.id,
        connector_source=source,
        warning_days=max(1, min(int(warning_days), 90)),
        max_rotate_per_run=max(1, min(int(max_rotate_per_run), 200)),
        auto_apply=bool(auto_apply),
        route_alert=bool(route_alert),
        schedule_interval_minutes=max(5, min(int(schedule_interval_minutes), 24 * 60)),
        enabled=bool(enabled),
        owner=owner[:64] or "security",
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"status": "created", "policy": _policy_row(created)}


def get_credential_hygiene_policy(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str = "*",
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}
    row = _resolve_policy(db, tenant.id, connector_source)
    if row:
        return {"status": "ok", "policy": _policy_row(row)}
    return {"status": "ok", "policy": _default_policy(str(tenant.id), connector_source)}


def run_credential_hygiene_for_tenant(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str = "*",
    dry_run: bool | None = None,
    actor: str = "credential_guard_ai",
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}
    policy_result = get_credential_hygiene_policy(db, tenant_code=tenant_code, connector_source=connector_source)
    policy = policy_result.get("policy", {})
    effective_dry_run = bool(dry_run) if dry_run is not None else (not bool(policy.get("auto_apply", False)))

    execution = auto_rotate_due_credentials(
        db,
        tenant_code=tenant_code,
        connector_source=connector_source,
        warning_days=int(policy.get("warning_days", 7) or 7),
        max_rotate=int(policy.get("max_rotate_per_run", 20) or 20),
        dry_run=effective_dry_run,
        actor=actor,
    )
    hygiene = evaluate_connector_credential_hygiene(
        db,
        tenant_code=tenant_code,
        connector_source=connector_source,
        warning_days=int(policy.get("warning_days", 7) or 7),
        limit=2000,
    )

    alert = {}
    alert_routed = False
    should_route = bool(policy.get("route_alert", True)) and (
        int(execution.get("candidate_count", 0)) > 0
        or int(execution.get("executed_count", 0)) > 0
        or int(execution.get("failed_count", 0)) > 0
    )
    if should_route:
        risk_tier = str((hygiene.get("risk", {}) or {}).get("risk_tier", "medium"))
        severity = "critical" if risk_tier == "critical" else ("high" if risk_tier in {"high", "medium"} else "medium")
        alert = dispatch_manual_alert(
            db,
            tenant_code=tenant_code,
            site_code="",
            source="credential_hygiene_scheduler",
            severity=severity,
            title="Credential Hygiene Scheduled Run",
            message=(
                f"tenant={tenant_code} source={connector_source} dry_run={effective_dry_run} "
                f"candidate={execution.get('candidate_count', 0)} executed={execution.get('executed_count', 0)} "
                f"failed={execution.get('failed_count', 0)}"
            ),
            payload={
                "tenant_code": tenant_code,
                "connector_source": connector_source,
                "dry_run": effective_dry_run,
                "candidate_count": execution.get("candidate_count", 0),
                "executed_count": execution.get("executed_count", 0),
                "failed_count": execution.get("failed_count", 0),
                "risk": hygiene.get("risk", {}),
            },
        )
        alert_routed = bool(alert.get("status") == "ok")

    run = ConnectorCredentialHygieneRun(
        tenant_id=tenant.id,
        connector_source=_normalize_source(connector_source),
        dry_run=effective_dry_run,
        status=str(execution.get("status", "ok")),
        candidate_count=int(execution.get("candidate_count", 0)),
        selected_count=int(execution.get("selected_count", 0)),
        planned_count=int(execution.get("planned_count", 0)),
        executed_count=int(execution.get("executed_count", 0)),
        failed_count=int(execution.get("failed_count", 0)),
        risk_score=int((hygiene.get("risk", {}) or {}).get("risk_score", 0)),
        risk_tier=str((hygiene.get("risk", {}) or {}).get("risk_tier", "low")),
        alert_routed=alert_routed,
        details_json=_as_json(
            {
                "execution": {
                    "candidate_count": execution.get("candidate_count", 0),
                    "selected_count": execution.get("selected_count", 0),
                    "planned_count": execution.get("planned_count", 0),
                    "executed_count": execution.get("executed_count", 0),
                    "failed_count": execution.get("failed_count", 0),
                },
                "hygiene_summary": hygiene.get("summary", {}),
                "alert": alert,
            }
        ),
        created_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return {
        "status": "ok",
        "tenant_id": str(tenant.id),
        "tenant_code": tenant_code,
        "policy": policy,
        "execution": execution,
        "hygiene": hygiene,
        "alert": alert,
        "run": _run_row(run),
    }


def list_credential_hygiene_runs(
    db: Session,
    *,
    tenant_code: str = "",
    limit: int = 200,
) -> dict[str, object]:
    stmt = (
        select(ConnectorCredentialHygieneRun)
        .order_by(desc(ConnectorCredentialHygieneRun.created_at))
        .limit(max(1, min(limit, 2000)))
    )
    if tenant_code:
        tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
        if not tenant:
            return {"count": 0, "rows": []}
        stmt = stmt.where(ConnectorCredentialHygieneRun.tenant_id == tenant.id)
    rows = db.scalars(stmt).all()
    return {"count": len(rows), "rows": [_run_row(row) for row in rows]}


def run_credential_hygiene_scheduler(
    db: Session,
    *,
    limit: int = 200,
    actor: str = "credential_guard_ai",
    dry_run_override: bool | None = None,
) -> dict[str, object]:
    policies = db.scalars(
        select(ConnectorCredentialHygienePolicy)
        .where(ConnectorCredentialHygienePolicy.enabled.is_(True))
        .order_by(desc(ConnectorCredentialHygienePolicy.updated_at))
        .limit(max(1, min(limit, 500)))
    ).all()
    now = datetime.now(timezone.utc)
    executed: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []

    for policy in policies:
        tenant = db.get(Tenant, policy.tenant_id)
        if not tenant:
            skipped.append({"tenant_id": str(policy.tenant_id), "connector_source": policy.connector_source, "reason": "tenant_not_found"})
            continue
        last_run = db.scalar(
            select(ConnectorCredentialHygieneRun)
            .where(
                ConnectorCredentialHygieneRun.tenant_id == policy.tenant_id,
                ConnectorCredentialHygieneRun.connector_source == policy.connector_source,
            )
            .order_by(desc(ConnectorCredentialHygieneRun.created_at))
            .limit(1)
        )
        interval_seconds = max(5, int(policy.schedule_interval_minutes) * 60)
        if last_run and last_run.created_at and (now - last_run.created_at).total_seconds() < interval_seconds:
            skipped.append(
                {
                    "tenant_code": tenant.tenant_code,
                    "connector_source": policy.connector_source,
                    "reason": "interval_not_elapsed",
                }
            )
            continue
        run_result = run_credential_hygiene_for_tenant(
            db,
            tenant_code=tenant.tenant_code,
            connector_source=policy.connector_source,
            dry_run=dry_run_override,
            actor=actor,
        )
        executed.append(
            {
                "tenant_code": tenant.tenant_code,
                "connector_source": policy.connector_source,
                "status": run_result.get("status", "unknown"),
                "run_id": ((run_result.get("run", {}) or {}).get("run_id", "")),
                "risk_tier": ((run_result.get("run", {}) or {}).get("risk_tier", "")),
            }
        )

    return {
        "timestamp": now.isoformat(),
        "scheduled_policy_count": len(policies),
        "executed_count": len(executed),
        "skipped_count": len(skipped),
        "executed": executed,
        "skipped": skipped,
    }


def process_credential_hygiene_schedules(
    limit: int = 200,
    *,
    actor: str = "credential_guard_ai",
    dry_run_override: bool | None = None,
) -> dict[str, object]:
    with SessionLocal() as db:
        return run_credential_hygiene_scheduler(
            db,
            limit=limit,
            actor=actor,
            dry_run_override=dry_run_override,
        )
