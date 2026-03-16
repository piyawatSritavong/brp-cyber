from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    AiCoworkerPlugin,
    AiCoworkerPluginRun,
    RedPluginIntelligenceItem,
    RedPluginIntelligenceSyncRun,
    RedPluginIntelligenceSyncSource,
    RedPluginSafetyPolicy,
    Site,
    ThreatContentPack,
)
from app.db.session import SessionLocal


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


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    return slug[:80] or "intel-item"


def _parse_published_at(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _normalize_source_type(value: str) -> str:
    normalized = str(value or "article").strip().lower()
    if normalized not in {"cve", "news", "article"}:
        return "article"
    return normalized


def _normalize_target_type(value: str) -> str:
    normalized = str(value or "web").strip().lower()
    return normalized[:32] or "web"


def _normalize_parser_kind(value: str) -> str:
    normalized = str(value or "json_feed").strip().lower()
    if normalized not in {"json_feed", "jsonl"}:
        return "json_feed"
    return normalized


def _normalize_string_list(values: list[Any]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        item = str(raw or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        normalized.append(item[:255])
    return normalized


def _sync_source_row(row: RedPluginIntelligenceSyncSource) -> dict[str, Any]:
    return {
        "sync_source_id": str(row.id),
        "site_id": str(row.site_id),
        "source_name": row.source_name,
        "source_type": row.source_type,
        "source_url": row.source_url,
        "target_type": row.target_type,
        "parser_kind": row.parser_kind,
        "request_headers": _safe_json_dict(row.request_headers_json),
        "sync_interval_minutes": row.sync_interval_minutes,
        "enabled": bool(row.enabled),
        "last_synced_at": _safe_iso(row.last_synced_at),
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _sync_run_row(row: RedPluginIntelligenceSyncRun) -> dict[str, Any]:
    return {
        "sync_run_id": str(row.id),
        "site_id": str(row.site_id),
        "sync_source_id": str(row.sync_source_id) if row.sync_source_id else "",
        "status": row.status,
        "dry_run": bool(row.dry_run),
        "fetched_count": int(row.fetched_count or 0),
        "imported_count": int(row.imported_count or 0),
        "updated_count": int(row.updated_count or 0),
        "details": _safe_json_dict(row.details_json),
        "actor": row.actor,
        "created_at": _safe_iso(row.created_at),
    }


def _default_red_plugin_safety_policy(site_id: UUID, *, target_type: str) -> dict[str, Any]:
    return {
        "policy_id": "",
        "site_id": str(site_id),
        "target_type": _normalize_target_type(target_type),
        "max_http_requests_per_run": 5,
        "max_script_lines": 80,
        "allow_network_calls": True,
        "require_comment_header": True,
        "require_disclaimer": True,
        "allowed_modules": ["requests"],
        "blocked_modules": ["subprocess", "socket", "paramiko"],
        "enabled": True,
        "owner": "security",
        "created_at": "",
        "updated_at": "",
    }


def _intel_row(row: RedPluginIntelligenceItem) -> dict[str, Any]:
    return {
        "intel_id": str(row.id),
        "site_id": str(row.site_id),
        "source_type": row.source_type,
        "source_name": row.source_name,
        "source_item_id": row.source_item_id,
        "title": row.title,
        "summary_th": row.summary_th,
        "cve_id": row.cve_id,
        "target_surface": row.target_surface,
        "target_type": row.target_type,
        "tags": _safe_json_list(row.tags_json),
        "references": _safe_json_list(row.references_json),
        "payload": _safe_json_dict(row.payload_json),
        "published_at": _safe_iso(row.published_at),
        "is_active": bool(row.is_active),
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _safety_policy_row(row: RedPluginSafetyPolicy | None, *, site_id: UUID, target_type: str) -> dict[str, Any]:
    if row is None:
        return _default_red_plugin_safety_policy(site_id, target_type=target_type)
    return {
        "policy_id": str(row.id),
        "site_id": str(row.site_id),
        "target_type": row.target_type,
        "max_http_requests_per_run": row.max_http_requests_per_run,
        "max_script_lines": row.max_script_lines,
        "allow_network_calls": bool(row.allow_network_calls),
        "require_comment_header": bool(row.require_comment_header),
        "require_disclaimer": bool(row.require_disclaimer),
        "allowed_modules": _safe_json_list(row.allowed_modules_json),
        "blocked_modules": _safe_json_list(row.blocked_modules_json),
        "enabled": bool(row.enabled),
        "owner": row.owner,
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def import_red_plugin_intelligence(
    db: Session,
    *,
    site_id: UUID,
    items: list[dict[str, Any]],
    actor: str = "red_plugin_intel_ai",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id), "count": 0, "rows": []}

    created = 0
    updated = 0
    now = datetime.now(timezone.utc)
    touched: list[RedPluginIntelligenceItem] = []
    for item in items:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        source_type = _normalize_source_type(str(item.get("source_type", "article")))
        source_name = str(item.get("source_name") or "manual").strip()[:64] or "manual"
        source_item_id = str(item.get("source_item_id") or item.get("cve_id") or _slugify(title)).strip()[:128]
        row = db.scalar(
            select(RedPluginIntelligenceItem).where(
                RedPluginIntelligenceItem.site_id == site.id,
                RedPluginIntelligenceItem.source_name == source_name,
                RedPluginIntelligenceItem.source_item_id == source_item_id,
            )
        )
        published_at = _parse_published_at(item.get("published_at"))
        tags = _normalize_string_list(list(item.get("tags") or []))
        references = _normalize_string_list(list(item.get("references") or []))
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        target_type = _normalize_target_type(str(item.get("target_type") or "web"))
        target_surface = str(item.get("target_surface") or "").strip()[:512]
        if row:
            row.source_type = source_type
            row.title = title[:255]
            row.summary_th = str(item.get("summary_th") or item.get("summary") or "").strip()
            row.cve_id = str(item.get("cve_id") or "").strip()[:64]
            row.target_surface = target_surface
            row.target_type = target_type
            row.tags_json = _as_json(tags)
            row.references_json = _as_json(references)
            payload_with_actor = {**payload, "actor": actor.strip()[:128] or "red_plugin_intel_ai"}
            row.payload_json = _as_json(payload_with_actor)
            row.published_at = published_at
            row.is_active = bool(item.get("is_active", True))
            row.updated_at = now
            updated += 1
            touched.append(row)
            continue

        created_row = RedPluginIntelligenceItem(
            site_id=site.id,
            source_type=source_type,
            source_name=source_name,
            source_item_id=source_item_id,
            title=title[:255],
            summary_th=str(item.get("summary_th") or item.get("summary") or "").strip(),
            cve_id=str(item.get("cve_id") or "").strip()[:64],
            target_surface=target_surface,
            target_type=target_type,
            tags_json=_as_json(tags),
            references_json=_as_json(references),
            payload_json=_as_json({**payload, "actor": actor.strip()[:128] or "red_plugin_intel_ai"}),
            published_at=published_at,
            is_active=bool(item.get("is_active", True)),
            created_at=now,
            updated_at=now,
        )
        db.add(created_row)
        touched.append(created_row)
        created += 1
    if created or updated:
        db.commit()
        for row in touched:
            db.refresh(row)
    return {
        "status": "ok",
        "site_id": str(site.id),
        "created_count": created,
        "updated_count": updated,
        "count": len(touched),
        "rows": [_intel_row(row) for row in touched],
    }


def list_red_plugin_intelligence(
    db: Session,
    *,
    site_id: UUID,
    source_type: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id), "count": 0, "rows": []}
    stmt = (
        select(RedPluginIntelligenceItem)
        .where(RedPluginIntelligenceItem.site_id == site.id)
        .order_by(desc(RedPluginIntelligenceItem.published_at), desc(RedPluginIntelligenceItem.updated_at))
        .limit(max(1, min(int(limit), 200)))
    )
    normalized = _normalize_source_type(source_type) if source_type else ""
    if normalized:
        stmt = stmt.where(RedPluginIntelligenceItem.source_type == normalized)
    rows = db.scalars(stmt).all()
    return {"status": "ok", "site_id": str(site.id), "count": len(rows), "rows": [_intel_row(row) for row in rows]}


def get_latest_red_plugin_intelligence(
    db: Session,
    *,
    site_id: UUID,
    target_surface: str = "",
    target_type: str = "",
) -> dict[str, Any] | None:
    rows = db.scalars(
        select(RedPluginIntelligenceItem)
        .where(
            RedPluginIntelligenceItem.site_id == site_id,
            RedPluginIntelligenceItem.is_active.is_(True),
        )
        .order_by(desc(RedPluginIntelligenceItem.published_at), desc(RedPluginIntelligenceItem.updated_at))
        .limit(20)
    ).all()
    normalized_target_type = _normalize_target_type(target_type or "web")
    normalized_target_surface = str(target_surface or "").strip()
    for row in rows:
        if row.target_type == normalized_target_type and normalized_target_surface and row.target_surface == normalized_target_surface:
            return _intel_row(row)
    for row in rows:
        if row.target_type == normalized_target_type:
            return _intel_row(row)
    return _intel_row(rows[0]) if rows else None


def upsert_red_plugin_safety_policy(
    db: Session,
    *,
    site_id: UUID,
    target_type: str,
    max_http_requests_per_run: int,
    max_script_lines: int,
    allow_network_calls: bool,
    require_comment_header: bool,
    require_disclaimer: bool,
    allowed_modules: list[str],
    blocked_modules: list[str],
    enabled: bool,
    owner: str,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    normalized_target_type = _normalize_target_type(target_type)
    row = db.scalar(
        select(RedPluginSafetyPolicy).where(
            RedPluginSafetyPolicy.site_id == site.id,
            RedPluginSafetyPolicy.target_type == normalized_target_type,
        )
    )
    now = datetime.now(timezone.utc)
    if row:
        row.max_http_requests_per_run = max(1, min(int(max_http_requests_per_run), 50))
        row.max_script_lines = max(10, min(int(max_script_lines), 500))
        row.allow_network_calls = bool(allow_network_calls)
        row.require_comment_header = bool(require_comment_header)
        row.require_disclaimer = bool(require_disclaimer)
        row.allowed_modules_json = _as_json(_normalize_string_list(allowed_modules))
        row.blocked_modules_json = _as_json(_normalize_string_list(blocked_modules))
        row.enabled = bool(enabled)
        row.owner = owner.strip()[:64] or "security"
        row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"status": "updated", "policy": _safety_policy_row(row, site_id=site.id, target_type=normalized_target_type)}

    created = RedPluginSafetyPolicy(
        site_id=site.id,
        target_type=normalized_target_type,
        max_http_requests_per_run=max(1, min(int(max_http_requests_per_run), 50)),
        max_script_lines=max(10, min(int(max_script_lines), 500)),
        allow_network_calls=bool(allow_network_calls),
        require_comment_header=bool(require_comment_header),
        require_disclaimer=bool(require_disclaimer),
        allowed_modules_json=_as_json(_normalize_string_list(allowed_modules)),
        blocked_modules_json=_as_json(_normalize_string_list(blocked_modules)),
        enabled=bool(enabled),
        owner=owner.strip()[:64] or "security",
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.commit()
    db.refresh(created)
    return {"status": "created", "policy": _safety_policy_row(created, site_id=site.id, target_type=normalized_target_type)}


def get_red_plugin_safety_policy(db: Session, *, site_id: UUID, target_type: str = "web") -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id), "policy": _default_red_plugin_safety_policy(site_id, target_type=target_type)}
    normalized_target_type = _normalize_target_type(target_type)
    row = db.scalar(
        select(RedPluginSafetyPolicy).where(
            RedPluginSafetyPolicy.site_id == site.id,
            RedPluginSafetyPolicy.target_type == normalized_target_type,
        )
    )
    return {"status": "ok", "site_id": str(site.id), "policy": _safety_policy_row(row, site_id=site.id, target_type=normalized_target_type)}


def list_red_plugin_sync_sources(db: Session, *, site_id: UUID, limit: int = 20) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id), "count": 0, "rows": []}
    rows = db.scalars(
        select(RedPluginIntelligenceSyncSource)
        .where(RedPluginIntelligenceSyncSource.site_id == site.id)
        .order_by(desc(RedPluginIntelligenceSyncSource.updated_at))
        .limit(max(1, min(int(limit), 200)))
    ).all()
    return {"status": "ok", "site_id": str(site.id), "count": len(rows), "rows": [_sync_source_row(row) for row in rows]}


def upsert_red_plugin_sync_source(
    db: Session,
    *,
    site_id: UUID,
    source_name: str,
    source_type: str,
    source_url: str,
    target_type: str,
    parser_kind: str = "json_feed",
    request_headers: dict[str, Any] | None = None,
    sync_interval_minutes: int = 1440,
    enabled: bool = True,
    owner: str = "security",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    normalized_source_name = str(source_name or "").strip()[:64] or "external_feed"
    normalized_source_url = str(source_url or "").strip()[:1024]
    row = db.scalar(
        select(RedPluginIntelligenceSyncSource).where(
            RedPluginIntelligenceSyncSource.site_id == site.id,
            RedPluginIntelligenceSyncSource.source_name == normalized_source_name,
            RedPluginIntelligenceSyncSource.source_url == normalized_source_url,
        )
    )
    now = datetime.now(timezone.utc)
    if row is None:
        row = RedPluginIntelligenceSyncSource(site_id=site.id, created_at=now)
        db.add(row)
        status = "created"
    else:
        status = "updated"
    row.source_name = normalized_source_name
    row.source_type = _normalize_source_type(source_type)
    row.source_url = normalized_source_url
    row.target_type = _normalize_target_type(target_type)
    row.parser_kind = _normalize_parser_kind(parser_kind)
    row.request_headers_json = _as_json(request_headers or {})
    row.sync_interval_minutes = max(5, min(int(sync_interval_minutes or 1440), 7 * 24 * 60))
    row.enabled = bool(enabled)
    row.owner = str(owner or "security").strip()[:64] or "security"
    row.updated_at = now
    db.commit()
    db.refresh(row)
    return {"status": status, "source": _sync_source_row(row)}


def _extract_sync_payload_items(payload: Any, *, parser_kind: str) -> list[dict[str, Any]]:
    if parser_kind == "jsonl":
        items: list[dict[str, Any]] = []
        for line in str(payload or "").splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except Exception:
                continue
            if isinstance(row, dict):
                items.append(row)
        return items
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("items", "rows", "results", "feed", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []


def _fetch_sync_source_payload(row: RedPluginIntelligenceSyncSource) -> tuple[str, Any]:
    headers = {str(key): str(value) for key, value in _safe_json_dict(row.request_headers_json).items() if str(key).strip()}
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        response = client.get(row.source_url, headers=headers)
        response.raise_for_status()
        if row.parser_kind == "jsonl":
            return "ok", response.text
        return "ok", response.json()


def _build_sync_import_items(row: RedPluginIntelligenceSyncSource, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for record in records:
        title = str(record.get("title") or record.get("headline") or record.get("name") or "").strip()
        if not title:
            continue
        source_item_id = str(record.get("source_item_id") or record.get("id") or record.get("cve_id") or _slugify(title)).strip()
        references = record.get("references") or record.get("urls") or record.get("links") or []
        if not isinstance(references, list):
            references = [references]
        tags = record.get("tags") or record.get("labels") or []
        if not isinstance(tags, list):
            tags = [tags]
        items.append(
            {
                "source_type": str(record.get("source_type") or row.source_type or "article"),
                "source_name": row.source_name,
                "source_item_id": source_item_id,
                "title": title,
                "summary_th": str(record.get("summary_th") or record.get("summary") or record.get("description") or "").strip(),
                "cve_id": str(record.get("cve_id") or record.get("cve") or "").strip(),
                "target_surface": str(record.get("target_surface") or record.get("affected_asset") or record.get("asset") or "").strip(),
                "target_type": str(record.get("target_type") or row.target_type or "web"),
                "tags": tags,
                "references": references,
                "published_at": record.get("published_at") or record.get("published") or record.get("date") or "",
                "payload": record if isinstance(record, dict) else {},
            }
        )
    return items


def sync_red_plugin_intelligence_source(
    db: Session,
    *,
    site_id: UUID,
    sync_source_id: UUID | None = None,
    dry_run: bool = True,
    actor: str = "red_plugin_sync_ai",
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    stmt = (
        select(RedPluginIntelligenceSyncSource)
        .where(RedPluginIntelligenceSyncSource.site_id == site.id)
        .order_by(desc(RedPluginIntelligenceSyncSource.updated_at))
        .limit(1)
    )
    if sync_source_id:
        stmt = select(RedPluginIntelligenceSyncSource).where(
            RedPluginIntelligenceSyncSource.id == sync_source_id,
            RedPluginIntelligenceSyncSource.site_id == site.id,
        )
    source = db.scalar(stmt)
    if source is None:
        return {"status": "sync_source_not_found", "site_id": str(site.id)}
    if not bool(source.enabled):
        return {"status": "disabled", "site_id": str(site.id), "sync_source": _sync_source_row(source)}
    fetched_items: list[dict[str, Any]] = []
    import_result: dict[str, Any] = {"status": "dry_run", "count": 0, "created_count": 0, "updated_count": 0, "rows": []}
    status = "ok"
    error_text = ""
    try:
        _result, payload = _fetch_sync_source_payload(source)
        fetched_items = _build_sync_import_items(source, _extract_sync_payload_items(payload, parser_kind=source.parser_kind))
        if not dry_run:
            import_result = import_red_plugin_intelligence(db, site_id=site.id, items=fetched_items, actor=actor)
            source.last_synced_at = datetime.now(timezone.utc)
            source.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(source)
        else:
            import_result = {
                "status": "dry_run",
                "site_id": str(site.id),
                "count": len(fetched_items),
                "created_count": len(fetched_items),
                "updated_count": 0,
                "rows": fetched_items[:10],
            }
    except Exception as exc:
        status = "fetch_failed"
        error_text = str(exc)
    run = RedPluginIntelligenceSyncRun(
        site_id=site.id,
        sync_source_id=source.id,
        status=status,
        dry_run=bool(dry_run),
        fetched_count=len(fetched_items),
        imported_count=int(import_result.get("created_count", 0) or 0),
        updated_count=int(import_result.get("updated_count", 0) or 0),
        details_json=_as_json(
            {
                "sync_source": _sync_source_row(source),
                "preview_items": fetched_items[:10],
                "error": error_text,
            }
        ),
        actor=str(actor or "red_plugin_sync_ai")[:128],
        created_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {
        "status": status,
        "site_id": str(site.id),
        "sync_source": _sync_source_row(source),
        "fetched_count": len(fetched_items),
        "import_result": import_result,
        "run": _sync_run_row(run),
    }


def list_red_plugin_sync_runs(db: Session, *, site_id: UUID, limit: int = 20) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id), "count": 0, "rows": []}
    rows = db.scalars(
        select(RedPluginIntelligenceSyncRun)
        .where(RedPluginIntelligenceSyncRun.site_id == site.id)
        .order_by(desc(RedPluginIntelligenceSyncRun.created_at))
        .limit(max(1, min(int(limit), 200)))
    ).all()
    return {"status": "ok", "site_id": str(site.id), "count": len(rows), "rows": [_sync_run_row(row) for row in rows]}


def _is_sync_due(row: RedPluginIntelligenceSyncSource) -> bool:
    if not bool(row.enabled):
        return False
    if row.last_synced_at is None:
        return True
    last_synced_at = row.last_synced_at if row.last_synced_at.tzinfo else row.last_synced_at.replace(tzinfo=timezone.utc)
    age_minutes = (datetime.now(timezone.utc) - last_synced_at).total_seconds() / 60
    return age_minutes >= max(5, int(row.sync_interval_minutes or 1440))


def run_red_plugin_sync_scheduler(
    db: Session,
    *,
    limit: int = 100,
    dry_run_override: bool | None = None,
    actor: str = "red_plugin_sync_ai",
) -> dict[str, Any]:
    rows = db.scalars(
        select(RedPluginIntelligenceSyncSource)
        .where(RedPluginIntelligenceSyncSource.enabled.is_(True))
        .order_by(desc(RedPluginIntelligenceSyncSource.updated_at))
        .limit(max(1, min(int(limit), 500)))
    ).all()
    executed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for row in rows:
        if not _is_sync_due(row):
            skipped.append({"site_id": str(row.site_id), "sync_source_id": str(row.id), "reason": "schedule_not_due"})
            continue
        result = sync_red_plugin_intelligence_source(
            db,
            site_id=row.site_id,
            sync_source_id=row.id,
            dry_run=True if dry_run_override is None else bool(dry_run_override),
            actor=actor,
        )
        executed.append(
            {
                "site_id": str(row.site_id),
                "sync_source_id": str(row.id),
                "status": result.get("status", "unknown"),
                "fetched_count": int(result.get("fetched_count", 0) or 0),
            }
        )
    return {
        "status": "ok",
        "scheduled_source_count": len(rows),
        "executed_count": len(executed),
        "skipped_count": len(skipped),
        "executed": executed,
        "skipped": skipped,
        "generated_at": _safe_iso(datetime.now(timezone.utc)),
    }


def process_red_plugin_sync_schedules(limit: int = 100) -> dict[str, Any]:
    with SessionLocal() as db:
        return run_red_plugin_sync_scheduler(
            db,
            limit=limit,
            dry_run_override=False,
            actor="autonomous_runtime",
        )


def _find_latest_plugin_run(db: Session, *, site_id: UUID, plugin_code: str, run_id: UUID | None = None) -> tuple[Site | None, AiCoworkerPlugin | None, AiCoworkerPluginRun | None]:
    site = db.get(Site, site_id)
    if not site:
        return None, None, None
    plugin = db.scalar(select(AiCoworkerPlugin).where(AiCoworkerPlugin.plugin_code == plugin_code))
    if not plugin:
        return site, None, None
    stmt = (
        select(AiCoworkerPluginRun)
        .where(
            AiCoworkerPluginRun.site_id == site.id,
            AiCoworkerPluginRun.plugin_id == plugin.id,
        )
        .order_by(desc(AiCoworkerPluginRun.created_at))
        .limit(1)
    )
    if run_id:
        stmt = select(AiCoworkerPluginRun).where(
            AiCoworkerPluginRun.id == run_id,
            AiCoworkerPluginRun.site_id == site.id,
            AiCoworkerPluginRun.plugin_id == plugin.id,
        )
    run = db.scalar(stmt)
    return site, plugin, run


def _lint_template(content: str) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    lowered = content.lower()
    if "id:" not in lowered:
        issues.append("missing id field")
    if "info:" not in lowered:
        issues.append("missing info block")
    if "http:" not in lowered:
        issues.append("missing http block")
    if "{{baseurl}}" not in lowered:
        warnings.append("missing BaseURL variable")
    if "severity:" not in lowered:
        warnings.append("missing severity metadata")
    if "matchers:" not in lowered:
        warnings.append("missing matcher definition")
    line_count = len([line for line in content.splitlines() if line.strip()])
    return {
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "warnings": warnings,
        "line_count": line_count,
        "kind": "nuclei_template",
    }


def _lint_exploit(content: str, safety_policy: dict[str, Any], *, language: str = "python") -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    blocked_modules = {str(item).strip() for item in safety_policy.get("blocked_modules", [])}
    allowed_modules = {str(item).strip() for item in safety_policy.get("allowed_modules", [])}
    lines = [line for line in content.splitlines() if line.strip()]
    line_count = len(lines)
    if safety_policy.get("require_comment_header") and not content.lstrip().startswith("#"):
        issues.append("missing required comment header")
    if safety_policy.get("require_disclaimer") and "authorized validation" not in content.lower():
        issues.append("missing required authorized-validation disclaimer")
    if not safety_policy.get("allow_network_calls", True) and any(
        marker in content for marker in ("requests.", "curl ", "curl\t", "curl -", "curl\n")
    ):
        issues.append("network calls disabled by policy")
    if language == "python":
        for module in blocked_modules:
            if module and f"import {module}" in content:
                issues.append(f"blocked module detected: {module}")
        for line in lines:
            if line.startswith("import "):
                module = line.replace("import ", "", 1).split(" as ", 1)[0].split(",", 1)[0].strip()
                if allowed_modules and module and module not in allowed_modules and module not in blocked_modules:
                    warnings.append(f"module not in allow-list: {module}")
        if "requests.get(" in content and "timeout=" not in content:
            warnings.append("requests call missing timeout")
    elif language == "bash":
        if "set -euo pipefail" not in content:
            warnings.append("bash script missing strict shell options")
        if "curl " in content and "--max-time" not in content:
            warnings.append("curl call missing --max-time")
    elif language == "curl":
        if "curl " in content and "--max-time" not in content:
            warnings.append("curl call missing --max-time")
    if line_count > int(safety_policy.get("max_script_lines", 80) or 80):
        warnings.append("script exceeds max_script_lines policy")
    return {
        "status": "pass" if not issues else "fail",
        "issues": issues,
        "warnings": warnings,
        "line_count": line_count,
        "kind": f"{language}_exploit_script",
    }


def lint_red_plugin_output(
    db: Session,
    *,
    site_id: UUID,
    plugin_code: str,
    run_id: UUID | None = None,
    content_override: str = "",
) -> dict[str, Any]:
    site, plugin, run = _find_latest_plugin_run(db, site_id=site_id, plugin_code=plugin_code, run_id=run_id)
    if site is None:
        return {"status": "not_found", "site_id": str(site_id)}
    if plugin is None:
        return {"status": "plugin_not_found", "site_id": str(site_id), "plugin_code": plugin_code}
    if run is None and not content_override:
        return {"status": "run_not_found", "site_id": str(site.id), "plugin_code": plugin_code}
    output_summary = _safe_json_dict(run.output_summary_json) if run else {}
    content = str(content_override or output_summary.get("template_preview") or output_summary.get("script_preview") or "")
    target_type = str(output_summary.get("target_type") or "web")
    safety_policy = get_red_plugin_safety_policy(db, site_id=site.id, target_type=target_type)["policy"]
    language = str(output_summary.get("language") or "python")
    lint = _lint_template(content) if plugin_code == "red_template_writer" else _lint_exploit(content, safety_policy, language=language)
    lint["target_type"] = target_type
    lint["language"] = language
    lint["preview_excerpt"] = content[:400]
    return {
        "status": "ok",
        "site_id": str(site.id),
        "plugin_code": plugin_code,
        "run_id": str(run.id) if run else "",
        "lint": lint,
        "safety_policy": safety_policy,
    }


def export_red_plugin_output(
    db: Session,
    *,
    site_id: UUID,
    plugin_code: str,
    run_id: UUID | None = None,
    export_kind: str = "bundle",
    title_override: str = "",
) -> dict[str, Any]:
    site, plugin, run = _find_latest_plugin_run(db, site_id=site_id, plugin_code=plugin_code, run_id=run_id)
    if site is None:
        return {"status": "not_found", "site_id": str(site_id)}
    if plugin is None:
        return {"status": "plugin_not_found", "site_id": str(site.id), "plugin_code": plugin_code}
    if run is None:
        return {"status": "run_not_found", "site_id": str(site.id), "plugin_code": plugin_code}
    output_summary = _safe_json_dict(run.output_summary_json)
    input_summary = _safe_json_dict(run.input_summary_json)
    content = str(output_summary.get("template_preview") or output_summary.get("script_preview") or "")
    intelligence = get_latest_red_plugin_intelligence(
        db,
        site_id=site.id,
        target_surface=str(input_summary.get("target_surface") or ""),
        target_type=str(input_summary.get("target_type") or output_summary.get("target_type") or "web"),
    )
    lint_result = lint_red_plugin_output(db, site_id=site.id, plugin_code=plugin_code, run_id=run.id)
    language = str(output_summary.get("language") or "python").lower()
    if plugin_code == "red_template_writer":
        extension = "yaml"
    elif language == "bash":
        extension = "sh"
    elif language == "curl":
        extension = "txt"
    else:
        extension = "py"
    filename = f"{site.site_code}-{plugin_code}-{str(run.id)[:8]}.{extension}.json"
    title = title_override.strip() or f"{plugin.display_name} export for {site.display_name}"
    export = {
        "filename": filename,
        "title": title,
        "export_kind": export_kind,
        "artifact_type": "nuclei_template" if plugin_code == "red_template_writer" else "exploit_script",
        "content": content,
        "metadata": {
            "site_id": str(site.id),
            "site_code": site.site_code,
            "plugin_code": plugin_code,
            "run_id": str(run.id),
            "created_at": _safe_iso(run.created_at),
            "input_summary": input_summary,
            "source_intelligence": intelligence or {},
        },
        "lint": lint_result.get("lint", {}),
    }
    if plugin_code == "red_template_writer":
        export["threat_content_suggestion"] = {
            "title": (intelligence or {}).get("title") or title,
            "category": (intelligence or {}).get("target_type") or "web",
            "mitre_techniques": [],
            "validation_mode": "simulation_safe",
        }
    return {
        "status": "ok",
        "site_id": str(site.id),
        "plugin_code": plugin_code,
        "run_id": str(run.id),
        "export": export,
    }


def publish_red_template_to_threat_pack(
    db: Session,
    *,
    site_id: UUID,
    run_id: UUID | None = None,
    activate: bool = True,
    actor: str = "red_plugin_publish_ai",
) -> dict[str, Any]:
    export_result = export_red_plugin_output(
        db,
        site_id=site_id,
        plugin_code="red_template_writer",
        run_id=run_id,
        export_kind="bundle",
        title_override="",
    )
    if export_result.get("status") != "ok":
        return export_result
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    export = export_result.get("export", {})
    suggestion = export.get("threat_content_suggestion", {}) if isinstance(export, dict) else {}
    metadata = export.get("metadata", {}) if isinstance(export, dict) else {}
    source_intelligence = metadata.get("source_intelligence", {}) if isinstance(metadata, dict) else {}
    title = str(suggestion.get("title") or export.get("title") or "Red Template Threat Pack").strip()[:255]
    category = _normalize_target_type(str(suggestion.get("category") or (source_intelligence or {}).get("target_type") or "web"))
    base_pack_code = f"{site.site_code}-{_slugify((source_intelligence or {}).get('cve_id') or title)}"
    pack_code = base_pack_code[:80] or f"{site.site_code}-template-pack"
    existing = db.scalar(select(ThreatContentPack).where(ThreatContentPack.pack_code == pack_code))
    attack_steps = [
        "nuclei template validation",
        "safe replay against changed surface",
    ]
    if isinstance(source_intelligence, dict) and source_intelligence.get("summary_th"):
        attack_steps.append(str(source_intelligence.get("summary_th"))[:255])
    now = datetime.now(timezone.utc)
    if existing is None:
        existing = ThreatContentPack(
            pack_code=pack_code,
            created_at=now,
        )
        db.add(existing)
        status = "created"
    else:
        status = "updated"
    existing.title = title
    existing.category = category
    existing.mitre_techniques_json = _as_json(_normalize_string_list(list(suggestion.get("mitre_techniques") or [])))
    existing.attack_steps_json = _as_json(_normalize_string_list(attack_steps))
    existing.validation_mode = "simulation_safe"
    existing.is_active = bool(activate)
    existing.updated_at = now
    db.commit()
    db.refresh(existing)
    return {
        "status": status,
        "site_id": str(site.id),
        "pack": {
            "pack_code": existing.pack_code,
            "title": existing.title,
            "category": existing.category,
            "mitre_techniques": _safe_json_list(existing.mitre_techniques_json),
            "attack_steps": _safe_json_list(existing.attack_steps_json),
            "validation_mode": existing.validation_mode,
            "is_active": bool(existing.is_active),
            "updated_at": _safe_iso(existing.updated_at),
        },
        "source_export": export,
        "actor": actor,
    }
