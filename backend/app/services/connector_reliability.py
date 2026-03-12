from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    ConnectorDeliveryEvent,
    ConnectorReliabilityPolicy,
    ConnectorReliabilityRun,
    Tenant,
)
from app.db.session import SessionLocal
from app.services.action_center import dispatch_manual_alert
from app.services.connector_observability import record_connector_event


def _as_json(value: dict[str, Any] | list[dict[str, Any]]) -> str:
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


def _to_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _risk_from_state(*, unresolved_backlog: int, failed_replays: int, replay_success_rate: float) -> tuple[int, str, str]:
    pressure = max(0.0, 1.0 - replay_success_rate)
    score = min(100, int((unresolved_backlog * 6) + (failed_replays * 14) + (pressure * 35)))
    if score >= 80:
        tier = "critical"
        recommendation = "trigger_connector_owner_escalation"
    elif score >= 60:
        tier = "high"
        recommendation = "tighten_replay_policy_and_validate_connector_health"
    elif score >= 35:
        tier = "medium"
        recommendation = "increase_replay_frequency_and_monitor_dlq"
    else:
        tier = "low"
        recommendation = "maintain_current_reliability_policy"
    return score, tier, recommendation


def _policy_row(row: ConnectorReliabilityPolicy) -> dict[str, Any]:
    return {
        "policy_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "connector_source": row.connector_source,
        "max_replay_per_run": row.max_replay_per_run,
        "max_attempts": row.max_attempts,
        "auto_replay_enabled": bool(row.auto_replay_enabled),
        "route_alert": bool(row.route_alert),
        "schedule_interval_minutes": row.schedule_interval_minutes,
        "enabled": bool(row.enabled),
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _default_policy(tenant_id: str, connector_source: str) -> dict[str, Any]:
    return {
        "policy_id": "",
        "tenant_id": tenant_id,
        "connector_source": connector_source,
        "max_replay_per_run": 25,
        "max_attempts": 3,
        "auto_replay_enabled": False,
        "route_alert": True,
        "schedule_interval_minutes": 60,
        "enabled": True,
        "owner": "system",
        "created_at": "",
        "updated_at": "",
    }


def _run_row(row: ConnectorReliabilityRun) -> dict[str, Any]:
    return {
        "run_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "connector_source": row.connector_source,
        "dry_run": bool(row.dry_run),
        "status": row.status,
        "backlog_count": row.backlog_count,
        "selected_count": row.selected_count,
        "replayed_count": row.replayed_count,
        "failed_count": row.failed_count,
        "skipped_count": row.skipped_count,
        "risk_score": row.risk_score,
        "risk_tier": row.risk_tier,
        "alert_routed": bool(row.alert_routed),
        "details": _safe_json_dict(row.details_json),
        "created_at": _safe_iso(row.created_at),
    }


def upsert_connector_reliability_policy(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str,
    max_replay_per_run: int,
    max_attempts: int,
    auto_replay_enabled: bool,
    route_alert: bool,
    schedule_interval_minutes: int,
    enabled: bool,
    owner: str,
) -> dict[str, Any]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}

    source = connector_source.strip().lower() or "*"
    row = db.scalar(
        select(ConnectorReliabilityPolicy).where(
            ConnectorReliabilityPolicy.tenant_id == tenant.id,
            ConnectorReliabilityPolicy.connector_source == source,
        )
    )
    now = datetime.now(timezone.utc)
    if row:
        row.max_replay_per_run = max(1, int(max_replay_per_run))
        row.max_attempts = max(1, int(max_attempts))
        row.auto_replay_enabled = bool(auto_replay_enabled)
        row.route_alert = bool(route_alert)
        row.schedule_interval_minutes = max(5, int(schedule_interval_minutes))
        row.enabled = bool(enabled)
        row.owner = owner.strip()[:64] or "security"
        row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"status": "updated", "policy": _policy_row(row)}

    created = ConnectorReliabilityPolicy(
        tenant_id=tenant.id,
        connector_source=source,
        max_replay_per_run=max(1, int(max_replay_per_run)),
        max_attempts=max(1, int(max_attempts)),
        auto_replay_enabled=bool(auto_replay_enabled),
        route_alert=bool(route_alert),
        schedule_interval_minutes=max(5, int(schedule_interval_minutes)),
        enabled=bool(enabled),
        owner=owner.strip()[:64] or "security",
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"status": "created", "policy": _policy_row(created)}


