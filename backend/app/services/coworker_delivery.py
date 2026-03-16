from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    AiCoworkerDeliveryEvent,
    AiCoworkerPlugin,
    AiCoworkerPluginRun,
    Site,
    SiteAiCoworkerDeliveryEscalationPolicy,
    SiteAiCoworkerDeliveryProfile,
)
from app.db.session import SessionLocal
from app.services.notifier import send_line_message, send_telegram_message, send_webhook_message

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
SUPPORTED_CHANNELS = {"telegram", "line", "teams", "webhook"}


def _as_json(value: Any) -> str:
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


def _safe_json_list(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        payload = json.loads(value)
        if isinstance(payload, list):
            return payload
    except Exception:
        pass
    return []


def _safe_iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_channel(value: str) -> str:
    channel = str(value or "").strip().lower()
    return channel[:32] or "telegram"


def _default_profile(site_id: UUID, channel: str) -> dict[str, Any]:
    default_mode = "auto" if channel in {"telegram", "line"} else "manual"
    return {
        "profile_id": "",
        "site_id": str(site_id),
        "channel": channel,
        "enabled": False,
        "min_severity": "medium",
        "delivery_mode": default_mode,
        "require_approval": True,
        "include_thai_summary": True,
        "webhook_url": "",
        "owner": "system",
        "created_at": "",
        "updated_at": "",
    }


def _profile_row(row: SiteAiCoworkerDeliveryProfile) -> dict[str, Any]:
    return {
        "profile_id": str(row.id),
        "site_id": str(row.site_id),
        "channel": row.channel,
        "enabled": bool(row.enabled),
        "min_severity": row.min_severity,
        "delivery_mode": row.delivery_mode,
        "require_approval": bool(row.require_approval),
        "include_thai_summary": bool(row.include_thai_summary),
        "webhook_url": row.webhook_url,
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _escalation_policy_row(row: SiteAiCoworkerDeliveryEscalationPolicy) -> dict[str, Any]:
    return {
        "policy_id": str(row.id),
        "site_id": str(row.site_id),
        "plugin_code": row.plugin_code,
        "enabled": bool(row.enabled),
        "escalate_after_minutes": int(row.escalate_after_minutes),
        "max_escalation_count": int(row.max_escalation_count),
        "fallback_channels": [str(item) for item in _safe_json_list(row.fallback_channels_json)],
        "escalate_on_statuses": [str(item) for item in _safe_json_list(row.escalate_on_statuses_json)],
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _default_escalation_policy(site_id: UUID, plugin_code: str) -> dict[str, Any]:
    return {
        "policy_id": "",
        "site_id": str(site_id),
        "plugin_code": plugin_code,
        "enabled": False,
        "escalate_after_minutes": 15,
        "max_escalation_count": 2,
        "fallback_channels": ["telegram", "line"],
        "escalate_on_statuses": ["approval_required", "failed"],
        "owner": "system",
        "created_at": "",
        "updated_at": "",
    }


def _event_row(row: AiCoworkerDeliveryEvent, plugin: AiCoworkerPlugin | None = None) -> dict[str, Any]:
    plugin_ref = plugin or row.plugin
    response = _safe_json_dict(row.response_json)
    return {
        "event_id": str(row.id),
        "site_id": str(row.site_id),
        "plugin_id": str(row.plugin_id) if row.plugin_id else "",
        "plugin_code": plugin_ref.plugin_code if plugin_ref else "",
        "display_name_th": plugin_ref.display_name_th if plugin_ref else "",
        "channel": row.channel,
        "status": row.status,
        "dry_run": bool(row.dry_run),
        "severity": row.severity,
        "title": row.title,
        "preview_text": row.preview_text,
        "actor": row.actor,
        "response": response,
        "approval_required": row.status == "approval_required" or bool(response.get("approval_requested_at")),
        "created_at": _safe_iso(row.created_at),
    }


def _message_from_run(site: Site, plugin: AiCoworkerPlugin, run: AiCoworkerPluginRun, include_thai_summary: bool) -> dict[str, Any]:
    output_summary = _safe_json_dict(run.output_summary_json)
    severity = str(output_summary.get("severity", "medium") or "medium").lower()
    severity = severity if severity in SEVERITY_ORDER else "medium"
    headline = str(output_summary.get("headline", plugin.display_name_th or plugin.display_name) or plugin.display_name)
    summary_th = str(output_summary.get("summary_th", "") or "").strip()
    body_lines = [
        f"[BRP Cyber AI Co-worker][{plugin.category.upper()}][{severity.upper()}]",
        f"ไซต์: {site.display_name} ({site.site_code})",
        f"ปลั๊กอิน: {plugin.display_name_th or plugin.display_name}",
        f"หัวข้อ: {headline}",
    ]
    if include_thai_summary and summary_th:
        body_lines.append(f"สรุป: {summary_th}")
    body_lines.append(f"run_id: {run.id}")
    message = "\n".join(body_lines)
    return {
        "severity": severity,
        "title": headline[:255],
        "message": message,
        "payload": {
            "site_id": str(site.id),
            "site_code": site.site_code,
            "plugin_code": plugin.plugin_code,
            "plugin_category": plugin.category,
            "run_id": str(run.id),
            "status": run.status,
            "output_summary": output_summary,
        },
    }


def _severity_allowed(min_severity: str, severity: str) -> bool:
    return SEVERITY_ORDER.get(str(severity).lower(), 1) >= SEVERITY_ORDER.get(str(min_severity).lower(), 1)


def _dispatch_to_channel(*, channel_name: str, profile: dict[str, Any], preview: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    message = str(preview.get("message", ""))
    title = str(preview.get("title", ""))
    response_payload: dict[str, Any] = {"channel": channel_name}
    if channel_name == "telegram":
        delivered = send_telegram_message(message)
        status = "sent" if delivered else "failed"
    elif channel_name == "line":
        delivered = send_line_message(message)
        status = "sent" if delivered else "failed"
    else:
        payload = dict(preview.get("payload", {}) or {})
        payload["title"] = title
        payload["message"] = message
        delivered = send_webhook_message(str(profile.get("webhook_url", "")), payload)
        status = "sent" if delivered else "failed"
        response_payload["webhook_payload"] = payload
    response_payload["delivered"] = delivered
    response_payload["dispatched_at"] = _now().isoformat()
    return status, response_payload


def _get_site_plugin_and_run(db: Session, site_id: UUID, plugin_code: str) -> tuple[Site | None, AiCoworkerPlugin | None, AiCoworkerPluginRun | None]:
    site = db.get(Site, site_id)
    if not site:
        return None, None, None
    plugin = db.scalar(select(AiCoworkerPlugin).where(AiCoworkerPlugin.plugin_code == plugin_code))
    if not plugin or not plugin.is_active:
        return site, None, None
    run = db.scalar(
        select(AiCoworkerPluginRun)
        .where(AiCoworkerPluginRun.site_id == site.id, AiCoworkerPluginRun.plugin_id == plugin.id)
        .order_by(desc(AiCoworkerPluginRun.created_at))
        .limit(1)
    )
    return site, plugin, run


def upsert_site_coworker_delivery_profile(
    db: Session,
    *,
    site_id: UUID,
    channel: str,
    enabled: bool,
    min_severity: str,
    delivery_mode: str,
    require_approval: bool,
    include_thai_summary: bool,
    webhook_url: str,
    owner: str,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    normalized_channel = _normalize_channel(channel)
    if normalized_channel not in SUPPORTED_CHANNELS:
        return {"status": "invalid_channel", "channel": normalized_channel}

    row = db.scalar(
        select(SiteAiCoworkerDeliveryProfile).where(
            SiteAiCoworkerDeliveryProfile.site_id == site.id,
            SiteAiCoworkerDeliveryProfile.channel == normalized_channel,
        )
    )
    now = datetime.now(timezone.utc)
    safe_severity = str(min_severity or "medium").lower()
    if safe_severity not in SEVERITY_ORDER:
        safe_severity = "medium"
    safe_mode = str(delivery_mode or "manual").lower()
    if safe_mode not in {"manual", "auto"}:
        safe_mode = "manual"

    if row:
        row.enabled = bool(enabled)
        row.min_severity = safe_severity
        row.delivery_mode = safe_mode
        row.require_approval = bool(require_approval)
        row.include_thai_summary = bool(include_thai_summary)
        row.webhook_url = webhook_url.strip()[:2048]
        row.owner = owner.strip()[:64] or "security"
        row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"status": "updated", "profile": _profile_row(row)}

    created = SiteAiCoworkerDeliveryProfile(
        site_id=site.id,
        channel=normalized_channel,
        enabled=bool(enabled),
        min_severity=safe_severity,
        delivery_mode=safe_mode,
        require_approval=bool(require_approval),
        include_thai_summary=bool(include_thai_summary),
        webhook_url=webhook_url.strip()[:2048],
        owner=owner.strip()[:64] or "security",
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"status": "created", "profile": _profile_row(created)}


def list_site_coworker_delivery_profiles(db: Session, *, site_id: UUID) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"site_id": str(site_id), "count": 0, "rows": []}

    rows = db.scalars(
        select(SiteAiCoworkerDeliveryProfile)
        .where(SiteAiCoworkerDeliveryProfile.site_id == site.id)
        .order_by(SiteAiCoworkerDeliveryProfile.channel)
    ).all()
    row_map = {row.channel: row for row in rows}
    ordered_rows = []
    for channel in ["telegram", "line", "teams", "webhook"]:
        ordered_rows.append(_profile_row(row_map[channel]) if channel in row_map else _default_profile(site.id, channel))
    return {"site_id": str(site.id), "count": len(ordered_rows), "rows": ordered_rows}


def preview_site_coworker_delivery(
    db: Session,
    *,
    site_id: UUID,
    plugin_code: str,
    channel: str,
) -> dict[str, Any]:
    normalized_channel = _normalize_channel(channel)
    if normalized_channel not in SUPPORTED_CHANNELS:
        return {"status": "invalid_channel", "channel": normalized_channel}
    site, plugin, run = _get_site_plugin_and_run(db, site_id, plugin_code)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    if not plugin:
        return {"status": "plugin_not_found", "plugin_code": plugin_code}
    if not run:
        return {"status": "no_plugin_run", "plugin_code": plugin_code, "site_id": str(site.id)}

    profile_row = db.scalar(
        select(SiteAiCoworkerDeliveryProfile).where(
            SiteAiCoworkerDeliveryProfile.site_id == site.id,
            SiteAiCoworkerDeliveryProfile.channel == normalized_channel,
        )
    )
    profile = _profile_row(profile_row) if profile_row else _default_profile(site.id, normalized_channel)
    preview = _message_from_run(site, plugin, run, bool(profile.get("include_thai_summary", True)))
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "plugin": {
            "plugin_id": str(plugin.id),
            "plugin_code": plugin.plugin_code,
            "display_name": plugin.display_name,
            "display_name_th": plugin.display_name_th,
            "category": plugin.category,
        },
        "profile": profile,
        "preview": {
            "channel": normalized_channel,
            **preview,
        },
        "run": {
            "run_id": str(run.id),
            "status": run.status,
            "created_at": _safe_iso(run.created_at),
        },
    }


def dispatch_site_coworker_delivery(
    db: Session,
    *,
    site_id: UUID,
    plugin_code: str,
    channel: str,
    dry_run: bool | None = None,
    force: bool = False,
    actor: str = "coworker_delivery_ai",
) -> dict[str, Any]:
    preview_result = preview_site_coworker_delivery(db, site_id=site_id, plugin_code=plugin_code, channel=channel)
    if preview_result.get("status") != "ok":
        return preview_result

    site = db.get(Site, site_id)
    plugin = db.scalar(select(AiCoworkerPlugin).where(AiCoworkerPlugin.plugin_code == plugin_code))
    preview = dict(preview_result.get("preview", {}) or {})
    profile = dict(preview_result.get("profile", {}) or {})
    severity = str(preview.get("severity", "medium"))
    resolved_dry_run = True if dry_run is None else bool(dry_run)
    approval_sla_minutes = max(1, int(getattr(settings, "coworker_delivery_approval_sla_minutes", 15)))

    status = "dry_run"
    response_payload: dict[str, Any] = {
        "channel": preview.get("channel", channel),
        "profile": profile,
        "preview": preview,
        "plugin": preview_result.get("plugin", {}),
    }

    if not bool(profile.get("enabled", False)) and not force:
        status = "disabled"
    elif not _severity_allowed(str(profile.get("min_severity", "medium")), severity) and not force:
        status = "filtered_threshold"
    elif bool(profile.get("require_approval", True)) and not resolved_dry_run and not force:
        status = "approval_required"
        response_payload["approval_requested_at"] = _now().isoformat()
        response_payload["approval_sla_due_at"] = (_now() + timedelta(minutes=approval_sla_minutes)).isoformat()
    elif resolved_dry_run:
        status = "dry_run"
    else:
        channel_name = str(preview.get("channel", channel))
        status, dispatched_payload = _dispatch_to_channel(channel_name=channel_name, profile=profile, preview=preview)
        response_payload.update(dispatched_payload)

    event = AiCoworkerDeliveryEvent(
        site_id=site.id if site else site_id,
        plugin_id=plugin.id if plugin else None,
        channel=str(preview.get("channel", channel)),
        status=status,
        dry_run=resolved_dry_run,
        severity=severity,
        title=str(preview.get("title", ""))[:255],
        preview_text=str(preview.get("message", ""))[:4000],
        actor=actor[:128],
        response_json=_as_json(response_payload),
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return {
        "status": status,
        "site_id": str(site.id) if site else str(site_id),
        "site_code": site.site_code if site else "",
        "plugin": preview_result.get("plugin", {}),
        "profile": profile,
        "preview": preview,
        "event": _event_row(event, plugin),
    }


def review_site_coworker_delivery_event(
    db: Session,
    *,
    site_id: UUID,
    event_id: UUID,
    approve: bool,
    actor: str = "security_reviewer",
    note: str = "",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    row = db.get(AiCoworkerDeliveryEvent, event_id)
    if not row or row.site_id != site.id:
        return {"status": "event_not_found", "site_id": str(site.id), "event_id": str(event_id)}

    response_payload = _safe_json_dict(row.response_json)
    if row.status != "approval_required":
        return {
            "status": "no_op",
            "site_id": str(site.id),
            "site_code": site.site_code,
            "event": _event_row(row),
        }

    preview = response_payload.get("preview", {})
    if not isinstance(preview, dict):
        preview = {}
    profile = response_payload.get("profile", {})
    if not isinstance(profile, dict):
        profile = {}

    if approve:
        status, dispatched = _dispatch_to_channel(channel_name=row.channel, profile=profile, preview=preview)
        response_payload.update(dispatched)
    else:
        status = "rejected"

    reviewed_at = _now()
    approval_requested_at_raw = str(response_payload.get("approval_requested_at", "") or "")
    approval_latency_seconds = 0
    if approval_requested_at_raw:
        try:
            requested_at = datetime.fromisoformat(approval_requested_at_raw)
            if requested_at.tzinfo is None:
                requested_at = requested_at.replace(tzinfo=timezone.utc)
            approval_latency_seconds = max(0, int((reviewed_at - requested_at).total_seconds()))
        except Exception:
            approval_latency_seconds = 0
    response_payload["review"] = {
        "approved": bool(approve),
        "actor": actor,
        "note": note,
        "reviewed_at": reviewed_at.isoformat(),
        "approval_latency_seconds": approval_latency_seconds,
    }
    row.status = status
    row.response_json = _as_json(response_payload)
    db.commit()
    db.refresh(row)
    return {
        "status": status,
        "site_id": str(site.id),
        "site_code": site.site_code,
        "event": _event_row(row),
    }


def get_site_coworker_delivery_sla(
    db: Session,
    *,
    site_id: UUID,
    limit: int = 100,
    approval_sla_minutes: int | None = None,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    rows = db.scalars(
        select(AiCoworkerDeliveryEvent)
        .where(AiCoworkerDeliveryEvent.site_id == site.id)
        .order_by(desc(AiCoworkerDeliveryEvent.created_at))
        .limit(max(1, min(limit, 500)))
    ).all()
    now = _now()
    sla_minutes = max(1, int(approval_sla_minutes or getattr(settings, "coworker_delivery_approval_sla_minutes", 15)))
    pending_count = 0
    overdue_count = 0
    approval_latencies: list[int] = []
    pending_rows: list[dict[str, Any]] = []
    for row in rows:
        response = _safe_json_dict(row.response_json)
        if row.status == "approval_required":
            pending_count += 1
            created_at = row.created_at if row.created_at and row.created_at.tzinfo else (row.created_at.replace(tzinfo=timezone.utc) if row.created_at else now)
            due_at = created_at + timedelta(minutes=sla_minutes)
            overdue = due_at < now
            if overdue:
                overdue_count += 1
            pending_rows.append(
                {
                    "event_id": str(row.id),
                    "channel": row.channel,
                    "title": row.title,
                    "created_at": _safe_iso(row.created_at),
                    "due_at": due_at.isoformat(),
                    "overdue": overdue,
                }
            )
        review = response.get("review", {})
        if isinstance(review, dict):
            latency = int(review.get("approval_latency_seconds", 0) or 0)
            if latency > 0:
                approval_latencies.append(latency)
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "approval_sla_minutes": sla_minutes,
        "summary": {
            "total_events": len(rows),
            "pending_approval_count": pending_count,
            "overdue_count": overdue_count,
            "approved_or_reviewed_count": len(approval_latencies),
            "average_approval_latency_seconds": round(sum(approval_latencies) / len(approval_latencies), 2) if approval_latencies else 0.0,
        },
        "pending_rows": pending_rows[:20],
    }


def get_site_coworker_delivery_escalation_policy(
    db: Session,
    *,
    site_id: UUID,
    plugin_code: str,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    normalized_plugin_code = str(plugin_code or "").strip()
    if not normalized_plugin_code:
        return {"status": "invalid_plugin_code", "site_id": str(site.id)}
    row = db.scalar(
        select(SiteAiCoworkerDeliveryEscalationPolicy).where(
            SiteAiCoworkerDeliveryEscalationPolicy.site_id == site.id,
            SiteAiCoworkerDeliveryEscalationPolicy.plugin_code == normalized_plugin_code,
        )
    )
    if not row:
        return {
            "status": "default",
            "site_id": str(site.id),
            "site_code": site.site_code,
            "policy": _default_escalation_policy(site.id, normalized_plugin_code),
        }
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "policy": _escalation_policy_row(row),
    }


def upsert_site_coworker_delivery_escalation_policy(
    db: Session,
    *,
    site_id: UUID,
    plugin_code: str,
    enabled: bool,
    escalate_after_minutes: int,
    max_escalation_count: int,
    fallback_channels: list[str],
    escalate_on_statuses: list[str],
    owner: str,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    normalized_plugin_code = str(plugin_code or "").strip()
    if not normalized_plugin_code:
        return {"status": "invalid_plugin_code", "site_id": str(site.id)}
    safe_channels = [
        channel
        for channel in (_normalize_channel(item) for item in fallback_channels or [])
        if channel in SUPPORTED_CHANNELS
    ] or ["telegram", "line"]
    safe_statuses = [str(item).strip() for item in (escalate_on_statuses or []) if str(item).strip()] or [
        "approval_required",
        "failed",
    ]
    row = db.scalar(
        select(SiteAiCoworkerDeliveryEscalationPolicy).where(
            SiteAiCoworkerDeliveryEscalationPolicy.site_id == site.id,
            SiteAiCoworkerDeliveryEscalationPolicy.plugin_code == normalized_plugin_code,
        )
    )
    now = _now()
    if row:
        row.enabled = bool(enabled)
        row.escalate_after_minutes = max(1, min(int(escalate_after_minutes or 15), 1440))
        row.max_escalation_count = max(1, min(int(max_escalation_count or 2), 10))
        row.fallback_channels_json = _as_json(safe_channels)
        row.escalate_on_statuses_json = _as_json(safe_statuses)
        row.owner = owner.strip()[:64] or "security"
        row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"status": "updated", "policy": _escalation_policy_row(row)}

    created = SiteAiCoworkerDeliveryEscalationPolicy(
        site_id=site.id,
        plugin_code=normalized_plugin_code,
        enabled=bool(enabled),
        escalate_after_minutes=max(1, min(int(escalate_after_minutes or 15), 1440)),
        max_escalation_count=max(1, min(int(max_escalation_count or 2), 10)),
        fallback_channels_json=_as_json(safe_channels),
        escalate_on_statuses_json=_as_json(safe_statuses),
        owner=owner.strip()[:64] or "security",
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"status": "created", "policy": _escalation_policy_row(created)}


def run_site_coworker_delivery_escalation(
    db: Session,
    *,
    site_id: UUID,
    plugin_code: str,
    dry_run: bool | None = None,
    force: bool = False,
    actor: str = "delivery_escalator_ai",
    limit: int = 50,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    plugin = db.scalar(select(AiCoworkerPlugin).where(AiCoworkerPlugin.plugin_code == plugin_code))
    if not plugin:
        return {"status": "plugin_not_found", "site_id": str(site.id), "plugin_code": plugin_code}
    policy_result = get_site_coworker_delivery_escalation_policy(db, site_id=site.id, plugin_code=plugin_code)
    policy = dict(policy_result.get("policy", {}) or {})
    if not bool(policy.get("enabled", False)) and not force:
        return {
            "status": "disabled",
            "site_id": str(site.id),
            "site_code": site.site_code,
            "policy": policy,
            "executed_count": 0,
            "skipped_count": 0,
            "executed": [],
            "skipped": [],
        }

    resolved_dry_run = True if dry_run is None else bool(dry_run)
    fallback_channels = [str(item).strip() for item in policy.get("fallback_channels", []) if str(item).strip()]
    escalate_statuses = {str(item).strip() for item in policy.get("escalate_on_statuses", []) if str(item).strip()}
    escalate_after_minutes = max(1, int(policy.get("escalate_after_minutes", 15) or 15))
    max_escalation_count = max(1, int(policy.get("max_escalation_count", 2) or 2))

    rows = db.scalars(
        select(AiCoworkerDeliveryEvent)
        .where(AiCoworkerDeliveryEvent.site_id == site.id, AiCoworkerDeliveryEvent.plugin_id == plugin.id)
        .order_by(desc(AiCoworkerDeliveryEvent.created_at))
        .limit(max(1, min(limit, 500)))
    ).all()

    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    now = _now()

    for source_event in rows:
        response = _safe_json_dict(source_event.response_json)
        if source_event.status not in escalate_statuses:
            skipped.append({"event_id": str(source_event.id), "reason": "status_not_eligible", "status": source_event.status})
            continue

        escalation = response.get("escalation", {})
        if not isinstance(escalation, dict):
            escalation = {}
        attempt_count = int(escalation.get("attempt_count", 0) or 0)
        if attempt_count >= max_escalation_count and not force:
            skipped.append({"event_id": str(source_event.id), "reason": "max_escalation_count_reached", "attempt_count": attempt_count})
            continue

        if source_event.status == "approval_required" and not force:
            approval_requested_at_raw = str(response.get("approval_requested_at", "") or "")
            due_at = source_event.created_at or now
            if approval_requested_at_raw:
                try:
                    due_at = datetime.fromisoformat(approval_requested_at_raw)
                    if due_at.tzinfo is None:
                        due_at = due_at.replace(tzinfo=timezone.utc)
                except Exception:
                    due_at = source_event.created_at or now
            due_at = due_at + timedelta(minutes=escalate_after_minutes)
            if due_at > now:
                skipped.append({"event_id": str(source_event.id), "reason": "within_sla_window", "due_at": due_at.isoformat()})
                continue

        preview = response.get("preview", {})
        if not isinstance(preview, dict):
            preview = {}
        preview.setdefault("severity", source_event.severity)
        preview.setdefault("title", source_event.title)
        preview.setdefault("message", source_event.preview_text)
        preview.setdefault("payload", {})

        target_channel = next((channel for channel in fallback_channels if channel != source_event.channel), "")
        if not target_channel:
            skipped.append({"event_id": str(source_event.id), "reason": "no_fallback_channel"})
            continue

        profile_row = db.scalar(
            select(SiteAiCoworkerDeliveryProfile).where(
                SiteAiCoworkerDeliveryProfile.site_id == site.id,
                SiteAiCoworkerDeliveryProfile.channel == target_channel,
            )
        )
        profile = _profile_row(profile_row) if profile_row else _default_profile(site.id, target_channel)
        if not bool(profile.get("enabled", False)) and not force:
            skipped.append({"event_id": str(source_event.id), "reason": "fallback_profile_disabled", "channel": target_channel})
            continue

        preview["channel"] = target_channel
        if resolved_dry_run:
            delivery_status = "escalation_dry_run"
            delivery_response = {"delivered": False, "dry_run": True, "channel": target_channel}
        else:
            delivery_status, delivery_response = _dispatch_to_channel(
                channel_name=target_channel,
                profile=profile,
                preview=preview,
            )
            if delivery_status == "sent":
                delivery_status = "escalated_sent"
            elif delivery_status == "failed":
                delivery_status = "escalated_failed"

        new_response = {
            "profile": profile,
            "preview": preview,
            "escalation": {
                "source_event_id": str(source_event.id),
                "source_status": source_event.status,
                "attempt_count": attempt_count + 1,
                "fallback_channel": target_channel,
                "actor": actor,
            },
            **delivery_response,
        }
        event = AiCoworkerDeliveryEvent(
            site_id=site.id,
            plugin_id=plugin.id,
            channel=target_channel,
            status=delivery_status,
            dry_run=resolved_dry_run,
            severity=str(preview.get("severity", source_event.severity)),
            title=str(preview.get("title", source_event.title))[:255],
            preview_text=str(preview.get("message", source_event.preview_text))[:4000],
            actor=actor[:128],
            response_json=_as_json(new_response),
            created_at=now,
        )
        db.add(event)
        response["escalation"] = {
            "attempt_count": attempt_count + 1,
            "last_channel": target_channel,
            "last_status": delivery_status,
            "last_attempted_at": now.isoformat(),
        }
        source_event.response_json = _as_json(response)
        executed.append(
            {
                "source_event_id": str(source_event.id),
                "escalated_event_id": str(getattr(event, "id", "")),
                "channel": target_channel,
                "status": delivery_status,
            }
        )

    db.commit()
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "policy": policy,
        "executed_count": len(executed),
        "skipped_count": len(skipped),
        "executed": executed,
        "skipped": skipped,
    }


def list_site_coworker_delivery_events(
    db: Session,
    *,
    site_id: UUID,
    channel: str = "",
    limit: int = 100,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"site_id": str(site_id), "count": 0, "rows": []}
    stmt = (
        select(AiCoworkerDeliveryEvent)
        .where(AiCoworkerDeliveryEvent.site_id == site.id)
        .order_by(desc(AiCoworkerDeliveryEvent.created_at))
        .limit(max(1, min(limit, 500)))
    )
    normalized_channel = _normalize_channel(channel) if channel else ""
    if normalized_channel:
        stmt = stmt.where(AiCoworkerDeliveryEvent.channel == normalized_channel)
    rows = db.scalars(stmt).all()
    return {"site_id": str(site.id), "count": len(rows), "rows": [_event_row(row) for row in rows]}


def run_coworker_delivery_escalation_scheduler(
    db: Session,
    *,
    site_id: UUID | None = None,
    plugin_code: str = "",
    limit: int = 100,
    dry_run_override: bool | None = None,
    actor: str = "delivery_escalator_scheduler",
) -> dict[str, Any]:
    stmt = (
        select(SiteAiCoworkerDeliveryEscalationPolicy)
        .where(SiteAiCoworkerDeliveryEscalationPolicy.enabled.is_(True))
        .order_by(desc(SiteAiCoworkerDeliveryEscalationPolicy.updated_at))
        .limit(max(1, min(limit, 500)))
    )
    if site_id is not None:
        stmt = stmt.where(SiteAiCoworkerDeliveryEscalationPolicy.site_id == site_id)
    normalized_plugin_code = str(plugin_code or "").strip()
    if normalized_plugin_code:
        stmt = stmt.where(SiteAiCoworkerDeliveryEscalationPolicy.plugin_code == normalized_plugin_code)

    policies = db.scalars(stmt).all()
    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    resolved_dry_run = (
        bool(dry_run_override)
        if dry_run_override is not None
        else bool(getattr(settings, "coworker_delivery_escalation_scheduler_default_dry_run", True))
    )

    for policy in policies:
        site = db.get(Site, policy.site_id)
        if not site:
            skipped.append(
                {
                    "site_id": str(policy.site_id),
                    "plugin_code": policy.plugin_code,
                    "status": "site_not_found",
                }
            )
            continue
        result = run_site_coworker_delivery_escalation(
            db,
            site_id=site.id,
            plugin_code=policy.plugin_code,
            dry_run=resolved_dry_run,
            force=False,
            actor=actor,
        )
        if str(result.get("status", "")) == "ok":
            executed.append(
                {
                    "site_id": str(site.id),
                    "site_code": site.site_code,
                    "plugin_code": policy.plugin_code,
                    "status": "ok",
                    "executed_count": int(result.get("executed_count", 0) or 0),
                    "skipped_count": int(result.get("skipped_count", 0) or 0),
                }
            )
        else:
            skipped.append(
                {
                    "site_id": str(site.id),
                    "site_code": site.site_code,
                    "plugin_code": policy.plugin_code,
                    "status": str(result.get("status", "skipped")),
                }
            )

    return {
        "timestamp": _now().isoformat(),
        "dry_run": resolved_dry_run,
        "scheduled_policy_count": len(policies),
        "executed_count": len(executed),
        "skipped_count": len(skipped),
        "executed": executed,
        "skipped": skipped,
    }


def coworker_delivery_escalation_federation_snapshot(
    db: Session,
    *,
    plugin_code: str = "",
    approval_sla_minutes: int | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    normalized_plugin_code = str(plugin_code or "").strip()
    max_rows = max(1, min(limit, 500))
    sites = db.scalars(
        select(Site)
        .order_by(desc(Site.updated_at), desc(Site.created_at))
        .limit(max_rows)
    ).all()

    rows: list[dict[str, Any]] = []
    healthy_sites = 0
    attention_sites = 0
    not_configured_sites = 0
    pending_approval_total = 0
    overdue_total = 0
    enabled_profile_total = 0
    enabled_escalation_policy_total = 0

    for site in sites:
        profile_rows = db.scalars(
            select(SiteAiCoworkerDeliveryProfile)
            .where(SiteAiCoworkerDeliveryProfile.site_id == site.id)
            .order_by(SiteAiCoworkerDeliveryProfile.channel)
        ).all()
        policy_stmt = (
            select(SiteAiCoworkerDeliveryEscalationPolicy)
            .where(SiteAiCoworkerDeliveryEscalationPolicy.site_id == site.id)
            .order_by(desc(SiteAiCoworkerDeliveryEscalationPolicy.updated_at))
        )
        if normalized_plugin_code:
            policy_stmt = policy_stmt.where(SiteAiCoworkerDeliveryEscalationPolicy.plugin_code == normalized_plugin_code)
        policy_rows = db.scalars(policy_stmt.limit(200)).all()
        sla = get_site_coworker_delivery_sla(
            db,
            site_id=site.id,
            limit=200,
            approval_sla_minutes=approval_sla_minutes,
        )
        pending_approval_count = int(sla.get("summary", {}).get("pending_approval_count", 0) or 0)
        overdue_count = int(sla.get("summary", {}).get("overdue_count", 0) or 0)
        avg_latency_seconds = int(sla.get("summary", {}).get("average_approval_latency_seconds", 0) or 0)
        enabled_profile_count = sum(1 for row in profile_rows if bool(row.enabled))
        auto_profile_count = sum(1 for row in profile_rows if bool(row.enabled) and row.delivery_mode == "auto")
        enabled_policy_count = sum(1 for row in policy_rows if bool(row.enabled))
        plugin_codes = sorted({str(row.plugin_code).strip() for row in policy_rows if str(row.plugin_code).strip()})

        status = "healthy"
        if enabled_profile_count == 0 and enabled_policy_count == 0:
            status = "not_configured"
            not_configured_sites += 1
        elif overdue_count > 0 or pending_approval_count > 0:
            status = "attention"
            attention_sites += 1
        else:
            healthy_sites += 1

        recommended_action = "Maintain current delivery routing and review escalation evidence weekly."
        if status == "not_configured":
            recommended_action = "Enable at least one delivery channel and one escalation policy before go-live."
        elif overdue_count > 0:
            recommended_action = "Reduce approval backlog or widen fallback channels to keep delivery SLA inside target."
        elif pending_approval_count > 0:
            recommended_action = "Review pending approvals before they convert into overdue escalations."

        pending_approval_total += pending_approval_count
        overdue_total += overdue_count
        enabled_profile_total += enabled_profile_count
        enabled_escalation_policy_total += enabled_policy_count

        rows.append(
            {
                "site_id": str(site.id),
                "site_code": site.site_code,
                "tenant_code": getattr(site, "tenant_code", "") or getattr(getattr(site, "tenant", None), "tenant_code", ""),
                "status": status,
                "enabled_profile_count": enabled_profile_count,
                "auto_profile_count": auto_profile_count,
                "enabled_escalation_policy_count": enabled_policy_count,
                "pending_approval_count": pending_approval_count,
                "overdue_count": overdue_count,
                "average_approval_latency_seconds": avg_latency_seconds,
                "plugin_codes": plugin_codes,
                "recommended_action": recommended_action,
            }
        )

    rows.sort(
        key=lambda item: (
            2 if item["status"] == "attention" else 1 if item["status"] == "not_configured" else 0,
            item["overdue_count"],
            item["pending_approval_count"],
            item["enabled_escalation_policy_count"],
        ),
        reverse=True,
    )

    return {
        "status": "ok",
        "generated_at": _now().isoformat(),
        "plugin_code": normalized_plugin_code,
        "approval_sla_minutes": max(
            1,
            int(approval_sla_minutes or getattr(settings, "coworker_delivery_approval_sla_minutes", 15) or 15),
        ),
        "count": len(rows),
        "summary": {
            "total_sites": len(rows),
            "healthy_sites": healthy_sites,
            "attention_sites": attention_sites,
            "not_configured_sites": not_configured_sites,
            "pending_approval_total": pending_approval_total,
            "overdue_total": overdue_total,
            "enabled_profile_total": enabled_profile_total,
            "enabled_escalation_policy_total": enabled_escalation_policy_total,
        },
        "rows": rows,
    }


def process_coworker_delivery_escalation_schedules(limit: int = 100) -> dict[str, Any]:
    with SessionLocal() as db:
        return run_coworker_delivery_escalation_scheduler(
            db,
            limit=max(1, min(limit, 500)),
            dry_run_override=bool(
                getattr(settings, "coworker_delivery_escalation_scheduler_default_dry_run", True)
            ),
            actor="autonomous_delivery_escalator",
        )
