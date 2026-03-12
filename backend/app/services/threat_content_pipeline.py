from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import ThreatContentPack, ThreatContentPipelinePolicy, ThreatContentPipelineRun
from app.db.session import SessionLocal

THREAT_PACK_LIBRARY: list[dict[str, Any]] = [
    {
        "pack_code": "identity_abuse_daily",
        "title": "Identity Abuse Daily Pack",
        "category": "identity",
        "mitre_techniques": ["T1078", "T1110", "T1556"],
        "attack_steps": [
            "credential stuffing simulation",
            "impossible travel account abuse",
            "MFA fatigue-style identity pressure",
        ],
        "validation_mode": "simulation_safe",
    },
    {
        "pack_code": "ransomware_preimpact_weekly",
        "title": "Ransomware Pre-Impact Validation",
        "category": "ransomware",
        "mitre_techniques": ["T1486", "T1021", "T1068"],
        "attack_steps": [
            "lateral movement chain replay",
            "privilege escalation signal validation",
            "impact-stage containment timing check",
        ],
        "validation_mode": "simulation_safe",
    },
    {
        "pack_code": "phishing_session_hijack",
        "title": "Phishing and Session Hijack Validation",
        "category": "phishing",
        "mitre_techniques": ["T1566", "T1539", "T1185"],
        "attack_steps": [
            "phishing entry simulation",
            "session token abuse replay",
            "post-auth privilege drift check",
        ],
        "validation_mode": "simulation_safe",
    },
    {
        "pack_code": "web_attack_surface_guard",
        "title": "Web Attack Surface Baseline",
        "category": "web",
        "mitre_techniques": ["T1190", "T1059", "T1505"],
        "attack_steps": [
            "public endpoint probe simulation",
            "auth endpoint brute-force pressure",
            "web shell persistence indicator replay",
        ],
        "validation_mode": "simulation_safe",
    },
]

DEFAULT_CATEGORIES = ["identity", "ransomware", "phishing", "web"]


def _as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


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


def _normalize_scope(value: str) -> str:
    scope = str(value or "global").strip().lower()
    return scope[:64] or "global"


