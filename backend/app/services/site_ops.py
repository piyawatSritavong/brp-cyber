from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import httpx
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import BlueEventLog, PurpleInsightReport, RedScanRun, Site, Tenant
from schemas.site_ops import BlueSiteEventIngestRequest, RedSiteScanRequest, SiteUpsertRequest

SECURITY_HEADERS = [
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
]


def _as_json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _safe_json_load(value: str | None) -> dict[str, object]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _site_row(site: Site) -> dict[str, object]:
    return {
        "site_id": str(site.id),
        "tenant_id": str(site.tenant_id),
        "site_code": site.site_code,
        "display_name": site.display_name,
        "base_url": site.base_url,
        "is_active": bool(site.is_active),
        "config": _safe_json_load(site.config_json),
        "created_at": site.created_at.isoformat() if site.created_at else "",
        "updated_at": site.updated_at.isoformat() if site.updated_at else "",
    }


def _ai_red_summary(findings: dict[str, object]) -> str:
    risk_score = int(findings.get("risk_score", 0) or 0)
    if risk_score >= 70:
        tier = "high"
    elif risk_score >= 35:
        tier = "medium"
    else:
        tier = "low"
    missing_headers = findings.get("missing_security_headers", [])
    open_paths = findings.get("sensitive_paths_open", [])
    return (
        f"AI Red Assessment: risk={tier} score={risk_score}. "
        f"MissingHeaders={len(missing_headers)} OpenSensitivePaths={len(open_paths)}. "
        "Recommendation: enforce security headers, lock sensitive routes, enable stronger auth policy."
    )


def _ai_blue_assess(event: BlueSiteEventIngestRequest) -> tuple[str, str]:
    severity = "low"
    recommendation = "notify_team"
    if event.status_code in {401, 403, 429}:
        severity = "medium"
        recommendation = "limit_user"
    if event.status_code >= 500 or "brute" in event.message.lower() or "sql" in event.message.lower():
        severity = "high"
        recommendation = "block_ip"
    if event.status_code == 200 and "health" in event.path:
        severity = "low"
        recommendation = "ignore"
    return severity, recommendation


def _ai_purple_analysis(red_runs: list[RedScanRun], blue_logs: list[BlueEventLog]) -> dict[str, object]:
    high_events = len([row for row in blue_logs if row.ai_severity == "high"])
    medium_events = len([row for row in blue_logs if row.ai_severity == "medium"])
    total_scans = len(red_runs)
    gap = high_events > 0 and total_scans == 0
    recommendation = (
        "Increase red scan frequency and tighten blue response thresholds."
        if high_events > 0
        else "Maintain baseline; continue continuous validation."
    )
    return {
        "high_events": high_events,
        "medium_events": medium_events,
        "total_scans": total_scans,
        "gap_detected": gap,
        "recommendation": recommendation,
    }


def list_sites(db: Session, *, tenant_code: str = "", limit: int = 200) -> dict[str, object]:
    stmt = select(Site).order_by(Site.created_at.desc()).limit(max(1, min(limit, 1000)))
    if tenant_code:
        tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
        if not tenant:
            return {"count": 0, "rows": []}
        stmt = stmt.where(Site.tenant_id == tenant.id)
    rows = db.scalars(stmt).all()
    return {"count": len(rows), "rows": [_site_row(row) for row in rows]}


