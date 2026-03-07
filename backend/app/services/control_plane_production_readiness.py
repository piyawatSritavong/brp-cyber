from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Tenant
from app.services.control_plane_orchestration_cost_guardrail import evaluate_orchestration_cost_guardrail
from app.services.enterprise.objective_gate import evaluate_and_persist_objective_gate
from app.services.enterprise.slo import get_slo_snapshot
from app.services.notifier import send_telegram_message
from app.services.redis_client import redis_client

PROD_V1_RUNBOOK_PREFIX = "control_plane_prod_v1_runbook"
PROD_V1_CLOSURE_STREAM = "control_plane_prod_v1_go_live_closure"
PROD_V1_BURN_RATE_PROFILE_PREFIX = "control_plane_prod_v1_burn_rate_profile"
PROD_V1_BURN_RATE_EVENT_STREAM = "control_plane_prod_v1_burn_rate_events"
PROD_V1_BURN_RATE_COOLDOWN_PREFIX = "control_plane_prod_v1_burn_rate_cooldown"


_DEFAULT_RUNBOOK_ITEMS = {
    "dr_smoke_passed": False,
    "security_signoff": False,
    "legal_signoff": False,
    "rollback_validated": False,
    "oncall_ready": False,
    "observability_ready": False,
    "incident_playbook_ready": False,
    "change_ticket_linked": False,
}


def _runbook_key(tenant_code: str) -> str:
    return f"{PROD_V1_RUNBOOK_PREFIX}:{tenant_code.lower().strip()}"


def _burn_rate_profile_key(tenant_code: str) -> str:
    return f"{PROD_V1_BURN_RATE_PROFILE_PREFIX}:{tenant_code.lower().strip()}"


def _burn_rate_cooldown_key(tenant_code: str) -> str:
    return f"{PROD_V1_BURN_RATE_COOLDOWN_PREFIX}:{tenant_code.lower().strip()}"


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    if value is None:
        return default
    return bool(value)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _find_tenant(db: Session, tenant_code: str) -> Tenant | None:
    return db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()


def _normalize_runbook(payload: dict[str, Any]) -> dict[str, Any]:
    row = payload or {}
    items_payload = row.get("items", {}) if isinstance(row.get("items", {}), dict) else {}
    items: dict[str, bool] = {}
    for key, default in _DEFAULT_RUNBOOK_ITEMS.items():
        items[key] = _as_bool(items_payload.get(key), default)

    return {
        "version": str(row.get("version", "1.0")),
        "owner": str(row.get("owner", "ops")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "change_ticket": str(row.get("change_ticket", "")).strip(),
        "notes": str(row.get("notes", "")),
        "items": items,
    }


def _normalize_burn_rate_profile(payload: dict[str, Any]) -> dict[str, Any]:
    rollback_target = str(payload.get("rollback_target_status", "staging")).strip().lower()
    if rollback_target not in {"staging", "suspended"}:
        rollback_target = "staging"
    return {
        "version": str(payload.get("version", "1.0")),
        "owner": str(payload.get("owner", "sre")),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "error_budget_fraction_per_day": min(1.0, max(0.0001, _as_float(payload.get("error_budget_fraction_per_day"), 0.01))),
        "burn_rate_warn_threshold": max(0.1, _as_float(payload.get("burn_rate_warn_threshold"), 1.0)),
        "burn_rate_rollback_threshold": max(0.1, _as_float(payload.get("burn_rate_rollback_threshold"), 2.0)),
        "min_requests_for_enforcement": max(1, _as_int(payload.get("min_requests_for_enforcement"), 100)),
        "auto_rollback_on_breach": _as_bool(payload.get("auto_rollback_on_breach"), True),
        "rollback_target_status": rollback_target,
        "cooldown_minutes": max(1, _as_int(payload.get("cooldown_minutes"), 30)),
        "notify_on_rollback": _as_bool(payload.get("notify_on_rollback"), True),
    }


def upsert_prod_v1_go_live_runbook(tenant_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    runbook = _normalize_runbook(payload)
    redis_client.set(_runbook_key(tenant_code), json.dumps(runbook, ensure_ascii=True, sort_keys=True))
    return {"status": "upserted", "tenant_code": tenant_code, "runbook": runbook}


def get_prod_v1_go_live_runbook(tenant_code: str) -> dict[str, Any]:
    raw = redis_client.get(_runbook_key(tenant_code))
    if not raw:
        return {"status": "default", "tenant_code": tenant_code, "runbook": _normalize_runbook({})}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "corrupted", "tenant_code": tenant_code, "runbook": _normalize_runbook({})}
    return {"status": "ok", "tenant_code": tenant_code, "runbook": _normalize_runbook(parsed)}


def upsert_prod_v1_burn_rate_profile(tenant_code: str, payload: dict[str, Any]) -> dict[str, Any]:
    profile = _normalize_burn_rate_profile(payload)
    redis_client.set(_burn_rate_profile_key(tenant_code), json.dumps(profile, ensure_ascii=True, sort_keys=True))
    return {"status": "upserted", "tenant_code": tenant_code, "profile": profile}


def get_prod_v1_burn_rate_profile(tenant_code: str) -> dict[str, Any]:
    raw = redis_client.get(_burn_rate_profile_key(tenant_code))
    if not raw:
        return {"status": "default", "tenant_code": tenant_code, "profile": _normalize_burn_rate_profile({})}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "corrupted", "tenant_code": tenant_code, "profile": _normalize_burn_rate_profile({})}
    return {"status": "ok", "tenant_code": tenant_code, "profile": _normalize_burn_rate_profile(parsed)}


