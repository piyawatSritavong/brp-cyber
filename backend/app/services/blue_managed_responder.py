from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import BlueEventLog, BlueManagedResponderPolicy, BlueManagedResponderRun, Site, SoarPlaybookExecution
from app.db.session import SessionLocal
from app.services.site_ops import apply_blue_recommendation
from app.services.soar_playbook_hub import approve_playbook_execution, execute_playbook

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
ALLOWED_ACTIONS = {"ai_recommended", "block_ip", "notify_team", "limit_user", "ignore"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _stable_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _safe_json(value: str | None) -> dict[str, Any]:
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


def _safe_site_config(site: Site) -> dict[str, Any]:
    return _safe_json(getattr(site, "config_json", ""))


def _safe_event_payload(event: BlueEventLog) -> dict[str, Any]:
    return _safe_json(getattr(event, "payload_json", ""))


def _normalize_severity(value: str) -> str:
    severity = str(value or "").strip().lower()
    return severity if severity in SEVERITY_RANK else "medium"


def _normalize_action_mode(value: str) -> str:
    action = str(value or "").strip().lower()
    return action if action in ALLOWED_ACTIONS else "ai_recommended"


def _csv_set(value: str) -> set[str]:
    return {item.strip() for item in str(value or "").split(",") if item.strip()}


def _evidence_key_bytes() -> bytes:
    material = (getattr(settings, "blue_managed_responder_evidence_hmac_key", "") or "brp-blue-managed-responder").encode("utf-8")
    return material


def _sign_evidence_payload(signed_payload: dict[str, Any], previous_signature: str) -> str:
    message = f"{previous_signature}|{_stable_json(signed_payload)}"
    return hmac.new(_evidence_key_bytes(), message.encode("utf-8"), hashlib.sha256).hexdigest()


def _safe_uuid(value: str) -> UUID | None:
    try:
        return UUID(str(value or "").strip())
    except Exception:
        return None


def _append_audit_entry(details: dict[str, Any], *, kind: str, actor: str, note: str, status: str) -> None:
    current = details.get("lifecycle_audit", [])
    history = current if isinstance(current, list) else []
    history.append(
        {
            "kind": kind,
            "actor": actor,
            "note": note,
            "status": status,
            "recorded_at": _now().isoformat(),
        }
    )
    details["lifecycle_audit"] = history[-20:]


def _previous_evidence_chain(db: Session, *, site_id: UUID) -> dict[str, Any]:
    previous = db.scalar(
        select(BlueManagedResponderRun)
        .where(BlueManagedResponderRun.site_id == site_id)
        .order_by(desc(BlueManagedResponderRun.created_at))
        .limit(1)
    )
    if not previous:
        return {"sequence": 0, "signature": ""}
    details = _safe_json(previous.details_json)
    evidence = details.get("evidence_chain", {})
    if not isinstance(evidence, dict):
        evidence = {}
    return {
        "sequence": int(evidence.get("sequence", 0) or 0),
        "signature": str(evidence.get("signature", "") or ""),
    }


def _build_evidence_chain(
    db: Session,
    *,
    site: Site,
    candidate: BlueEventLog,
    created_at: datetime,
    status: str,
    dry_run: bool,
    selected_action: str,
    selected_severity: str,
    playbook_code: str,
    playbook_execution_id: str,
    action_applied: bool,
    playbook_dispatched: bool,
    candidate_status_before: str,
    candidate_action_before: str,
    guardrails: dict[str, Any],
    approval_required: bool,
    connector_source: str = "",
    connector_action_status: str = "",
) -> dict[str, Any]:
    previous = _previous_evidence_chain(db, site_id=site.id)
    signed_payload = {
        "site_id": str(site.id),
        "site_code": site.site_code,
        "event_id": str(candidate.id),
        "event_type": str(candidate.event_type or ""),
        "source_ip": str(candidate.source_ip or ""),
        "created_at": created_at.isoformat(),
        "status": status,
        "dry_run": bool(dry_run),
        "selected_action": selected_action,
        "selected_severity": selected_severity,
        "playbook_code": playbook_code,
        "playbook_execution_id": playbook_execution_id,
        "action_applied": bool(action_applied),
        "playbook_dispatched": bool(playbook_dispatched),
        "candidate_status_before": candidate_status_before,
        "candidate_action_before": candidate_action_before,
        "guardrail_reason": str(guardrails.get("reason", "") or ""),
        "approval_required": bool(approval_required),
        "connector_source": connector_source,
        "connector_action_status": connector_action_status,
    }
    previous_signature = str(previous.get("signature", "") or "")
    return {
        "sequence": int(previous.get("sequence", 0) or 0) + 1,
        "previous_signature": previous_signature,
        "signature": _sign_evidence_payload(signed_payload, previous_signature),
        "signed_payload": signed_payload,
        "generated_at": created_at.isoformat(),
    }


def _recent_run_count(db: Session, *, site_id: UUID, now: datetime, window_minutes: int = 60) -> int:
    cutoff = now - timedelta(minutes=max(1, int(window_minutes)))
    rows = db.scalars(
        select(BlueManagedResponderRun)
        .where(BlueManagedResponderRun.site_id == site_id)
        .order_by(desc(BlueManagedResponderRun.created_at))
        .limit(500)
    ).all()
    count = 0
    for row in rows:
        created_at = row.created_at
        if created_at is None:
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if created_at >= cutoff:
            count += 1
    return count


def _policy_row(row: BlueManagedResponderPolicy) -> dict[str, Any]:
    return {
        "policy_id": str(row.id),
        "site_id": str(row.site_id),
        "min_severity": row.min_severity,
        "action_mode": row.action_mode,
        "dispatch_playbook": bool(row.dispatch_playbook),
        "playbook_code": row.playbook_code,
        "require_approval": bool(row.require_approval),
        "dry_run_default": bool(row.dry_run_default),
        "enabled": bool(row.enabled),
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _default_policy(site_id: UUID) -> dict[str, Any]:
    return {
        "policy_id": "",
        "site_id": str(site_id),
        "min_severity": "medium",
        "action_mode": "ai_recommended",
        "dispatch_playbook": True,
        "playbook_code": "block-ip-and-waf-tighten",
        "require_approval": True,
        "dry_run_default": True,
        "enabled": True,
        "owner": "system",
        "created_at": "",
        "updated_at": "",
    }


def _run_row(row: BlueManagedResponderRun) -> dict[str, Any]:
    details = _safe_json(row.details_json)
    evidence = details.get("evidence_chain", {})
    if not isinstance(evidence, dict):
        evidence = {}
    connector_action = details.get("connector_action_result", {})
    if not isinstance(connector_action, dict):
        connector_action = {}
    rollback = details.get("rollback", {})
    if not isinstance(rollback, dict):
        rollback = {}
    connector_rollback = rollback.get("connector_rollback", {})
    if not isinstance(connector_rollback, dict):
        connector_rollback = {}
    return {
        "run_id": str(row.id),
        "site_id": str(row.site_id),
        "event_id": str(row.event_id) if row.event_id else "",
        "status": row.status,
        "dry_run": bool(row.dry_run),
        "selected_severity": row.selected_severity,
        "selected_action": row.selected_action,
        "playbook_code": row.playbook_code,
        "playbook_execution_id": row.playbook_execution_id,
        "action_applied": bool(row.action_applied),
        "playbook_dispatched": bool(row.playbook_dispatched),
        "approval_required": bool(details.get("approval_required", False)),
        "rollback_supported": bool(details.get("rollback_supported", False)),
        "evidence_sequence": int(evidence.get("sequence", 0) or 0),
        "evidence_signature": str(evidence.get("signature", "") or ""),
        "connector_source": str(connector_action.get("connector_source", "") or ""),
        "connector_action_status": str(connector_action.get("status", "") or ""),
        "connector_confirmation_status": str((connector_action.get("confirmation", {}) or {}).get("status", "") or ""),
        "connector_rollback_status": str(connector_rollback.get("status", "") or ""),
        "details": details,
        "created_at": _safe_iso(row.created_at),
    }


def get_managed_responder_policy(db: Session, *, site_id: UUID) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    row = db.scalar(select(BlueManagedResponderPolicy).where(BlueManagedResponderPolicy.site_id == site.id))
    if not row:
        return {"status": "ok", "policy": _default_policy(site.id)}
    return {"status": "ok", "policy": _policy_row(row)}


def upsert_managed_responder_policy(
    db: Session,
    *,
    site_id: UUID,
    min_severity: str,
    action_mode: str,
    dispatch_playbook: bool,
    playbook_code: str,
    require_approval: bool,
    dry_run_default: bool,
    enabled: bool,
    owner: str,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    row = db.scalar(select(BlueManagedResponderPolicy).where(BlueManagedResponderPolicy.site_id == site.id))
    now = _now()
    normalized_severity = _normalize_severity(min_severity)
    normalized_action = _normalize_action_mode(action_mode)
    if row:
        row.min_severity = normalized_severity
        row.action_mode = normalized_action
        row.dispatch_playbook = bool(dispatch_playbook)
        row.playbook_code = str(playbook_code or "").strip()[:80]
        row.require_approval = bool(require_approval)
        row.dry_run_default = bool(dry_run_default)
        row.enabled = bool(enabled)
        row.owner = owner.strip()[:64] or "security"
        row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"status": "updated", "policy": _policy_row(row)}

    created = BlueManagedResponderPolicy(
        site_id=site.id,
        min_severity=normalized_severity,
        action_mode=normalized_action,
        dispatch_playbook=bool(dispatch_playbook),
        playbook_code=str(playbook_code or "").strip()[:80],
        require_approval=bool(require_approval),
        dry_run_default=bool(dry_run_default),
        enabled=bool(enabled),
        owner=owner.strip()[:64] or "security",
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"status": "created", "policy": _policy_row(created)}


def list_managed_responder_runs(db: Session, *, site_id: UUID, limit: int = 100) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"site_id": str(site_id), "count": 0, "rows": []}
    rows = db.scalars(
        select(BlueManagedResponderRun)
        .where(BlueManagedResponderRun.site_id == site.id)
        .order_by(desc(BlueManagedResponderRun.created_at))
        .limit(max(1, min(limit, 500)))
    ).all()
    return {"site_id": str(site.id), "count": len(rows), "rows": [_run_row(row) for row in rows]}


def _pick_candidate_event(db: Session, *, site_id: UUID, min_severity: str) -> BlueEventLog | None:
    min_rank = SEVERITY_RANK.get(_normalize_severity(min_severity), 2)
    rows = db.scalars(
        select(BlueEventLog)
        .where(BlueEventLog.site_id == site_id)
        .order_by(desc(BlueEventLog.created_at))
        .limit(100)
    ).all()
    for row in rows:
        if row.status != "open":
            continue
        if SEVERITY_RANK.get(_normalize_severity(row.ai_severity), 1) >= min_rank:
            return row
    return None


def _guardrail_decision(
    db: Session,
    *,
    site: Site,
    candidate: BlueEventLog,
    selected_action: str,
    dry_run: bool,
    force: bool,
) -> dict[str, Any]:
    if force:
        return {"blocked": False, "reason": ""}

    source_ip = str(candidate.source_ip or "").strip()
    site_config = _safe_site_config(site)
    global_allowlist = _csv_set(getattr(settings, "allowlist_ips", ""))
    blocked_sources_raw = site_config.get("managed_responder_blocked_source_ips", [])
    site_blocked_sources = {str(item).strip() for item in blocked_sources_raw if str(item).strip()} if isinstance(blocked_sources_raw, list) else set()

    if bool(getattr(settings, "blue_managed_responder_respect_allowlist", True)) and source_ip and source_ip in global_allowlist:
        return {"blocked": True, "reason": "allowlisted_source_ip", "source_ip": source_ip}
    if source_ip and source_ip in site_blocked_sources:
        return {"blocked": True, "reason": "site_blocked_source_ip", "source_ip": source_ip}
    if bool(getattr(settings, "blue_managed_responder_skip_ignore_action", True)) and selected_action == "ignore":
        return {"blocked": True, "reason": "selected_action_ignore"}

    recent_runs = _recent_run_count(
        db,
        site_id=site.id,
        now=_now(),
        window_minutes=60,
    )
    max_runs = max(1, int(getattr(settings, "blue_managed_responder_max_runs_per_hour", 6)))
    if recent_runs >= max_runs:
        return {"blocked": True, "reason": "max_runs_per_hour_exceeded", "recent_runs": recent_runs, "max_runs_per_hour": max_runs}

    apply_min_severity = _normalize_severity(getattr(settings, "blue_managed_responder_apply_min_severity", "high"))
    candidate_severity = _normalize_severity(candidate.ai_severity)
    if not dry_run and SEVERITY_RANK.get(candidate_severity, 1) < SEVERITY_RANK.get(apply_min_severity, 3):
        return {
            "blocked": True,
            "reason": "apply_min_severity_not_met",
            "required_min_severity": apply_min_severity,
            "candidate_severity": candidate_severity,
        }
    return {"blocked": False, "reason": ""}


def _resolve_connector_source(site: Site, candidate: BlueEventLog) -> str:
    site_config = _safe_site_config(site)
    payload = _safe_event_payload(candidate)
    candidates = [
        payload.get("connector_source"),
        payload.get("source_tool"),
        site_config.get("managed_responder_connector_source"),
        site_config.get("default_connector_source"),
    ]
    for value in candidates:
        normalized = str(value or "").strip().lower()
        if normalized in {"cloudflare", "crowdstrike", "splunk", "generic"}:
            return normalized
    event_type = str(candidate.event_type or "").lower()
    if event_type.startswith("waf") or "cloudflare" in event_type:
        return "cloudflare"
    if "endpoint" in event_type or "crowdstrike" in event_type:
        return "crowdstrike"
    if "siem" in event_type or "splunk" in event_type:
        return "splunk"
    return "generic"


def _build_connector_action_plan(site: Site, candidate: BlueEventLog, *, selected_action: str, actor: str) -> dict[str, Any]:
    connector_source = _resolve_connector_source(site, candidate)
    event_payload = _safe_event_payload(candidate)
    base = {
        "connector_source": connector_source,
        "selected_action": selected_action,
        "actor": actor,
        "event_id": str(candidate.id),
        "event_type": str(candidate.event_type or ""),
        "source_ip": str(candidate.source_ip or ""),
        "requested_at": _now().isoformat(),
    }
    if connector_source == "cloudflare":
        return {
            **base,
            "operation": "firewall.access_rule.block" if selected_action == "block_ip" else "waf.custom_response",
            "request_payload": {
                "mode": "block" if selected_action == "block_ip" else "managed_challenge",
                "configuration": {"target": "ip", "value": str(candidate.source_ip or "")},
                "notes": f"Managed responder action for {site.site_code}",
            },
            "rollback_payload": {
                "operation": "firewall.access_rule.remove",
                "configuration": {"target": "ip", "value": str(candidate.source_ip or "")},
            },
        }
    if connector_source == "crowdstrike":
        host_id = str(event_payload.get("device_id") or event_payload.get("host_id") or candidate.source_ip or "")
        return {
            **base,
            "operation": "hosts.contain" if selected_action in {"block_ip", "limit_user"} else "alerts.annotate",
            "request_payload": {
                "device_id": host_id,
                "action": "contain_host" if selected_action in {"block_ip", "limit_user"} else "annotate",
                "comment": f"Managed responder for {site.site_code}",
            },
            "rollback_payload": {
                "operation": "hosts.release",
                "device_id": host_id,
            },
        }
    if connector_source == "splunk":
        return {
            **base,
            "operation": "adaptive_response.dispatch",
            "request_payload": {
                "search_name": "BRP Managed Responder",
                "notable_title": f"{selected_action} for {site.site_code}",
                "source_ip": str(candidate.source_ip or ""),
                "event_type": str(candidate.event_type or ""),
            },
            "rollback_payload": {
                "operation": "notable.close",
                "reason": "rollback",
            },
        }
    return {
        **base,
        "operation": "generic.webhook.dispatch",
        "request_payload": {
            "selected_action": selected_action,
            "source_ip": str(candidate.source_ip or ""),
            "event_type": str(candidate.event_type or ""),
        },
        "rollback_payload": {
            "operation": "generic.webhook.rollback",
            "selected_action": selected_action,
        },
    }


def _execute_connector_action_plan(plan: dict[str, Any], *, dry_run: bool, actor: str) -> dict[str, Any]:
    if dry_run:
        return {
            "status": "dry_run",
            "connector_source": str(plan.get("connector_source", "") or ""),
            "operation": str(plan.get("operation", "") or ""),
            "request_payload": dict(plan.get("request_payload", {}) or {}),
            "confirmation": {
                "status": "dry_run",
                "confirmation_ref": "",
                "confirmed_at": "",
                "actor": actor,
            },
            "rollback_ready": bool(plan.get("rollback_payload")),
        }
    confirmation_ref = hashlib.sha256(_stable_json(plan).encode("utf-8")).hexdigest()[:16]
    return {
        "status": "confirmed",
        "connector_source": str(plan.get("connector_source", "") or ""),
        "operation": str(plan.get("operation", "") or ""),
        "request_payload": dict(plan.get("request_payload", {}) or {}),
        "confirmation": {
            "status": "confirmed",
            "confirmation_ref": confirmation_ref,
            "confirmed_at": _now().isoformat(),
            "actor": actor,
        },
        "rollback_ready": bool(plan.get("rollback_payload")),
    }


def _rollback_connector_action(plan: dict[str, Any], *, actor: str, note: str) -> dict[str, Any]:
    if not plan:
        return {"status": "skipped"}
    confirmation_ref = hashlib.sha256(f"rollback|{_stable_json(plan)}|{note}".encode("utf-8")).hexdigest()[:16]
    return {
        "status": "rolled_back",
        "connector_source": str(plan.get("connector_source", "") or ""),
        "operation": str((plan.get("rollback_payload", {}) or {}).get("operation", "") or ""),
        "request_payload": dict(plan.get("rollback_payload", {}) or {}),
        "confirmation": {
            "status": "confirmed",
            "confirmation_ref": confirmation_ref,
            "confirmed_at": _now().isoformat(),
            "actor": actor,
        },
        "note": note,
    }


def run_managed_responder(
    db: Session,
    *,
    site_id: UUID,
    dry_run: bool | None = None,
    force: bool = False,
    actor: str = "managed_ai_responder",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    policy_result = get_managed_responder_policy(db, site_id=site_id)
    policy = policy_result.get("policy", _default_policy(site_id))
    if not bool(policy.get("enabled", True)) and not force:
        return {"status": "disabled", "site_id": str(site.id), "policy": policy}

    candidate = _pick_candidate_event(db, site_id=site.id, min_severity=str(policy.get("min_severity", "medium")))
    if candidate is None:
        return {"status": "no_candidate", "site_id": str(site.id), "policy": policy}

    resolved_dry_run = bool(policy.get("dry_run_default", True)) if dry_run is None else bool(dry_run)
    action_mode = _normalize_action_mode(str(policy.get("action_mode", "ai_recommended")))
    selected_action = candidate.ai_recommendation if action_mode == "ai_recommended" else action_mode
    selected_action = _normalize_action_mode(selected_action if selected_action != "ai_recommended" else "notify_team")
    if selected_action == "ai_recommended":
        selected_action = "notify_team"

    action_result: dict[str, Any] = {"status": "skipped"}
    playbook_result: dict[str, Any] = {"status": "skipped"}
    connector_action_plan = _build_connector_action_plan(site, candidate, selected_action=selected_action, actor=actor)
    connector_action_result: dict[str, Any] = {
        "status": "planned",
        "connector_source": str(connector_action_plan.get("connector_source", "") or ""),
        "operation": str(connector_action_plan.get("operation", "") or ""),
        "request_payload": dict(connector_action_plan.get("request_payload", {}) or {}),
        "confirmation": {"status": "pending"},
        "rollback_ready": bool(connector_action_plan.get("rollback_payload")),
    }
    playbook_code = str(policy.get("playbook_code", "") or "").strip()
    playbook_execution_id = ""
    action_applied = False
    playbook_dispatched = False
    status = "dry_run" if resolved_dry_run else "ok"
    candidate_status_before = candidate.status
    candidate_action_before = str(candidate.action_taken or "")
    guardrails = _guardrail_decision(
        db,
        site=site,
        candidate=candidate,
        selected_action=selected_action,
        dry_run=resolved_dry_run,
        force=force,
    )
    approval_required = bool(policy.get("require_approval", True)) and not resolved_dry_run and not force
    created_at = _now()

    if bool(guardrails.get("blocked")):
        status = "guardrail_blocked"
    elif resolved_dry_run:
        connector_action_result = _execute_connector_action_plan(connector_action_plan, dry_run=True, actor=actor)
    elif approval_required:
        action_result = {"status": "pending_approval", "selected_action": selected_action}
        connector_action_result["status"] = "pending_approval"
        connector_action_result["confirmation"] = {"status": "pending_approval"}
        if bool(policy.get("dispatch_playbook", True)) and playbook_code:
            playbook_result = execute_playbook(
                db,
                site_id=site.id,
                playbook_code=playbook_code,
                actor=actor,
                require_approval=True,
                dry_run=False,
                params={
                    "source_ip": candidate.source_ip,
                    "event_id": str(candidate.id),
                    "event_type": candidate.event_type,
                    "selected_action": selected_action,
                    "ai_recommendation": candidate.ai_recommendation,
                },
            )
            playbook_execution_id = str(playbook_result.get("execution", {}).get("execution_id", "") or "")
            playbook_dispatched = playbook_result.get("status") in {"pending_approval", "applied"}
        status = "pending_approval"
    elif not resolved_dry_run:
        action_result = apply_blue_recommendation(db, site.id, candidate.id, selected_action)
        action_applied = action_result.get("status") == "applied"
        if action_applied:
            connector_action_result = _execute_connector_action_plan(connector_action_plan, dry_run=False, actor=actor)
        if bool(policy.get("dispatch_playbook", True)) and playbook_code:
            playbook_result = execute_playbook(
                db,
                site_id=site.id,
                playbook_code=playbook_code,
                actor=actor,
                require_approval=bool(policy.get("require_approval", True)),
                dry_run=False,
                params={
                    "source_ip": candidate.source_ip,
                    "event_id": str(candidate.id),
                    "event_type": candidate.event_type,
                    "selected_action": selected_action,
                    "ai_recommendation": candidate.ai_recommendation,
                },
            )
            playbook_execution_id = str(playbook_result.get("execution", {}).get("execution_id", "") or "")
            playbook_dispatched = playbook_result.get("status") in {"dry_run", "pending_approval", "applied"}
            if playbook_result.get("status") not in {"dry_run", "pending_approval", "applied", "skipped"}:
                status = "partial" if action_applied else "error"
            elif playbook_result.get("status") == "pending_approval":
                status = "pending_approval"
        elif action_applied:
            status = "applied"
        if action_applied and connector_action_result.get("status") != "confirmed":
            status = "partial"

    evidence_chain = _build_evidence_chain(
        db,
        site=site,
        candidate=candidate,
        created_at=created_at,
        status=status,
        dry_run=resolved_dry_run,
        selected_action=selected_action,
        selected_severity=_normalize_severity(candidate.ai_severity),
        playbook_code=playbook_code,
        playbook_execution_id=playbook_execution_id[:64],
        action_applied=action_applied,
        playbook_dispatched=playbook_dispatched,
        candidate_status_before=candidate_status_before,
        candidate_action_before=candidate_action_before,
        guardrails=guardrails,
        approval_required=approval_required,
        connector_source=str(connector_action_plan.get("connector_source", "") or ""),
        connector_action_status=str(connector_action_result.get("status", "") or ""),
    )

    details = {
        "actor": actor,
        "force": force,
        "candidate_event_type": candidate.event_type,
        "candidate_source_ip": candidate.source_ip,
        "candidate_status_before": candidate_status_before,
        "candidate_action_before": candidate_action_before,
        "guardrails": guardrails,
        "approval_required": approval_required,
        "rollback_supported": not resolved_dry_run and not bool(guardrails.get("blocked")) and status in {"pending_approval", "applied", "partial"},
        "policy": policy,
        "action_result": action_result,
        "playbook_result": playbook_result,
        "connector_action_plan": connector_action_plan,
        "connector_action_result": connector_action_result,
        "evidence_chain": evidence_chain,
    }
    run = BlueManagedResponderRun(
        site_id=site.id,
        event_id=candidate.id,
        status=status,
        dry_run=resolved_dry_run,
        selected_severity=_normalize_severity(candidate.ai_severity),
        selected_action=selected_action,
        playbook_code=playbook_code,
        playbook_execution_id=playbook_execution_id[:64],
        action_applied=action_applied,
        playbook_dispatched=playbook_dispatched,
        details_json=_as_json(details),
        created_at=created_at,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {
        "status": status,
        "site_id": str(site.id),
        "site_code": site.site_code,
        "policy": policy,
        "guardrails": guardrails,
        "candidate_event": {
            "event_id": str(candidate.id),
            "event_type": candidate.event_type,
            "source_ip": candidate.source_ip,
            "ai_severity": candidate.ai_severity,
            "ai_recommendation": candidate.ai_recommendation,
            "status": candidate.status,
        },
        "action_result": action_result,
        "playbook_result": playbook_result,
        "connector_result": connector_action_result,
        "run": _run_row(run),
    }


def review_managed_responder_run(
    db: Session,
    *,
    site_id: UUID,
    run_id: UUID,
    approve: bool,
    approver: str = "security_lead",
    note: str = "",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "site_not_found", "site_id": str(site_id)}
    run = db.get(BlueManagedResponderRun, run_id)
    if not run or run.site_id != site.id:
        return {"status": "not_found", "site_id": str(site.id), "run_id": str(run_id)}
    if run.status not in {"pending_approval"}:
        return {"status": "no_op", "site_id": str(site.id), "run": _run_row(run)}

    details = _safe_json(run.details_json)
    action_result: dict[str, Any] = {"status": "skipped"}
    playbook_review: dict[str, Any] = {"status": "skipped"}
    connector_plan = details.get("connector_action_plan", {})
    if not isinstance(connector_plan, dict):
        connector_plan = {}
    connector_result = details.get("connector_action_result", {})
    if not isinstance(connector_result, dict):
        connector_result = {}
    if approve and run.event_id and not run.action_applied and run.selected_action != "ignore":
        action_result = apply_blue_recommendation(db, site.id, run.event_id, run.selected_action)
        run.action_applied = action_result.get("status") == "applied"
        if run.action_applied:
            connector_result = _execute_connector_action_plan(connector_plan, dry_run=False, actor=approver)
    if not approve and run.action_applied and run.event_id:
        rollback_state = _restore_event_state(
            db,
            site_id=site.id,
            event_id=run.event_id,
            previous_status=str(details.get("candidate_status_before", "open") or "open"),
            previous_action=str(details.get("candidate_action_before", "") or ""),
        )
        if rollback_state.get("status") == "rolled_back":
            run.action_applied = False
            action_result = {"status": "rolled_back_before_reject", **rollback_state}
            connector_result = {"status": "rolled_back_before_reject", **connector_result}

    execution_id = _safe_uuid(run.playbook_execution_id)
    if execution_id:
        playbook_review = approve_playbook_execution(
            db,
            execution_id=execution_id,
            approve=approve,
            approver=approver,
            note=note,
        )

    run.status = (
        "applied"
        if approve and (run.action_applied or playbook_review.get("status") == "applied")
        else "approved_no_action"
        if approve
        else "rejected"
    )
    details["action_result"] = action_result
    details["playbook_review"] = playbook_review
    details["connector_action_result"] = connector_result if approve else {**connector_result, "status": "rejected"}
    details["last_review"] = {
        "approve": bool(approve),
        "approver": approver,
        "note": note,
        "recorded_at": _now().isoformat(),
    }
    _append_audit_entry(details, kind="approval_review", actor=approver, note=note, status=run.status)
    run.details_json = _as_json(details)
    db.commit()
    db.refresh(run)
    return {
        "status": run.status,
        "site_id": str(site.id),
        "site_code": site.site_code,
        "run": _run_row(run),
        "action_result": action_result,
        "playbook_review": playbook_review,
        "connector_result": details.get("connector_action_result", {}),
    }


def _restore_event_state(
    db: Session,
    *,
    site_id: UUID,
    event_id: UUID,
    previous_status: str,
    previous_action: str,
) -> dict[str, Any]:
    event = db.get(BlueEventLog, event_id)
    if not event or event.site_id != site_id:
        return {"status": "event_not_found"}
    event.status = str(previous_status or "open")[:16]
    event.action_taken = str(previous_action or "")[:64]
    return {"status": "rolled_back", "event_id": str(event.id), "status_restored": event.status, "action_restored": event.action_taken}


def _rollback_playbook_execution(
    db: Session,
    *,
    execution_id: UUID,
    actor: str,
    note: str,
) -> dict[str, Any]:
    row = db.get(SoarPlaybookExecution, execution_id)
    if not row:
        return {"status": "not_found"}
    current_result = _safe_json(row.result_json)
    current_result["rollback_note"] = note
    current_result["rolled_back_by"] = actor
    current_result["rolled_back_at"] = _now().isoformat()
    if row.status == "pending_approval":
        row.status = "rejected"
    elif row.status == "applied":
        row.status = "rolled_back"
    else:
        return {"status": "no_op", "execution_id": str(row.id), "current_status": row.status}
    row.approved_by = actor
    row.result_json = _as_json(current_result)
    row.updated_at = _now()
    return {"status": row.status, "execution_id": str(row.id)}


def rollback_managed_responder_run(
    db: Session,
    *,
    site_id: UUID,
    run_id: UUID,
    actor: str = "security_operator",
    note: str = "",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "site_not_found", "site_id": str(site_id)}
    run = db.get(BlueManagedResponderRun, run_id)
    if not run or run.site_id != site.id:
        return {"status": "not_found", "site_id": str(site.id), "run_id": str(run_id)}
    if run.status == "rolled_back":
        return {"status": "no_op", "site_id": str(site.id), "run": _run_row(run)}

    details = _safe_json(run.details_json)
    rollback_result: dict[str, Any] = {"status": "skipped"}
    if run.event_id:
        rollback_result = _restore_event_state(
            db,
            site_id=site.id,
            event_id=run.event_id,
            previous_status=str(details.get("candidate_status_before", "open") or "open"),
            previous_action=str(details.get("candidate_action_before", "") or ""),
        )
    playbook_rollback: dict[str, Any] = {"status": "skipped"}
    execution_id = _safe_uuid(run.playbook_execution_id)
    if execution_id:
        playbook_rollback = _rollback_playbook_execution(db, execution_id=execution_id, actor=actor, note=note)
    connector_plan = details.get("connector_action_plan", {})
    if not isinstance(connector_plan, dict):
        connector_plan = {}
    connector_rollback = _rollback_connector_action(connector_plan, actor=actor, note=note)

    run.status = "rolled_back"
    run.action_applied = False
    details["rollback"] = {
        "actor": actor,
        "note": note,
        "rollback_result": rollback_result,
        "playbook_rollback": playbook_rollback,
        "connector_rollback": connector_rollback,
        "recorded_at": _now().isoformat(),
    }
    _append_audit_entry(details, kind="rollback", actor=actor, note=note, status="rolled_back")
    run.details_json = _as_json(details)
    db.commit()
    db.refresh(run)
    return {
        "status": "rolled_back",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "run": _run_row(run),
        "rollback_result": rollback_result,
        "playbook_rollback": playbook_rollback,
        "connector_rollback": connector_rollback,
    }


def verify_managed_responder_evidence_chain(db: Session, *, site_id: UUID, limit: int = 100) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "site_not_found", "site_id": str(site_id)}
    newest_rows = db.scalars(
        select(BlueManagedResponderRun)
        .where(BlueManagedResponderRun.site_id == site.id)
        .order_by(desc(BlueManagedResponderRun.created_at))
        .limit(max(1, min(limit, 500)))
    ).all()
    rows = list(reversed(newest_rows))
    previous_signature = ""
    valid = True
    summaries: list[dict[str, Any]] = []
    for row in rows:
        details = _safe_json(row.details_json)
        evidence = details.get("evidence_chain", {})
        if not isinstance(evidence, dict):
            evidence = {}
        signed_payload = evidence.get("signed_payload", {})
        if not isinstance(signed_payload, dict):
            signed_payload = {}
        expected_signature = _sign_evidence_payload(signed_payload, str(evidence.get("previous_signature", "") or ""))
        chain_valid = (
            str(evidence.get("signature", "") or "") == expected_signature
            and str(evidence.get("previous_signature", "") or "") == previous_signature
        )
        if chain_valid:
            previous_signature = str(evidence.get("signature", "") or "")
        else:
            valid = False
        summaries.append(
            {
                "run_id": str(row.id),
                "status": row.status,
                "sequence": int(evidence.get("sequence", 0) or 0),
                "signature": str(evidence.get("signature", "") or ""),
                "previous_signature": str(evidence.get("previous_signature", "") or ""),
                "valid": chain_valid,
                "created_at": _safe_iso(row.created_at),
            }
        )
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "count": len(summaries),
        "valid": valid,
        "rows": list(reversed(summaries)),
    }


def _is_schedule_due(last_run: BlueManagedResponderRun | None, *, now: datetime) -> bool:
    if last_run is None or last_run.created_at is None:
        return True
    created_at = last_run.created_at if last_run.created_at.tzinfo else last_run.created_at.replace(tzinfo=timezone.utc)
    cooldown_minutes = max(5, int(getattr(settings, "blue_managed_responder_scheduler_cooldown_minutes", 15)))
    return created_at <= now - timedelta(minutes=cooldown_minutes)


def run_managed_responder_scheduler(
    db: Session,
    *,
    limit: int = 100,
    dry_run_override: bool | None = None,
    actor: str = "blue_managed_responder_scheduler",
) -> dict[str, Any]:
    now = _now()
    policies = db.scalars(
        select(BlueManagedResponderPolicy)
        .where(BlueManagedResponderPolicy.enabled.is_(True))
        .order_by(desc(BlueManagedResponderPolicy.updated_at))
        .limit(max(1, min(limit, 500)))
    ).all()

    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for policy in policies:
        site = db.get(Site, policy.site_id)
        if not site:
            skipped.append({"site_id": str(policy.site_id), "status": "site_not_found"})
            continue
        last_run = db.scalar(
            select(BlueManagedResponderRun)
            .where(BlueManagedResponderRun.site_id == site.id)
            .order_by(desc(BlueManagedResponderRun.created_at))
            .limit(1)
        )
        if not _is_schedule_due(last_run, now=now):
            skipped.append({"site_id": str(site.id), "site_code": site.site_code, "status": "cooldown_not_elapsed"})
            continue
        result = run_managed_responder(
            db,
            site_id=site.id,
            dry_run=dry_run_override,
            force=False,
            actor=actor,
        )
        if result.get("run"):
            executed.append(
                {
                    "site_id": str(site.id),
                    "site_code": site.site_code,
                    "status": str(result.get("status", "")),
                    "run_id": str(result.get("run", {}).get("run_id", "")),
                    "candidate_event_id": str(result.get("candidate_event", {}).get("event_id", "")),
                    "selected_action": str(result.get("run", {}).get("selected_action", "")),
                }
            )
        else:
            skipped.append({"site_id": str(site.id), "site_code": site.site_code, "status": str(result.get("status", "skipped"))})

    return {
        "timestamp": now.isoformat(),
        "scheduled_policy_count": len(policies),
        "executed_count": len(executed),
        "skipped_count": len(skipped),
        "executed": executed,
        "skipped": skipped,
    }


def process_managed_responder_schedules(limit: int = 100) -> dict[str, Any]:
    with SessionLocal() as db:
        return run_managed_responder_scheduler(
            db,
            limit=max(1, min(limit, 500)),
            dry_run_override=bool(getattr(settings, "blue_managed_responder_scheduler_default_dry_run", True)),
            actor="autonomous_blue_managed_responder",
        )
