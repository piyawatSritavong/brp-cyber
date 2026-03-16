from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    BlueEventLog,
    BlueDetectionRule,
    BlueThreatFeedItem,
    BlueThreatLocalizerPolicy,
    BlueThreatLocalizerRun,
    RedExploitPathRun,
    Site,
    SiteEmbeddedWorkflowEndpoint,
    ThreatContentPack,
)
from app.db.session import SessionLocal

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
ALLOWED_CATEGORIES = {"identity", "phishing", "ransomware", "web", "malware", "insider"}

SECTOR_PROFILES: dict[str, dict[str, Any]] = {
    "general": {
        "label_th": "องค์กรทั่วไป",
        "priority_categories": ["identity", "phishing", "web"],
        "keywords": ["login", "credential", "mail", "http", "waf"],
        "risk_bias": 1.0,
    },
    "finance": {
        "label_th": "การเงิน/ธนาคาร",
        "priority_categories": ["identity", "phishing", "ransomware", "web"],
        "keywords": ["payment", "swift", "credential", "otp", "admin"],
        "risk_bias": 1.25,
    },
    "government": {
        "label_th": "หน่วยงานรัฐ",
        "priority_categories": ["phishing", "identity", "web", "insider"],
        "keywords": ["document", "mail", "account", "portal", "attachment"],
        "risk_bias": 1.15,
    },
    "healthcare": {
        "label_th": "สาธารณสุข",
        "priority_categories": ["ransomware", "identity", "phishing"],
        "keywords": ["patient", "records", "credential", "vpn"],
        "risk_bias": 1.2,
    },
    "education": {
        "label_th": "การศึกษา",
        "priority_categories": ["phishing", "identity", "web"],
        "keywords": ["student", "mail", "portal", "password"],
        "risk_bias": 1.05,
    },
}

ADAPTER_TEMPLATES: dict[str, dict[str, Any]] = {
    "splunk": {
        "display_name": "Splunk Threat Feed Adapter",
        "description": "Normalize Splunk ES notable/search results into Blue threat feed rows.",
        "field_mapping": [
            {"incoming": "result.search_name", "mapped_to": "title"},
            {"incoming": "result.description", "mapped_to": "summary_th"},
            {"incoming": "result.severity", "mapped_to": "severity"},
            {"incoming": "result.tag/category", "mapped_to": "category"},
        ],
        "categories_supported": ["identity", "phishing", "ransomware", "web", "malware"],
        "sample_payload": {
            "results": [
                {
                    "sid": "splunk-001",
                    "search_name": "Brute Force Against Admin Login",
                    "description": "Repeated failed login against admin portal from suspicious IP.",
                    "severity": "high",
                    "category": "identity",
                    "region": "thailand",
                    "src_ip": "198.51.100.20",
                    "tags": ["finance"],
                }
            ]
        },
    },
    "crowdstrike": {
        "display_name": "CrowdStrike Threat Feed Adapter",
        "description": "Normalize CrowdStrike alert resources into localized threat feed rows.",
        "field_mapping": [
            {"incoming": "resource.behavior", "mapped_to": "title"},
            {"incoming": "resource.description", "mapped_to": "summary_th"},
            {"incoming": "resource.severity_name", "mapped_to": "severity"},
            {"incoming": "resource.tactic/technique", "mapped_to": "category"},
        ],
        "categories_supported": ["identity", "malware", "phishing", "ransomware"],
        "sample_payload": {
            "resources": [
                {
                    "id": "cs-001",
                    "behavior": "Credential Dumping Attempt",
                    "description": "Falcon observed credential dumping behavior on finance workstation.",
                    "severity_name": "critical",
                    "tactic": "credential_access",
                    "region": "thailand",
                    "host_groups": ["finance"],
                    "device_id": "aid-123",
                }
            ]
        },
    },
    "cloudflare": {
        "display_name": "Cloudflare Threat Feed Adapter",
        "description": "Normalize Cloudflare security analytics rows into localized threat feed rows.",
        "field_mapping": [
            {"incoming": "result.action/service", "mapped_to": "title"},
            {"incoming": "result.message", "mapped_to": "summary_th"},
            {"incoming": "result.score/severity", "mapped_to": "severity"},
            {"incoming": "result.service", "mapped_to": "category"},
        ],
        "categories_supported": ["web", "identity", "phishing"],
        "sample_payload": {
            "result": [
                {
                    "ray_id": "cf-ray-001",
                    "action": "managed_challenge",
                    "service": "waf",
                    "message": "Observed credential stuffing pattern against /admin/login.",
                    "severity": "high",
                    "region": "thailand",
                    "clientIP": "203.0.113.50",
                    "tags": ["web", "government"],
                }
            ]
        },
    },
    "generic": {
        "display_name": "Generic Threat Feed Adapter",
        "description": "Pass through generic threat rows with best-effort category inference.",
        "field_mapping": [
            {"incoming": "item.title", "mapped_to": "title"},
            {"incoming": "item.summary_th/description", "mapped_to": "summary_th"},
            {"incoming": "item.severity", "mapped_to": "severity"},
            {"incoming": "item.category", "mapped_to": "category"},
        ],
        "categories_supported": ["identity", "phishing", "ransomware", "web", "malware", "insider"],
        "sample_payload": {
            "items": [
                {
                    "id": "generic-001",
                    "title": "Thai phishing campaign abusing tax refund lure",
                    "description": "Campaign targets finance staff with Thai-language login pages.",
                    "severity": "high",
                    "category": "phishing",
                    "focus_region": "thailand",
                    "sectors": ["finance"],
                    "iocs": ["tax-refund-login.example"],
                }
            ]
        },
    },
}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "identity": ["credential", "login", "auth", "password", "mfa", "admin", "signin"],
    "phishing": ["phish", "mail", "smtp", "otp", "lure", "spoof", "attachment"],
    "ransomware": ["ransom", "encrypt", "locker", "double extortion"],
    "web": ["waf", "http", "sql", "xss", "api", "upload", "graphql"],
    "malware": ["malware", "trojan", "beacon", "rat", "loader"],
    "insider": ["privilege", "abuse", "insider", "exfiltration"],
}

