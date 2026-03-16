from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import httpx
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    BlueDetectionRule,
    BlueEventLog,
    PurpleInsightReport,
    RedExploitPathRun,
    RedScanRun,
    Site,
    Tenant,
    ThreatContentPack,
)
from schemas.site_ops import BlueSiteEventIngestRequest, RedSiteScanRequest, SiteUpsertRequest

SECURITY_HEADERS = [
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
]

SIGNAL_MITRE_HINTS: dict[str, list[str]] = {
    "failed_login_spike": ["T1110"],
    "impossible_auth_pattern": ["T1078"],
    "lateral_movement_plus_privilege_escalation": ["T1021", "T1068"],
    "waf_403_burst": ["T1190"],
    "credential_reuse_or_bruteforce": ["T1110"],
}

RULE_HINT_MITRE: dict[str, list[str]] = {
    "velocity guard": ["T1110"],
    "identity abuse": ["T1078"],
    "ransomware": ["T1486"],
    "adaptive waf": ["T1190"],
}


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


def _safe_json_list(value: str | None) -> list[object]:
    if not value:
        return []
    try:
        payload = json.loads(value)
        if isinstance(payload, list):
            return payload
    except Exception:
        pass
    return []


def _site_row(site: Site) -> dict[str, object]:
    return {
        "site_id": str(site.id),
        "tenant_id": str(site.tenant_id),
        "tenant_code": site.tenant.tenant_code if site.tenant else "",
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


def _gap_analysis_context(db: Session, site_id: UUID, *, limit: int = 200) -> dict[str, Any]:
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
    return {
        "status": "ok",
        "site": site,
        "red_rows": red_rows,
        "blue_rows": blue_rows,
        "purple_rows": purple_rows,
        "missing_headers": missing_headers,
        "sensitive_open": sensitive_open,
        "high_blue": high_blue,
        "applied_blue": applied_blue,
        "blue_total": blue_total,
        "mttr_hint_seconds": mttr_hint_seconds,
        "coverage": coverage,
    }


def generate_iso27001_gap_template(db: Session, site_id: UUID, *, limit: int = 200) -> dict[str, object]:
    context = _gap_analysis_context(db, site_id, limit=limit)
    if context.get("status") != "ok":
        return context
    site = context["site"]
    red_rows = context["red_rows"]
    blue_rows = context["blue_rows"]
    purple_rows = context["purple_rows"]
    missing_headers = int(context["missing_headers"])
    sensitive_open = int(context["sensitive_open"])
    high_blue = int(context["high_blue"])
    applied_blue = int(context["applied_blue"])
    blue_total = int(context["blue_total"])
    mttr_hint_seconds = int(context["mttr_hint_seconds"])
    coverage = float(context["coverage"])

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


def generate_nist_csf_gap_template(db: Session, site_id: UUID, *, limit: int = 200) -> dict[str, object]:
    context = _gap_analysis_context(db, site_id, limit=limit)
    if context.get("status") != "ok":
        return context
    site = context["site"]
    red_rows = context["red_rows"]
    blue_rows = context["blue_rows"]
    purple_rows = context["purple_rows"]
    missing_headers = int(context["missing_headers"])
    sensitive_open = int(context["sensitive_open"])
    high_blue = int(context["high_blue"])
    applied_blue = int(context["applied_blue"])
    blue_total = int(context["blue_total"])
    mttr_hint_seconds = int(context["mttr_hint_seconds"])
    coverage = float(context["coverage"])

    def _status(pass_condition: bool, partial_condition: bool) -> str:
        if pass_condition:
            return "pass"
        if partial_condition:
            return "partial"
        return "gap"

    control_rows = [
        {
            "control_id": "ID.RA-01",
            "control_name": "Asset and vulnerability risk visibility",
            "status": _status(len(red_rows) > 0 and missing_headers == 0 and sensitive_open == 0, len(red_rows) > 0),
            "evidence": f"red_scans={len(red_rows)} missing_headers={missing_headers} sensitive_paths_open={sensitive_open}",
            "recommendation": "Maintain continuous discovery plus vulnerability validation for exposed paths and missing protective controls.",
        },
        {
            "control_id": "DE.CM-01",
            "control_name": "Security continuous monitoring",
            "status": _status(blue_total > 0 and high_blue == 0, blue_total > 0),
            "evidence": f"blue_events={blue_total} high_severity={high_blue}",
            "recommendation": "Expand telemetry coverage and keep detection tuning active for high-severity signals.",
        },
        {
            "control_id": "RS.MA-01",
            "control_name": "Incident response execution and mitigation",
            "status": _status(applied_blue > 0 and mttr_hint_seconds <= 120, applied_blue > 0),
            "evidence": f"applied_actions={applied_blue} mttr_hint_seconds={mttr_hint_seconds}",
            "recommendation": "Use managed responder approval policies and playbook automation to keep MTTR inside target.",
        },
        {
            "control_id": "GV.RM-01",
            "control_name": "Risk management strategy informed by operations",
            "status": _status(len(purple_rows) > 0 and coverage >= 0.5, len(purple_rows) > 0 or coverage > 0),
            "evidence": f"purple_reports={len(purple_rows)} blue_applied_ratio={coverage}",
            "recommendation": "Feed Red/Blue evidence into governance reviews and refresh security priorities from measured outcomes.",
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
        "framework": "NIST Cybersecurity Framework 2.0",
        "summary": summary,
        "controls": control_rows,
    }


def _extract_red_mitre_techniques(db: Session, red_runs: list[RedExploitPathRun]) -> dict[str, int]:
    attacked_counts: dict[str, int] = defaultdict(int)
    for run in red_runs:
        proof = _safe_json_load(run.proof_json)
        techniques = proof.get("mitre_techniques", []) if isinstance(proof, dict) else []
        if isinstance(techniques, list):
            for technique in techniques:
                technique_id = str(technique).strip().upper()
                if technique_id:
                    attacked_counts[technique_id] += 1
        if run.threat_pack_id:
            pack = db.get(ThreatContentPack, run.threat_pack_id)
            if pack:
                for technique in _safe_json_list(pack.mitre_techniques_json):
                    technique_id = str(technique).strip().upper()
                    if technique_id:
                        attacked_counts[technique_id] += 1
    return attacked_counts


def _extract_detection_mitre_coverage(rules: list[BlueDetectionRule]) -> set[str]:
    covered: set[str] = set()
    for rule in rules:
        logic = _safe_json_load(rule.rule_logic_json)
        if isinstance(logic, dict):
            techniques = logic.get("mitre_techniques", [])
            if isinstance(techniques, list):
                for technique in techniques:
                    technique_id = str(technique).strip().upper()
                    if technique_id:
                        covered.add(technique_id)
            signal = str(logic.get("signal", "")).strip().lower()
            for technique_id in SIGNAL_MITRE_HINTS.get(signal, []):
                covered.add(technique_id.upper())
        rule_name = (rule.rule_name or "").lower()
        for hint, technique_ids in RULE_HINT_MITRE.items():
            if hint in rule_name:
                for technique_id in technique_ids:
                    covered.add(technique_id.upper())
    return covered


def _estimate_mttr_seconds(blue_rows: list[BlueEventLog], suspicious_total: int) -> int:
    if suspicious_total <= 0:
        return 0
    applied_suspicious = len(
        [row for row in blue_rows if row.ai_severity in {"high", "medium"} and row.status == "applied"]
    )
    unresolved = max(0, suspicious_total - applied_suspicious)
    weighted = (applied_suspicious * 60) + (unresolved * 240)
    return int(weighted / suspicious_total)


def generate_purple_executive_scorecard(
    db: Session,
    site_id: UUID,
    *,
    lookback_runs: int = 30,
    lookback_events: int = 500,
    sla_target_seconds: int = 120,
) -> dict[str, object]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}

    red_runs = db.scalars(
        select(RedExploitPathRun)
        .where(RedExploitPathRun.site_id == site_id)
        .order_by(desc(RedExploitPathRun.created_at))
        .limit(max(1, min(lookback_runs, 500)))
    ).all()
    blue_rows = db.scalars(
        select(BlueEventLog)
        .where(BlueEventLog.site_id == site_id)
        .order_by(desc(BlueEventLog.created_at))
        .limit(max(1, min(lookback_events, 2000)))
    ).all()
    detection_rules = db.scalars(
        select(BlueDetectionRule)
        .where(BlueDetectionRule.site_id == site_id)
        .order_by(desc(BlueDetectionRule.updated_at))
        .limit(500)
    ).all()

    attacked_counts = _extract_red_mitre_techniques(db, red_runs)
    covered_techniques = _extract_detection_mitre_coverage(detection_rules)

    suspicious_total = len([row for row in blue_rows if row.ai_severity in {"high", "medium"}])
    applied_suspicious = len([row for row in blue_rows if row.ai_severity in {"high", "medium"} and row.status == "applied"])
    detection_total = len([row for row in blue_rows if row.ai_severity in {"high", "medium"}])
    mttr_seconds = _estimate_mttr_seconds(blue_rows, suspicious_total)
    target_seconds = max(30, min(int(sla_target_seconds), 3600))
    apply_rate = round((applied_suspicious / suspicious_total) if suspicious_total else 0.0, 4)
    response_sla_pass = mttr_seconds <= target_seconds and apply_rate >= 0.7

    if attacked_counts:
        technique_rows = []
        for technique_id, count in sorted(attacked_counts.items(), key=lambda item: item[0]):
            covered = technique_id in covered_techniques
            status = "covered" if covered else ("partial" if apply_rate >= 0.5 else "gap")
            technique_rows.append(
                {
                    "technique_id": technique_id,
                    "attack_count": int(count),
                    "detection_status": status,
                    "mitigation_time_seconds": mttr_seconds if detection_total else None,
                    "sla_status": "pass" if response_sla_pass else "at_risk",
                    "recommendation": (
                        "Maintain control and continue validation."
                        if covered
                        else "Add/tune detection rule mapped to this MITRE technique."
                    ),
                }
            )
    else:
        technique_rows = []

    attacked_unique = len(attacked_counts)
    covered_unique = len([row for row in technique_rows if row["detection_status"] == "covered"])
    partial_unique = len([row for row in technique_rows if row["detection_status"] == "partial"])
    heatmap_coverage = round((covered_unique / attacked_unique), 4) if attacked_unique else 0.0

    executive_summary = {
        "site_id": str(site.id),
        "site_code": site.site_code,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "red_exploit_runs": len(red_runs),
        "blue_events": len(blue_rows),
        "detection_rules": len(detection_rules),
        "attacked_techniques": attacked_unique,
        "covered_techniques": covered_unique,
        "partial_techniques": partial_unique,
        "heatmap_coverage": heatmap_coverage,
    }

    remediation_sla = {
        "target_mttr_seconds": target_seconds,
        "estimated_mttr_seconds": mttr_seconds,
        "suspicious_event_count": suspicious_total,
        "applied_event_count": applied_suspicious,
        "apply_rate": apply_rate,
        "detection_event_count": detection_total,
        "sla_status": "pass" if response_sla_pass else "at_risk",
        "recommendation": (
            "SLA healthy. Continue iterative red/blue tuning."
            if response_sla_pass
            else "Increase blue auto-apply rate and tighten detection thresholds for faster mitigation."
        ),
    }

    return {
        "status": "completed",
        "framework": "MITRE ATT&CK + Remediation SLA",
        "summary": executive_summary,
        "heatmap": technique_rows,
        "remediation_sla": remediation_sla,
    }


def purple_executive_federation(
    db: Session,
    *,
    limit: int = 200,
    lookback_runs: int = 30,
    lookback_events: int = 500,
    sla_target_seconds: int = 120,
) -> dict[str, object]:
    sites = db.scalars(select(Site).order_by(desc(Site.created_at)).limit(max(1, min(limit, 1000)))).all()
    rows: list[dict[str, object]] = []
    for site in sites:
        scorecard = generate_purple_executive_scorecard(
            db,
            site.id,
            lookback_runs=lookback_runs,
            lookback_events=lookback_events,
            sla_target_seconds=sla_target_seconds,
        )
        if scorecard.get("status") != "completed":
            continue
        summary = scorecard.get("summary", {})
        remediation = scorecard.get("remediation_sla", {})
        rows.append(
            {
                "site_id": str(site.id),
                "site_code": site.site_code,
                "tenant_code": site.tenant.tenant_code if site.tenant else "",
                "heatmap_coverage": float(summary.get("heatmap_coverage", 0.0)),
                "attacked_techniques": int(summary.get("attacked_techniques", 0)),
                "covered_techniques": int(summary.get("covered_techniques", 0)),
                "estimated_mttr_seconds": int(remediation.get("estimated_mttr_seconds", 0)),
                "target_mttr_seconds": int(remediation.get("target_mttr_seconds", 0)),
                "sla_status": str(remediation.get("sla_status", "at_risk")),
                "apply_rate": float(remediation.get("apply_rate", 0.0)),
            }
        )
    rows.sort(
        key=lambda row: (
            1 if row["sla_status"] != "pass" else 0,
            1.0 - row["heatmap_coverage"],
            row["estimated_mttr_seconds"],
        ),
        reverse=True,
    )
    passing = len([row for row in rows if row["sla_status"] == "pass"])
    return {
        "status": "completed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "passing_sites": passing,
        "at_risk_sites": max(0, len(rows) - passing),
        "rows": rows,
    }
