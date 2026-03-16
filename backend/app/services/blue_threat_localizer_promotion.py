from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    BlueThreatLocalizerPromotionRun,
    BlueThreatLocalizerRoutingPolicy,
    BlueThreatLocalizerRun,
    Site,
    Tenant,
)
from app.services.action_center import dispatch_manual_alert
from app.services.detection_autotune import run_detection_autotune
from app.services.soar_playbook_hub import execute_playbook

RISK_TIER_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
DEFAULT_GROUPS = ["soc_l1", "threat_hunting", "security_lead"]
DEFAULT_GROUP_CHANNELS = {
    "soc_l1": ["telegram"],
    "threat_hunting": ["teams"],
    "security_lead": ["line"],
}
DEFAULT_CATEGORY_GROUPS = {
    "identity": ["soc_l1", "security_lead"],
    "phishing": ["soc_l1", "security_lead"],
    "web": ["threat_hunting", "soc_l1"],
    "ransomware": ["threat_hunting", "security_lead"],
    "malware": ["threat_hunting"],
    "insider": ["security_lead"],
}
CATEGORY_PLAYBOOK_MAP = {
    "identity": ["notify-and-clear-session"],
    "phishing": ["notify-and-clear-session"],
    "web": ["block-ip-and-waf-tighten"],
    "ransomware": ["isolate-host-and-reset-session"],
    "malware": ["isolate-host-and-reset-session"],
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


def _normalize_tier(value: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in RISK_TIER_RANK else "high"


def _normalize_group_list(value: list[Any] | None) -> list[str]:
    out: list[str] = []
    for item in value or []:
        candidate = str(item or "").strip().lower()
        if candidate and candidate not in out:
            out.append(candidate)
    return out


def _normalize_group_channel_map(value: dict[str, Any] | None) -> dict[str, list[str]]:
    raw = value or {}
    out: dict[str, list[str]] = {}
    for group, channels in raw.items():
        key = str(group or "").strip().lower()
        if not key:
            continue
        if isinstance(channels, list):
            normalized = [str(item or "").strip().lower() for item in channels if str(item or "").strip()]
        else:
            normalized = [str(channels or "").strip().lower()] if str(channels or "").strip() else []
        out[key] = list(dict.fromkeys(normalized))
    return out


def _routing_policy_row(site: Site, row: BlueThreatLocalizerRoutingPolicy | None) -> dict[str, Any]:
    if row is None:
        return {
            "routing_policy_id": "",
            "site_id": str(site.id),
            "stakeholder_groups": list(DEFAULT_GROUPS),
            "group_channel_map": dict(DEFAULT_GROUP_CHANNELS),
            "category_group_map": dict(DEFAULT_CATEGORY_GROUPS),
            "min_priority_score": 60,
            "min_risk_tier": "high",
            "auto_promote_on_gap": True,
            "auto_apply_autotune": False,
            "dispatch_via_action_center": True,
            "playbook_promotion_enabled": True,
            "owner": "security",
            "created_at": "",
            "updated_at": "",
        }
    return {
        "routing_policy_id": str(row.id),
        "site_id": str(row.site_id),
        "stakeholder_groups": [str(item) for item in _safe_json_list(row.stakeholder_groups_json)],
        "group_channel_map": _safe_json_dict(row.group_channel_map_json),
        "category_group_map": _safe_json_dict(row.category_group_map_json),
        "min_priority_score": row.min_priority_score,
        "min_risk_tier": row.min_risk_tier,
        "auto_promote_on_gap": bool(row.auto_promote_on_gap),
        "auto_apply_autotune": bool(row.auto_apply_autotune),
        "dispatch_via_action_center": bool(row.dispatch_via_action_center),
        "playbook_promotion_enabled": bool(row.playbook_promotion_enabled),
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _promotion_run_row(row: BlueThreatLocalizerPromotionRun) -> dict[str, Any]:
    return {
        "promotion_run_id": str(row.id),
        "site_id": str(row.site_id),
        "localizer_run_id": str(row.localizer_run_id) if row.localizer_run_id else "",
        "status": row.status,
        "promoted_categories": [str(item) for item in _safe_json_list(row.promoted_categories_json)],
        "routed_groups": [str(item) for item in _safe_json_list(row.routed_groups_json)],
        "playbook_codes": [str(item) for item in _safe_json_list(row.playbook_codes_json)],
        "autotune_run_id": row.autotune_run_id,
        "details": _safe_json_dict(row.details_json),
        "actor": row.actor,
        "created_at": _safe_iso(row.created_at),
    }


def get_blue_threat_localizer_routing_policy(db: Session, *, site_id: UUID) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    row = db.scalar(select(BlueThreatLocalizerRoutingPolicy).where(BlueThreatLocalizerRoutingPolicy.site_id == site.id))
    return {"status": "ok", "policy": _routing_policy_row(site, row)}


def upsert_blue_threat_localizer_routing_policy(
    db: Session,
    *,
    site_id: UUID,
    stakeholder_groups: list[str],
    group_channel_map: dict[str, Any],
    category_group_map: dict[str, Any],
    min_priority_score: int = 60,
    min_risk_tier: str = "high",
    auto_promote_on_gap: bool = True,
    auto_apply_autotune: bool = False,
    dispatch_via_action_center: bool = True,
    playbook_promotion_enabled: bool = True,
    owner: str = "security",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    row = db.scalar(select(BlueThreatLocalizerRoutingPolicy).where(BlueThreatLocalizerRoutingPolicy.site_id == site.id))
    now = _now()
    if row is None:
        row = BlueThreatLocalizerRoutingPolicy(site_id=site.id, created_at=now)
        db.add(row)
    normalized_groups = _normalize_group_list(stakeholder_groups) or list(DEFAULT_GROUPS)
    normalized_channels = _normalize_group_channel_map(group_channel_map) or dict(DEFAULT_GROUP_CHANNELS)
    normalized_category_groups = _normalize_group_channel_map(category_group_map) or dict(DEFAULT_CATEGORY_GROUPS)
    row.stakeholder_groups_json = _as_json(normalized_groups)
    row.group_channel_map_json = _as_json(normalized_channels)
    row.category_group_map_json = _as_json(normalized_category_groups)
    row.min_priority_score = max(1, min(int(min_priority_score or 60), 100))
    row.min_risk_tier = _normalize_tier(min_risk_tier)
    row.auto_promote_on_gap = bool(auto_promote_on_gap)
    row.auto_apply_autotune = bool(auto_apply_autotune)
    row.dispatch_via_action_center = bool(dispatch_via_action_center)
    row.playbook_promotion_enabled = bool(playbook_promotion_enabled)
    row.owner = str(owner or "security")[:64]
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return {"status": "ok", "policy": _routing_policy_row(site, row)}


def _risk_meets_threshold(priority_score: int, risk_tier: str, *, min_priority_score: int, min_risk_tier: str) -> bool:
    return int(priority_score or 0) >= int(min_priority_score or 60) and RISK_TIER_RANK.get(_normalize_tier(risk_tier), 0) >= RISK_TIER_RANK.get(
        _normalize_tier(min_risk_tier), 0
    )


def _select_groups(policy: dict[str, Any], missing_categories: list[str]) -> list[str]:
    stakeholder_groups = _normalize_group_list(policy.get("stakeholder_groups")) or list(DEFAULT_GROUPS)
    category_group_map = _normalize_group_channel_map(policy.get("category_group_map")) or dict(DEFAULT_CATEGORY_GROUPS)
    selected: list[str] = []
    for category in missing_categories:
        for group in category_group_map.get(str(category or "").strip().lower(), []):
            if group in stakeholder_groups and group not in selected:
                selected.append(group)
    return selected or stakeholder_groups


def _recommended_playbooks(missing_categories: list[str]) -> list[str]:
    codes: list[str] = []
    for category in missing_categories:
        for code in CATEGORY_PLAYBOOK_MAP.get(str(category or "").strip().lower(), []):
            if code not in codes:
                codes.append(code)
    return codes[:3]


def promote_blue_threat_localizer_gap(
    db: Session,
    *,
    site_id: UUID,
    localizer_run_id: UUID | None = None,
    auto_apply_override: bool | None = None,
    playbook_promotion_override: bool | None = None,
    actor: str = "blue_threat_promotion_ai",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    localizer_run = None
    if localizer_run_id:
        localizer_run = db.get(BlueThreatLocalizerRun, localizer_run_id)
        if localizer_run and localizer_run.site_id != site.id:
            localizer_run = None
    if localizer_run is None:
        localizer_run = db.scalar(
            select(BlueThreatLocalizerRun)
            .where(BlueThreatLocalizerRun.site_id == site.id)
            .order_by(desc(BlueThreatLocalizerRun.created_at))
            .limit(1)
        )
    if localizer_run is None:
        return {"status": "localizer_run_not_found", "site_id": str(site.id), "site_code": site.site_code}

    routing_policy = get_blue_threat_localizer_routing_policy(db, site_id=site.id).get("policy", _routing_policy_row(site, None))
    details = _safe_json_dict(localizer_run.details_json)
    detection_gap = details.get("detection_gap", {})
    if not isinstance(detection_gap, dict):
        detection_gap = {}
    missing_categories = [str(item) for item in detection_gap.get("missing_categories", []) if str(item)]
    if not missing_categories:
        return {
            "status": "no_gap",
            "site_id": str(site.id),
            "site_code": site.site_code,
            "routing_policy": routing_policy,
            "localizer_run": {
                "run_id": str(localizer_run.id),
                "priority_score": localizer_run.priority_score,
                "risk_tier": localizer_run.risk_tier,
            },
        }

    if not _risk_meets_threshold(
        localizer_run.priority_score,
        localizer_run.risk_tier,
        min_priority_score=int(routing_policy.get("min_priority_score", 60)),
        min_risk_tier=str(routing_policy.get("min_risk_tier", "high")),
    ):
        return {
            "status": "below_threshold",
            "site_id": str(site.id),
            "site_code": site.site_code,
            "routing_policy": routing_policy,
            "localizer_run": {
                "run_id": str(localizer_run.id),
                "priority_score": localizer_run.priority_score,
                "risk_tier": localizer_run.risk_tier,
            },
            "missing_categories": missing_categories,
        }

    groups = _select_groups(routing_policy, missing_categories)
    group_channel_map = _normalize_group_channel_map(routing_policy.get("group_channel_map")) or dict(DEFAULT_GROUP_CHANNELS)
    tenant = db.get(Tenant, site.tenant_id)
    dispatch_rows: list[dict[str, Any]] = []
    if bool(routing_policy.get("dispatch_via_action_center", True)) and tenant:
        for group in groups[:6]:
            dispatch = dispatch_manual_alert(
                db,
                tenant_code=tenant.tenant_code,
                site_code=site.site_code,
                source=f"blue_threat_localizer:{group}",
                severity=_normalize_tier(localizer_run.risk_tier),
                title=f"Threat Localizer Gap Promotion: {site.display_name}",
                message=f"missing_categories={', '.join(missing_categories)} priority={localizer_run.priority_score} routed_group={group}",
                payload={
                    "stakeholder_group": group,
                    "channels": group_channel_map.get(group, []),
                    "missing_categories": missing_categories,
                    "localizer_run_id": str(localizer_run.id),
                },
            )
            dispatch_rows.append(
                {
                    "group": group,
                    "channels": group_channel_map.get(group, []),
                    "routing": dispatch.get("routing", {}),
                }
            )

    auto_apply = bool(routing_policy.get("auto_apply_autotune", False)) if auto_apply_override is None else bool(auto_apply_override)
    autotune_result = run_detection_autotune(
        db,
        site_id=site.id,
        dry_run=False if auto_apply else True,
        force=True,
        actor=actor,
    )
    playbook_enabled = bool(routing_policy.get("playbook_promotion_enabled", True))
    if playbook_promotion_override is not None:
        playbook_enabled = bool(playbook_promotion_override)
    playbook_codes = _recommended_playbooks(missing_categories) if playbook_enabled else []
    playbook_results: list[dict[str, Any]] = []
    for code in playbook_codes:
        result = execute_playbook(
            db,
            site_id=site.id,
            playbook_code=code,
            actor=actor,
            require_approval=not auto_apply,
            dry_run=not auto_apply,
            params={
                "source": "blue_threat_localizer_promotion",
                "localizer_run_id": str(localizer_run.id),
                "missing_categories": missing_categories,
                "priority_score": localizer_run.priority_score,
            },
        )
        playbook_results.append(
            {
                "playbook_code": code,
                "status": str(result.get("status", "unknown")),
                "execution_id": str((result.get("execution", {}) or {}).get("execution_id", "")),
            }
        )

    promotion_status = "promoted"
    if not dispatch_rows and not playbook_results and not autotune_result.get("run"):
        promotion_status = "no_action"
    row = BlueThreatLocalizerPromotionRun(
        site_id=site.id,
        localizer_run_id=localizer_run.id,
        status=promotion_status,
        promoted_categories_json=_as_json(missing_categories),
        routed_groups_json=_as_json(groups),
        playbook_codes_json=_as_json(playbook_codes),
        autotune_run_id=str((autotune_result.get("run", {}) or {}).get("run_id", "")),
        details_json=_as_json(
            {
                "dispatches": dispatch_rows,
                "autotune": autotune_result,
                "playbooks": playbook_results,
                "priority_score": localizer_run.priority_score,
                "risk_tier": localizer_run.risk_tier,
            }
        ),
        actor=str(actor or "blue_threat_promotion_ai")[:128],
        created_at=_now(),
    )
    db.add(row)
    localizer_details = _safe_json_dict(localizer_run.details_json)
    localizer_details["routing_pack"] = {
        "stakeholder_groups": groups,
        "group_channel_map": group_channel_map,
        "auto_promote_on_gap": bool(routing_policy.get("auto_promote_on_gap", True)),
    }
    localizer_details["gap_promotion"] = {
        "promotion_status": promotion_status,
        "playbook_codes": playbook_codes,
        "autotune_run_id": row.autotune_run_id,
        "routed_group_count": len(groups),
    }
    localizer_run.details_json = _as_json(localizer_details)
    db.commit()
    db.refresh(row)
    return {
        "status": promotion_status,
        "site_id": str(site.id),
        "site_code": site.site_code,
        "routing_policy": routing_policy,
        "promotion": _promotion_run_row(row),
    }


def list_blue_threat_localizer_promotion_runs(db: Session, *, site_id: UUID, limit: int = 20) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    rows = db.scalars(
        select(BlueThreatLocalizerPromotionRun)
        .where(BlueThreatLocalizerPromotionRun.site_id == site.id)
        .order_by(desc(BlueThreatLocalizerPromotionRun.created_at))
        .limit(max(1, min(limit, 200)))
    ).all()
    return {"status": "ok", "count": len(rows), "rows": [_promotion_run_row(row) for row in rows]}
