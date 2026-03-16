from __future__ import annotations

import base64
import io
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from xml.sax.saxutils import escape as xml_escape
import zipfile

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import BlueEventLog, PurpleInsightReport, PurpleReportRelease, Site
from app.services.purple_roi_dashboard import _render_pdf_bytes, _safe_filename_part
from app.services.site_ops import (
    generate_iso27001_gap_template,
    generate_nist_csf_gap_template,
    generate_purple_executive_scorecard,
)

TEMPLATE_PACKS: list[dict[str, Any]] = [
    {
        "pack_code": "incident_company_standard",
        "kind": "incident_report",
        "display_name": "Company Standard Incident Pack",
        "audience": "security_ops",
        "output_profile": "company",
        "description": "แพ็ก incident report สำหรับใช้งานภายในบริษัทและส่งให้ทีมปฏิบัติการ",
        "sections": ["executive_summary", "incident_timeline", "impact", "recommended_actions", "follow_up"],
    },
    {
        "pack_code": "incident_board_brief",
        "kind": "incident_report",
        "display_name": "Board Brief Incident Pack",
        "audience": "board",
        "output_profile": "executive",
        "description": "สรุป incident สำหรับผู้บริหาร เน้น risk, business impact, และ decision items",
        "sections": ["board_statement", "business_impact", "risk_signal", "decision_items"],
    },
    {
        "pack_code": "incident_nca_th",
        "kind": "incident_report",
        "display_name": "Thai Regulator Incident Pack",
        "audience": "regulator",
        "output_profile": "nca_th",
        "description": "incident report ภาษาไทยแนวหน่วยงานกำกับ ใช้เป็น baseline ก่อนจัดทำเอกสารส่งจริง",
        "sections": ["incident_summary", "affected_scope", "evidence_chain", "containment", "reporting_notes"],
    },
    {
        "pack_code": "regulated_nca_th",
        "kind": "regulated_report",
        "display_name": "NCA Thailand Regulated Output",
        "audience": "regulator",
        "output_profile": "nca_th",
        "description": "แพ็ก baseline สำหรับส่งต่อทีม compliance/regulatory พร้อม incident และ control gaps ที่เกี่ยวข้อง",
        "sections": ["regulatory_summary", "incident_obligation", "control_gaps", "evidence_attachments", "submission_notes"],
    },
    {
        "pack_code": "regulated_iso27001_audit",
        "kind": "regulated_report",
        "display_name": "ISO 27001 Audit Output",
        "audience": "audit",
        "output_profile": "iso27001",
        "description": "แพ็ก baseline สำหรับ audit/compliance โดยใช้ ISO gap evidence ล่าสุด",
        "sections": ["audit_summary", "control_status", "evidence_snapshot", "remediation_plan"],
    },
    {
        "pack_code": "regulated_nist_csf_ops",
        "kind": "regulated_report",
        "display_name": "NIST CSF Operations Output",
        "audience": "governance",
        "output_profile": "nist_csf",
        "description": "แพ็ก baseline สำหรับ governance review ตาม NIST CSF 2.0",
        "sections": ["framework_summary", "coverage_findings", "operational_gaps", "next_actions"],
    },
]


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