def evaluate_prod_v1_readiness_final(
    db: Session,
    tenant_code: str,
    *,
    max_monthly_cost_usd: float = 50.0,
) -> dict[str, Any]:
    tenant = _find_tenant(db, tenant_code)
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}

    objective = evaluate_and_persist_objective_gate(tenant.id, max_monthly_cost_usd=max_monthly_cost_usd)
    cost_eval = evaluate_orchestration_cost_guardrail(tenant.id, tenant.tenant_code, apply_actions=False)
    runbook = get_prod_v1_go_live_runbook(tenant.tenant_code).get("runbook", _normalize_runbook({}))
    items = dict(runbook.get("items", {}))

    runbook_pass = all(bool(items.get(key, False)) for key in _DEFAULT_RUNBOOK_ITEMS)
    cost_pass = not bool(cost_eval.get("state", {}).get("breached", False)) and not bool(cost_eval.get("state", {}).get("anomaly", False))
    objective_pass = bool(objective.get("overall_pass", False))

    blockers: list[dict[str, Any]] = []
    if not objective_pass:
        blockers.append({"type": "objective_gate", "reason": "objective_gate_not_passed"})
    if not cost_pass:
        blockers.append(
            {
                "type": "cost_guardrail",
                "reason": "cost_breach_or_anomaly_detected",
                "state": cost_eval.get("state", {}),
            }
        )
    if not runbook_pass:
        blockers.append(
            {
                "type": "runbook",
                "reason": "go_live_checklist_incomplete",
                "missing_items": [k for k, v in items.items() if not bool(v)],
            }
        )

    final_pass = objective_pass and cost_pass and runbook_pass

    return {
        "status": "ok",
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.tenant_code,
        "production_v1_ready": final_pass,
        "final_gate": {
            "objective_pass": objective_pass,
            "cost_pass": cost_pass,
            "runbook_pass": runbook_pass,
        },
        "objective_gate": objective,
        "cost_guardrail": {
            "state": cost_eval.get("state", {}),
            "metrics": cost_eval.get("metrics", {}),
        },
        "runbook": runbook,
        "blockers": blockers,
    }