def upsert_site(db: Session, payload: SiteUpsertRequest) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == payload.tenant_code))
    if not tenant:
        tenant = Tenant(
            tenant_code=payload.tenant_code,
            display_name=payload.tenant_code.upper(),
            status="active",
        )
        db.add(tenant)
        db.flush()

    existing = db.scalar(select(Site).where(Site.site_code == payload.site_code))
    now = datetime.now(timezone.utc)
    if existing:
        existing.display_name = payload.display_name
        existing.base_url = str(payload.base_url)
        existing.is_active = payload.is_active
        existing.config_json = _as_json(payload.config)
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return {"status": "updated", "site": _site_row(existing)}

    site = Site(
        tenant_id=tenant.id,
        site_code=payload.site_code,
        display_name=payload.display_name,
        base_url=str(payload.base_url),
        is_active=payload.is_active,
        config_json=_as_json(payload.config),
        created_at=now,
        updated_at=now,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return {"status": "created", "site": _site_row(site)}


def _scan_url(url: str) -> dict[str, object]:
    start = time.perf_counter()
    parsed = urlparse(url)
    host = parsed.netloc
    findings: dict[str, object] = {
        "target_url": url,
        "host": host,
        "status_code": 0,
        "response_time_ms": 0.0,
        "security_headers": {},
        "missing_security_headers": [],
        "sensitive_paths_open": [],
        "notes": [],
    }
    try:
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            response = client.get(url)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            findings["status_code"] = int(response.status_code)
            findings["response_time_ms"] = round(elapsed_ms, 2)
            headers = {key.lower(): value for key, value in response.headers.items()}
            findings["security_headers"] = {h: headers.get(h, "") for h in SECURITY_HEADERS}
            findings["missing_security_headers"] = [h for h in SECURITY_HEADERS if not headers.get(h)]

            for path in ["/admin", "/login", "/wp-login.php", "/.env", "/config"]:
                probe = client.get(url.rstrip("/") + path)
                if probe.status_code in {200, 401, 403}:
                    findings["sensitive_paths_open"].append({"path": path, "status_code": probe.status_code})

    except Exception as exc:
        findings["notes"].append(f"scan_error:{exc}")

    risk_score = 0
    risk_score += min(40, len(findings["missing_security_headers"]) * 8)
    risk_score += min(40, len(findings["sensitive_paths_open"]) * 10)
    if findings["status_code"] >= 500:
        risk_score += 25
    findings["risk_score"] = min(100, risk_score)
    return findings


def run_red_site_scan(db: Session, site_id: UUID, payload: RedSiteScanRequest) -> dict[str, object]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    findings = _scan_url(site.base_url)
    ai_summary = _ai_red_summary(findings)
    row = RedScanRun(
        site_id=site.id,
        scan_type=payload.scan_type,
        status="completed",
        findings_json=_as_json(findings),
        ai_summary=ai_summary,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "status": "completed",
        "site": _site_row(site),
        "scan_id": str(row.id),
        "scan_type": row.scan_type,
        "findings": findings,
        "ai_summary": ai_summary,
    }


def list_red_scans(db: Session, site_id: UUID, *, limit: int = 30) -> dict[str, object]:
    rows = db.scalars(
        select(RedScanRun)
        .where(RedScanRun.site_id == site_id)
        .order_by(desc(RedScanRun.created_at))
        .limit(max(1, min(limit, 200)))
    ).all()
    return {
        "count": len(rows),
        "rows": [
            {
                "scan_id": str(row.id),
                "scan_type": row.scan_type,
                "status": row.status,
                "ai_summary": row.ai_summary,
                "findings": _safe_json_load(row.findings_json),
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ],
    }


def ingest_blue_site_event(db: Session, site_id: UUID, payload: BlueSiteEventIngestRequest) -> dict[str, object]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    severity, recommendation = _ai_blue_assess(payload)
    merged_payload = dict(payload.payload)
    merged_payload.update(
        {
            "path": payload.path,
            "method": payload.method,
            "status_code": payload.status_code,
            "message": payload.message,
        }
    )
    row = BlueEventLog(
        site_id=site.id,
        event_type=payload.event_type,
        source_ip=payload.source_ip,
        payload_json=_as_json(merged_payload),
        ai_severity=severity,
        ai_recommendation=recommendation,
        status="open",
        action_taken="",
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "status": "accepted",
        "event_id": str(row.id),
        "ai": {"severity": severity, "recommendation": recommendation},
    }


def list_blue_site_events(db: Session, site_id: UUID, *, limit: int = 100) -> dict[str, object]:
    rows = db.scalars(
        select(BlueEventLog)
        .where(BlueEventLog.site_id == site_id)
        .order_by(desc(BlueEventLog.created_at))
        .limit(max(1, min(limit, 500)))
    ).all()
    return {
        "count": len(rows),
        "rows": [
            {
                "event_id": str(row.id),
                "event_type": row.event_type,
                "source_ip": row.source_ip,
                "payload": _safe_json_load(row.payload_json),
                "ai_severity": row.ai_severity,
                "ai_recommendation": row.ai_recommendation,
                "status": row.status,
                "action_taken": row.action_taken,
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ],
    }


def apply_blue_recommendation(db: Session, site_id: UUID, event_id: UUID, action: str) -> dict[str, object]:
    row = db.get(BlueEventLog, event_id)
    if not row or row.site_id != site_id:
        return {"status": "not_found"}
    row.status = "applied"
    row.action_taken = action
    db.commit()
    db.refresh(row)
    return {"status": "applied", "event_id": str(row.id), "action": action}


def generate_purple_site_report(db: Session, site_id: UUID) -> dict[str, object]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    red_rows = db.scalars(
        select(RedScanRun).where(RedScanRun.site_id == site_id).order_by(desc(RedScanRun.created_at)).limit(50)
    ).all()
    blue_rows = db.scalars(
        select(BlueEventLog).where(BlueEventLog.site_id == site_id).order_by(desc(BlueEventLog.created_at)).limit(500)
    ).all()
    analysis = _ai_purple_analysis(red_rows, blue_rows)
    metrics = {
        "red_scan_count": len(red_rows),
        "blue_event_count": len(blue_rows),
        "blue_high_count": len([row for row in blue_rows if row.ai_severity == "high"]),
        "blue_medium_count": len([row for row in blue_rows if row.ai_severity == "medium"]),
        "blue_low_count": len([row for row in blue_rows if row.ai_severity == "low"]),
    }
    summary = (
        f"Purple AI Summary for {site.display_name}: scans={metrics['red_scan_count']} "
        f"events={metrics['blue_event_count']} high={metrics['blue_high_count']}."
    )
    report = PurpleInsightReport(
        site_id=site.id,
        summary=summary,
        metrics_json=_as_json(metrics),
        ai_analysis_json=_as_json(analysis),
        created_at=datetime.now(timezone.utc),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {
        "status": "completed",
        "report_id": str(report.id),
        "site": _site_row(site),
        "summary": summary,
        "metrics": metrics,
        "ai_analysis": analysis,
    }


def list_purple_site_reports(db: Session, site_id: UUID, *, limit: int = 30) -> dict[str, object]:
    rows = db.scalars(
        select(PurpleInsightReport)
        .where(PurpleInsightReport.site_id == site_id)
        .order_by(desc(PurpleInsightReport.created_at))
        .limit(max(1, min(limit, 200)))
    ).all()
    return {
        "count": len(rows),
        "rows": [
            {
                "report_id": str(row.id),
                "summary": row.summary,
                "metrics": _safe_json_load(row.metrics_json),
                "ai_analysis": _safe_json_load(row.ai_analysis_json),
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ],
    }


def generate_iso27001_gap_template(db: Session, site_id: UUID, *, limit: int = 200) -> dict[str, object]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}

    red_rows = db.scalars(
        select(RedScanRun).where(RedScanRun.site_id == site_id).order_by(desc(RedScanRun.created_at)).limit(max(1, min(limit, 500)))
    ).all()
    blue_rows = db.scalars(
        select(BlueEventLog).where(BlueEventLog.site_id == site_id).order_by(desc(BlueEventLog.created_at)).limit(max(1, min(limit, 1000)))
    ).all()
    purple_rows = db.scalars(
        select(PurpleInsightReport)
        .where(PurpleInsightReport.site_id == site_id)
        .order_by(desc(PurpleInsightReport.created_at))
        .limit(max(1, min(limit, 300)))
    ).all()

    latest_red_findings: dict[str, Any] = _safe_json_load(red_rows[0].findings_json) if red_rows else {}
    missing_headers = len(latest_red_findings.get("missing_security_headers", [])) if latest_red_findings else 0
    sensitive_open = len(latest_red_findings.get("sensitive_paths_open", [])) if latest_red_findings else 0
    high_blue = len([row for row in blue_rows if row.ai_severity == "high"])
    applied_blue = len([row for row in blue_rows if row.status == "applied"])
    blue_total = len(blue_rows)
    mttr_hint_seconds = 0 if applied_blue == 0 else int((high_blue + 1) * 30)
    coverage = 0.0 if blue_total == 0 else round(applied_blue / blue_total, 4)

    def _status(pass_condition: bool, partial_condition: bool) -> str:
        if pass_condition:
            return "pass"
        if partial_condition:
            return "partial"
        return "gap"

    control_rows = [
        {
            "control_id": "A.8.8",
            "control_name": "Management of technical vulnerabilities",
            "status": _status(missing_headers == 0 and sensitive_open == 0, red_rows != []),
            "evidence": f"red_scans={len(red_rows)} missing_headers={missing_headers} sensitive_paths_open={sensitive_open}",
            "recommendation": "Run continuous baseline scans and patch exposed paths/security headers within SLA.",
        },
        {
            "control_id": "A.8.16",
            "control_name": "Monitoring activities",
            "status": _status(blue_total > 0 and high_blue == 0, blue_total > 0),
            "evidence": f"blue_events={blue_total} high_severity={high_blue}",
            "recommendation": "Keep webhook adapters active and tune severity mapping for false-positive reduction.",
        },
        {
            "control_id": "A.5.24",
            "control_name": "Information security incident management planning and preparation",
            "status": _status(applied_blue > 0, blue_total > 0),
            "evidence": f"applied_actions={applied_blue} total_events={blue_total} mttr_hint_seconds={mttr_hint_seconds}",
            "recommendation": "Use one-click playbooks for containment and track MTTR trend weekly.",
        },
        {
            "control_id": "A.5.7",
            "control_name": "Threat intelligence",
            "status": _status(len(red_rows) > 0 and len(purple_rows) > 0, len(red_rows) > 0 or len(purple_rows) > 0),
            "evidence": f"red_reports={len(red_rows)} purple_reports={len(purple_rows)}",
            "recommendation": "Correlate external intelligence with Red findings and push strategy updates to Blue rules.",
        },
    ]

    summary = {
        "site_id": str(site.id),
        "site_code": site.site_code,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "red_scan_count": len(red_rows),
        "blue_event_count": blue_total,
        "purple_report_count": len(purple_rows),
        "blue_applied_ratio": coverage,
        "mttr_hint_seconds": mttr_hint_seconds,
    }
    return {
        "status": "completed",
        "framework": "ISO/IEC 27001:2022",
        "summary": summary,
        "controls": control_rows,
    }