def _normalize_kind(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized[:64]


def _find_template_pack(pack_code: str, *, expected_kind: str = "") -> dict[str, Any] | None:
    normalized_code = str(pack_code or "").strip()
    normalized_kind = _normalize_kind(expected_kind)
    for row in TEMPLATE_PACKS:
        if row["pack_code"] != normalized_code:
            continue
        if normalized_kind and row["kind"] != normalized_kind:
            continue
        return row
    return None


def _render_docx_bytes(title: str, sections: list[dict[str, Any]], footer_label: str) -> bytes:
    lines: list[str] = [title, ""]
    for section in sections:
        lines.append(str(section.get("section", "")))
        for item in section.get("content", []):
            lines.append(f"- {item}")
        lines.append("")
    if footer_label:
        lines.append(footer_label)

    paragraphs = []
    for line in lines:
        safe = xml_escape(str(line or ""))
        paragraphs.append(
            "<w:p><w:r><w:t xml:space=\"preserve\">"
            f"{safe}"
            "</w:t></w:r></w:p>"
        )
    document_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:wpc=\"http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas\" "
        "xmlns:mc=\"http://schemas.openxmlformats.org/markup-compatibility/2006\" "
        "xmlns:o=\"urn:schemas-microsoft-com:office:office\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:m=\"http://schemas.openxmlformats.org/officeDocument/2006/math\" "
        "xmlns:v=\"urn:schemas-microsoft-com:vml\" "
        "xmlns:wp14=\"http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing\" "
        "xmlns:wp=\"http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing\" "
        "xmlns:w10=\"urn:schemas-microsoft-com:office:word\" "
        "xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\" "
        "xmlns:w14=\"http://schemas.microsoft.com/office/word/2010/wordml\" "
        "xmlns:wpg=\"http://schemas.microsoft.com/office/word/2010/wordprocessingGroup\" "
        "xmlns:wpi=\"http://schemas.microsoft.com/office/word/2010/wordprocessingInk\" "
        "xmlns:wne=\"http://schemas.microsoft.com/office/word/2006/wordml\" "
        "xmlns:wps=\"http://schemas.microsoft.com/office/word/2010/wordprocessingShape\" mc:Ignorable=\"w14 wp14\">"
        f"<w:body>{''.join(paragraphs)}<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/><w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\"/></w:sectPr></w:body></w:document>"
    )
    content_types = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
        "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        "<Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>"
        "</Types>"
    )
    rels = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>"
        "</Relationships>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def _build_binary_export(
    *,
    title: str,
    sections: list[dict[str, Any]],
    footer_label: str,
    export_type: str,
    site_code: str,
    pack_code: str,
    export_format: str,
) -> dict[str, Any]:
    normalized = str(export_format or "").strip().lower()
    if normalized == "pdf":
        binary = _render_pdf_bytes(title, sections, footer_label)
        mime_type = "application/pdf"
        filename = f"{site_code}-{_safe_filename_part(pack_code)}-{_safe_filename_part(export_type)}.pdf"
    else:
        binary = _render_docx_bytes(title, sections, footer_label)
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"{site_code}-{_safe_filename_part(pack_code)}-{_safe_filename_part(export_type)}.docx"
        normalized = "docx"
    return {
        "export_format": normalized,
        "renderer": "native_binary",
        "mime_type": mime_type,
        "filename": filename,
        "byte_size": len(binary),
        "content_base64": base64.b64encode(binary).decode("ascii"),
    }


def _release_row(row: PurpleReportRelease) -> dict[str, Any]:
    return {
        "release_id": str(row.id),
        "site_id": str(row.site_id),
        "report_kind": row.report_kind,
        "export_format": row.export_format,
        "title": row.title,
        "filename": row.filename,
        "status": row.status,
        "requested_by": row.requested_by,
        "approved_by": row.approved_by,
        "note": row.note,
        "payload": _safe_json_dict(row.payload_json),
        "created_at": _safe_iso(row.created_at),
        "updated_at": _safe_iso(row.updated_at),
    }


def list_purple_export_template_packs(*, kind: str = "", audience: str = "") -> dict[str, Any]:
    normalized_kind = _normalize_kind(kind)
    normalized_audience = str(audience or "").strip().lower()
    rows = []
    for row in TEMPLATE_PACKS:
        if normalized_kind and row["kind"] != normalized_kind:
            continue
        if normalized_audience and row["audience"] != normalized_audience:
            continue
        rows.append(row)
    return {"status": "ok", "count": len(rows), "rows": rows}


def _site_or_not_found(db: Session, site_id: UUID) -> Site | None:
    return db.get(Site, site_id)