def close_prod_v1_go_live(
    db: Session,
    tenant_code: str,
    *,
    approved_by: str,
    change_ticket: str,
    dry_run: bool = True,
    promote_on_pass: bool = True,
    max_monthly_cost_usd: float = 50.0,
) -> dict[str, Any]:
    readiness = evaluate_prod_v1_readiness_final(db, tenant_code, max_monthly_cost_usd=max_monthly_cost_usd)
    if readiness.get("status") != "ok":
        return readiness

    tenant = _find_tenant(db, tenant_code)
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}

    go_live_ready = bool(readiness.get("production_v1_ready", False))
    previous_status = str(tenant.status)
    next_status = tenant.status
    closure_status = "blocked"

    if go_live_ready:
        closure_status = "ready"
        if not dry_run and promote_on_pass:
            tenant.status = "production"
            db.commit()
            db.refresh(tenant)
            next_status = tenant.status
            closure_status = "closed"

    closure = {
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.tenant_code,
        "approved_by": approved_by,
        "change_ticket": change_ticket,
        "dry_run": dry_run,
        "promote_on_pass": promote_on_pass,
        "status": closure_status,
        "previous_status": previous_status,
        "current_status": next_status,
        "production_v1_ready": go_live_ready,
        "closed_at": datetime.now(timezone.utc).isoformat(),
        "readiness": readiness,
    }

    redis_client.xadd(
        PROD_V1_CLOSURE_STREAM,
        {
            "tenant_code": tenant.tenant_code,
            "approved_by": approved_by,
            "change_ticket": change_ticket,
            "status": closure_status,
            "dry_run": "1" if dry_run else "0",
            "promote_on_pass": "1" if promote_on_pass else "0",
            "closed_at": closure["closed_at"],
            "payload": json.dumps(closure, ensure_ascii=True),
        },
        maxlen=100000,
        approximate=True,
    )
    return closure


