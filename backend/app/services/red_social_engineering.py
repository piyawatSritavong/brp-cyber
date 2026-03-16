from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    BlueEventLog,
    ConnectorDeliveryEvent,
    RedSocialCampaignExecution,
    RedSocialCampaignPolicy,
    RedSocialCampaignRecipient,
    RedSocialEngineeringRun,
    RedSocialRosterEntry,
    Site,
    ThreatContentPack,
)

CONNECTOR_TYPES = {"simulated", "smtp", "webhook"}
FINAL_SOCIAL_STATUSES = {"completed", "rejected", "killed", "blocked_by_kill_switch", "roster_required"}
CALLBACK_EVENT_TYPES = {"delivered", "opened", "clicked", "reported", "bounced", "complained"}
SOCIAL_CAMPAIGN_TYPES = {"awareness", "credential_reset", "hr_notice", "finance_notice", "brand_protection"}

SOCIAL_TEMPLATE_PACKS: list[dict[str, Any]] = [
    {
        "template_pack_code": "th_awareness_basic",
        "campaign_type": "awareness",
        "jurisdiction": "th",
        "title": "Thai Awareness Basic",
        "approval_required": True,
        "evidence_retention_days": 90,
        "legal_notice_th": "ใช้เพื่อการทดสอบภายในที่ได้รับอนุมัติเท่านั้น ต้องเก็บหลักฐานการส่งและการยินยอมตาม SOP ภายในองค์กร",
        "compliance_controls_th": ["PDPA awareness", "security awareness evidence", "internal change approval"],
        "recommended_subject_suffixes": ["ยืนยันการเข้าใช้งานบัญชีภายในวันนี้", "ตรวจสอบการแจ้งเตือนความปลอดภัยล่าสุด"],
    },
    {
        "template_pack_code": "th_hr_notice_pdpa",
        "campaign_type": "hr_notice",
        "jurisdiction": "th",
        "title": "Thai HR Notice / PDPA",
        "approval_required": True,
        "evidence_retention_days": 180,
        "legal_notice_th": "ใช้กับแบบทดสอบที่เลียนแบบเอกสาร HR/PDPA โดยต้องมีผู้อนุมัติจาก HR และ Security ก่อนส่งทุกครั้ง",
        "compliance_controls_th": ["PDPA notification handling", "HR approval trace", "awareness drill evidence"],
        "recommended_subject_suffixes": ["ยืนยันเอกสาร HR/PDPA ภายในวันทำการนี้", "ตรวจสอบการอัปเดตข้อมูลพนักงาน"],
    },
    {
        "template_pack_code": "th_finance_regulated",
        "campaign_type": "finance_notice",
        "jurisdiction": "th",
        "title": "Thai Finance Regulated",
        "approval_required": True,
        "evidence_retention_days": 365,
        "legal_notice_th": "เหมาะกับแคมเปญสายการเงินหรือหน่วยงานกำกับ ต้องมี evidence chain, reviewer และ retention ยาวกว่าปกติ",
        "compliance_controls_th": ["regulated phishing simulation record", "finance reviewer evidence", "extended retention"],
        "recommended_subject_suffixes": ["ตรวจสอบรายการชำระเงินที่ผิดปกติ", "ยืนยันการโอนเงินนอกเวลา"],
    },
    {
        "template_pack_code": "th_brand_protection",
        "campaign_type": "brand_protection",
        "jurisdiction": "th",
        "title": "Thai Brand Protection",
        "approval_required": True,
        "evidence_retention_days": 120,
        "legal_notice_th": "ใช้กับเคสเลียนแบบแบรนด์หรือ partner notification โดยต้องตรวจสอบผลกระทบด้าน reputational risk ก่อนทุกครั้ง",
        "compliance_controls_th": ["brand impersonation review", "stakeholder notification", "reputation evidence pack"],
        "recommended_subject_suffixes": ["แจ้งเตือนการปลอมแปลงแบรนด์องค์กร", "ตรวจสอบการใช้งาน partner portal ผิดปกติ"],
    },
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_json(value: dict[str, Any] | list[Any]) -> str:
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


def _tier_from_score(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _normalize_connector_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in CONNECTOR_TYPES else "simulated"


def _normalize_callback_event_type(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in CALLBACK_EVENT_TYPES else "delivered"


def _normalize_campaign_type(value: str) -> str:
    normalized = str(value or "awareness").strip().lower()
    return normalized if normalized in SOCIAL_CAMPAIGN_TYPES else "awareness"


def _template_pack_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "template_pack_code": str(row.get("template_pack_code") or ""),
        "campaign_type": _normalize_campaign_type(str(row.get("campaign_type") or "awareness")),
        "jurisdiction": str(row.get("jurisdiction") or "th"),
        "title": str(row.get("title") or ""),
        "approval_required": bool(row.get("approval_required", True)),
        "evidence_retention_days": int(row.get("evidence_retention_days") or 90),
        "legal_notice_th": str(row.get("legal_notice_th") or ""),
        "compliance_controls_th": [str(item) for item in row.get("compliance_controls_th", []) if str(item).strip()],
        "recommended_subject_suffixes": [str(item) for item in row.get("recommended_subject_suffixes", []) if str(item).strip()],
    }


def list_social_template_packs(*, campaign_type: str = "", jurisdiction: str = "th") -> dict[str, Any]:
    normalized_campaign_type = _normalize_campaign_type(campaign_type) if campaign_type else ""
    normalized_jurisdiction = str(jurisdiction or "th").strip().lower() or "th"
    rows = [
        _template_pack_row(row)
        for row in SOCIAL_TEMPLATE_PACKS
        if (not normalized_campaign_type or _normalize_campaign_type(str(row.get("campaign_type"))) == normalized_campaign_type)
        and str(row.get("jurisdiction") or "th").strip().lower() == normalized_jurisdiction
    ]
    return {
        "status": "ok",
        "campaign_type": normalized_campaign_type,
        "jurisdiction": normalized_jurisdiction,
        "count": len(rows),
        "rows": rows,
    }


def _resolve_social_template_pack(*, campaign_type: str, template_pack_code: str = "") -> dict[str, Any]:
    normalized_campaign_type = _normalize_campaign_type(campaign_type)
    normalized_pack_code = str(template_pack_code or "").strip().lower()
    for row in SOCIAL_TEMPLATE_PACKS:
        if normalized_pack_code and str(row.get("template_pack_code") or "").strip().lower() == normalized_pack_code:
            return _template_pack_row(row)
    for row in SOCIAL_TEMPLATE_PACKS:
        if _normalize_campaign_type(str(row.get("campaign_type") or "awareness")) == normalized_campaign_type:
            return _template_pack_row(row)
    return _template_pack_row(SOCIAL_TEMPLATE_PACKS[0])


def _bool_from_config(config: dict[str, Any], key: str, default: bool) -> bool:
    value = config.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _tag_list(value: str | None) -> list[str]:
    tags = []
    for item in _safe_json_list(value):
        text = str(item or "").strip()
        if text:
            tags.append(text.lower())
    return tags


def _employee_segment_matches(row: RedSocialRosterEntry, segment: str) -> bool:
    normalized = str(segment or "all_staff").strip().lower()
    if normalized in {"", "all", "all_staff", "everyone"}:
        return True
    fields = {
        str(row.department or "").strip().lower(),
        str(row.role_title or "").strip().lower(),
        str(row.employee_code or "").strip().lower(),
        str(row.risk_level or "").strip().lower(),
    }
    if normalized in fields:
        return True
    return normalized in _tag_list(row.tags_json)


def _default_policy(site: Site) -> dict[str, Any]:
    domain = site.base_url.replace("https://", "").replace("http://", "").split("/")[0]
    return {
        "policy_id": "",
        "site_id": str(site.id),
        "connector_type": "simulated",
        "sender_name": f"{site.display_name} Security Awareness",
        "sender_email": f"security-awareness@{domain or 'example.local'}",
        "subject_prefix": "[Awareness]",
        "landing_base_url": site.base_url.rstrip("/"),
        "report_mailbox": f"security@{domain or 'example.local'}",
        "require_approval": True,
        "enable_open_tracking": True,
        "enable_click_tracking": True,
        "max_emails_per_run": 200,
        "kill_switch_active": False,
        "allowed_domains": [domain] if domain else [],
        "connector_config": {
            "simulate_delivery": True,
            "campaign_type": "awareness",
            "template_pack_code": "th_awareness_basic",
            "evidence_retention_days": 90,
            "legal_ack_required": True,
        },
        "campaign_type": "awareness",
        "template_pack_code": "th_awareness_basic",
        "evidence_retention_days": 90,
        "legal_ack_required": True,
        "enabled": True,
        "owner": "security",
        "created_at": "",
        "updated_at": "",
    }


def _policy_row(row: RedSocialCampaignPolicy | None, *, site: Site) -> dict[str, Any]:
    if row is None:
        return _default_policy(site)
    connector_config = _safe_json_dict(row.connector_config_json)
    return {
        "policy_id": str(row.id),
        "site_id": str(row.site_id),
        "connector_type": _normalize_connector_type(row.connector_type),
        "sender_name": row.sender_name,
        "sender_email": row.sender_email,
        "subject_prefix": row.subject_prefix,
        "landing_base_url": row.landing_base_url,
        "report_mailbox": row.report_mailbox,
        "require_approval": bool(row.require_approval),
        "enable_open_tracking": bool(row.enable_open_tracking),
        "enable_click_tracking": bool(row.enable_click_tracking),
        "max_emails_per_run": int(row.max_emails_per_run or 200),
        "kill_switch_active": bool(row.kill_switch_active),
        "allowed_domains": [str(item) for item in _safe_json_list(row.allowed_domains_json)],
        "connector_config": connector_config,
        "campaign_type": _normalize_campaign_type(str(connector_config.get("campaign_type") or "awareness")),
        "template_pack_code": str(connector_config.get("template_pack_code") or "th_awareness_basic"),
        "evidence_retention_days": int(connector_config.get("evidence_retention_days") or 90),
        "legal_ack_required": _bool_from_config(connector_config, "legal_ack_required", True),
        "enabled": bool(row.enabled),
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _roster_row(row: RedSocialRosterEntry) -> dict[str, Any]:
    return {
        "roster_entry_id": str(row.id),
        "site_id": str(row.site_id),
        "employee_code": row.employee_code,
        "full_name": row.full_name,
        "email": row.email,
        "department": row.department,
        "role_title": row.role_title,
        "locale": row.locale,
        "risk_level": row.risk_level,
        "tags": [str(item) for item in _safe_json_list(row.tags_json)],
        "metadata": _safe_json_dict(row.metadata_json),
        "is_active": bool(row.is_active),
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _recipient_row(row: RedSocialCampaignRecipient) -> dict[str, Any]:
    return {
        "recipient_id": str(row.id),
        "run_id": str(row.run_id),
        "roster_entry_id": str(row.roster_entry_id) if row.roster_entry_id else "",
        "recipient_email": row.recipient_email,
        "recipient_name": row.recipient_name,
        "department": row.department,
        "delivery_status": row.delivery_status,
        "sent_at": _safe_iso(row.sent_at),
        "opened_at": _safe_iso(row.opened_at),
        "clicked_at": _safe_iso(row.clicked_at),
        "reported_at": _safe_iso(row.reported_at),
        "telemetry": _safe_json_dict(row.telemetry_json),
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _execution_summary(execution: RedSocialCampaignExecution | None) -> dict[str, Any]:
    if execution is None:
        return {
            "execution_id": "",
            "status": "",
            "connector_type": "",
            "approval_required": False,
            "dispatch_mode": "",
            "requested_by": "",
            "reviewed_by": "",
            "review_note": "",
            "reviewed_at": "",
            "dispatched_at": "",
            "completed_at": "",
            "killed_at": "",
            "killed_by": "",
            "kill_reason": "",
            "telemetry_summary": {},
            "connector_config": {},
        }
    return {
        "execution_id": str(execution.id),
        "status": execution.status,
        "connector_type": execution.connector_type,
        "approval_required": bool(execution.approval_required),
        "dispatch_mode": execution.dispatch_mode,
        "requested_by": execution.requested_by,
        "reviewed_by": execution.reviewed_by,
        "review_note": execution.review_note,
        "reviewed_at": _safe_iso(execution.reviewed_at),
        "dispatched_at": _safe_iso(execution.dispatched_at),
        "completed_at": _safe_iso(execution.completed_at),
        "killed_at": _safe_iso(execution.killed_at),
        "killed_by": execution.killed_by,
        "kill_reason": execution.kill_reason,
        "telemetry_summary": _safe_json_dict(execution.telemetry_summary_json),
        "connector_config": _safe_json_dict(execution.connector_config_json),
    }


def _run_row(row: RedSocialEngineeringRun) -> dict[str, Any]:
    execution = getattr(row, "execution", None)
    return {
        "run_id": str(row.id),
        "site_id": str(row.site_id),
        "campaign_name": row.campaign_name,
        "employee_segment": row.employee_segment,
        "language": row.language,
        "difficulty": row.difficulty,
        "impersonation_brand": row.impersonation_brand,
        "email_count": row.email_count,
        "dry_run": bool(row.dry_run),
        "risk_score": row.risk_score,
        "risk_tier": row.risk_tier,
        "summary_th": row.summary_th,
        "details": _safe_json_dict(row.details_json),
        "execution": _execution_summary(execution),
        "created_at": _safe_iso(row.created_at),
    }


def _load_policy_row(db: Session, *, site: Site) -> RedSocialCampaignPolicy | None:
    return db.scalar(select(RedSocialCampaignPolicy).where(RedSocialCampaignPolicy.site_id == site.id))


def get_social_engineering_policy(db: Session, *, site_id: UUID) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    return {"status": "ok", "policy": _policy_row(_load_policy_row(db, site=site), site=site)}


def upsert_social_engineering_policy(
    db: Session,
    *,
    site_id: UUID,
    connector_type: str,
    sender_name: str,
    sender_email: str,
    subject_prefix: str,
    landing_base_url: str,
    report_mailbox: str,
    require_approval: bool,
    enable_open_tracking: bool,
    enable_click_tracking: bool,
    max_emails_per_run: int,
    kill_switch_active: bool,
    allowed_domains: list[str],
    connector_config: dict[str, Any],
    campaign_type: str = "awareness",
    template_pack_code: str = "th_awareness_basic",
    evidence_retention_days: int = 90,
    legal_ack_required: bool = True,
    enabled: bool,
    owner: str,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    row = _load_policy_row(db, site=site)
    now = _now()
    created = row is None
    normalized_domains = sorted({str(item).strip().lower() for item in allowed_domains if str(item).strip()})
    normalized_connector = _normalize_connector_type(connector_type)
    normalized_campaign_type = _normalize_campaign_type(campaign_type)
    template_pack = _resolve_social_template_pack(campaign_type=normalized_campaign_type, template_pack_code=template_pack_code)
    enriched_connector_config = {
        **(connector_config or {}),
        "campaign_type": normalized_campaign_type,
        "template_pack_code": template_pack["template_pack_code"],
        "evidence_retention_days": max(1, min(int(evidence_retention_days), 3650)),
        "legal_ack_required": bool(legal_ack_required),
    }
    payload_json = _as_json(enriched_connector_config)
    if row is None:
        row = RedSocialCampaignPolicy(
            site_id=site.id,
            created_at=now,
        )
        db.add(row)
    row.connector_type = normalized_connector
    row.sender_name = sender_name.strip()[:128] or f"{site.display_name} Security Awareness"
    row.sender_email = sender_email.strip()[:255] or _default_policy(site)["sender_email"]
    row.subject_prefix = subject_prefix.strip()[:64] or "[Awareness]"
    row.landing_base_url = landing_base_url.strip()[:1024] or site.base_url.rstrip("/")
    row.report_mailbox = report_mailbox.strip()[:255]
    row.require_approval = bool(require_approval)
    row.enable_open_tracking = bool(enable_open_tracking)
    row.enable_click_tracking = bool(enable_click_tracking)
    row.max_emails_per_run = max(1, min(int(max_emails_per_run), 5000))
    row.kill_switch_active = bool(kill_switch_active)
    row.allowed_domains_json = _as_json(normalized_domains)
    row.connector_config_json = payload_json
    row.enabled = bool(enabled)
    row.owner = owner.strip()[:64] or "security"
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return {"status": "created" if created else "updated", "policy": _policy_row(row, site=site)}


def import_social_roster(
    db: Session,
    *,
    site_id: UUID,
    entries: list[dict[str, Any]],
    actor: str = "red_social_roster_ai",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    imported = 0
    updated = 0
    changed_emails: list[str] = []
    now = _now()
    for raw in entries[:5000]:
        email = str(raw.get("email", "") or "").strip().lower()
        if not email:
            continue
        row = db.scalar(
            select(RedSocialRosterEntry)
            .where(RedSocialRosterEntry.site_id == site.id)
            .where(RedSocialRosterEntry.email == email)
        )
        is_new = row is None
        if row is None:
            row = RedSocialRosterEntry(site_id=site.id, email=email, created_at=now)
            db.add(row)
        row.employee_code = str(raw.get("employee_code", "") or "").strip()[:64]
        row.full_name = str(raw.get("full_name", raw.get("name", "")) or "").strip()[:255]
        row.email = email[:255]
        row.department = str(raw.get("department", "") or "").strip()[:128]
        row.role_title = str(raw.get("role_title", raw.get("title", "")) or "").strip()[:128]
        row.locale = str(raw.get("locale", "th") or "th").strip()[:32]
        row.risk_level = str(raw.get("risk_level", "medium") or "medium").strip()[:16]
        tags = raw.get("tags", [])
        if not isinstance(tags, list):
            tags = [tags]
        row.tags_json = _as_json([str(item).strip() for item in tags if str(item).strip()])
        metadata = raw.get("metadata", {})
        row.metadata_json = _as_json(metadata if isinstance(metadata, dict) else {"raw": metadata, "actor": actor})
        row.is_active = bool(raw.get("is_active", True))
        row.updated_at = now
        if is_new:
            imported += 1
        else:
            updated += 1
        changed_emails.append(email)
    db.commit()
    rows = db.scalars(
        select(RedSocialRosterEntry)
        .where(RedSocialRosterEntry.site_id == site.id)
        .where(RedSocialRosterEntry.email.in_(changed_emails[:50] or [""]))
        .order_by(RedSocialRosterEntry.email.asc())
    ).all()
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "actor": actor,
        "received_count": len(entries),
        "imported_count": imported,
        "updated_count": updated,
        "rows": [_roster_row(row) for row in rows],
    }


def list_social_roster(
    db: Session,
    *,
    site_id: UUID,
    active_only: bool = True,
    limit: int = 200,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    stmt = (
        select(RedSocialRosterEntry)
        .where(RedSocialRosterEntry.site_id == site.id)
        .order_by(RedSocialRosterEntry.department.asc(), RedSocialRosterEntry.full_name.asc(), RedSocialRosterEntry.email.asc())
        .limit(max(1, min(limit, 500)))
    )
    if active_only:
        stmt = stmt.where(RedSocialRosterEntry.is_active.is_(True))
    rows = db.scalars(stmt).all()
    return {
        "status": "ok",
        "count": len(rows),
        "summary": {
            "departments": sorted({row.department for row in rows if row.department})[:20],
            "active_count": sum(1 for row in rows if row.is_active),
            "high_risk_count": sum(1 for row in rows if str(row.risk_level or "").lower() in {"high", "critical"}),
        },
        "rows": [_roster_row(row) for row in rows],
    }


def _select_roster_targets(
    db: Session,
    *,
    site_id: UUID,
    employee_segment: str,
    email_count: int,
    allowed_domains: list[str],
) -> list[RedSocialRosterEntry]:
    rows = db.scalars(
        select(RedSocialRosterEntry)
        .where(RedSocialRosterEntry.site_id == site_id)
        .where(RedSocialRosterEntry.is_active.is_(True))
        .order_by(RedSocialRosterEntry.department.asc(), RedSocialRosterEntry.full_name.asc(), RedSocialRosterEntry.email.asc())
        .limit(5000)
    ).all()
    normalized_domains = {item.strip().lower() for item in allowed_domains if item.strip()}
    selected: list[RedSocialRosterEntry] = []
    for row in rows:
        if not _employee_segment_matches(row, employee_segment):
            continue
        if normalized_domains:
            domain = row.email.split("@")[-1].strip().lower() if "@" in row.email else ""
            if domain not in normalized_domains:
                continue
        selected.append(row)
        if len(selected) >= email_count:
            break
    return selected


def _simulate_recipient_telemetry(
    *,
    recipient_email: str,
    campaign_name: str,
    risk_score: int,
    difficulty: str,
    sent_at: datetime,
    enable_open_tracking: bool,
    enable_click_tracking: bool,
) -> dict[str, Any]:
    seed = hashlib.sha256(f"{recipient_email}|{campaign_name}|{difficulty}|{risk_score}".encode("utf-8")).hexdigest()
    score = int(seed[:8], 16) % 100
    open_threshold = min(92, 35 + (risk_score // 2))
    click_threshold = min(85, 12 + (risk_score // 3))
    report_threshold = max(10, 78 - (risk_score // 5))

    opened = enable_open_tracking and score < open_threshold
    clicked = enable_click_tracking and opened and score < click_threshold
    reported = opened and score > report_threshold

    open_at = sent_at + timedelta(minutes=(score % 7) + 1) if opened else None
    click_at = (open_at or sent_at) + timedelta(minutes=(score % 11) + 2) if clicked else None
    report_at = (click_at or open_at or sent_at) + timedelta(minutes=(score % 17) + 5) if reported else None

    status = "delivered"
    if reported:
        status = "reported"
    elif clicked:
        status = "clicked"
    elif opened:
        status = "opened"

    return {
        "status": status,
        "sent_at": sent_at,
        "opened_at": open_at,
        "clicked_at": click_at,
        "reported_at": report_at,
        "payload": {
            "events": {
                "sent": True,
                "opened": opened,
                "clicked": clicked,
                "reported": reported,
            },
            "journey_seed": seed[:12],
            "difficulty": difficulty,
            "risk_score": risk_score,
        },
    }


def _telemetry_summary(recipients: list[RedSocialCampaignRecipient], *, expected_count: int) -> dict[str, Any]:
    delivered = 0
    opened = 0
    clicked = 0
    reported = 0
    killed = 0
    for recipient in recipients:
        if recipient.sent_at:
            delivered += 1
        if recipient.opened_at:
            opened += 1
        if recipient.clicked_at:
            clicked += 1
        if recipient.reported_at:
            reported += 1
        if recipient.delivery_status == "killed":
            killed += 1
    safe_divisor = expected_count or len(recipients) or 1
    return {
        "expected_count": expected_count,
        "delivered_count": delivered,
        "opened_count": opened,
        "clicked_count": clicked,
        "reported_count": reported,
        "killed_count": killed,
        "open_rate_pct": round((opened / safe_divisor) * 100, 2),
        "click_rate_pct": round((clicked / safe_divisor) * 100, 2),
        "report_rate_pct": round((reported / safe_divisor) * 100, 2),
    }


def _persist_delivery_audit(
    db: Session,
    *,
    site: Site,
    connector_source: str,
    status: str,
    payload: dict[str, Any],
) -> None:
    db.add(
        ConnectorDeliveryEvent(
            tenant_id=site.tenant_id,
            site_id=site.id,
            connector_source=f"red_social_{connector_source}",
            event_type="campaign_dispatch",
            status=status,
            latency_ms=0,
            attempt=1,
            payload_json=_as_json(payload),
            error_message="",
            created_at=_now(),
        )
    )


def _load_recipients_for_run(db: Session, *, execution_id: UUID) -> list[RedSocialCampaignRecipient]:
    return db.scalars(
        select(RedSocialCampaignRecipient)
        .where(RedSocialCampaignRecipient.execution_id == execution_id)
        .order_by(RedSocialCampaignRecipient.created_at.asc())
    ).all()


def _dispatch_campaign(
    db: Session,
    *,
    site: Site,
    run: RedSocialEngineeringRun,
    execution: RedSocialCampaignExecution,
    roster: list[RedSocialRosterEntry],
    policy: dict[str, Any],
    actor: str,
) -> dict[str, Any]:
    now = _now()
    connector_config = dict(policy.get("connector_config", {}))
    simulate_delivery = _bool_from_config(connector_config, "simulate_delivery", True)
    recipients: list[RedSocialCampaignRecipient] = []
    for roster_entry in roster:
        recipient = RedSocialCampaignRecipient(
            site_id=site.id,
            run_id=run.id,
            execution_id=execution.id,
            roster_entry_id=roster_entry.id,
            recipient_email=roster_entry.email,
            recipient_name=roster_entry.full_name,
            department=roster_entry.department,
            delivery_status="queued" if not simulate_delivery else "delivered",
            created_at=now,
            updated_at=now,
        )
        journey = _simulate_recipient_telemetry(
            recipient_email=roster_entry.email,
            campaign_name=run.campaign_name,
            risk_score=run.risk_score,
            difficulty=run.difficulty,
            sent_at=now,
            enable_open_tracking=bool(policy.get("enable_open_tracking", True)),
            enable_click_tracking=bool(policy.get("enable_click_tracking", True)),
        )
        recipient.sent_at = journey["sent_at"]
        recipient.opened_at = journey["opened_at"] if simulate_delivery else None
        recipient.clicked_at = journey["clicked_at"] if simulate_delivery else None
        recipient.reported_at = journey["reported_at"] if simulate_delivery else None
        recipient.delivery_status = str(journey["status"] if simulate_delivery else "sent")
        recipient.telemetry_json = _as_json(
            {
                **journey["payload"],
                "connector_type": execution.connector_type,
                "simulate_delivery": simulate_delivery,
                "actor": actor,
            }
        )
        recipients.append(recipient)
        db.add(recipient)

    summary = _telemetry_summary(recipients, expected_count=run.email_count)
    execution.status = "completed"
    execution.dispatch_mode = "simulated" if simulate_delivery else "connector_ready"
    execution.dispatched_at = now
    execution.completed_at = now
    execution.telemetry_summary_json = _as_json(summary)
    execution.updated_at = now

    _persist_delivery_audit(
        db,
        site=site,
        connector_source=execution.connector_type,
        status="success",
        payload={
            "run_id": str(run.id),
            "execution_id": str(execution.id),
            "campaign_name": run.campaign_name,
            "recipient_count": len(recipients),
            "connector_type": execution.connector_type,
            "dispatch_mode": execution.dispatch_mode,
            "simulate_delivery": simulate_delivery,
        },
    )
    return summary


def run_social_engineering_simulator(
    db: Session,
    *,
    site_id: UUID,
    campaign_name: str = "thai_phishing_awareness",
    employee_segment: str = "all_staff",
    email_count: int = 50,
    difficulty: str = "medium",
    impersonation_brand: str = "",
    campaign_type: str = "awareness",
    template_pack_code: str = "",
    dry_run: bool = True,
    actor: str = "red_social_sim_ai",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}

    difficulty_value = str(difficulty or "medium").strip().lower()
    if difficulty_value not in {"low", "medium", "high"}:
        difficulty_value = "medium"

    policy_row = _load_policy_row(db, site=site)
    policy = _policy_row(policy_row, site=site)
    effective_campaign_type = _normalize_campaign_type(campaign_type or str(policy.get("campaign_type") or "awareness"))
    template_pack = _resolve_social_template_pack(
        campaign_type=effective_campaign_type,
        template_pack_code=template_pack_code or str(policy.get("template_pack_code") or ""),
    )

    phishing_packs = db.scalars(
        select(ThreatContentPack)
        .where(ThreatContentPack.is_active.is_(True))
        .where(ThreatContentPack.category.in_(["phishing", "identity"]))
        .order_by(desc(ThreatContentPack.updated_at))
        .limit(6)
    ).all()
    recent_blue_events = db.scalars(
        select(BlueEventLog)
        .where(BlueEventLog.site_id == site.id)
        .order_by(desc(BlueEventLog.created_at))
        .limit(100)
    ).all()
    suspicious_events = [
        row
        for row in recent_blue_events
        if row.ai_severity in {"medium", "high"}
        or "phish" in row.payload_json.lower()
        or "credential" in row.payload_json.lower()
    ]

    requested_email_count = max(1, min(int(email_count), 5000))
    capped_email_count = min(requested_email_count, int(policy.get("max_emails_per_run", 200) or 200))
    roster = _select_roster_targets(
        db,
        site_id=site.id,
        employee_segment=employee_segment,
        email_count=capped_email_count,
        allowed_domains=[str(item) for item in policy.get("allowed_domains", [])],
    )

    base_score = {"low": 28, "medium": 47, "high": 68}[difficulty_value]
    roster_factor = min(18, len(roster) // 4)
    risk_score = min(95, base_score + (len(suspicious_events) * 4) + (len(phishing_packs) * 3) + roster_factor)
    risk_tier = _tier_from_score(risk_score)

    brand = impersonation_brand.strip() or site.display_name
    landing_path = "/security-review" if difficulty_value == "low" else "/urgent-access-check"
    landing_url = f"{(policy.get('landing_base_url') or site.base_url.rstrip('/')).rstrip('/')}{landing_path}"
    subject_suffixes = list(template_pack.get("recommended_subject_suffixes", [])) or [
        "ยืนยันการเข้าใช้งานบัญชีภายในวันนี้",
        "ตรวจสอบการแจ้งเตือนความปลอดภัยล่าสุด",
    ]
    subject_lines = [
        f"{policy.get('subject_prefix', '[Awareness]')} {brand}: {subject_suffixes[0]}",
        f"{policy.get('subject_prefix', '[Awareness]')} {brand}: {subject_suffixes[min(1, len(subject_suffixes) - 1)]}",
        f"{policy.get('subject_prefix', '[Awareness]')} แบบประเมินความปลอดภัยประจำเดือนของ {brand}",
    ]
    lures = [
        "แจ้งเตือนบัญชีอีเมลภายใน",
        "คำขอรีเซ็ตรหัสผ่านจากทีม IT",
        "เอกสาร HR/Compliance ที่ต้องกดยืนยัน",
    ]
    recommended_controls = [
        "เปิดใช้งาน MFA กับบัญชี privileged และบัญชีพนักงานทั้งหมด",
        "ปรับ mailbox rule เพื่อตรวจโดเมนเลียนแบบชื่อองค์กร",
        "ฝึกอบรม phishing awareness ภาษาไทยตามสถานการณ์จริงในไทย",
    ]
    estimated_click_rate_pct = min(42, 8 + (risk_score // 5))

    warnings: list[str] = []
    execution_status = "preview" if dry_run else "ready"
    if not bool(policy.get("enabled", True)):
        warnings.append("policy_disabled")
        execution_status = "policy_disabled"
    elif not roster:
        warnings.append("roster_required")
        execution_status = "roster_required"
    elif bool(policy.get("kill_switch_active", False)) and not dry_run:
        warnings.append("kill_switch_active")
        execution_status = "blocked_by_kill_switch"
    elif not dry_run and (bool(policy.get("require_approval", True)) or bool(template_pack.get("approval_required", True))):
        execution_status = "pending_approval"

    summary_th = (
        f"AI ประเมินแคมเปญ {campaign_name} สำหรับกลุ่ม {employee_segment} ว่ามีความเสี่ยงระดับ {risk_tier} "
        f"(score={risk_score}) เป้าหมายพร้อมใช้งาน {len(roster)}/{capped_email_count} ราย ผ่าน connector={policy.get('connector_type')} "
        f"และสถานะปฏิบัติการ={execution_status}."
    )

    details = {
        "campaign_name": campaign_name,
        "employee_segment": employee_segment,
        "campaign_type": effective_campaign_type,
        "language": "th",
        "difficulty": difficulty_value,
        "impersonation_brand": brand,
        "estimated_click_rate_pct": estimated_click_rate_pct,
        "email_subjects_th": subject_lines,
        "landing_url": landing_url,
        "lure_scenarios_th": lures,
        "recommended_controls_th": recommended_controls,
        "legal_template_pack": template_pack,
        "legal_notice_th": template_pack.get("legal_notice_th", ""),
        "compliance_controls_th": template_pack.get("compliance_controls_th", []),
        "phishing_pack_codes": [pack.pack_code for pack in phishing_packs],
        "suspicious_signal_count": len(suspicious_events),
        "dry_run": bool(dry_run),
        "actor": actor,
        "selected_roster_count": len(roster),
        "selected_recipients_preview": [
            {"name": row.full_name, "email": row.email, "department": row.department}
            for row in roster[:10]
        ],
        "policy_snapshot": policy,
        "warnings": warnings,
    }

    now = _now()
    run = RedSocialEngineeringRun(
        site_id=site.id,
        campaign_name=campaign_name.strip()[:255] or "thai_phishing_awareness",
        employee_segment=employee_segment.strip()[:128] or "all_staff",
        language="th",
        difficulty=difficulty_value,
        impersonation_brand=brand[:128],
        email_count=len(roster) if roster else capped_email_count,
        dry_run=bool(dry_run),
        risk_score=risk_score,
        risk_tier=risk_tier,
        summary_th=summary_th,
        details_json=_as_json(details),
        created_at=now,
    )
    db.add(run)
    db.flush()

    execution = RedSocialCampaignExecution(
        site_id=site.id,
        run_id=run.id,
        connector_type=str(policy.get("connector_type", "simulated")),
        status=execution_status,
        approval_required=bool((bool(policy.get("require_approval", True)) or bool(template_pack.get("approval_required", True))) and not dry_run),
        requested_by=actor,
        dispatch_mode="dry_run" if dry_run else "queued",
        connector_config_json=_as_json(policy.get("connector_config", {})),
        telemetry_summary_json=_as_json(
            {
                "expected_count": len(roster) if roster else capped_email_count,
                "delivered_count": 0,
                "opened_count": 0,
                "clicked_count": 0,
                "reported_count": 0,
                "killed_count": 0,
                "open_rate_pct": 0.0,
                "click_rate_pct": 0.0,
                "report_rate_pct": 0.0,
            }
        ),
        created_at=now,
        updated_at=now,
    )
    run.execution = execution
    db.add(execution)

    if execution_status == "ready":
        summary = _dispatch_campaign(db, site=site, run=run, execution=execution, roster=roster, policy=policy, actor=actor)
        details["telemetry_summary"] = summary
        run.details_json = _as_json(details)

    db.commit()
    db.refresh(run)
    return {
        "status": "simulated" if dry_run else execution.status,
        "site_id": str(site.id),
        "site_code": site.site_code,
        "run": _run_row(run),
    }


def list_social_engineering_runs(db: Session, *, site_id: UUID, limit: int = 20) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    rows = db.scalars(
        select(RedSocialEngineeringRun)
        .where(RedSocialEngineeringRun.site_id == site.id)
        .order_by(desc(RedSocialEngineeringRun.created_at))
        .limit(max(1, min(limit, 200)))
    ).all()
    return {"status": "ok", "count": len(rows), "rows": [_run_row(row) for row in rows]}


def _load_execution(db: Session, *, site_id: UUID, run_id: UUID) -> tuple[Site | None, RedSocialEngineeringRun | None, RedSocialCampaignExecution | None]:
    site = db.get(Site, site_id)
    if not site:
        return None, None, None
    run = db.scalar(
        select(RedSocialEngineeringRun)
        .where(RedSocialEngineeringRun.site_id == site.id)
        .where(RedSocialEngineeringRun.id == run_id)
    )
    if run is None:
        return site, None, None
    execution = db.scalar(
        select(RedSocialCampaignExecution)
        .where(RedSocialCampaignExecution.site_id == site.id)
        .where(RedSocialCampaignExecution.run_id == run.id)
    )
    return site, run, execution


def review_social_campaign(
    db: Session,
    *,
    site_id: UUID,
    run_id: UUID,
    approve: bool,
    actor: str,
    note: str = "",
) -> dict[str, Any]:
    site, run, execution = _load_execution(db, site_id=site_id, run_id=run_id)
    if site is None:
        return {"status": "not_found", "site_id": str(site_id)}
    if run is None or execution is None:
        return {"status": "not_found", "site_id": str(site.id), "run_id": str(run_id)}
    if execution.status != "pending_approval":
        return {"status": "invalid_state", "site_id": str(site.id), "run_id": str(run.id), "current_status": execution.status}

    now = _now()
    execution.reviewed_by = actor
    execution.review_note = note[:2048]
    execution.reviewed_at = now
    execution.updated_at = now

    if not approve:
        execution.status = "rejected"
        db.commit()
        db.refresh(run)
        return {"status": "rejected", "site_id": str(site.id), "site_code": site.site_code, "run": _run_row(run)}

    policy = _policy_row(_load_policy_row(db, site=site), site=site)
    roster = _select_roster_targets(
        db,
        site_id=site.id,
        employee_segment=run.employee_segment,
        email_count=run.email_count,
        allowed_domains=[str(item) for item in policy.get("allowed_domains", [])],
    )
    if not roster:
        execution.status = "roster_required"
        db.commit()
        db.refresh(run)
        return {"status": execution.status, "site_id": str(site.id), "site_code": site.site_code, "run": _run_row(run)}
    if bool(policy.get("kill_switch_active", False)):
        execution.status = "blocked_by_kill_switch"
        db.commit()
        db.refresh(run)
        return {"status": execution.status, "site_id": str(site.id), "site_code": site.site_code, "run": _run_row(run)}

    summary = _dispatch_campaign(db, site=site, run=run, execution=execution, roster=roster, policy=policy, actor=actor)
    details = _safe_json_dict(run.details_json)
    details["approval"] = {"approved": True, "approver": actor, "note": note, "approved_at": now.isoformat()}
    details["telemetry_summary"] = summary
    run.details_json = _as_json(details)
    db.commit()
    db.refresh(run)
    return {"status": execution.status, "site_id": str(site.id), "site_code": site.site_code, "run": _run_row(run)}


def kill_social_campaign(
    db: Session,
    *,
    site_id: UUID,
    run_id: UUID,
    actor: str,
    note: str = "",
    activate_site_kill_switch: bool = False,
) -> dict[str, Any]:
    site, run, execution = _load_execution(db, site_id=site_id, run_id=run_id)
    if site is None:
        return {"status": "not_found", "site_id": str(site_id)}
    if run is None or execution is None:
        return {"status": "not_found", "site_id": str(site.id), "run_id": str(run_id)}

    now = _now()
    execution.status = "killed"
    execution.killed_at = now
    execution.killed_by = actor
    execution.kill_reason = note[:2048]
    execution.updated_at = now

    recipients = _load_recipients_for_run(db, execution_id=execution.id)
    for recipient in recipients:
        if recipient.delivery_status in {"pending", "queued", "sent", "delivered", "opened"}:
            recipient.delivery_status = "killed"
            recipient.updated_at = now

    summary = _telemetry_summary(recipients, expected_count=run.email_count)
    execution.telemetry_summary_json = _as_json(summary)

    if activate_site_kill_switch:
        policy_row = _load_policy_row(db, site=site)
        if policy_row is None:
            policy_result = upsert_social_engineering_policy(
                db,
                site_id=site.id,
                connector_type="simulated",
                sender_name=_default_policy(site)["sender_name"],
                sender_email=_default_policy(site)["sender_email"],
                subject_prefix="[Awareness]",
                landing_base_url=site.base_url.rstrip("/"),
                report_mailbox=_default_policy(site)["report_mailbox"],
                require_approval=True,
                enable_open_tracking=True,
                enable_click_tracking=True,
                max_emails_per_run=200,
                kill_switch_active=True,
                allowed_domains=_default_policy(site)["allowed_domains"],
                connector_config={"simulate_delivery": True},
                enabled=True,
                owner="security",
            )
            policy_row = _load_policy_row(db, site=site)
            if not policy_result:
                pass
        if policy_row is not None:
            policy_row.kill_switch_active = True
            policy_row.updated_at = now

    details = _safe_json_dict(run.details_json)
    details["kill_switch"] = {
        "killed": True,
        "actor": actor,
        "note": note,
        "activate_site_kill_switch": bool(activate_site_kill_switch),
        "killed_at": now.isoformat(),
    }
    details["telemetry_summary"] = summary
    run.details_json = _as_json(details)
    db.commit()
    db.refresh(run)
    return {"status": "killed", "site_id": str(site.id), "site_code": site.site_code, "run": _run_row(run)}


def get_social_campaign_telemetry(
    db: Session,
    *,
    site_id: UUID,
    run_id: UUID | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    stmt = (
        select(RedSocialCampaignRecipient)
        .where(RedSocialCampaignRecipient.site_id == site.id)
        .order_by(desc(RedSocialCampaignRecipient.created_at))
        .limit(max(1, min(limit, 500)))
    )
    if run_id is not None:
        stmt = stmt.where(RedSocialCampaignRecipient.run_id == run_id)
    rows = db.scalars(stmt).all()
    return {
        "status": "ok",
        "site_id": str(site.id),
        "run_id": str(run_id) if run_id else "",
        "summary": _telemetry_summary(rows, expected_count=len(rows)),
        "rows": [_recipient_row(row) for row in rows],
    }


def ingest_social_provider_callback(
    db: Session,
    *,
    site_id: UUID,
    run_id: UUID,
    connector_type: str,
    event_type: str,
    recipient_email: str,
    occurred_at: str = "",
    provider_event_id: str = "",
    metadata: dict[str, Any] | None = None,
    actor: str = "provider_callback_ingest",
) -> dict[str, Any]:
    site, run, execution = _load_execution(db, site_id=site_id, run_id=run_id)
    if site is None:
        return {"status": "not_found", "site_id": str(site_id)}
    if run is None or execution is None:
        return {"status": "not_found", "site_id": str(site.id), "run_id": str(run_id)}

    connector_value = _normalize_connector_type(connector_type or execution.connector_type)
    event_value = _normalize_callback_event_type(event_type)
    recipient_email_value = str(recipient_email or "").strip().lower()
    if not recipient_email_value:
        return {"status": "recipient_required", "site_id": str(site.id), "run_id": str(run.id)}

    recipient = db.scalar(
        select(RedSocialCampaignRecipient)
        .where(RedSocialCampaignRecipient.run_id == run.id)
        .where(RedSocialCampaignRecipient.recipient_email == recipient_email_value)
    )
    if recipient is None:
        return {
            "status": "recipient_not_found",
            "site_id": str(site.id),
            "run_id": str(run.id),
            "recipient_email": recipient_email_value,
        }

    occurred = _now()
    occurred_value = str(occurred_at or "").strip()
    if occurred_value:
        try:
            occurred = datetime.fromisoformat(occurred_value.replace("Z", "+00:00"))
        except Exception:
            occurred = _now()
    if occurred.tzinfo is None:
        occurred = occurred.replace(tzinfo=timezone.utc)

    telemetry = _safe_json_dict(recipient.telemetry_json)
    provider_callbacks = telemetry.get("provider_callbacks", [])
    if not isinstance(provider_callbacks, list):
        provider_callbacks = []
    provider_callbacks.append(
        {
            "event_type": event_value,
            "provider_event_id": provider_event_id.strip()[:128],
            "connector_type": connector_value,
            "actor": actor,
            "occurred_at": occurred.isoformat(),
            "metadata": metadata or {},
        }
    )
    telemetry["provider_callbacks"] = provider_callbacks[-20:]
    telemetry["external_feedback"] = {
        "latest_event_type": event_value,
        "latest_occurred_at": occurred.isoformat(),
        "provider_event_id": provider_event_id.strip()[:128],
        "connector_type": connector_value,
    }

    if event_value == "delivered":
        recipient.sent_at = recipient.sent_at or occurred
        recipient.delivery_status = "delivered"
    elif event_value == "opened":
        recipient.sent_at = recipient.sent_at or occurred
        recipient.opened_at = recipient.opened_at or occurred
        recipient.delivery_status = "opened"
    elif event_value == "clicked":
        recipient.sent_at = recipient.sent_at or occurred
        recipient.opened_at = recipient.opened_at or occurred
        recipient.clicked_at = recipient.clicked_at or occurred
        recipient.delivery_status = "clicked"
    elif event_value in {"reported", "complained"}:
        recipient.sent_at = recipient.sent_at or occurred
        recipient.reported_at = recipient.reported_at or occurred
        recipient.delivery_status = "reported"
    elif event_value == "bounced":
        recipient.delivery_status = "bounced"

    recipient.telemetry_json = _as_json(telemetry)
    recipient.updated_at = _now()

    recipients = _load_recipients_for_run(db, execution_id=execution.id)
    summary = _telemetry_summary(recipients, expected_count=run.email_count)
    execution.telemetry_summary_json = _as_json(summary)
    execution.updated_at = _now()
    if execution.status in {"connector_ready", "queued"}:
        execution.status = "completed"
        execution.dispatched_at = execution.dispatched_at or occurred
        execution.completed_at = execution.completed_at or _now()

    details = _safe_json_dict(run.details_json)
    details["provider_callback"] = {
        "event_type": event_value,
        "recipient_email": recipient_email_value,
        "provider_event_id": provider_event_id.strip()[:128],
        "connector_type": connector_value,
        "occurred_at": occurred.isoformat(),
        "actor": actor,
    }
    details["telemetry_summary"] = summary
    run.details_json = _as_json(details)

    _persist_delivery_audit(
        db,
        site=site,
        connector_source=connector_value,
        status="provider_callback",
        payload={
            "run_id": str(run.id),
            "execution_id": str(execution.id),
            "event_type": event_value,
            "recipient_email": recipient_email_value,
            "provider_event_id": provider_event_id.strip()[:128],
            "actor": actor,
        },
    )

    db.commit()
    db.refresh(run)
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "run": _run_row(run),
        "recipient": _recipient_row(recipient),
        "callback": {
            "event_type": event_value,
            "connector_type": connector_value,
            "occurred_at": occurred.isoformat(),
            "provider_event_id": provider_event_id.strip()[:128],
        },
    }