def export_purple_mitre_heatmap(
    db: Session,
    *,
    site_id: UUID,
    export_format: str = "markdown",
    title_override: str = "",
    include_recommendations: bool = True,
    lookback_runs: int = 30,
    lookback_events: int = 500,
    sla_target_seconds: int = 120,
) -> dict[str, Any]:
    site = _site_or_not_found(db, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    scorecard = generate_purple_executive_scorecard(
        db,
        site_id,
        lookback_runs=lookback_runs,
        lookback_events=lookback_events,
        sla_target_seconds=sla_target_seconds,
    )
    rows = scorecard.get("heatmap", []) if isinstance(scorecard, dict) else []
    summary = scorecard.get("summary", {}) if isinstance(scorecard, dict) else {}
    remediation = scorecard.get("remediation_sla", {}) if isinstance(scorecard, dict) else {}
    title = title_override.strip() or f"MITRE ATT&CK Heatmap Export - {site.display_name}"
    generated_at = datetime.now(timezone.utc).isoformat()
    format_name = str(export_format or "markdown").strip().lower()

    if format_name == "csv":
        header = "technique_id,detection_status,attack_count,mitigation_time_seconds,sla_status,recommendation"
        lines = [header]
        for row in rows:
            lines.append(
                ",".join(
                    [
                        str(row.get("technique_id", "")),
                        str(row.get("detection_status", "")),
                        str(row.get("attack_count", 0)),
                        str(row.get("mitigation_time_seconds", "")),
                        str(row.get("sla_status", "")),
                        str(row.get("recommendation", "")).replace(",", ";"),
                    ]
                )
            )
        content = "\n".join(lines)
    elif format_name == "attack_layer_json":
        content = json.dumps(
            {
                "version": "4.5",
                "name": title,
                "domain": "enterprise-attack",
                "description": f"BRP-generated export for {site.site_code}",
                "techniques": [
                    {
                        "techniqueID": str(row.get("technique_id", "")),
                        "score": 100 if row.get("detection_status") == "covered" else (60 if row.get("detection_status") == "partial" else 20),
                        "comment": str(row.get("recommendation", "")),
                    }
                    for row in rows
                ],
            },
            ensure_ascii=True,
            indent=2,
        )
    else:
        lines = [
            f"# {title}",
            "",
            f"- site: {site.site_code}",
            f"- generated_at: {generated_at}",
            f"- attacked_techniques: {summary.get('attacked_techniques', 0)}",
            f"- covered_techniques: {summary.get('covered_techniques', 0)}",
            f"- heatmap_coverage: {summary.get('heatmap_coverage', 0)}",
            f"- remediation_sla_status: {remediation.get('sla_status', 'unknown')}",
            "",
            "## Techniques",
        ]
        for row in rows:
            line = (
                f"- {row.get('technique_id')} [{row.get('detection_status')}] "
                f"attack_count={row.get('attack_count')} mitigation={row.get('mitigation_time_seconds')}s"
            )
            if include_recommendations:
                line += f" recommendation={row.get('recommendation', '')}"
            lines.append(line)
        content = "\n".join(lines)
        format_name = "markdown"

    filename_ext = "md" if format_name == "markdown" else ("csv" if format_name == "csv" else "json")
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "export": {
            "export_type": "mitre_heatmap",
            "export_format": format_name,
            "title": title,
            "filename": f"{site.site_code}-mitre-heatmap.{filename_ext}",
            "generated_at": generated_at,
            "summary": summary,
            "remediation_sla": remediation,
            "rows": rows,
            "content": content,
        },
    }


def _latest_purple_report(db: Session, site_id: UUID) -> PurpleInsightReport | None:
    return db.scalar(
        select(PurpleInsightReport)
        .where(PurpleInsightReport.site_id == site_id)
        .order_by(desc(PurpleInsightReport.created_at))
        .limit(1)
    )


def _recent_blue_events(db: Session, site_id: UUID, limit: int) -> list[BlueEventLog]:
    return db.scalars(
        select(BlueEventLog)
        .where(BlueEventLog.site_id == site_id)
        .order_by(desc(BlueEventLog.created_at))
        .limit(max(1, min(limit, 200)))
    ).all()


