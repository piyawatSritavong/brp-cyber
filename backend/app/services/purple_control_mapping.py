from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    BlueDetectionRule,
    BlueLogRefinerPolicy,
    BlueLogRefinerRun,
    BlueManagedResponderPolicy,
    BlueManagedResponderRun,
    BlueThreatLocalizerPolicy,
    BlueThreatLocalizerRun,
    PurpleReportRelease,
    Site,
)
from app.services.site_ops import (
    generate_iso27001_gap_template,
    generate_nist_csf_gap_template,
    generate_purple_executive_scorecard,
)

ISO_FAMILY_LABELS = {
    "A.5": "ISO A.5 Organizational Controls",
    "A.6": "ISO A.6 People Controls",
    "A.7": "ISO A.7 Physical Controls",
    "A.8": "ISO A.8 Technological Controls",
}
NIST_FAMILY_LABELS = {
    "GV": "NIST Govern",
    "ID": "NIST Identify",
    "PR": "NIST Protect",
    "DE": "NIST Detect",
    "RS": "NIST Respond",
    "RC": "NIST Recover",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json(value: str | None) -> dict[str, Any]:
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


def _coverage_status(implemented: int, partial: int, gap: int) -> str:
    if gap <= 0 and implemented > 0:
        return "implemented"
    if implemented > 0 or partial > 0:
        return "partial"
    return "gap"


def _row_counts(controls: list[dict[str, Any]], prefix: str) -> tuple[int, int, int, int, list[str]]:
    matched = [row for row in controls if str(row.get("control_id", "")).upper().startswith(prefix.upper())]
    implemented = len([row for row in matched if str(row.get("status", "")).lower() in {"pass", "implemented"}])
    partial = len([row for row in matched if str(row.get("status", "")).lower() == "partial"])
    gap = len([row for row in matched if str(row.get("status", "")).lower() in {"gap", "missing"}])
    top_gaps = [str(row.get("control_id", "")) for row in matched if str(row.get("status", "")).lower() in {"gap", "missing"}][:5]
    return len(matched), implemented, partial, gap, top_gaps


def _policy_and_evidence_snapshot(db: Session, site_id: UUID) -> dict[str, Any]:
    detection_rules = db.scalars(select(BlueDetectionRule).where(BlueDetectionRule.site_id == site_id)).all()
    managed_policy = db.scalar(select(BlueManagedResponderPolicy).where(BlueManagedResponderPolicy.site_id == site_id))
    log_refiner_policies = db.scalars(select(BlueLogRefinerPolicy).where(BlueLogRefinerPolicy.site_id == site_id)).all()
    localizer_policy = db.scalar(select(BlueThreatLocalizerPolicy).where(BlueThreatLocalizerPolicy.site_id == site_id))
    managed_runs = db.scalars(
        select(BlueManagedResponderRun).where(BlueManagedResponderRun.site_id == site_id).order_by(desc(BlueManagedResponderRun.created_at)).limit(50)
    ).all()
    log_refiner_runs = db.scalars(
        select(BlueLogRefinerRun).where(BlueLogRefinerRun.site_id == site_id).order_by(desc(BlueLogRefinerRun.created_at)).limit(50)
    ).all()
    localizer_runs = db.scalars(
        select(BlueThreatLocalizerRun).where(BlueThreatLocalizerRun.site_id == site_id).order_by(desc(BlueThreatLocalizerRun.created_at)).limit(50)
    ).all()
    report_releases = db.scalars(
        select(PurpleReportRelease).where(PurpleReportRelease.site_id == site_id).order_by(desc(PurpleReportRelease.updated_at)).limit(50)
    ).all()
    return {
        "detection_rules": detection_rules,
        "managed_policy": managed_policy,
        "log_refiner_policies": log_refiner_policies,
        "localizer_policy": localizer_policy,
        "managed_runs": managed_runs,
        "log_refiner_runs": log_refiner_runs,
        "localizer_runs": localizer_runs,
        "report_releases": report_releases,
    }


def _policy_refs(snapshot: dict[str, Any], family: str) -> list[str]:
    refs: list[str] = []
    if family in {"A.5", "GV", "RS", "RC"} and snapshot.get("managed_policy") is not None:
        refs.append("managed_responder_policy")
    if family in {"A.5", "GV", "RC"} and snapshot.get("report_releases"):
        refs.append("report_release_workflow")
    if family in {"A.8", "DE", "RS"} and snapshot.get("detection_rules"):
        refs.append("detection_rules")
    if family in {"A.8", "DE"} and snapshot.get("log_refiner_policies"):
        refs.append("log_refiner_policy")
    if family in {"A.5", "ID", "PR"} and snapshot.get("localizer_policy") is not None:
        refs.append("threat_localizer_policy")
    return refs


def _evidence_refs(snapshot: dict[str, Any], family: str, scorecard: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    if family in {"A.8", "DE"} and snapshot.get("log_refiner_runs"):
        refs.append(f"log_refiner_runs={len(snapshot['log_refiner_runs'])}")
    if family in {"A.5", "A.8", "RS", "RC", "PR"} and snapshot.get("managed_runs"):
        refs.append(f"managed_responder_runs={len(snapshot['managed_runs'])}")
    if family in {"A.5", "ID", "GV"} and snapshot.get("localizer_runs"):
        refs.append(f"threat_localizer_runs={len(snapshot['localizer_runs'])}")
    if family in {"GV", "RS", "RC"} and snapshot.get("report_releases"):
        refs.append(f"report_releases={len(snapshot['report_releases'])}")
    summary = scorecard.get("summary", {}) if isinstance(scorecard, dict) else {}
    remediation = scorecard.get("remediation_sla", {}) if isinstance(scorecard, dict) else {}
    if family in {"DE", "RS"}:
        refs.append(f"heatmap_coverage={summary.get('heatmap_coverage', 0)}")
        refs.append(f"mttr={remediation.get('estimated_mttr_seconds', 0)}")
    return refs


def build_purple_control_family_map(
    db: Session,
    *,
    site_id: UUID,
    framework: str = "combined",
    lookback_runs: int = 30,
    lookback_events: int = 500,
    sla_target_seconds: int = 120,
 ) -> dict[str, Any]:
    site = _site_or_not_found(db, site_id)
    if site is None:
        return {"status": "not_found", "site_id": str(site_id)}
    iso = generate_iso27001_gap_template(db, site_id, limit=200)
    nist = generate_nist_csf_gap_template(db, site_id, limit=200)
    scorecard = generate_purple_executive_scorecard(
        db,
        site_id,
        lookback_runs=lookback_runs,
        lookback_events=lookback_events,
        sla_target_seconds=sla_target_seconds,
    )
    snapshot = _policy_and_evidence_snapshot(db, site_id)
    iso_controls = iso.get("controls", []) if isinstance(iso, dict) else []
    nist_controls = nist.get("controls", []) if isinstance(nist, dict) else []
    rows: list[dict[str, Any]] = []

    normalized_framework = str(framework or "combined").strip().lower()
    if normalized_framework in {"combined", "iso27001"}:
        for family_code, family_label in ISO_FAMILY_LABELS.items():
            total, implemented, partial, gap, top_gaps = _row_counts(iso_controls, family_code)
            rows.append(
                {
                    "framework": "ISO27001",
                    "family_code": family_code,
                    "family_name": family_label,
                    "control_total": total,
                    "implemented_count": implemented,
                    "partial_count": partial,
                    "gap_count": gap,
                    "coverage_status": _coverage_status(implemented, partial, gap),
                    "coverage_pct": round((implemented / total), 4) if total else 0.0,
                    "policy_refs": _policy_refs(snapshot, family_code),
                    "evidence_refs": _evidence_refs(snapshot, family_code, scorecard),
                    "top_gaps": top_gaps,
                }
            )
    if normalized_framework in {"combined", "nist_csf"}:
        for family_code, family_label in NIST_FAMILY_LABELS.items():
            total, implemented, partial, gap, top_gaps = _row_counts(nist_controls, family_code)
            rows.append(
                {
                    "framework": "NIST_CSF",
                    "family_code": family_code,
                    "family_name": family_label,
                    "control_total": total,
                    "implemented_count": implemented,
                    "partial_count": partial,
                    "gap_count": gap,
                    "coverage_status": _coverage_status(implemented, partial, gap),
                    "coverage_pct": round((implemented / total), 4) if total else 0.0,
                    "policy_refs": _policy_refs(snapshot, family_code),
                    "evidence_refs": _evidence_refs(snapshot, family_code, scorecard),
                    "top_gaps": top_gaps,
                }
            )
    rows.sort(key=lambda row: (row["framework"], row["family_code"]))
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "framework": normalized_framework,
        "generated_at": _now(),
        "summary": {
            "family_count": len(rows),
            "implemented_family_count": len([row for row in rows if row["coverage_status"] == "implemented"]),
            "partial_family_count": len([row for row in rows if row["coverage_status"] == "partial"]),
            "gap_family_count": len([row for row in rows if row["coverage_status"] == "gap"]),
            "heatmap_coverage": (scorecard.get("summary", {}) if isinstance(scorecard, dict) else {}).get("heatmap_coverage", 0),
            "report_release_count": len(snapshot.get("report_releases", [])),
        },
        "rows": rows,
    }


def export_purple_control_family_map(
    db: Session,
    *,
    site_id: UUID,
    framework: str = "combined",
    export_format: str = "markdown",
 ) -> dict[str, Any]:
    result = build_purple_control_family_map(db, site_id=site_id, framework=framework)
    if result.get("status") != "ok":
        return result
    site_code = str(result.get("site_code", "site"))
    rows = result.get("rows", []) if isinstance(result, dict) else []
    summary = result.get("summary", {}) if isinstance(result, dict) else {}
    normalized = str(export_format or "markdown").strip().lower()
    if normalized == "json":
        content = json.dumps(result, ensure_ascii=True, indent=2)
        filename = f"{site_code}-control-family-map.json"
    elif normalized == "csv":
        lines = ["framework,family_code,family_name,coverage_status,coverage_pct,control_total,implemented_count,partial_count,gap_count,policy_refs,evidence_refs,top_gaps"]
        for row in rows:
            lines.append(
                ",".join(
                    [
                        str(row.get("framework", "")),
                        str(row.get("family_code", "")),
                        str(row.get("family_name", "")).replace(",", ";"),
                        str(row.get("coverage_status", "")),
                        str(row.get("coverage_pct", 0)),
                        str(row.get("control_total", 0)),
                        str(row.get("implemented_count", 0)),
                        str(row.get("partial_count", 0)),
                        str(row.get("gap_count", 0)),
                        ";".join(row.get("policy_refs", [])),
                        ";".join(row.get("evidence_refs", [])),
                        ";".join(row.get("top_gaps", [])),
                    ]
                )
            )
        content = "\n".join(lines)
        filename = f"{site_code}-control-family-map.csv"
        normalized = "csv"
    else:
        lines = [
            f"# Control Family Map - {site_code}",
            "",
            f"- generated_at: {result.get('generated_at', '')}",
            f"- family_count: {summary.get('family_count', 0)}",
            f"- implemented_families: {summary.get('implemented_family_count', 0)}",
            f"- partial_families: {summary.get('partial_family_count', 0)}",
            f"- gap_families: {summary.get('gap_family_count', 0)}",
            "",
        ]
        for row in rows:
            lines.append(f"## {row.get('framework')} {row.get('family_code')} {row.get('family_name')}")
            lines.append(
                f"- coverage={row.get('coverage_status')} ({row.get('coverage_pct')}) controls={row.get('control_total')} implemented={row.get('implemented_count')} partial={row.get('partial_count')} gap={row.get('gap_count')}"
            )
            lines.append(f"- policy_refs: {', '.join(row.get('policy_refs', [])) or 'none'}")
            lines.append(f"- evidence_refs: {', '.join(row.get('evidence_refs', [])) or 'none'}")
            lines.append(f"- top_gaps: {', '.join(row.get('top_gaps', [])) or 'none'}")
            lines.append("")
        content = "\n".join(lines)
        filename = f"{site_code}-control-family-map.md"
        normalized = "markdown"
    return {
        "status": "ok",
        "site_id": result["site_id"],
        "site_code": site_code,
        "export": {
            "export_type": "control_family_map",
            "export_format": normalized,
            "filename": filename,
            "generated_at": result.get("generated_at", ""),
            "summary": summary,
            "rows": rows,
            "content": content,
        },
    }
