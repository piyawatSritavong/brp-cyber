from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import PurpleAttackLayerWorkspace, Site
from app.services.site_ops import generate_purple_executive_scorecard


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


def _site_or_not_found(db: Session, site_id: UUID) -> Site | None:
    return db.get(Site, site_id)


def _normalize_layer_document(layer_document: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(layer_document, str):
        parsed = json.loads(layer_document or "{}")
        if isinstance(parsed, dict):
            layer_document = parsed
        else:
            layer_document = {}
    layer = dict(layer_document or {})
    techniques = layer.get("techniques", [])
    if not isinstance(techniques, list):
        techniques = []
    normalized_techniques = []
    for row in techniques:
        if not isinstance(row, dict):
            continue
        technique_id = str(row.get("techniqueID") or row.get("technique_id") or "").strip().upper()
        if not technique_id:
            continue
        normalized_techniques.append(
            {
                "techniqueID": technique_id,
                "score": int(row.get("score", 0) or 0),
                "color": str(row.get("color", "") or "").strip(),
                "comment": str(row.get("comment", "") or "").strip(),
                "enabled": bool(row.get("enabled", True)),
            }
        )
    return {
        "version": str(layer.get("version", "4.5") or "4.5"),
        "name": str(layer.get("name", "BRP Imported Layer") or "BRP Imported Layer"),
        "domain": str(layer.get("domain", "enterprise-attack") or "enterprise-attack"),
        "description": str(layer.get("description", "") or ""),
        "techniques": normalized_techniques,
    }


def _workspace_row(row: PurpleAttackLayerWorkspace) -> dict[str, Any]:
    layer = _safe_json_dict(row.layer_json)
    details = _safe_json_dict(row.details_json)
    techniques = layer.get("techniques", []) if isinstance(layer, dict) else []
    if not isinstance(techniques, list):
        techniques = []
    return {
        "workspace_id": str(row.id),
        "site_id": str(row.site_id),
        "layer_name": row.layer_name,
        "source_kind": row.source_kind,
        "actor": row.actor,
        "title": row.title,
        "notes": row.notes,
        "layer": layer,
        "summary": {
            "technique_count": len(techniques),
            "enabled_count": len([item for item in techniques if isinstance(item, dict) and bool(item.get("enabled", True))]),
            **details,
        },
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def _render_svg(title: str, techniques: list[dict[str, Any]]) -> str:
    width = 960
    header_height = 70
    cell_width = 150
    cell_height = 54
    cols = 5
    rows = max(1, (len(techniques) + cols - 1) // cols)
    height = header_height + (rows * cell_height) + 40
    rects: list[str] = []
    for index, row in enumerate(techniques):
        x = 20 + (index % cols) * (cell_width + 10)
        y = header_height + (index // cols) * (cell_height + 10)
        color = str(row.get("color") or "").strip() or ("#F76C45" if int(row.get("score", 0) or 0) >= 80 else "#F7B045")
        comment = str(row.get("comment", "") or "")[:60]
        rects.append(
            f'<g><rect x="{x}" y="{y}" width="{cell_width}" height="{cell_height}" rx="12" fill="{color}" opacity="0.92" />'
            f'<text x="{x + 12}" y="{y + 22}" font-size="14" font-family="Arial" fill="#110B0A">{row.get("techniqueID", "")}</text>'
            f'<text x="{x + 12}" y="{y + 40}" font-size="10" font-family="Arial" fill="#110B0A">{comment}</text></g>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<rect width="100%" height="100%" fill="#FFFFFF"/>'
        f'<text x="20" y="32" font-size="24" font-family="Arial" fill="#110B0A">{title}</text>'
        f'<text x="20" y="52" font-size="12" font-family="Arial" fill="#F76C45">BRP graphical ATT&CK layer export</text>'
        f"{''.join(rects)}"
        '</svg>'
    )


def _live_layer_document(db: Session, site: Site, *, lookback_runs: int, lookback_events: int, sla_target_seconds: int) -> dict[str, Any]:
    scorecard = generate_purple_executive_scorecard(
        db,
        site.id,
        lookback_runs=lookback_runs,
        lookback_events=lookback_events,
        sla_target_seconds=sla_target_seconds,
    )
    rows = scorecard.get("heatmap", []) if isinstance(scorecard, dict) else []
    return {
        "version": "4.5",
        "name": f"BRP Live Layer - {site.display_name}",
        "domain": "enterprise-attack",
        "description": f"Generated from BRP executive scorecard for {site.site_code}",
        "techniques": [
            {
                "techniqueID": str(row.get("technique_id", "") or "").strip().upper(),
                "score": 100 if row.get("detection_status") == "covered" else (60 if row.get("detection_status") == "partial" else 20),
                "color": "#3bb273" if row.get("detection_status") == "covered" else ("#f7b045" if row.get("detection_status") == "partial" else "#f76c45"),
                "comment": str(row.get("recommendation", "") or ""),
                "enabled": True,
            }
            for row in rows
            if str(row.get("technique_id", "") or "").strip()
        ],
    }


def list_purple_attack_layer_workspaces(db: Session, *, site_id: UUID, limit: int = 20) -> dict[str, Any]:
    site = _site_or_not_found(db, site_id)
    if site is None:
        return {"status": "not_found", "site_id": str(site_id)}
    rows = db.scalars(
        select(PurpleAttackLayerWorkspace)
        .where(PurpleAttackLayerWorkspace.site_id == site.id)
        .order_by(desc(PurpleAttackLayerWorkspace.updated_at))
        .limit(max(1, min(limit, 100)))
    ).all()
    return {"status": "ok", "site_id": str(site.id), "site_code": site.site_code, "count": len(rows), "rows": [_workspace_row(row) for row in rows]}


def import_purple_attack_layer_workspace(
    db: Session,
    *,
    site_id: UUID,
    layer_name: str,
    layer_document: dict[str, Any] | str,
    actor: str = "purple_operator",
    notes: str = "",
 ) -> dict[str, Any]:
    site = _site_or_not_found(db, site_id)
    if site is None:
        return {"status": "not_found", "site_id": str(site_id)}
    layer = _normalize_layer_document(layer_document)
    now = datetime.now(timezone.utc)
    row = PurpleAttackLayerWorkspace(
        site_id=site.id,
        layer_name=str(layer_name or layer.get("name", "Imported Layer"))[:255],
        source_kind="imported",
        actor=str(actor or "purple_operator")[:128],
        title=str(layer.get("name", "Imported Layer"))[:255],
        notes=str(notes or "")[:4000],
        layer_json=json.dumps(layer, ensure_ascii=True),
        details_json=json.dumps({"domain": layer.get("domain", "enterprise-attack")}, ensure_ascii=True),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "ok", "site_id": str(site.id), "site_code": site.site_code, "workspace": _workspace_row(row)}


def update_purple_attack_layer_workspace(
    db: Session,
    *,
    site_id: UUID,
    layer_id: UUID,
    layer_name: str = "",
    notes: str = "",
    technique_overrides: list[dict[str, Any]] | None = None,
    actor: str = "purple_operator",
 ) -> dict[str, Any]:
    site = _site_or_not_found(db, site_id)
    if site is None:
        return {"status": "not_found", "site_id": str(site_id)}
    row = db.get(PurpleAttackLayerWorkspace, layer_id)
    if row is None or row.site_id != site.id:
        return {"status": "workspace_not_found", "site_id": str(site.id), "layer_id": str(layer_id)}
    layer = _safe_json_dict(row.layer_json)
    techniques = layer.get("techniques", []) if isinstance(layer, dict) else []
    if not isinstance(techniques, list):
        techniques = []
    by_id: dict[str, dict[str, Any]] = {}
    ordered_ids: list[str] = []
    for item in techniques:
        if not isinstance(item, dict):
            continue
        technique_id = str(item.get("techniqueID", "") or "").strip().upper()
        if not technique_id:
            continue
        by_id[technique_id] = dict(item)
        ordered_ids.append(technique_id)
    for override in technique_overrides or []:
        technique_id = str(override.get("techniqueID") or override.get("technique_id") or "").strip().upper()
        if not technique_id:
            continue
        current = dict(by_id.get(technique_id, {"techniqueID": technique_id, "enabled": True}))
        for key in ("score", "color", "comment", "enabled"):
            if key in override:
                current[key] = override[key]
        by_id[technique_id] = current
        if technique_id not in ordered_ids:
            ordered_ids.append(technique_id)
    layer["techniques"] = [by_id[technique_id] for technique_id in ordered_ids]
    if layer_name.strip():
        row.layer_name = layer_name.strip()[:255]
        layer["name"] = row.layer_name
    row.notes = str(notes or row.notes or "")[:4000]
    row.actor = str(actor or row.actor or "purple_operator")[:128]
    row.title = str(layer.get("name", row.title or row.layer_name or "Layer"))[:255]
    row.layer_json = json.dumps(layer, ensure_ascii=True)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return {"status": "ok", "site_id": str(site.id), "site_code": site.site_code, "workspace": _workspace_row(row)}


def export_purple_attack_layer_workspace(
    db: Session,
    *,
    site_id: UUID,
    layer_id: UUID,
    export_format: str = "attack_layer_json",
 ) -> dict[str, Any]:
    site = _site_or_not_found(db, site_id)
    if site is None:
        return {"status": "not_found", "site_id": str(site_id)}
    row = db.get(PurpleAttackLayerWorkspace, layer_id)
    if row is None or row.site_id != site.id:
        return {"status": "workspace_not_found", "site_id": str(site.id), "layer_id": str(layer_id)}
    layer = _safe_json_dict(row.layer_json)
    techniques = layer.get("techniques", []) if isinstance(layer, dict) else []
    if not isinstance(techniques, list):
        techniques = []
    normalized = str(export_format or "attack_layer_json").strip().lower()
    if normalized == "svg":
        content = _render_svg(str(layer.get("name", row.layer_name or "Layer")), [dict(item) for item in techniques if isinstance(item, dict)])
        filename = f"{site.site_code}-{row.layer_name or 'layer'}.svg"
    else:
        content = json.dumps(layer, ensure_ascii=True, indent=2)
        filename = f"{site.site_code}-{row.layer_name or 'layer'}.json"
        normalized = "attack_layer_json"
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "workspace": _workspace_row(row),
        "export": {
            "export_type": "attack_layer_workspace",
            "export_format": normalized,
            "filename": filename,
            "generated_at": _safe_iso(datetime.now(timezone.utc)),
            "content": content,
        },
    }


def export_live_purple_attack_layer_graphic(
    db: Session,
    *,
    site_id: UUID,
    export_format: str = "svg",
    lookback_runs: int = 30,
    lookback_events: int = 500,
    sla_target_seconds: int = 120,
 ) -> dict[str, Any]:
    site = _site_or_not_found(db, site_id)
    if site is None:
        return {"status": "not_found", "site_id": str(site_id)}
    layer = _live_layer_document(
        db,
        site,
        lookback_runs=lookback_runs,
        lookback_events=lookback_events,
        sla_target_seconds=sla_target_seconds,
    )
    techniques = layer.get("techniques", []) if isinstance(layer, dict) else []
    if not isinstance(techniques, list):
        techniques = []
    normalized = str(export_format or "svg").strip().lower()
    if normalized == "attack_layer_json":
        content = json.dumps(layer, ensure_ascii=True, indent=2)
        filename = f"{site.site_code}-live-attack-layer.json"
    else:
        content = _render_svg(str(layer.get("name", f"BRP Live Layer - {site.site_code}")), [dict(item) for item in techniques if isinstance(item, dict)])
        filename = f"{site.site_code}-live-attack-layer.svg"
        normalized = "svg"
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "export": {
            "export_type": "attack_layer_live",
            "export_format": normalized,
            "filename": filename,
            "generated_at": _safe_iso(datetime.now(timezone.utc)),
            "technique_count": len(techniques),
            "content": content,
        },
    }