def export_purple_incident_report(
    db: Session,
    *,
    site_id: UUID,
    template_pack: str = "incident_company_standard",
    export_format: str = "markdown",
    title_override: str = "",
    include_regulatory_mapping: bool = True,
    blue_event_limit: int = 20,
) -> dict[str, Any]:
    site = _site_or_not_found(db, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    pack = _find_template_pack(template_pack, expected_kind="incident_report")
    if not pack:
        return {"status": "template_pack_not_found", "site_id": str(site.id), "template_pack": template_pack}
    latest_report = _latest_purple_report(db, site.id)
    blue_rows = _recent_blue_events(db, site.id, blue_event_limit)
    high_count = len([row for row in blue_rows if row.ai_severity == "high"])
    medium_count = len([row for row in blue_rows if row.ai_severity == "medium"])
    summary = latest_report.summary if latest_report else "ยังไม่มี Purple insight ล่าสุด"
    title = title_override.strip() or f"{pack['display_name']} - {site.display_name}"
    generated_at = datetime.now(timezone.utc).isoformat()
    sections = [
        {
            "section": "Executive Summary",
            "content": [
                summary,
                f"high_events={high_count} medium_events={medium_count} total_events={len(blue_rows)}",
            ],
        },
        {
            "section": "Recent Event Timeline",
            "content": [
                f"{row.created_at.isoformat() if row.created_at else ''} [{row.ai_severity}] {row.event_type} from {row.source_ip} -> {row.ai_recommendation}"
                for row in blue_rows[:8]
            ]
            or ["No recent blue events."],
        },
        {
            "section": "Containment and Recommendations",
            "content": [
                f"{row.event_type}: {row.ai_recommendation} status={row.status} action={row.action_taken or 'none'}"
                for row in blue_rows[:5]
            ]
            or ["No containment recommendations available."],
        },
    ]
    if include_regulatory_mapping:
        sections.append(
            {
                "section": "Regulatory Mapping Notes",
                "content": [
                    "ใช้ baseline นี้เพื่อให้ทีม compliance ปรับข้อความให้ตรงนโยบายองค์กรและข้อกำหนดหน่วยงานกำกับก่อนส่งจริง",
                    f"template_pack={pack['pack_code']} output_profile={pack['output_profile']}",
                ],
            }
        )

    normalized_format = str(export_format or "markdown").strip().lower()
    binary_export: dict[str, Any] = {}
    if normalized_format in {"pdf", "docx"}:
        binary_export = _build_binary_export(
            title=title,
            sections=sections,
            footer_label=str(pack.get("display_name", "")),
            export_type="incident-report",
            site_code=site.site_code,
            pack_code=str(pack["pack_code"]),
            export_format=normalized_format,
        )
        content = ""
        normalized_format = binary_export["export_format"]
    elif normalized_format == "json":
        content = json.dumps({"title": title, "sections": sections, "template_pack": pack}, ensure_ascii=True, indent=2)
    else:
        lines = [f"# {title}", "", f"- template_pack: {pack['pack_code']}", f"- generated_at: {generated_at}", ""]
        for section in sections:
            lines.append(f"## {section['section']}")
            for item in section["content"]:
                lines.append(f"- {item}")
            lines.append("")
        content = "\n".join(lines)
        normalized_format = "markdown"
    filename_ext = "json" if normalized_format == "json" else "md"
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "export": {
            "export_type": "incident_report",
            "export_format": normalized_format,
            "template_pack": pack,
            "title": title,
            "filename": binary_export.get("filename", f"{site.site_code}-{pack['pack_code']}.{filename_ext}"),
            "generated_at": generated_at,
            "sections": sections,
            "content": content,
            "renderer": binary_export.get("renderer", "text"),
            "mime_type": binary_export.get("mime_type", "text/plain"),
            "byte_size": binary_export.get("byte_size", len(content.encode("utf-8"))),
            "content_base64": binary_export.get("content_base64", ""),
        },
    }