def prod_v1_go_live_closure_history(tenant_code: str = "", limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(PROD_V1_CLOSURE_STREAM, count=max(1, limit))
    rows: list[dict[str, Any]] = []
    wanted = tenant_code.strip().lower()

    for event_id, fields in entries:
        code = str(fields.get("tenant_code", "")).strip().lower()
        if wanted and code != wanted:
            continue
        row: dict[str, Any] = {"id": event_id}
        row.update(fields)
        payload = str(fields.get("payload", ""))
        if payload:
            try:
                row["payload"] = json.loads(payload)
            except json.JSONDecodeError:
                row["payload"] = {}
        rows.append(row)

    return {"count": len(rows), "rows": rows}


def evaluate_prod_v1_burn_rate_guard(
    db: Session,
    tenant_code: str,
    *,
    apply: bool = False,
) -> dict[str, Any]:
    tenant = _find_tenant(db, tenant_code)
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}

    profile_resp = get_prod_v1_burn_rate_profile(tenant.tenant_code)
    profile = profile_resp.get("profile", _normalize_burn_rate_profile({}))
    slo = get_slo_snapshot(tenant.id)
    requests_total = max(0, _as_int(slo.get("requests_total"), 0))
    requests_failed = max(0, _as_int(slo.get("requests_failed"), 0))

    error_budget = max(1.0, requests_total * _as_float(profile.get("error_budget_fraction_per_day"), 0.01))
    burn_rate = (requests_failed / error_budget) if error_budget > 0 else 0.0
    warn_threshold = _as_float(profile.get("burn_rate_warn_threshold"), 1.0)
    rollback_threshold = _as_float(profile.get("burn_rate_rollback_threshold"), 2.0)
    min_requests = _as_int(profile.get("min_requests_for_enforcement"), 100)

    insufficient_sample = requests_total < min_requests
    production_status = str(tenant.status).lower() == "production"
    should_warn = not insufficient_sample and burn_rate >= warn_threshold
    should_rollback = not insufficient_sample and burn_rate >= rollback_threshold and production_status

    now = datetime.now(timezone.utc)
    cooldown_minutes = _as_int(profile.get("cooldown_minutes"), 30)
    cooldown_seconds = max(60, cooldown_minutes * 60)
    cooldown_until_epoch = _as_int(redis_client.get(_burn_rate_cooldown_key(tenant.tenant_code)), 0)
    now_epoch = int(now.timestamp())
    cooldown_active = cooldown_until_epoch > now_epoch

    action = {"executed": False, "type": "", "reason": ""}
    if apply and should_rollback and _as_bool(profile.get("auto_rollback_on_breach"), True):
        if cooldown_active:
            action = {"executed": False, "type": "rollback_blocked", "reason": "cooldown_active"}
        else:
            target_status = str(profile.get("rollback_target_status", "staging")).strip().lower()
            previous_status = str(tenant.status)
            tenant.status = target_status
            db.commit()
            db.refresh(tenant)
            redis_client.set(_burn_rate_cooldown_key(tenant.tenant_code), str(now_epoch + cooldown_seconds))
            action = {
                "executed": True,
                "type": "auto_rollback",
                "reason": "burn_rate_threshold_exceeded",
                "from_status": previous_status,
                "to_status": target_status,
            }
            if _as_bool(profile.get("notify_on_rollback"), True):
                send_telegram_message(
                    f"[BRP-Cyber] Production v1 auto-rollback tenant={tenant.tenant_code} "
                    f"burn_rate={burn_rate:.3f} threshold={rollback_threshold:.3f} "
                    f"from={previous_status} to={target_status}"
                )

    result = {
        "status": "ok",
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.tenant_code,
        "tenant_status": str(tenant.status),
        "profile": profile,
        "slo": {
            "requests_total": requests_total,
            "requests_failed": requests_failed,
            "availability": _as_float(slo.get("availability"), 1.0),
        },
        "burn_rate": {
            "value": round(burn_rate, 6),
            "error_budget": round(error_budget, 6),
            "warn_threshold": warn_threshold,
            "rollback_threshold": rollback_threshold,
            "insufficient_sample": insufficient_sample,
            "min_requests_for_enforcement": min_requests,
        },
        "decision": {
            "should_warn": should_warn,
            "should_rollback": should_rollback,
            "production_status_required": production_status,
            "cooldown_active": cooldown_active,
            "cooldown_until_epoch": cooldown_until_epoch,
        },
        "action": action,
    }

    redis_client.xadd(
        PROD_V1_BURN_RATE_EVENT_STREAM,
        {
            "tenant_code": tenant.tenant_code,
            "timestamp": now.isoformat(),
            "burn_rate": str(round(burn_rate, 6)),
            "should_warn": "1" if should_warn else "0",
            "should_rollback": "1" if should_rollback else "0",
            "action_executed": "1" if bool(action.get("executed", False)) else "0",
            "action_type": str(action.get("type", "")),
            "payload": json.dumps(result, ensure_ascii=True),
        },
        maxlen=100000,
        approximate=True,
    )
    return result


def prod_v1_burn_rate_guard_history(tenant_code: str = "", limit: int = 100) -> dict[str, Any]:
    entries = redis_client.xrevrange(PROD_V1_BURN_RATE_EVENT_STREAM, count=max(1, limit))
    rows: list[dict[str, Any]] = []
    wanted = tenant_code.strip().lower()
    for event_id, fields in entries:
        code = str(fields.get("tenant_code", "")).strip().lower()
        if wanted and code != wanted:
            continue
        row: dict[str, Any] = {"id": event_id}
        row.update(fields)
        payload = str(fields.get("payload", ""))
        if payload:
            try:
                row["payload"] = json.loads(payload)
            except json.JSONDecodeError:
                row["payload"] = {}
        rows.append(row)
    return {"count": len(rows), "rows": rows}