CONNECTOR_CATEGORY_COVERAGE: dict[str, list[str]] = {
    "splunk": ["identity", "phishing", "ransomware", "web", "malware", "insider"],
    "crowdstrike": ["identity", "malware", "ransomware"],
    "cloudflare": ["web", "identity", "phishing"],
    "generic": ["identity", "phishing", "ransomware", "web"],
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


def _tier_from_score(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _normalize_region(value: str) -> str:
    text = str(value or "").strip().lower()
    return text or "thailand"


def _normalize_sector(value: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in SECTOR_PROFILES else "general"


def _normalize_category(value: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in ALLOWED_CATEGORIES else "identity"


def _normalize_severity(value: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in SEVERITY_RANK else "medium"


def _profile_for_sector(sector: str) -> dict[str, Any]:
    return dict(SECTOR_PROFILES.get(_normalize_sector(sector), SECTOR_PROFILES["general"]))


def _normalize_adapter_source(value: str) -> str:
    text = str(value or "").strip().lower()
    return text if text in ADAPTER_TEMPLATES else "generic"


def _infer_category_from_text(*parts: str) -> str:
    joined = " ".join(str(part or "").lower() for part in parts)
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in joined for keyword in keywords):
            return category
    return "identity"


def _infer_sectors(*parts: Any) -> list[str]:
    normalized: list[str] = []
    for part in parts:
        if isinstance(part, list):
            for item in part:
                sector = _normalize_sector(str(item or "general"))
                if sector not in normalized:
                    normalized.append(sector)
        elif isinstance(part, str) and part.strip():
            sector = _normalize_sector(part)
            if sector not in normalized:
                normalized.append(sector)
    return normalized or ["general"]


def _extract_iocs(raw: dict[str, Any], candidate_keys: list[str]) -> list[Any]:
    iocs: list[Any] = []
    for key in candidate_keys:
        value = raw.get(key)
        if value in (None, "", []):
            continue
        if isinstance(value, list):
            iocs.extend(value[:10])
        else:
            iocs.append(value)
    return iocs[:20]


def _policy_row(row: BlueThreatLocalizerPolicy | None, *, site: Site) -> dict[str, Any]:
    if row is None:
        return {
            "policy_id": "",
            "site_id": str(site.id),
            "focus_region": "thailand",
            "sector": "general",
            "subscribed_categories": ["identity", "phishing", "ransomware", "web"],
            "recurring_digest_enabled": True,
            "schedule_interval_minutes": 240,
            "min_feed_priority": "medium",
            "enabled": True,
            "owner": "security",
            "created_at": "",
            "updated_at": "",
        }
    return {
        "policy_id": str(row.id),
        "site_id": str(row.site_id),
        "focus_region": row.focus_region,
        "sector": row.sector,
        "subscribed_categories": [str(item) for item in _safe_json_list(row.subscribed_categories_json)],
        "recurring_digest_enabled": bool(row.recurring_digest_enabled),
        "schedule_interval_minutes": int(row.schedule_interval_minutes or 240),
        "min_feed_priority": row.min_feed_priority,
        "enabled": bool(row.enabled),
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _feed_row(row: BlueThreatFeedItem) -> dict[str, Any]:
    return {
        "feed_item_id": str(row.id),
        "source_name": row.source_name,
        "source_item_id": row.source_item_id,
        "title": row.title,
        "summary_th": row.summary_th,
        "category": row.category,
        "severity": row.severity,
        "focus_region": row.focus_region,
        "sectors": [str(item) for item in _safe_json_list(row.sectors_json)],
        "iocs": _safe_json_list(row.iocs_json),
        "references": _safe_json_list(row.references_json),
        "payload": _safe_json_dict(row.payload_json),
        "published_at": _safe_iso(row.published_at),
        "is_active": bool(row.is_active),
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _run_row(row: BlueThreatLocalizerRun) -> dict[str, Any]:
    return {
        "run_id": str(row.id),
        "site_id": str(row.site_id),
        "focus_region": row.focus_region,
        "sector": row.sector,
        "dry_run": bool(row.dry_run),
        "priority_score": row.priority_score,
        "risk_tier": row.risk_tier,
        "headline": row.headline,
        "summary_th": row.summary_th,
        "details": _safe_json_dict(row.details_json),
        "created_at": _safe_iso(row.created_at),
    }


def list_threat_sector_profiles() -> dict[str, Any]:
    rows = []
    for sector, profile in SECTOR_PROFILES.items():
        rows.append(
            {
                "sector": sector,
                "label_th": profile["label_th"],
                "priority_categories": list(profile["priority_categories"]),
                "keywords": list(profile["keywords"]),
                "risk_bias": float(profile["risk_bias"]),
            }
        )
    return {"status": "ok", "count": len(rows), "rows": rows}


def list_threat_feed_adapter_templates(*, source: str = "") -> dict[str, Any]:
    rows = []
    selected = _normalize_adapter_source(source) if source else ""
    for adapter_source, template in ADAPTER_TEMPLATES.items():
        if selected and adapter_source != selected:
            continue
        rows.append(
            {
                "source": adapter_source,
                "display_name": template["display_name"],
                "description": template["description"],
                "field_mapping": list(template["field_mapping"]),
                "categories_supported": list(template["categories_supported"]),
                "sample_payload": template["sample_payload"],
            }
        )
    return {"status": "ok", "count": len(rows), "rows": rows}


def _normalize_adapter_items(source: str, payload: Any) -> list[dict[str, Any]]:
    source_value = _normalize_adapter_source(source)
    if source_value == "splunk":
        rows = payload.get("results", []) if isinstance(payload, dict) else []
        items = []
        for index, row in enumerate(rows[:500]):
            if not isinstance(row, dict):
                continue
            title = str(row.get("search_name", row.get("title", "Splunk notable")))[:255]
            summary = str(row.get("description", row.get("message", title)))
            items.append(
                {
                    "source_item_id": row.get("sid") or row.get("id") or f"splunk-{index+1}",
                    "title": title,
                    "summary_th": summary,
                    "severity": _normalize_severity(str(row.get("severity", row.get("urgency", "medium")))),
                    "category": _infer_category_from_text(str(row.get("category", "")), title, summary),
                    "focus_region": _normalize_region(str(row.get("region", "thailand"))),
                    "sectors": _infer_sectors(row.get("tags", []), row.get("sector", "")),
                    "iocs": _extract_iocs(row, ["src_ip", "dest_ip", "ioc", "artifact"]),
                    "references": row.get("references", []),
                    "published_at": row.get("published_at", ""),
                    "payload": row,
                }
            )
        return items
    if source_value == "crowdstrike":
        rows = payload.get("resources", payload.get("alerts", [])) if isinstance(payload, dict) else []
        items = []
        for index, row in enumerate(rows[:500]):
            if not isinstance(row, dict):
                continue
            title = str(row.get("behavior", row.get("name", "CrowdStrike alert")))[:255]
            summary = str(row.get("description", row.get("summary", title)))
            items.append(
                {
                    "source_item_id": row.get("id") or row.get("alert_id") or f"crowdstrike-{index+1}",
                    "title": title,
                    "summary_th": summary,
                    "severity": _normalize_severity(str(row.get("severity_name", row.get("severity", "medium")))),
                    "category": _infer_category_from_text(str(row.get("tactic", "")), str(row.get("technique", "")), title, summary),
                    "focus_region": _normalize_region(str(row.get("region", "thailand"))),
                    "sectors": _infer_sectors(row.get("host_groups", []), row.get("sector", "")),
                    "iocs": _extract_iocs(row, ["device_id", "ioc", "indicator", "sha256", "md5"]),
                    "references": row.get("references", []),
                    "published_at": row.get("published_at", ""),
                    "payload": row,
                }
            )
        return items
    if source_value == "cloudflare":
        rows = payload.get("result", payload.get("items", [])) if isinstance(payload, dict) else []
        items = []
        for index, row in enumerate(rows[:500]):
            if not isinstance(row, dict):
                continue
            title = f"{row.get('service', 'waf')}:{row.get('action', 'observe')}"[:255]
            summary = str(row.get("message", row.get("description", title)))
            items.append(
                {
                    "source_item_id": row.get("ray_id") or row.get("id") or f"cloudflare-{index+1}",
                    "title": title,
                    "summary_th": summary,
                    "severity": _normalize_severity(str(row.get("severity", row.get("score", "medium")))),
                    "category": _infer_category_from_text(str(row.get("service", "")), title, summary),
                    "focus_region": _normalize_region(str(row.get("region", "thailand"))),
                    "sectors": _infer_sectors(row.get("tags", []), row.get("sector", "")),
                    "iocs": _extract_iocs(row, ["clientIP", "ip", "host"]),
                    "references": row.get("references", []),
                    "published_at": row.get("published_at", ""),
                    "payload": row,
                }
            )
        return items

    if isinstance(payload, dict):
        rows = payload.get("items", payload.get("rows", payload.get("results", [])))
    else:
        rows = payload
    if not isinstance(rows, list):
        rows = [rows]
    items = []
    for index, row in enumerate(rows[:500]):
        if not isinstance(row, dict):
            continue
        title = str(row.get("title", row.get("headline", row.get("name", "Generic threat item"))))[:255]
        summary = str(row.get("summary_th", row.get("summary", row.get("description", title))))
        items.append(
            {
                "source_item_id": row.get("id") or row.get("source_item_id") or f"generic-{index+1}",
                "title": title,
                "summary_th": summary,
                "severity": _normalize_severity(str(row.get("severity", "medium"))),
                "category": _normalize_category(str(row.get("category", _infer_category_from_text(title, summary)))),
                "focus_region": _normalize_region(str(row.get("focus_region", row.get("region", "thailand")))),
                "sectors": _infer_sectors(row.get("sectors", []), row.get("sector", "")),
                "iocs": row.get("iocs", []),
                "references": row.get("references", []),
                "published_at": row.get("published_at", ""),
                "payload": row,
            }
        )
    return items


def import_threat_feed_adapter_payload(
    db: Session,
    *,
    source: str,
    payload: Any,
    actor: str = "blue_threat_feed_adapter_ai",
) -> dict[str, Any]:
    source_value = _normalize_adapter_source(source)
    items = _normalize_adapter_items(source_value, payload)
    imported = import_threat_feed_items(
        db,
        items=items,
        source_name=source_value,
        actor=actor,
    )
    imported["adapter_source"] = source_value
    imported["normalized_count"] = len(items)
    return imported


def import_threat_feed_items(
    db: Session,
    *,
    items: list[dict[str, Any]],
    source_name: str = "manual",
    actor: str = "blue_threat_feed_ai",
) -> dict[str, Any]:
    normalized_source = str(source_name or "manual").strip().lower()[:64] or "manual"
    imported = 0
    updated = 0
    now = _now()
    changed: list[BlueThreatFeedItem] = []
    for index, raw in enumerate(items[:1000]):
        item_id = str(raw.get("source_item_id") or raw.get("external_id") or raw.get("id") or f"{normalized_source}-{index+1}").strip()[:128]
        row = db.scalar(
            select(BlueThreatFeedItem)
            .where(BlueThreatFeedItem.source_name == normalized_source)
            .where(BlueThreatFeedItem.source_item_id == item_id)
        )
        is_new = row is None
        if row is None:
            row = BlueThreatFeedItem(
                source_name=normalized_source,
                source_item_id=item_id,
                created_at=now,
            )
            db.add(row)
        row.title = str(raw.get("title", raw.get("headline", "")) or "").strip()[:255]
        row.summary_th = str(raw.get("summary_th", raw.get("summary", raw.get("description", ""))) or "").strip()
        row.category = _normalize_category(str(raw.get("category", "identity")))
        row.severity = _normalize_severity(str(raw.get("severity", "medium")))
        row.focus_region = _normalize_region(str(raw.get("focus_region", raw.get("region", "thailand"))))
        sectors = raw.get("sectors", [raw.get("sector", "general")])
        if not isinstance(sectors, list):
            sectors = [sectors]
        normalized_sectors = sorted({_normalize_sector(str(item or "general")) for item in sectors})
        row.sectors_json = _as_json(normalized_sectors or ["general"])
        iocs = raw.get("iocs", [])
        row.iocs_json = _as_json(iocs if isinstance(iocs, list) else [iocs])
        references = raw.get("references", raw.get("links", []))
        row.references_json = _as_json(references if isinstance(references, list) else [references])
        payload = raw.get("payload", raw)
        row.payload_json = _as_json(payload if isinstance(payload, dict) else {"raw": payload, "actor": actor})
        published_at_raw = str(raw.get("published_at", "") or "").strip()
        row.published_at = None
        if published_at_raw:
            try:
                row.published_at = datetime.fromisoformat(published_at_raw.replace("Z", "+00:00"))
            except Exception:
                row.published_at = now
        row.is_active = bool(raw.get("is_active", True))
        row.updated_at = now
        if is_new:
            imported += 1
        else:
            updated += 1
        changed.append(row)
    db.commit()
    return {
        "status": "ok",
        "source_name": normalized_source,
        "actor": actor,
        "received_count": len(items),
        "imported_count": imported,
        "updated_count": updated,
        "rows": [_feed_row(row) for row in changed[:30]],
    }


def list_threat_feed_items(
    db: Session,
    *,
    focus_region: str = "",
    sector: str = "",
    category: str = "",
    active_only: bool = True,
    limit: int = 100,
) -> dict[str, Any]:
    stmt = select(BlueThreatFeedItem).order_by(desc(BlueThreatFeedItem.published_at), desc(BlueThreatFeedItem.updated_at)).limit(max(1, min(limit, 300)))
    if active_only:
        stmt = stmt.where(BlueThreatFeedItem.is_active.is_(True))
    if focus_region:
        stmt = stmt.where(BlueThreatFeedItem.focus_region == _normalize_region(focus_region))
    if category:
        stmt = stmt.where(BlueThreatFeedItem.category == _normalize_category(category))
    rows = db.scalars(stmt).all()
    sector_value = _normalize_sector(sector) if sector else ""
    filtered = []
    for row in rows:
        sectors = [str(item) for item in _safe_json_list(row.sectors_json)]
        if sector_value and sector_value not in sectors and "general" not in sectors:
            continue
        filtered.append(row)
    return {"status": "ok", "count": len(filtered), "rows": [_feed_row(row) for row in filtered]}


def get_threat_localizer_policy(db: Session, *, site_id: UUID) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    row = db.scalar(select(BlueThreatLocalizerPolicy).where(BlueThreatLocalizerPolicy.site_id == site.id))
    return {"status": "ok", "policy": _policy_row(row, site=site)}


def upsert_threat_localizer_policy(
    db: Session,
    *,
    site_id: UUID,
    focus_region: str,
    sector: str,
    subscribed_categories: list[str],
    recurring_digest_enabled: bool,
    schedule_interval_minutes: int,
    min_feed_priority: str,
    enabled: bool,
    owner: str,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    row = db.scalar(select(BlueThreatLocalizerPolicy).where(BlueThreatLocalizerPolicy.site_id == site.id))
    now = _now()
    created = row is None
    if row is None:
        row = BlueThreatLocalizerPolicy(site_id=site.id, created_at=now)
        db.add(row)
    row.focus_region = _normalize_region(focus_region)
    row.sector = _normalize_sector(sector)
    normalized_categories = []
    for item in subscribed_categories or []:
        value = _normalize_category(item)
        if value not in normalized_categories:
            normalized_categories.append(value)
    row.subscribed_categories_json = _as_json(normalized_categories or ["identity", "phishing", "ransomware", "web"])
    row.recurring_digest_enabled = bool(recurring_digest_enabled)
    row.schedule_interval_minutes = max(15, min(int(schedule_interval_minutes), 10080))
    row.min_feed_priority = _normalize_severity(min_feed_priority)
    row.enabled = bool(enabled)
    row.owner = owner.strip()[:64] or "security"
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return {"status": "created" if created else "updated", "policy": _policy_row(row, site=site)}


def _match_feed_items(
    db: Session,
    *,
    focus_region: str,
    sector: str,
    categories: list[str],
    min_feed_priority: str,
) -> list[BlueThreatFeedItem]:
    rows = db.scalars(
        select(BlueThreatFeedItem)
        .where(BlueThreatFeedItem.is_active.is_(True))
        .order_by(desc(BlueThreatFeedItem.published_at), desc(BlueThreatFeedItem.updated_at))
        .limit(200)
    ).all()
    threshold = SEVERITY_RANK[_normalize_severity(min_feed_priority)]
    out = []
    for row in rows:
        if row.focus_region not in {focus_region, "sea", "asean", "apac", "global"}:
            continue
        if row.category not in categories:
            continue
        if SEVERITY_RANK[_normalize_severity(row.severity)] < threshold:
            continue
        sectors = [str(item) for item in _safe_json_list(row.sectors_json)]
        if sector not in sectors and "general" not in sectors:
            continue
        out.append(row)
    return out[:20]


def _event_keyword_counts(events: list[BlueEventLog], *, profile: dict[str, Any]) -> dict[str, int]:
    counts = {category: 0 for category in ALLOWED_CATEGORIES}
    profile_keywords = {str(item).lower() for item in profile.get("keywords", [])}
    for event in events:
        payload = str(event.payload_json or "").lower()
        severity = str(event.ai_severity or "").lower()
        if "credential" in payload or "login" in payload or "auth" in payload:
            counts["identity"] += 1
        if "phish" in payload or "mail" in payload or "smtp" in payload:
            counts["phishing"] += 1
        if "ransom" in payload or "encrypt" in payload:
            counts["ransomware"] += 1
        if "waf" in payload or "http" in payload or "sql" in payload:
            counts["web"] += 1
        if "malware" in payload or "trojan" in payload:
            counts["malware"] += 1
        if "insider" in payload or "privilege" in payload:
            counts["insider"] += 1
        if severity in {"high", "critical"} and any(keyword in payload for keyword in profile_keywords):
            for category in profile.get("priority_categories", []):
                counts[_normalize_category(category)] += 1
    return counts


def _rule_matches_category(rule: BlueDetectionRule, category: str) -> bool:
    haystack = f"{rule.rule_name} {rule.rule_logic_json}".lower()
    return any(keyword in haystack for keyword in CATEGORY_KEYWORDS.get(category, []))


def _connector_matches_category(connector_source: str, category: str) -> bool:
    supported = CONNECTOR_CATEGORY_COVERAGE.get(str(connector_source or "").lower(), CONNECTOR_CATEGORY_COVERAGE["generic"])
    return category in supported


def _build_detection_gap_summary(
    db: Session,
    *,
    site_id: UUID,
    categories: list[str],
    feed_items: list[BlueThreatFeedItem],
    top_category: str,
) -> dict[str, Any]:
    rules = db.scalars(
        select(BlueDetectionRule)
        .where(BlueDetectionRule.site_id == site_id)
        .order_by(desc(BlueDetectionRule.updated_at))
        .limit(100)
    ).all()
    endpoints = db.scalars(
        select(SiteEmbeddedWorkflowEndpoint)
        .where(SiteEmbeddedWorkflowEndpoint.site_id == site_id)
        .where(SiteEmbeddedWorkflowEndpoint.enabled.is_(True))
        .order_by(desc(SiteEmbeddedWorkflowEndpoint.updated_at))
        .limit(100)
    ).all()
    connector_sources = sorted({str(endpoint.connector_source or "generic").lower() for endpoint in endpoints})

    priority_categories = list(dict.fromkeys([top_category] + [feed.category for feed in feed_items[:6]] + list(categories)))[:6]
    coverage_rows = []
    missing_categories: list[str] = []
    for category in priority_categories:
        matched_rules = [rule.rule_name for rule in rules if _rule_matches_category(rule, category)]
        matched_connectors = [source for source in connector_sources if _connector_matches_category(source, category)]
        status = "covered" if matched_rules or matched_connectors else "gap"
        if status == "gap":
            missing_categories.append(category)
        coverage_rows.append(
            {
                "category": category,
                "status": status,
                "matched_rule_count": len(matched_rules),
                "matched_rules": matched_rules[:5],
                "connector_sources": matched_connectors,
            }
        )
    return {
        "rule_count": len(rules),
        "connector_source_count": len(connector_sources),
        "connector_sources": connector_sources,
        "coverage_rows": coverage_rows,
        "missing_categories": missing_categories,
        "correlation_status": "gap_detected" if missing_categories else "covered_baseline",
    }


def run_threat_intelligence_localizer(
    db: Session,
    *,
    site_id: UUID,
    focus_region: str = "thailand",
    sector: str = "general",
    dry_run: bool = True,
    actor: str = "blue_threat_localizer_ai",
    subscribed_categories: list[str] | None = None,
    digest_mode: bool = False,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}

    policy_row = db.scalar(select(BlueThreatLocalizerPolicy).where(BlueThreatLocalizerPolicy.site_id == site.id))
    policy = _policy_row(policy_row, site=site)
    focus_region_value = _normalize_region(focus_region or str(policy.get("focus_region", "thailand")))
    sector_value = _normalize_sector(sector or str(policy.get("sector", "general")))
    category_list = subscribed_categories or list(policy.get("subscribed_categories", [])) or ["identity", "phishing", "ransomware", "web"]
    categories = [_normalize_category(item) for item in category_list]
    min_feed_priority = _normalize_severity(str(policy.get("min_feed_priority", "medium")))
    profile = _profile_for_sector(sector_value)

    recent_blue_events = db.scalars(
        select(BlueEventLog)
        .where(BlueEventLog.site_id == site.id)
        .order_by(desc(BlueEventLog.created_at))
        .limit(120)
    ).all()
    latest_exploit = db.scalar(
        select(RedExploitPathRun)
        .where(RedExploitPathRun.site_id == site.id)
        .order_by(desc(RedExploitPathRun.created_at))
        .limit(1)
    )
    relevant_packs = db.scalars(
        select(ThreatContentPack)
        .where(ThreatContentPack.is_active.is_(True))
        .where(ThreatContentPack.category.in_(categories))
        .order_by(desc(ThreatContentPack.updated_at))
        .limit(8)
    ).all()
    feed_items = _match_feed_items(
        db,
        focus_region=focus_region_value,
        sector=sector_value,
        categories=categories,
        min_feed_priority=min_feed_priority,
    )

    keyword_counts = _event_keyword_counts(recent_blue_events, profile=profile)
    suspicious_events = sum(1 for event in recent_blue_events if str(event.ai_severity or "").lower() in {"medium", "high", "critical"})
    exploit_risk = int(getattr(latest_exploit, "risk_score", 0) or 0) if latest_exploit else 0

    profile_bias = float(profile.get("risk_bias", 1.0))
    feed_score = sum(SEVERITY_RANK[_normalize_severity(row.severity)] * 6 for row in feed_items)
    sector_score = int(sum(keyword_counts.get(_normalize_category(item), 0) for item in profile.get("priority_categories", [])) * 4 * profile_bias)
    pack_score = len(relevant_packs) * 4
    priority_score = min(98, int(14 + (suspicious_events * 3) + (exploit_risk * 0.45) + feed_score + sector_score + pack_score))
    risk_tier = _tier_from_score(priority_score)

    category_candidates = {category: keyword_counts.get(category, 0) for category in categories}
    for feed in feed_items:
        category_candidates[feed.category] = category_candidates.get(feed.category, 0) + SEVERITY_RANK[_normalize_severity(feed.severity)] * 2
    top_category = sorted(category_candidates.items(), key=lambda item: item[1], reverse=True)[0][0] if category_candidates else "identity"
    top_packs = [pack for pack in relevant_packs if pack.category == top_category][:3] or relevant_packs[:3]
    detection_gap = _build_detection_gap_summary(
        db,
        site_id=site.id,
        categories=categories,
        feed_items=feed_items,
        top_category=top_category,
    )
    site_impact_score = min(
        100,
        int((priority_score * 0.55) + (exploit_risk * 0.25) + (suspicious_events * 3) + (len(feed_items) * 4)),
    )

    headlines = []
    for feed in feed_items[:3]:
        headlines.append(
            {
                "headline_th": feed.summary_th or feed.title,
                "category": feed.category,
                "severity": feed.severity,
                "source_name": feed.source_name,
                "site_relevance": "high" if site_impact_score >= 65 else "medium",
            }
        )
    if not headlines:
        headlines = [
            {
                "headline_th": f"แนวโน้มภัย {top_category} ใน{focus_region_value}มีความเกี่ยวข้องกับไซต์ {site.display_name}",
                "category": top_category,
                "severity": risk_tier,
                "source_name": "localizer",
                "site_relevance": "high" if suspicious_events > 0 or exploit_risk >= 50 else "medium",
            }
        ]

    actions = [
        "เพิ่ม rule/alert สำหรับ credential abuse และ web attack ที่สัมพันธ์กับ telemetry ล่าสุด",
        "เทียบ feed ใหม่กับ detection rules และ embedded connectors ของไซต์ทันที",
        "แจ้งทีมปฏิบัติการให้เฝ้าระวังโดเมนเลียนแบบและ phishing ภาษาไทย",
    ]
    if detection_gap["missing_categories"]:
        actions.insert(
            0,
            f"พบ detection gap ในหมวด {', '.join(detection_gap['missing_categories'][:3])} ควรเพิ่ม rule หรือ connector coverage ทันที",
        )
    summary_th = (
        f"AI Localizer สรุปภัยคุกคามใน{focus_region_value}สำหรับ sector={sector_value} ว่าควรโฟกัสหมวด {top_category} "
        f"โดย site impact={site_impact_score} priority={priority_score} ระดับ {risk_tier} จาก feed ภายนอก {len(feed_items)} รายการ "
        f"รวมกับ telemetry ล่าสุดและ Red validation โดย correlation={detection_gap['correlation_status']}."
    )
    details = {
        "focus_region": focus_region_value,
        "sector": sector_value,
        "subscribed_categories": categories,
        "sector_profile": {
            "sector": sector_value,
            "label_th": profile["label_th"],
            "priority_categories": profile["priority_categories"],
            "risk_bias": profile["risk_bias"],
        },
        "headline_rows": headlines,
        "priority_actions_th": actions,
        "keyword_counts": keyword_counts,
        "relevant_pack_codes": [pack.pack_code for pack in top_packs],
        "relevant_pack_titles": [pack.title for pack in top_packs],
        "feed_rows": [_feed_row(feed) for feed in feed_items[:6]],
        "feed_match_count": len(feed_items),
        "exploit_risk": exploit_risk,
        "suspicious_event_count": suspicious_events,
        "site_impact_score": site_impact_score,
        "detection_gap": detection_gap,
        "digest_mode": bool(digest_mode),
        "dry_run": bool(dry_run),
        "actor": actor,
    }

    headline = f"Threat focus: {top_category} / {focus_region_value}"
    row = BlueThreatLocalizerRun(
        site_id=site.id,
        focus_region=focus_region_value,
        sector=sector_value,
        dry_run=bool(dry_run),
        priority_score=priority_score,
        risk_tier=risk_tier,
        headline=headline,
        summary_th=summary_th,
        details_json=_as_json(details),
        created_at=_now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "completed", "site_id": str(site.id), "site_code": site.site_code, "run": _run_row(row)}


def list_threat_localizer_runs(db: Session, *, site_id: UUID, limit: int = 20) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    rows = db.scalars(
        select(BlueThreatLocalizerRun)
        .where(BlueThreatLocalizerRun.site_id == site.id)
        .order_by(desc(BlueThreatLocalizerRun.created_at))
        .limit(max(1, min(limit, 200)))
    ).all()
    return {"status": "ok", "count": len(rows), "rows": [_run_row(row) for row in rows]}


def run_threat_localizer_scheduler(
    db: Session,
    *,
    limit: int = 100,
    dry_run_override: bool | None = None,
    actor: str = "blue_threat_localizer_scheduler_ai",
) -> dict[str, Any]:
    policies = db.scalars(
        select(BlueThreatLocalizerPolicy)
        .where(BlueThreatLocalizerPolicy.enabled.is_(True))
        .where(BlueThreatLocalizerPolicy.recurring_digest_enabled.is_(True))
        .order_by(BlueThreatLocalizerPolicy.updated_at.asc())
        .limit(max(1, min(limit, 500)))
    ).all()
    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for policy in policies:
        last_run = db.scalar(
            select(BlueThreatLocalizerRun)
            .where(BlueThreatLocalizerRun.site_id == policy.site_id)
            .order_by(desc(BlueThreatLocalizerRun.created_at))
            .limit(1)
        )
        due = True
        if last_run and last_run.created_at:
            due_at = last_run.created_at
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
            due = due_at <= (_now() - timedelta(minutes=max(15, int(policy.schedule_interval_minutes or 240))))
        if not due:
            skipped.append({"site_id": str(policy.site_id), "reason": "not_due"})
            continue
        result = run_threat_intelligence_localizer(
            db,
            site_id=policy.site_id,
            focus_region=policy.focus_region,
            sector=policy.sector,
            dry_run=True if dry_run_override is None else bool(dry_run_override),
            actor=actor,
            subscribed_categories=[str(item) for item in _safe_json_list(policy.subscribed_categories_json)],
            digest_mode=True,
        )
        promotion_summary: dict[str, Any] | None = None
        try:
            from app.services.blue_threat_localizer_promotion import (
                get_blue_threat_localizer_routing_policy,
                promote_blue_threat_localizer_gap,
            )

            routing_policy = get_blue_threat_localizer_routing_policy(db, site_id=policy.site_id).get("policy", {})
            if bool(routing_policy.get("auto_promote_on_gap", True)):
                run_id_value = str((result.get("run", {}) or {}).get("run_id", "") or "").strip()
                promotion_summary = promote_blue_threat_localizer_gap(
                    db,
                    site_id=policy.site_id,
                    localizer_run_id=UUID(run_id_value) if run_id_value else None,
                    actor=f"{actor}:promotion",
                )
        except Exception as exc:
            promotion_summary = {"status": "promotion_error", "reason": str(exc)}
        executed.append(
            {
                "site_id": str(policy.site_id),
                "status": result.get("status", "unknown"),
                "run_id": result.get("run", {}).get("run_id", ""),
                "promotion_status": (promotion_summary or {}).get("status", ""),
            }
        )
    return {
        "status": "ok",
        "scheduled_policy_count": len(policies),
        "executed_count": len(executed),
        "skipped_count": len(skipped),
        "executed": executed,
        "skipped": skipped,
        "generated_at": _now().isoformat(),
    }


def process_blue_threat_localizer_schedules(limit: int = 100) -> dict[str, Any]:
    with SessionLocal() as db:
        return run_threat_localizer_scheduler(db, limit=limit, dry_run_override=None)