def _normalize_categories(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        category = str(raw or "").strip().lower()
        if not category:
            continue
        category = category[:64]
        if category in seen:
            continue
        seen.add(category)
        out.append(category)
    return out


def _default_policy(scope: str) -> dict[str, Any]:
    return {
        "policy_id": "",
        "scope": scope,
        "min_refresh_interval_minutes": 1440,
        "preferred_categories": list(DEFAULT_CATEGORIES),
        "max_packs_per_run": 8,
        "auto_activate": True,
        "route_alert": False,
        "enabled": True,
        "owner": "system",
        "created_at": "",
        "updated_at": "",
    }


def _policy_row(row: ThreatContentPipelinePolicy) -> dict[str, Any]:
    categories = _normalize_categories([str(item) for item in _safe_json_list(row.preferred_categories_json)])
    if not categories:
        categories = list(DEFAULT_CATEGORIES)
    return {
        "policy_id": str(row.id),
        "scope": row.scope,
        "min_refresh_interval_minutes": row.min_refresh_interval_minutes,
        "preferred_categories": categories,
        "max_packs_per_run": row.max_packs_per_run,
        "auto_activate": bool(row.auto_activate),
        "route_alert": bool(row.route_alert),
        "enabled": bool(row.enabled),
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _run_row(row: ThreatContentPipelineRun) -> dict[str, Any]:
    return {
        "run_id": str(row.id),
        "scope": row.scope,
        "status": row.status,
        "dry_run": bool(row.dry_run),
        "selected_categories": _safe_json_list(row.selected_categories_json),
        "candidate_count": row.candidate_count,
        "refreshed_count": row.refreshed_count,
        "created_count": row.created_count,
        "activated_count": row.activated_count,
        "skipped_count": row.skipped_count,
        "alert_routed": bool(row.alert_routed),
        "details": _safe_json_dict(row.details_json),
        "created_at": _safe_iso(row.created_at),
    }


def get_threat_content_pipeline_policy(db: Session, scope: str = "global") -> dict[str, Any]:
    scope_key = _normalize_scope(scope)
    row = db.scalar(select(ThreatContentPipelinePolicy).where(ThreatContentPipelinePolicy.scope == scope_key))
    if row:
        return {"status": "ok", "policy": _policy_row(row)}
    return {"status": "default", "policy": _default_policy(scope_key)}


def upsert_threat_content_pipeline_policy(
    db: Session,
    *,
    scope: str,
    min_refresh_interval_minutes: int,
    preferred_categories: list[str],
    max_packs_per_run: int,
    auto_activate: bool,
    route_alert: bool,
    enabled: bool,
    owner: str,
) -> dict[str, Any]:
    scope_key = _normalize_scope(scope)
    categories = _normalize_categories(preferred_categories)
    if not categories:
        categories = list(DEFAULT_CATEGORIES)

    now = datetime.now(timezone.utc)
    row = db.scalar(select(ThreatContentPipelinePolicy).where(ThreatContentPipelinePolicy.scope == scope_key))
    if row:
        row.min_refresh_interval_minutes = max(5, min(int(min_refresh_interval_minutes), 7 * 24 * 60))
        row.preferred_categories_json = _as_json(categories)
        row.max_packs_per_run = max(1, min(int(max_packs_per_run), 50))
        row.auto_activate = bool(auto_activate)
        row.route_alert = bool(route_alert)
        row.enabled = bool(enabled)
        row.owner = owner.strip()[:64] or "security"
        row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"status": "updated", "policy": _policy_row(row)}

    created = ThreatContentPipelinePolicy(
        scope=scope_key,
        min_refresh_interval_minutes=max(5, min(int(min_refresh_interval_minutes), 7 * 24 * 60)),
        preferred_categories_json=_as_json(categories),
        max_packs_per_run=max(1, min(int(max_packs_per_run), 50)),
        auto_activate=bool(auto_activate),
        route_alert=bool(route_alert),
        enabled=bool(enabled),
        owner=owner.strip()[:64] or "security",
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"status": "created", "policy": _policy_row(created)}


def _is_schedule_due(*, enabled: bool, min_refresh_interval_minutes: int, last_run: ThreatContentPipelineRun | None, now: datetime) -> bool:
    if not bool(enabled):
        return False
    if last_run is None:
        return True
    if last_run.created_at is None:
        return True
    created_at = last_run.created_at if last_run.created_at.tzinfo else last_run.created_at.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(minutes=max(5, int(min_refresh_interval_minutes or 1440)))
    return created_at <= cutoff


def _select_candidates(categories: list[str], max_packs: int) -> list[dict[str, Any]]:
    category_set = set(_normalize_categories(categories) or DEFAULT_CATEGORIES)
    selected = [pack for pack in THREAT_PACK_LIBRARY if str(pack.get("category", "")).lower() in category_set]
    if not selected:
        selected = list(THREAT_PACK_LIBRARY)
    return selected[: max(1, min(max_packs, 50))]


def _apply_candidate(db: Session, candidate: dict[str, Any], *, dry_run: bool, auto_activate: bool) -> dict[str, Any]:
    pack_code = str(candidate.get("pack_code", "")).strip().lower()
    if not pack_code:
        return {"status": "skipped", "reason": "invalid_pack_code", "pack_code": ""}

    existing = db.scalar(select(ThreatContentPack).where(ThreatContentPack.pack_code == pack_code))
    if dry_run:
        return {
            "status": "dry_run",
            "pack_code": pack_code,
            "action": "update" if existing else "create",
            "activate": bool(auto_activate),
        }

    now = datetime.now(timezone.utc)
    if existing:
        existing.title = str(candidate.get("title", existing.title))[:255]
        existing.category = str(candidate.get("category", existing.category))[:64]
        existing.mitre_techniques_json = _as_json(candidate.get("mitre_techniques", []))
        existing.attack_steps_json = _as_json(candidate.get("attack_steps", []))
        existing.validation_mode = str(candidate.get("validation_mode", "simulation_safe"))[:32]
        if auto_activate:
            existing.is_active = True
        existing.updated_at = now
        return {
            "status": "refreshed",
            "pack_code": pack_code,
            "action": "update",
            "activate": bool(auto_activate),
        }

    row = ThreatContentPack(
        pack_code=pack_code,
        title=str(candidate.get("title", pack_code))[:255],
        category=str(candidate.get("category", "generic"))[:64],
        mitre_techniques_json=_as_json(candidate.get("mitre_techniques", [])),
        attack_steps_json=_as_json(candidate.get("attack_steps", [])),
        validation_mode=str(candidate.get("validation_mode", "simulation_safe"))[:32],
        is_active=bool(auto_activate),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    return {
        "status": "created",
        "pack_code": pack_code,
        "action": "create",
        "activate": bool(auto_activate),
    }


def run_threat_content_pipeline(
    db: Session,
    *,
    scope: str = "global",
    dry_run: bool | None = None,
    force: bool = False,
    actor: str = "threat_content_pipeline_ai",
) -> dict[str, Any]:
    scope_key = _normalize_scope(scope)
    policy_resp = get_threat_content_pipeline_policy(db, scope_key)
    policy = policy_resp.get("policy", {}) if isinstance(policy_resp, dict) else {}
    if not policy:
        return {"status": "policy_not_found", "scope": scope_key}
    if not bool(policy.get("enabled", True)):
        return {"status": "disabled", "scope": scope_key, "policy": policy}

    selected_categories = _normalize_categories([str(item) for item in policy.get("preferred_categories", [])]) or list(DEFAULT_CATEGORIES)
    max_packs = max(1, min(int(policy.get("max_packs_per_run", 8) or 8), 50))
    candidates = _select_candidates(selected_categories, max_packs)

    last_run = db.scalar(
        select(ThreatContentPipelineRun)
        .where(ThreatContentPipelineRun.scope == scope_key)
        .order_by(desc(ThreatContentPipelineRun.created_at))
        .limit(1)
    )
    now = datetime.now(timezone.utc)
    due = _is_schedule_due(
        enabled=bool(policy.get("enabled", True)),
        min_refresh_interval_minutes=max(5, min(int(policy.get("min_refresh_interval_minutes", 1440) or 1440), 7 * 24 * 60)),
        last_run=last_run,
        now=now,
    )
    should_run = bool(force or due)

    resolved_dry_run = (not bool(policy.get("auto_activate", True))) if dry_run is None else bool(dry_run)

    refreshed_count = 0
    created_count = 0
    activated_count = 0
    skipped_count = 0
    candidate_details: list[dict[str, Any]] = []

    status = "no_action"
    reason = "schedule_not_due"
    if should_run:
        reason = "scheduled_refresh" if due and not force else "forced_refresh"
        status = "dry_run" if resolved_dry_run else "ok"
        for candidate in candidates:
            result = _apply_candidate(db, candidate, dry_run=resolved_dry_run, auto_activate=bool(policy.get("auto_activate", True)))
            candidate_details.append(result)
            action = str(result.get("status", "skipped"))
            if action == "created":
                created_count += 1
            elif action == "refreshed":
                refreshed_count += 1
            elif action == "dry_run":
                skipped_count += 1
            else:
                skipped_count += 1
            if bool(result.get("activate", False)):
                activated_count += 1

    run = ThreatContentPipelineRun(
        scope=scope_key,
        status=status,
        dry_run=resolved_dry_run,
        selected_categories_json=_as_json(selected_categories),
        candidate_count=len(candidates),
        refreshed_count=refreshed_count,
        created_count=created_count,
        activated_count=activated_count,
        skipped_count=skipped_count,
        alert_routed=False,
        details_json=_as_json(
            {
                "reason": reason,
                "force": force,
                "actor": actor,
                "policy": policy,
                "candidate_results": candidate_details,
            }
        ),
        created_at=now,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    federation = threat_content_pipeline_federation(db, limit=200)
    return {
        "status": status,
        "scope": scope_key,
        "policy": policy,
        "execution": {
            "should_run": should_run,
            "dry_run": resolved_dry_run,
            "reason": reason,
            "candidate_count": len(candidates),
            "created_count": created_count,
            "refreshed_count": refreshed_count,
            "activated_count": activated_count,
            "skipped_count": skipped_count,
        },
        "run": _run_row(run),
        "federation": federation,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def list_threat_content_pipeline_runs(db: Session, *, scope: str = "", limit: int = 100) -> dict[str, Any]:
    stmt = select(ThreatContentPipelineRun).order_by(desc(ThreatContentPipelineRun.created_at)).limit(max(1, min(limit, 1000)))
    if scope:
        stmt = stmt.where(ThreatContentPipelineRun.scope == _normalize_scope(scope))
    rows = db.scalars(stmt).all()
    return {
        "count": len(rows),
        "rows": [_run_row(row) for row in rows],
    }


def threat_content_pipeline_federation(db: Session, *, limit: int = 200, stale_after_hours: int = 48) -> dict[str, Any]:
    rows = db.scalars(
        select(ThreatContentPack)
        .where(ThreatContentPack.is_active.is_(True))
        .order_by(desc(ThreatContentPack.updated_at))
        .limit(max(1, min(limit, 5000)))
    ).all()

    now = datetime.now(timezone.utc)
    grouped: dict[str, list[ThreatContentPack]] = defaultdict(list)
    for row in rows:
        grouped[(row.category or "generic").lower()].append(row)

    federation_rows: list[dict[str, Any]] = []
    stale_count = 0
    for category in sorted(grouped.keys()):
        packs = grouped[category]
        latest = max((pack.updated_at for pack in packs if pack.updated_at), default=None)
        latest_iso = _safe_iso(latest)
        is_stale = False
        if latest:
            latest_time = latest if latest.tzinfo else latest.replace(tzinfo=timezone.utc)
            is_stale = latest_time <= now - timedelta(hours=max(1, min(int(stale_after_hours), 24 * 30)))
        if is_stale:
            stale_count += 1

        techniques = set()
        for pack in packs:
            for technique in _safe_json_list(pack.mitre_techniques_json):
                techniques.add(str(technique))

        federation_rows.append(
            {
                "category": category,
                "pack_count": len(packs),
                "unique_mitre_techniques": len(techniques),
                "latest_updated_at": latest_iso,
                "is_stale": is_stale,
            }
        )

    return {
        "generated_at": now.isoformat(),
        "count": len(federation_rows),
        "stale_count": stale_count,
        "rows": federation_rows,
    }


def run_threat_content_pipeline_scheduler(
    db: Session,
    *,
    limit: int = 200,
    dry_run_override: bool | None = None,
    actor: str = "threat_content_pipeline_ai",
) -> dict[str, Any]:
    policies = db.scalars(
        select(ThreatContentPipelinePolicy)
        .where(ThreatContentPipelinePolicy.enabled.is_(True))
        .order_by(desc(ThreatContentPipelinePolicy.updated_at))
        .limit(max(1, min(limit, 2000)))
    ).all()

    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for policy in policies:
        result = run_threat_content_pipeline(
            db,
            scope=policy.scope,
            dry_run=dry_run_override,
            force=False,
            actor=actor,
        )
        execution = result.get("execution", {}) if isinstance(result, dict) else {}
        if not bool(execution.get("should_run", False)):
            skipped.append(
                {
                    "scope": policy.scope,
                    "reason": str(execution.get("reason", "schedule_not_due")),
                }
            )
            continue

        executed.append(
            {
                "scope": policy.scope,
                "status": str(result.get("status", "unknown")),
                "run_id": str((result.get("run", {}) or {}).get("run_id", "")),
                "candidate_count": int(execution.get("candidate_count", 0) or 0),
            }
        )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scheduled_policy_count": len(policies),
        "executed_count": len(executed),
        "skipped_count": len(skipped),
        "executed": executed,
        "skipped": skipped,
    }


def process_threat_content_pipeline_schedules(limit: int = 100) -> dict[str, Any]:
    with SessionLocal() as db:
        return run_threat_content_pipeline_scheduler(
            db,
            limit=limit,
            dry_run_override=None,
            actor="threat_content_pipeline_ai",
        )