def get_connector_reliability_policy(db: Session, tenant_code: str, connector_source: str = "*") -> dict[str, Any]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}

    source = connector_source.strip().lower() or "*"
    row = db.scalar(
        select(ConnectorReliabilityPolicy).where(
            ConnectorReliabilityPolicy.tenant_id == tenant.id,
            ConnectorReliabilityPolicy.connector_source == source,
        )
    )
    if row:
        return {"status": "ok", "policy": _policy_row(row)}

    wildcard = db.scalar(
        select(ConnectorReliabilityPolicy).where(
            ConnectorReliabilityPolicy.tenant_id == tenant.id,
            ConnectorReliabilityPolicy.connector_source == "*",
        )
    )
    if wildcard:
        return {"status": "ok", "policy": _policy_row(wildcard)}
    return {"status": "default", "policy": _default_policy(str(tenant.id), source)}


def _collect_replayed_refs(rows: list[ConnectorDeliveryEvent]) -> set[str]:
    refs: set[str] = set()
    for row in rows:
        payload = _safe_json_dict(row.payload_json)
        replay_of = str(payload.get("replay_of_event_id", "")).strip()
        if replay_of:
            refs.add(replay_of)
    return refs


def list_connector_dead_letter_backlog(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str = "",
    limit: int = 200,
) -> dict[str, Any]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}

    source = connector_source.strip().lower()
    stmt = (
        select(ConnectorDeliveryEvent)
        .where(ConnectorDeliveryEvent.tenant_id == tenant.id, ConnectorDeliveryEvent.event_type == "dead_letter")
        .order_by(desc(ConnectorDeliveryEvent.created_at))
        .limit(max(1, min(limit, 5000)))
    )
    if source and source != "*":
        stmt = stmt.where(ConnectorDeliveryEvent.connector_source == source)
    dead_rows = db.scalars(stmt).all()

    replay_rows = db.scalars(
        select(ConnectorDeliveryEvent)
        .where(ConnectorDeliveryEvent.tenant_id == tenant.id)
        .order_by(desc(ConnectorDeliveryEvent.created_at))
        .limit(5000)
    ).all()
    replayed_refs = _collect_replayed_refs(replay_rows)

    rows: list[dict[str, Any]] = []
    unresolved_count = 0
    for event in dead_rows:
        replayed = str(event.id) in replayed_refs
        if not replayed:
            unresolved_count += 1
        payload = _safe_json_dict(event.payload_json)
        rows.append(
            {
                "event_id": str(event.id),
                "tenant_id": str(event.tenant_id) if event.tenant_id else "",
                "site_id": str(event.site_id) if event.site_id else "",
                "connector_source": event.connector_source,
                "event_type": event.event_type,
                "status": event.status,
                "attempt": int(event.attempt),
                "latency_ms": int(event.latency_ms),
                "error_message": event.error_message,
                "payload": payload,
                "replayed": replayed,
                "created_at": _safe_iso(event.created_at),
            }
        )

    return {
        "status": "ok",
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.tenant_code,
        "connector_source": source or "*",
        "count": len(rows),
        "summary": {
            "dead_letter_count": len(rows),
            "replayed_count": len(rows) - unresolved_count,
            "unresolved_count": unresolved_count,
        },
        "rows": rows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def run_connector_dead_letter_replay(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str = "*",
    dry_run: bool | None = None,
    actor: str = "connector_replay_ai",
) -> dict[str, Any]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}

    policy_resp = get_connector_reliability_policy(db, tenant_code, connector_source)
    policy = policy_resp.get("policy", {}) if isinstance(policy_resp, dict) else {}
    if not policy:
        return {"status": "policy_not_found", "tenant_code": tenant_code}
    if not bool(policy.get("enabled", True)):
        return {"status": "disabled", "tenant_code": tenant_code, "policy": policy}

    source_filter = str(policy.get("connector_source", "*")).strip().lower() or "*"
    resolved_dry_run = (not bool(policy.get("auto_replay_enabled", False))) if dry_run is None else bool(dry_run)

    backlog = list_connector_dead_letter_backlog(
        db,
        tenant_code=tenant_code,
        connector_source=source_filter,
        limit=5000,
    )
    backlog_rows = backlog.get("rows", []) if isinstance(backlog, dict) else []
    max_replay = max(1, int(policy.get("max_replay_per_run", 25) or 25))
    max_attempts = max(1, int(policy.get("max_attempts", 3) or 3))

    candidates = [
        row
        for row in backlog_rows
        if not bool(row.get("replayed", False)) and int(row.get("attempt", 1) or 1) < max_attempts
    ]
    selected = candidates[:max_replay]

    replayed_count = 0
    failed_count = 0
    skipped_count = max(0, len(candidates) - len(selected))
    actions: list[dict[str, Any]] = []

    for item in selected:
        next_attempt = max(1, int(item.get("attempt", 1) or 1) + 1)
        action_payload = {
            "replay_of_event_id": item.get("event_id", ""),
            "actor": actor,
            "original_event_type": item.get("event_type", ""),
            "original_error_message": item.get("error_message", ""),
            "connector_source": item.get("connector_source", ""),
        }

        if resolved_dry_run:
            actions.append(
                {
                    "event_id": item.get("event_id", ""),
                    "connector_source": item.get("connector_source", ""),
                    "status": "planned",
                    "next_attempt": next_attempt,
                }
            )
            continue

        record_connector_event(
            db,
            tenant_id=tenant.id,
            site_id=None,
            connector_source=str(item.get("connector_source", "")),
            event_type="retry",
            status="retrying",
            latency_ms=max(0, int(item.get("latency_ms", 0) or 0)),
            attempt=next_attempt,
            payload=action_payload,
            error_message="",
        )

        permanent_failure = "permanent" in str(item.get("error_message", "")).lower()
        if permanent_failure or next_attempt >= max_attempts:
            failed_count += 1
            record_connector_event(
                db,
                tenant_id=tenant.id,
                site_id=None,
                connector_source=str(item.get("connector_source", "")),
                event_type="dead_letter",
                status="failed",
                latency_ms=max(0, int(item.get("latency_ms", 0) or 0)),
                attempt=next_attempt,
                payload=action_payload,
                error_message="replay_max_attempts_reached" if not permanent_failure else "replay_permanent_failure",
            )
            actions.append(
                {
                    "event_id": item.get("event_id", ""),
                    "connector_source": item.get("connector_source", ""),
                    "status": "failed",
                    "next_attempt": next_attempt,
                }
            )
            continue

        replayed_count += 1
        record_connector_event(
            db,
            tenant_id=tenant.id,
            site_id=None,
            connector_source=str(item.get("connector_source", "")),
            event_type="delivery_attempt",
            status="success",
            latency_ms=max(1, int(item.get("latency_ms", 0) or 0) - 40),
            attempt=next_attempt,
            payload=action_payload,
            error_message="",
        )
        actions.append(
            {
                "event_id": item.get("event_id", ""),
                "connector_source": item.get("connector_source", ""),
                "status": "replayed",
                "next_attempt": next_attempt,
            }
        )

    unresolved_backlog = max(0, int(backlog.get("summary", {}).get("unresolved_count", 0) or 0) - replayed_count)
    replay_success_rate = round((replayed_count / len(selected)), 4) if selected else 1.0
    risk_score, risk_tier, recommendation = _risk_from_state(
        unresolved_backlog=unresolved_backlog,
        failed_replays=failed_count,
        replay_success_rate=replay_success_rate,
    )

    status = "ok"
    if failed_count > 0:
        status = "degraded"
    elif not selected:
        status = "no_action"

    alert = {"status": "skipped"}
    should_alert = bool(policy.get("route_alert", True)) and (risk_tier in {"high", "critical"} or failed_count > 0)
    if should_alert:
        severity = "critical" if risk_tier == "critical" else "high"
        alert = dispatch_manual_alert(
            db,
            tenant_code=tenant_code,
            site_code="",
            source="connector_reliability_replay",
            severity=severity,
            title=f"Connector replay run {status}",
            message=(
                f"tenant={tenant_code} source={source_filter} dry_run={resolved_dry_run} "
                f"selected={len(selected)} replayed={replayed_count} failed={failed_count} unresolved={unresolved_backlog}"
            ),
            payload={
                "tenant_code": tenant_code,
                "connector_source": source_filter,
                "risk_score": risk_score,
                "risk_tier": risk_tier,
                "selected_count": len(selected),
                "replayed_count": replayed_count,
                "failed_count": failed_count,
                "unresolved_backlog": unresolved_backlog,
                "dry_run": resolved_dry_run,
            },
        )

    run = ConnectorReliabilityRun(
        tenant_id=tenant.id,
        connector_source=source_filter,
        dry_run=resolved_dry_run,
        status=status,
        backlog_count=int(backlog.get("summary", {}).get("unresolved_count", 0) or 0),
        selected_count=len(selected),
        replayed_count=replayed_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        risk_score=risk_score,
        risk_tier=risk_tier,
        alert_routed=alert.get("status") == "ok",
        details_json=_as_json(
            {
                "replay_success_rate": replay_success_rate,
                "recommendation": recommendation,
                "actions": actions[:200],
            }
        ),
        created_at=datetime.now(timezone.utc),
    )
    db.add(run)

    if not resolved_dry_run:
        record_connector_event(
            db,
            tenant_id=tenant.id,
            site_id=None,
            connector_source=source_filter,
            event_type="replay_batch",
            status="success" if failed_count == 0 else "degraded",
            latency_ms=0,
            attempt=1,
            payload={
                "actor": actor,
                "selected_count": len(selected),
                "replayed_count": replayed_count,
                "failed_count": failed_count,
                "risk_tier": risk_tier,
            },
            error_message="",
        )

    db.commit()
    db.refresh(run)

    return {
        "status": status,
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.tenant_code,
        "dry_run": resolved_dry_run,
        "policy": policy,
        "execution": {
            "backlog_count": int(backlog.get("summary", {}).get("unresolved_count", 0) or 0),
            "selected_count": len(selected),
            "replayed_count": replayed_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "actions": actions,
        },
        "risk": {
            "risk_score": risk_score,
            "risk_tier": risk_tier,
            "recommendation": recommendation,
        },
        "alert": alert,
        "run": _run_row(run),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def list_connector_reliability_runs(
    db: Session,
    *,
    tenant_code: str = "",
    limit: int = 200,
) -> dict[str, Any]:
    tenant_id = None
    tenant_code_out = ""
    if tenant_code:
        tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
        if not tenant:
            return {"count": 0, "rows": []}
        tenant_id = tenant.id
        tenant_code_out = tenant.tenant_code

    stmt = select(ConnectorReliabilityRun).order_by(desc(ConnectorReliabilityRun.created_at)).limit(max(1, min(limit, 2000)))
    if tenant_id:
        stmt = stmt.where(ConnectorReliabilityRun.tenant_id == tenant_id)

    rows = db.scalars(stmt).all()
    return {
        "tenant_code": tenant_code_out,
        "count": len(rows),
        "rows": [_run_row(row) for row in rows],
    }


def _is_policy_due(policy: ConnectorReliabilityPolicy, last_run: ConnectorReliabilityRun | None, now: datetime) -> bool:
    if not bool(policy.enabled):
        return False
    if last_run is None:
        return True
    interval = max(5, int(policy.schedule_interval_minutes))
    cutoff = now - timedelta(minutes=interval)
    return _to_utc(last_run.created_at) <= cutoff


def run_connector_replay_scheduler(
    db: Session,
    *,
    limit: int = 200,
    dry_run_override: bool | None = None,
    actor: str = "connector_replay_ai",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    policies = db.scalars(
        select(ConnectorReliabilityPolicy)
        .where(ConnectorReliabilityPolicy.enabled.is_(True))
        .order_by(desc(ConnectorReliabilityPolicy.updated_at))
        .limit(max(1, min(limit, 2000)))
    ).all()

    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for policy in policies:
        tenant = db.get(Tenant, policy.tenant_id)
        if not tenant:
            skipped.append(
                {
                    "tenant_id": str(policy.tenant_id),
                    "tenant_code": "",
                    "connector_source": policy.connector_source,
                    "reason": "tenant_not_found",
                }
            )
            continue

        last_run = db.scalar(
            select(ConnectorReliabilityRun)
            .where(
                ConnectorReliabilityRun.tenant_id == policy.tenant_id,
                ConnectorReliabilityRun.connector_source == policy.connector_source,
            )
            .order_by(desc(ConnectorReliabilityRun.created_at))
            .limit(1)
        )
        if not _is_policy_due(policy, last_run, now):
            skipped.append(
                {
                    "tenant_id": str(policy.tenant_id),
                    "tenant_code": tenant.tenant_code,
                    "connector_source": policy.connector_source,
                    "reason": "schedule_not_due",
                }
            )
            continue

        run_result = run_connector_dead_letter_replay(
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
                "status": str(run_result.get("status", "unknown")),
                "run_id": str((run_result.get("run", {}) or {}).get("run_id", "")),
                "risk_tier": str((run_result.get("risk", {}) or {}).get("risk_tier", "")),
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


def connector_reliability_federation(db: Session, *, limit: int = 200) -> dict[str, Any]:
    tenants = db.scalars(select(Tenant).order_by(desc(Tenant.created_at)).limit(max(1, min(limit, 2000)))).all()
    rows: list[dict[str, Any]] = []

    for tenant in tenants:
        backlog = list_connector_dead_letter_backlog(db, tenant_code=tenant.tenant_code, connector_source="*", limit=5000)
        unresolved = int((backlog.get("summary", {}) or {}).get("unresolved_count", 0) or 0)

        run_rows = db.scalars(
            select(ConnectorReliabilityRun)
            .where(ConnectorReliabilityRun.tenant_id == tenant.id)
            .order_by(desc(ConnectorReliabilityRun.created_at))
            .limit(100)
        ).all()

        replayed_total = sum(int(run.replayed_count or 0) for run in run_rows)
        failed_total = sum(int(run.failed_count or 0) for run in run_rows)
        replay_success_rate = round((replayed_total / (replayed_total + failed_total)), 4) if (replayed_total + failed_total) else 1.0
        risk_score, risk_tier, recommendation = _risk_from_state(
            unresolved_backlog=unresolved,
            failed_replays=failed_total,
            replay_success_rate=replay_success_rate,
        )

        rows.append(
            {
                "tenant_id": str(tenant.id),
                "tenant_code": tenant.tenant_code,
                "unresolved_dead_letter_count": unresolved,
                "replayed_count": replayed_total,
                "failed_replay_count": failed_total,
                "replay_success_rate": replay_success_rate,
                "risk_score": risk_score,
                "risk_tier": risk_tier,
                "recommendation": recommendation,
            }
        )

    rows.sort(
        key=lambda item: (
            int(item.get("risk_score", 0)),
            int(item.get("unresolved_dead_letter_count", 0)),
            -float(item.get("replay_success_rate", 0.0)),
        ),
        reverse=True,
    )
    tier_counts: dict[str, int] = {}
    for row in rows:
        tier = str(row.get("risk_tier", "low"))
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    return {
        "count": len(rows),
        "tier_counts": tier_counts,
        "summary": {
            "total_unresolved_dead_letter": sum(int(row.get("unresolved_dead_letter_count", 0)) for row in rows),
            "total_failed_replay": sum(int(row.get("failed_replay_count", 0)) for row in rows),
            "average_replay_success_rate": round(
                sum(float(row.get("replay_success_rate", 0.0)) for row in rows) / len(rows),
                4,
            )
            if rows
            else 0.0,
        },
        "rows": rows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def process_connector_replay_schedules(limit: int = 100) -> dict[str, Any]:
    with SessionLocal() as db:
        return run_connector_replay_scheduler(
            db,
            limit=limit,
            dry_run_override=None,
            actor="connector_replay_ai",
        )
