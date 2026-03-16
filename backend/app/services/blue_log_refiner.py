from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    BlueEventLog,
    BlueLogRefinerCallbackEvent,
    BlueLogRefinerFeedback,
    BlueLogRefinerPolicy,
    BlueLogRefinerRun,
    BlueLogRefinerSchedulePolicy,
    Site,
)
from app.db.session import SessionLocal

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
FEEDBACK_TYPES = {"keep_signal", "drop_noise", "false_positive", "signal_missed"}
EXECUTION_MODES = {"pre_ingest", "post_ingest"}
CALLBACK_TYPES = {"stream_result", "storage_report", "delivery_receipt"}

MAPPING_PACKS: dict[str, dict[str, Any]] = {
    "generic": {
        "display_name": "Generic Security Event Mapping",
        "execution_mode": "post_ingest",
        "notes": [
            "ใช้กับ source ทั่วไปที่ยังไม่มี adapter เฉพาะทาง",
            "เหมาะกับ ingest ผ่าน webhook/integration event แล้วค่อยคัด noise ในชั้น orchestration",
        ],
        "field_mapping": [
            {"incoming": "event_type", "mapped_to": "event_type"},
            {"incoming": "severity", "mapped_to": "ai_severity"},
            {"incoming": "recommendation", "mapped_to": "ai_recommendation"},
        ],
    },
    "splunk": {
        "display_name": "Splunk Pre-Ingest Refiner Pack",
        "execution_mode": "pre_ingest",
        "notes": [
            "ใช้คัด noisy notable events ก่อนเก็บลง index retention tier แพง",
            "เหมาะกับวัด KPI ลด storage และ alert fatigue ต่อ source SIEM",
        ],
        "field_mapping": [
            {"incoming": "result.sourcetype", "mapped_to": "event_type"},
            {"incoming": "result.urgency", "mapped_to": "ai_severity"},
            {"incoming": "result.src", "mapped_to": "source_ip"},
        ],
    },
    "elk": {
        "display_name": "ELK / OpenSearch Refinement Pack",
        "execution_mode": "post_ingest",
        "notes": [
            "ใช้กับ Elastic/OpenSearch pipeline ที่ต้องการวัด signal-to-noise ratio ต่อ stream",
            "เหมาะกับทีมที่ ingest log เยอะและต้องการ feedback loop ให้ analyst ปรับลด false positive",
        ],
        "field_mapping": [
            {"incoming": "event.dataset", "mapped_to": "event_type"},
            {"incoming": "source.ip", "mapped_to": "source_ip"},
            {"incoming": "event.severity", "mapped_to": "ai_severity"},
        ],
    },
    "cloudflare": {
        "display_name": "Cloudflare WAF Refiner Pack",
        "execution_mode": "pre_ingest",
        "notes": [
            "เน้นคัด WAF events ที่ block อยู่แล้วออกจาก analyst queue ถ้า risk ต่ำ",
            "จับคู่กับ Auto-Playbook Executor และ Managed Responder ได้",
        ],
        "field_mapping": [
            {"incoming": "ClientIP", "mapped_to": "source_ip"},
            {"incoming": "Action", "mapped_to": "status"},
            {"incoming": "RuleMessage", "mapped_to": "event_type"},
        ],
    },
    "crowdstrike": {
        "display_name": "CrowdStrike Detection Refiner Pack",
        "execution_mode": "post_ingest",
        "notes": [
            "เหมาะกับการคัด detection ที่ severity ต่ำหรือ recommendation เป็น ignore ออกจาก queue L1",
            "ควรใช้ร่วมกับ Thai Alert Translator และ Managed Responder",
        ],
        "field_mapping": [
            {"incoming": "behavior_id", "mapped_to": "event_type"},
            {"incoming": "severity", "mapped_to": "ai_severity"},
            {"incoming": "device.external_ip", "mapped_to": "source_ip"},
        ],
    },
}


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


def _normalize_connector(value: str) -> str:
    text = str(value or "").strip().lower()
    return text[:64] or "generic"