def export_purple_regulated_report(
    db: Session,
    *,
    site_id: UUID,
    template_pack: str = "regulated_nca_th",
    export_format: str = "markdown",
    title_override: str = "",
    include_incident_context: bool = True,
) -> dict[str, Any]:
    site = _site_or_not_found(db, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    pack = _find_template_pack(template_pack, expected_kind="regulated_report")
    if not pack:
        return {"status": "template_pack_not_found", "site_id": str(site.id), "template_pack": template_pack}

    iso_gap = generate_iso27001_gap_template(db, site.id, limit=200)
    nist_gap = generate_nist_csf_gap_template(db, site.id, limit=200)
    latest_report = _latest_purple_report(db, site.id)
    summary = latest_report.summary if latest_report else "ยังไม่มี Purple insight ล่าสุด"

    sections = [
        {
            "section": "Regulatory Summary",
            "content": [
                f"profile={pack['output_profile']}",
                f"generated_at={datetime.now(timezone.utc).isoformat()}",
                summary,
            ],
        },
        {
            "section": "ISO 27001 Gap Snapshot",
            "content": [
                f"{control['control_id']} [{control['status']}] {control['control_name']}"
                for control in iso_gap.get("controls", [])[:4]
            ]
            or ["No ISO controls available."],
        },
        {
            "section": "NIST CSF Gap Snapshot",
            "content": [
                f"{control['control_id']} [{control['status']}] {control['control_name']}"
                for control in nist_gap.get("controls", [])[:4]
            ]
            or ["No NIST controls available."],
        },
    ]
    if include_incident_context:
        blue_rows = _recent_blue_events(db, site.id, 10)
        sections.append(
            {
                "section": "Incident Context",
                "content": [
                    f"{row.event_type} [{row.ai_severity}] {row.source_ip} -> {row.ai_recommendation}"
                    for row in blue_rows[:5]
                ]
                or ["No recent incident context."],
            }
        )
    sections.append(
        {
            "section": "Submission Notes",
            "content": [
                "เป็น baseline output สำหรับทีม compliance/regulatory ใช้ต่อยอดก่อนส่งจริง",
                "ควรแนบ evidence chain, ticket, และ approval records ตามนโยบายองค์กร",
            ],
        }
    )
    title = title_override.strip() or f"{pack['display_name']} - {site.display_name}"
    generated_at = datetime.now(timezone.utc).isoformat()
    normalized_format = str(export_format or "markdown").strip().lower()
    binary_export: dict[str, Any] = {}
    if normalized_format in {"pdf", "docx"}:
        binary_export = _build_binary_export(
            title=title,
            sections=sections,
            footer_label=str(pack.get("display_name", "")),
            export_type="regulated-report",
            site_code=site.site_code,
            pack_code=str(pack["pack_code"]),
            export_format=normalized_format,
        )
        content = ""
        normalized_format = binary_export["export_format"]
    elif normalized_format == "json":
        content = json.dumps({"title": title, "sections": sections, "template_pack": pack}, ensure_ascii=True, indent=2)
    else:
        lines = [f"# {title}", "", f"- output_profile: {pack['output_profile']}", f"- generated_at: {generated_at}", ""]
        for section in sections:
            lines.append(f"## {section['section']}")
            for item in section["content"]:
                lines.append(f"- {item}")
            lines.append("")
        content = "\n".join(lines)
        normalized_format = "markdown"
    filename_ext = "json" if normalized_format == "json" else "md"
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "export": {
            "export_type": "regulated_report",
            "export_format": normalized_format,
            "template_pack": pack,
            "title": title,
            "filename": binary_export.get("filename", f"{site.site_code}-{pack['pack_code']}.{filename_ext}"),
            "generated_at": generated_at,
            "sections": sections,
            "content": content,
            "renderer": binary_export.get("renderer", "text"),
            "mime_type": binary_export.get("mime_type", "text/plain"),
            "byte_size": binary_export.get("byte_size", len(content.encode("utf-8"))),
            "content_base64": binary_export.get("content_base64", ""),
        },
    }


def request_purple_report_release(
    db: Session,
    *,
    site_id: UUID,
    report_kind: str,
    export_format: str,
    title: str,
    filename: str,
    payload: dict[str, Any],
    requester: str = "purple_ai",
    note: str = "",
) -> dict[str, Any]:
    site = _site_or_not_found(db, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    row = PurpleReportRelease(
        site_id=site.id,
        report_kind=str(report_kind or "incident_report")[:64],
        export_format=str(export_format or "pdf")[:32],
        title=str(title or "")[:255],
        filename=str(filename or "")[:255],
        status="pending_approval",
        requested_by=str(requester or "purple_ai")[:128],
        approved_by="",
        note=str(note or "")[:2000],
        payload_json=json.dumps(payload or {}, ensure_ascii=True),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "ok", "release": _release_row(row)}


def review_purple_report_release(
    db: Session,
    *,
    release_id: UUID,
    approve: bool,
    approver: str,
    note: str = "",
) -> dict[str, Any]:
    row = db.get(PurpleReportRelease, release_id)
    if row is None:
        return {"status": "not_found"}
    if row.status not in {"pending_approval"}:
        return {"status": "no_op", "release": _release_row(row)}
    row.status = "approved" if approve else "rejected"
    row.approved_by = str(approver or "security_lead")[:128]
    row.note = str(note or "")[:2000]
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return {"status": row.status, "release": _release_row(row)}


def list_purple_report_releases(db: Session, *, site_id: UUID, limit: int = 20) -> dict[str, Any]:
    site = _site_or_not_found(db, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    rows = db.scalars(
        select(PurpleReportRelease)
        .where(PurpleReportRelease.site_id == site.id)
        .order_by(desc(PurpleReportRelease.updated_at))
        .limit(max(1, min(limit, 200)))
    ).all()
    return {"status": "ok", "count": len(rows), "rows": [_release_row(row) for row in rows]}