def _normalize_mode(value: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in EXECUTION_MODES else "pre_ingest"


def _normalize_severity(value: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in SEVERITY_RANK else "medium"


def _normalize_status(value: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in {"ok", "warning", "error", "duplicate"} else "ok"


def _normalize_callback_type(value: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in CALLBACK_TYPES else "stream_result"


def _feedback_row(row: BlueLogRefinerFeedback) -> dict[str, Any]:
    return {
        "feedback_id": str(row.id),
        "site_id": str(row.site_id),
        "run_id": str(row.run_id) if row.run_id else "",
        "connector_source": row.connector_source,
        "event_type": row.event_type,
        "recommendation_code": row.recommendation_code,
        "feedback_type": row.feedback_type,
        "note": row.note,
        "actor": row.actor,
        "created_at": _safe_iso(row.created_at),
    }


def _schedule_policy_row(site: Site, row: BlueLogRefinerSchedulePolicy | None, *, connector_source: str) -> dict[str, Any]:
    if row is None:
        return {
            "schedule_policy_id": "",
            "site_id": str(site.id),
            "connector_source": connector_source,
            "schedule_interval_minutes": 60,
            "dry_run_default": True,
            "callback_ingest_enabled": True,
            "enabled": True,
            "owner": "security",
            "created_at": "",
            "updated_at": "",
        }
    return {
        "schedule_policy_id": str(row.id),
        "site_id": str(row.site_id),
        "connector_source": row.connector_source,
        "schedule_interval_minutes": row.schedule_interval_minutes,
        "dry_run_default": bool(row.dry_run_default),
        "callback_ingest_enabled": bool(row.callback_ingest_enabled),
        "enabled": bool(row.enabled),
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _callback_row(row: BlueLogRefinerCallbackEvent) -> dict[str, Any]:
    return {
        "callback_id": str(row.id),
        "site_id": str(row.site_id),
        "run_id": str(row.run_id) if row.run_id else "",
        "connector_source": row.connector_source,
        "callback_type": row.callback_type,
        "source_system": row.source_system,
        "external_run_ref": row.external_run_ref,
        "webhook_event_id": row.webhook_event_id,
        "status": row.status,
        "total_events": row.total_events,
        "kept_events": row.kept_events,
        "dropped_events": row.dropped_events,
        "noise_reduction_pct": row.noise_reduction_pct,
        "estimated_storage_saved_kb": row.estimated_storage_saved_kb,
        "actor": row.actor,
        "details": _safe_json_dict(row.details_json),
        "created_at": _safe_iso(row.created_at),
    }


def _policy_row(site: Site, row: BlueLogRefinerPolicy | None, *, connector_source: str) -> dict[str, Any]:
    default_mode = MAPPING_PACKS.get(connector_source, MAPPING_PACKS["generic"])["execution_mode"]
    if row is None:
        return {
            "policy_id": "",
            "site_id": str(site.id),
            "connector_source": connector_source,
            "execution_mode": default_mode,
            "lookback_limit": 200,
            "min_keep_severity": "medium",
            "drop_recommendation_codes": ["ignore"],
            "target_noise_reduction_pct": 80,
            "average_event_size_kb": 4,
            "enabled": True,
            "owner": "security",
            "created_at": "",
            "updated_at": "",
        }
    return {
        "policy_id": str(row.id),
        "site_id": str(row.site_id),
        "connector_source": row.connector_source,
        "execution_mode": row.execution_mode,
        "lookback_limit": row.lookback_limit,
        "min_keep_severity": row.min_keep_severity,
        "drop_recommendation_codes": [str(item) for item in _safe_json_list(row.drop_recommendation_codes_json)],
        "target_noise_reduction_pct": row.target_noise_reduction_pct,
        "average_event_size_kb": row.average_event_size_kb,
        "enabled": bool(row.enabled),
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _run_row(row: BlueLogRefinerRun) -> dict[str, Any]:
    return {
        "run_id": str(row.id),
        "site_id": str(row.site_id),
        "connector_source": row.connector_source,
        "execution_mode": row.execution_mode,
        "dry_run": bool(row.dry_run),
        "status": row.status,
        "total_events": row.total_events,
        "kept_events": row.kept_events,
        "dropped_events": row.dropped_events,
        "feedback_adjusted_events": row.feedback_adjusted_events,
        "noise_reduction_pct": row.noise_reduction_pct,
        "estimated_storage_saved_kb": row.estimated_storage_saved_kb,
        "details": _safe_json_dict(row.details_json),
        "created_at": _safe_iso(row.created_at),
    }


def list_log_refiner_mapping_packs(*, source: str = "") -> dict[str, Any]:
    connector = _normalize_connector(source) if source else ""
    rows = []
    for pack_source, pack in MAPPING_PACKS.items():
        if connector and pack_source != connector:
            continue
        rows.append(
            {
                "source": pack_source,
                "display_name": pack["display_name"],
                "execution_mode": pack["execution_mode"],
                "notes": list(pack["notes"]),
                "field_mapping": list(pack["field_mapping"]),
            }
        )
    return {"status": "ok", "count": len(rows), "rows": rows}


def get_blue_log_refiner_policy(db: Session, *, site_id: UUID, connector_source: str = "generic") -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    normalized_connector = _normalize_connector(connector_source)
    row = db.scalar(
        select(BlueLogRefinerPolicy).where(
            BlueLogRefinerPolicy.site_id == site.id,
            BlueLogRefinerPolicy.connector_source == normalized_connector,
        )
    )
    return {"status": "ok", "policy": _policy_row(site, row, connector_source=normalized_connector)}


def get_blue_log_refiner_schedule_policy(db: Session, *, site_id: UUID, connector_source: str = "generic") -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    normalized_connector = _normalize_connector(connector_source)
    row = db.scalar(
        select(BlueLogRefinerSchedulePolicy).where(
            BlueLogRefinerSchedulePolicy.site_id == site.id,
            BlueLogRefinerSchedulePolicy.connector_source == normalized_connector,
        )
    )
    return {"status": "ok", "policy": _schedule_policy_row(site, row, connector_source=normalized_connector)}


def upsert_blue_log_refiner_schedule_policy(
    db: Session,
    *,
    site_id: UUID,
    connector_source: str = "generic",
    schedule_interval_minutes: int = 60,
    dry_run_default: bool = True,
    callback_ingest_enabled: bool = True,
    enabled: bool = True,
    owner: str = "security",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    normalized_connector = _normalize_connector(connector_source)
    row = db.scalar(
        select(BlueLogRefinerSchedulePolicy).where(
            BlueLogRefinerSchedulePolicy.site_id == site.id,
            BlueLogRefinerSchedulePolicy.connector_source == normalized_connector,
        )
    )
    now = _now()
    if row is None:
        row = BlueLogRefinerSchedulePolicy(site_id=site.id, connector_source=normalized_connector, created_at=now)
        db.add(row)
    row.schedule_interval_minutes = max(5, min(int(schedule_interval_minutes or 60), 1440))
    row.dry_run_default = bool(dry_run_default)
    row.callback_ingest_enabled = bool(callback_ingest_enabled)
    row.enabled = bool(enabled)
    row.owner = str(owner or "security")[:64]
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return {"status": "ok", "policy": _schedule_policy_row(site, row, connector_source=normalized_connector)}


def upsert_blue_log_refiner_policy(
    db: Session,
    *,
    site_id: UUID,
    connector_source: str = "generic",
    execution_mode: str = "pre_ingest",
    lookback_limit: int = 200,
    min_keep_severity: str = "medium",
    drop_recommendation_codes: list[str] | None = None,
    target_noise_reduction_pct: int = 80,
    average_event_size_kb: int = 4,
    enabled: bool = True,
    owner: str = "security",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    normalized_connector = _normalize_connector(connector_source)
    row = db.scalar(
        select(BlueLogRefinerPolicy).where(
            BlueLogRefinerPolicy.site_id == site.id,
            BlueLogRefinerPolicy.connector_source == normalized_connector,
        )
    )
    now = _now()
    if row is None:
        row = BlueLogRefinerPolicy(site_id=site.id, connector_source=normalized_connector, created_at=now)
        db.add(row)
    row.execution_mode = _normalize_mode(execution_mode)
    row.lookback_limit = max(20, min(int(lookback_limit or 200), 2000))
    row.min_keep_severity = _normalize_severity(min_keep_severity)
    row.drop_recommendation_codes_json = _as_json(
        [str(item).strip().lower() for item in (drop_recommendation_codes or ["ignore"]) if str(item).strip()]
    )
    row.target_noise_reduction_pct = max(10, min(int(target_noise_reduction_pct or 80), 99))
    row.average_event_size_kb = max(1, min(int(average_event_size_kb or 4), 512))
    row.enabled = bool(enabled)
    row.owner = str(owner or "security")[:64]
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return {"status": "ok", "policy": _policy_row(site, row, connector_source=normalized_connector)}


def _event_connector(row: BlueEventLog) -> str:
    payload = _safe_json_dict(row.payload_json)
    return _normalize_connector(payload.get("source") or payload.get("connector_source") or "generic")


def _feedback_preferences(rows: list[BlueLogRefinerFeedback]) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    keep: set[tuple[str, str]] = set()
    drop: set[tuple[str, str]] = set()
    for row in rows:
        fingerprint = (row.event_type or "", row.recommendation_code or "")
        if row.feedback_type in {"keep_signal", "signal_missed"}:
            keep.add(fingerprint)
        elif row.feedback_type in {"drop_noise", "false_positive"}:
            drop.add(fingerprint)
    return keep, drop


def run_blue_log_refiner(
    db: Session,
    *,
    site_id: UUID,
    connector_source: str = "generic",
    dry_run: bool = True,
    actor: str = "blue_log_refiner_ai",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    policy_payload = get_blue_log_refiner_policy(db, site_id=site.id, connector_source=connector_source)
    policy = policy_payload["policy"]
    if not policy.get("enabled", True):
        return {"status": "disabled", "site_id": str(site.id), "site_code": site.site_code, "policy": policy}

    rows = db.scalars(
        select(BlueEventLog)
        .where(BlueEventLog.site_id == site.id)
        .order_by(desc(BlueEventLog.created_at))
        .limit(max(20, min(int(policy["lookback_limit"]), 2000)))
    ).all()
    normalized_connector = _normalize_connector(connector_source)
    filtered_rows = [row for row in rows if _event_connector(row) == normalized_connector or normalized_connector == "generic"]

    feedback_rows = db.scalars(
        select(BlueLogRefinerFeedback)
        .where(
            BlueLogRefinerFeedback.site_id == site.id,
            BlueLogRefinerFeedback.connector_source == normalized_connector,
        )
        .order_by(desc(BlueLogRefinerFeedback.created_at))
        .limit(200)
    ).all()
    keep_preferences, drop_preferences = _feedback_preferences(feedback_rows)
    min_keep_rank = SEVERITY_RANK.get(str(policy["min_keep_severity"]), 2)
    drop_codes = {str(item).strip().lower() for item in policy.get("drop_recommendation_codes", [])}

    kept_rows: list[BlueEventLog] = []
    dropped_rows: list[BlueEventLog] = []
    adjusted = 0
    for row in filtered_rows:
        fingerprint = (row.event_type or "", row.ai_recommendation or "")
        keep_event = SEVERITY_RANK.get(row.ai_severity or "low", 1) >= min_keep_rank
        if (row.ai_recommendation or "").strip().lower() in drop_codes:
            keep_event = False
        if fingerprint in keep_preferences and not keep_event:
            keep_event = True
            adjusted += 1
        if fingerprint in drop_preferences and keep_event:
            keep_event = False
            adjusted += 1
        if keep_event:
            kept_rows.append(row)
        else:
            dropped_rows.append(row)

    total = len(filtered_rows)
    kept = len(kept_rows)
    dropped = len(dropped_rows)
    noise_reduction_pct = round((dropped / total) * 100) if total else 0
    estimated_storage_saved_kb = dropped * max(1, int(policy["average_event_size_kb"]))
    target_noise = int(policy["target_noise_reduction_pct"])
    status = "ok" if noise_reduction_pct >= target_noise else "warning"
    details = {
        "actor": actor,
        "target_noise_reduction_pct": target_noise,
        "average_event_size_kb": int(policy["average_event_size_kb"]),
        "signal_rows": [
            {
                "event_type": row.event_type,
                "severity": row.ai_severity,
                "source_ip": row.source_ip,
                "recommendation": row.ai_recommendation,
            }
            for row in kept_rows[:8]
        ],
        "dropped_rows": [
            {
                "event_type": row.event_type,
                "severity": row.ai_severity,
                "source_ip": row.source_ip,
                "recommendation": row.ai_recommendation,
            }
            for row in dropped_rows[:8]
        ],
        "feedback_summary": {
            "feedback_count": len(feedback_rows),
            "feedback_adjusted_events": adjusted,
        },
        "kpi": {
            "source_connector": normalized_connector,
            "source_siem_total_events": total,
            "refined_signal_events": kept,
            "noise_events_removed": dropped,
            "noise_reduction_pct": noise_reduction_pct,
            "estimated_storage_saved_kb": estimated_storage_saved_kb,
        },
    }
    row = BlueLogRefinerRun(
        site_id=site.id,
        connector_source=normalized_connector,
        execution_mode=str(policy["execution_mode"]),
        dry_run=bool(dry_run),
        status=status,
        total_events=total,
        kept_events=kept,
        dropped_events=dropped,
        feedback_adjusted_events=adjusted,
        noise_reduction_pct=noise_reduction_pct,
        estimated_storage_saved_kb=estimated_storage_saved_kb,
        details_json=_as_json(details),
        created_at=_now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "status": status,
        "site_id": str(site.id),
        "site_code": site.site_code,
        "policy": policy,
        "run": _run_row(row),
    }


def list_blue_log_refiner_runs(db: Session, *, site_id: UUID, connector_source: str = "", limit: int = 20) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    stmt = (
        select(BlueLogRefinerRun)
        .where(BlueLogRefinerRun.site_id == site.id)
        .order_by(desc(BlueLogRefinerRun.created_at))
        .limit(max(1, min(limit, 200)))
    )
    normalized_connector = _normalize_connector(connector_source) if connector_source else ""
    if normalized_connector:
        stmt = stmt.where(BlueLogRefinerRun.connector_source == normalized_connector)
    rows = db.scalars(stmt).all()
    return {"status": "ok", "count": len(rows), "rows": [_run_row(row) for row in rows]}


def submit_blue_log_refiner_feedback(
    db: Session,
    *,
    site_id: UUID,
    connector_source: str = "generic",
    feedback_type: str = "keep_signal",
    event_type: str = "",
    recommendation_code: str = "",
    note: str = "",
    actor: str = "analyst",
    run_id: UUID | None = None,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    normalized_feedback = str(feedback_type or "").strip().lower()
    if normalized_feedback not in FEEDBACK_TYPES:
        normalized_feedback = "keep_signal"
    row = BlueLogRefinerFeedback(
        site_id=site.id,
        run_id=run_id,
        connector_source=_normalize_connector(connector_source),
        event_type=str(event_type or "")[:64],
        recommendation_code=str(recommendation_code or "")[:64],
        feedback_type=normalized_feedback,
        note=str(note or "")[:2048],
        actor=str(actor or "analyst")[:128],
        created_at=_now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "ok", "feedback": _feedback_row(row)}


def list_blue_log_refiner_feedback(db: Session, *, site_id: UUID, connector_source: str = "", limit: int = 20) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    stmt = (
        select(BlueLogRefinerFeedback)
        .where(BlueLogRefinerFeedback.site_id == site.id)
        .order_by(desc(BlueLogRefinerFeedback.created_at))
        .limit(max(1, min(limit, 200)))
    )
    normalized_connector = _normalize_connector(connector_source) if connector_source else ""
    if normalized_connector:
        stmt = stmt.where(BlueLogRefinerFeedback.connector_source == normalized_connector)
    rows = db.scalars(stmt).all()
    return {"status": "ok", "count": len(rows), "rows": [_feedback_row(row) for row in rows]}


def _resolve_log_refiner_site(db: Session, *, site_id: UUID | None = None, site_code: str = "") -> Site | None:
    if site_id:
        return db.get(Site, site_id)
    code = str(site_code or "").strip().lower()
    if not code:
        return None
    return db.scalar(select(Site).where(Site.site_code == code))


def _find_matching_run(
    db: Session,
    *,
    site_id: UUID,
    connector_source: str,
    run_id: UUID | None = None,
) -> BlueLogRefinerRun | None:
    if run_id:
        run = db.get(BlueLogRefinerRun, run_id)
        if run and run.site_id == site_id:
            return run
    return db.scalar(
        select(BlueLogRefinerRun)
        .where(
            BlueLogRefinerRun.site_id == site_id,
            BlueLogRefinerRun.connector_source == connector_source,
        )
        .order_by(desc(BlueLogRefinerRun.created_at))
        .limit(1)
    )


def ingest_blue_log_refiner_callback(
    db: Session,
    *,
    site_id: UUID | None = None,
    site_code: str = "",
    connector_source: str = "generic",
    callback_type: str = "stream_result",
    source_system: str = "",
    external_run_ref: str = "",
    webhook_event_id: str = "",
    run_id: UUID | None = None,
    total_events: int = 0,
    kept_events: int = 0,
    dropped_events: int = 0,
    noise_reduction_pct: int | None = None,
    estimated_storage_saved_kb: int = 0,
    status: str = "ok",
    payload: dict[str, Any] | None = None,
    actor: str = "siem_callback",
) -> dict[str, Any]:
    site = _resolve_log_refiner_site(db, site_id=site_id, site_code=site_code)
    if not site:
        return {"status": "not_found", "site_id": str(site_id or ""), "site_code": str(site_code or "")}

    normalized_connector = _normalize_connector(connector_source)
    callback_id = str(webhook_event_id or "").strip()
    if callback_id:
        existing = db.scalar(
            select(BlueLogRefinerCallbackEvent)
            .where(
                BlueLogRefinerCallbackEvent.site_id == site.id,
                BlueLogRefinerCallbackEvent.connector_source == normalized_connector,
                BlueLogRefinerCallbackEvent.webhook_event_id == callback_id,
            )
            .order_by(desc(BlueLogRefinerCallbackEvent.created_at))
            .limit(1)
        )
        if existing:
            return {
                "status": "duplicate",
                "site_id": str(site.id),
                "site_code": site.site_code,
                "callback": _callback_row(existing),
                "matched_run": None,
            }

    total = max(0, int(total_events or 0))
    kept = max(0, int(kept_events or 0))
    dropped = max(0, int(dropped_events or 0))
    if total <= 0:
        total = max(kept + dropped, 0)
    if kept <= 0 and total > 0 and dropped <= total:
        kept = max(total - dropped, 0)
    if dropped <= 0 and total > 0 and kept <= total:
        dropped = max(total - kept, 0)
    computed_noise = round((dropped / total) * 100) if total else 0
    effective_noise = computed_noise if noise_reduction_pct is None else max(0, min(int(noise_reduction_pct), 100))

    matched_run = _find_matching_run(db, site_id=site.id, connector_source=normalized_connector, run_id=run_id)
    baseline_noise = matched_run.noise_reduction_pct if matched_run else None
    baseline_total = matched_run.total_events if matched_run else None
    delta_noise = effective_noise - int(baseline_noise or 0) if baseline_noise is not None else 0
    delta_total = total - int(baseline_total or 0) if baseline_total is not None else 0
    callback_status = _normalize_status(status)
    if callback_status == "ok" and matched_run and abs(delta_noise) >= 15:
        callback_status = "warning"

    details = {
        "payload": dict(payload or {}),
        "matched_run_id": str(matched_run.id) if matched_run else "",
        "baseline_run_noise_reduction_pct": baseline_noise,
        "baseline_run_total_events": baseline_total,
        "noise_reduction_delta_pct": delta_noise,
        "source_total_delta": delta_total,
    }
    row = BlueLogRefinerCallbackEvent(
        site_id=site.id,
        run_id=matched_run.id if matched_run else None,
        connector_source=normalized_connector,
        callback_type=_normalize_callback_type(callback_type),
        source_system=str(source_system or normalized_connector)[:64],
        external_run_ref=str(external_run_ref or "")[:128],
        webhook_event_id=callback_id[:255],
        status=callback_status,
        total_events=total,
        kept_events=kept,
        dropped_events=dropped,
        noise_reduction_pct=effective_noise,
        estimated_storage_saved_kb=max(0, int(estimated_storage_saved_kb or 0)),
        details_json=_as_json(details),
        actor=str(actor or "siem_callback")[:128],
        created_at=_now(),
    )
    db.add(row)
    if matched_run:
        run_details = _safe_json_dict(matched_run.details_json)
        run_details["latest_source_callback"] = {
            "callback_type": row.callback_type,
            "source_system": row.source_system,
            "status": callback_status,
            "noise_reduction_pct": effective_noise,
            "noise_reduction_delta_pct": delta_noise,
            "source_total_delta": delta_total,
            "external_run_ref": row.external_run_ref,
            "webhook_event_id": row.webhook_event_id,
        }
        run_details["callback_correlation"] = {
            "matched": True,
            "baseline_noise_reduction_pct": baseline_noise,
            "source_noise_reduction_pct": effective_noise,
            "noise_reduction_delta_pct": delta_noise,
            "baseline_total_events": baseline_total,
            "source_total_events": total,
            "source_total_delta": delta_total,
        }
        matched_run.details_json = _as_json(run_details)
    db.commit()
    db.refresh(row)
    return {
        "status": callback_status,
        "site_id": str(site.id),
        "site_code": site.site_code,
        "callback": _callback_row(row),
        "matched_run": _run_row(matched_run) if matched_run else None,
    }


def list_blue_log_refiner_callbacks(db: Session, *, site_id: UUID, connector_source: str = "", limit: int = 20) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    stmt = (
        select(BlueLogRefinerCallbackEvent)
        .where(BlueLogRefinerCallbackEvent.site_id == site.id)
        .order_by(desc(BlueLogRefinerCallbackEvent.created_at))
        .limit(max(1, min(limit, 200)))
    )
    normalized_connector = _normalize_connector(connector_source) if connector_source else ""
    if normalized_connector:
        stmt = stmt.where(BlueLogRefinerCallbackEvent.connector_source == normalized_connector)
    rows = db.scalars(stmt).all()
    return {"status": "ok", "count": len(rows), "rows": [_callback_row(row) for row in rows]}


def _is_schedule_due(policy: BlueLogRefinerSchedulePolicy, last_run: BlueLogRefinerRun | None, now: datetime) -> bool:
    if last_run is None or last_run.created_at is None:
        return True
    delta_minutes = (now - last_run.created_at).total_seconds() / 60.0
    return delta_minutes >= max(5, int(policy.schedule_interval_minutes or 60))


def run_blue_log_refiner_scheduler(
    db: Session,
    *,
    limit: int = 100,
    dry_run_override: bool | None = None,
    actor: str = "blue_log_refiner_scheduler_ai",
) -> dict[str, Any]:
    now = _now()
    policies = db.scalars(
        select(BlueLogRefinerSchedulePolicy)
        .where(BlueLogRefinerSchedulePolicy.enabled.is_(True))
        .order_by(desc(BlueLogRefinerSchedulePolicy.updated_at), desc(BlueLogRefinerSchedulePolicy.created_at))
        .limit(max(1, min(limit, 500)))
    ).all()
    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for schedule in policies:
        site = db.get(Site, schedule.site_id)
        if not site:
            skipped.append({"site_id": str(schedule.site_id), "site_code": "", "reason": "site_not_found"})
            continue
        policy = get_blue_log_refiner_policy(db, site_id=site.id, connector_source=schedule.connector_source).get("policy", {})
        if not bool(policy.get("enabled", True)):
            skipped.append(
                {
                    "site_id": str(site.id),
                    "site_code": site.site_code,
                    "connector_source": schedule.connector_source,
                    "reason": "policy_disabled",
                }
            )
            continue
        last_run = db.scalar(
            select(BlueLogRefinerRun)
            .where(
                BlueLogRefinerRun.site_id == site.id,
                BlueLogRefinerRun.connector_source == schedule.connector_source,
            )
            .order_by(desc(BlueLogRefinerRun.created_at))
            .limit(1)
        )
        if not _is_schedule_due(schedule, last_run, now):
            skipped.append(
                {
                    "site_id": str(site.id),
                    "site_code": site.site_code,
                    "connector_source": schedule.connector_source,
                    "reason": "schedule_not_due",
                }
            )
            continue
        result = run_blue_log_refiner(
            db,
            site_id=site.id,
            connector_source=schedule.connector_source,
            dry_run=schedule.dry_run_default if dry_run_override is None else bool(dry_run_override),
            actor=actor,
        )
        executed.append(
            {
                "site_id": str(site.id),
                "site_code": site.site_code,
                "connector_source": schedule.connector_source,
                "status": str(result.get("status", "unknown")),
                "run_id": str((result.get("run", {}) or {}).get("run_id", "")),
                "noise_reduction_pct": int((result.get("run", {}) or {}).get("noise_reduction_pct", 0) or 0),
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


def process_blue_log_refiner_schedules(limit: int = 100) -> dict[str, Any]:
    with SessionLocal() as db:
        return run_blue_log_refiner_scheduler(
            db,
            limit=limit,
            dry_run_override=None,
            actor="blue_log_refiner_ai",
        )
