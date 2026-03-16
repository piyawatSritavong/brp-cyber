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

from app.db.models import (
    BlueDetectionRule,
    BlueEventLog,
    PurpleInsightReport,
    PurpleRoiDashboardSnapshot,
    RedExploitPathRun,
    RedScanRun,
    Site,
    Tenant,
)

ROI_TEMPLATE_PACKS: list[dict[str, Any]] = [
    {
        "pack_code": "roi_board_minimal",
        "display_name": "Executive Minimal Board Pack",
        "audience": "board",
        "description": "แพ็กสรุปผู้บริหารแบบกระชับ เน้นตัวเลขสำคัญและ portfolio overview",
        "layout_style": "minimal",
        "accent_hex": "F76C45",
        "cover_label": "Board Executive Review",
        "footer_label": "BRP Cyber ROI",
        "section_order": ["Executive Summary", "Board Metrics", "Trend Summary", "Portfolio Roll-up"],
    },
    {
        "pack_code": "roi_risk_committee",
        "display_name": "Risk Committee Deep Dive",
        "audience": "risk_committee",
        "description": "แพ็กสำหรับคณะกรรมการความเสี่ยง เน้น trend, high-risk signal, และ value drivers",
        "layout_style": "risk_committee",
        "accent_hex": "C84D2D",
        "cover_label": "Risk Committee Review",
        "footer_label": "Risk Posture Snapshot",
        "section_order": ["Executive Summary", "Risk Signals", "Board Metrics", "Trend Summary", "Top Value Drivers"],
    },
    {
        "pack_code": "roi_mssp_monthly",
        "display_name": "MSSP Monthly Service Review",
        "audience": "mssp",
        "description": "แพ็กสำหรับ MSSP/partner review เน้น portfolio roll-up, service value, และ trend ต่อ site",
        "layout_style": "mssp",
        "accent_hex": "DD6E42",
        "cover_label": "Monthly Service Review",
        "footer_label": "Managed Security ROI",
        "section_order": ["Executive Summary", "Portfolio Roll-up", "Board Metrics", "Trend Summary", "Top Value Drivers"],
    },
]


def _as_json(value: dict[str, Any]) -> str:
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


def _safe_iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def _safe_filename_part(value: str) -> str:
    sanitized = "".join(char.lower() if char.isalnum() else "-" for char in str(value or "").strip())
    while "--" in sanitized:
        sanitized = sanitized.replace("--", "-")
    return sanitized.strip("-") or "export"


def _ascii_safe(value: Any) -> str:
    text = str(value or "")
    return text.encode("ascii", "replace").decode("ascii")


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _chunk_lines(lines: list[str], per_page: int) -> list[list[str]]:
    if not lines:
        return [["No content available."]]
    return [lines[index : index + per_page] for index in range(0, len(lines), per_page)]


def _find_roi_template_pack(pack_code: str) -> dict[str, Any]:
    normalized = str(pack_code or "").strip()
    for row in ROI_TEMPLATE_PACKS:
        if row["pack_code"] == normalized:
            return row
    return ROI_TEMPLATE_PACKS[0]


def list_purple_roi_template_packs(*, audience: str = "") -> dict[str, Any]:
    audience_value = str(audience or "").strip().lower()
    rows = []
    for row in ROI_TEMPLATE_PACKS:
        if audience_value and row["audience"] != audience_value:
            continue
        rows.append(row)
    return {"status": "ok", "count": len(rows), "rows": rows}


def _snapshot_row(row: PurpleRoiDashboardSnapshot) -> dict[str, Any]:
    return {
        "snapshot_id": str(row.id),
        "site_id": str(row.site_id),
        "lookback_days": row.lookback_days,
        "status": row.status,
        "summary": _safe_json_dict(row.summary_json),
        "details": _safe_json_dict(row.details_json),
        "created_at": _safe_iso(row.created_at),
    }


def _metric_number(snapshot: dict[str, Any], key: str) -> float:
    summary = snapshot.get("summary", {})
    board_metrics = summary.get("board_metrics", {}) if isinstance(summary, dict) else {}
    value = board_metrics.get(key, 0)
    try:
        return float(value)
    except Exception:
        return 0.0


def _trend_row(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "snapshot_id": snapshot.get("snapshot_id", ""),
        "created_at": snapshot.get("created_at", ""),
        "validated_findings": _metric_number(snapshot, "validated_findings"),
        "high_risk_findings": _metric_number(snapshot, "high_risk_findings"),
        "automation_coverage_pct": _metric_number(snapshot, "automation_coverage_pct"),
        "noise_reduction_pct": _metric_number(snapshot, "noise_reduction_pct"),
        "estimated_manual_effort_saved_usd": _metric_number(snapshot, "estimated_manual_effort_saved_usd"),
    }


def _resolve_tenant(db: Session, site: Site) -> Tenant | None:
    tenant = getattr(site, "tenant", None)
    if tenant is not None:
        return tenant
    tenant_id = getattr(site, "tenant_id", None)
    if tenant_id:
        return db.get(Tenant, tenant_id)
    return None


def _build_roi_section_map(
    *,
    summary: dict[str, Any],
    details: dict[str, Any],
    trend: dict[str, Any],
    portfolio: dict[str, Any],
    include_portfolio: bool,
) -> dict[str, list[str]]:
    board_metrics = summary.get("board_metrics", {}) if isinstance(summary, dict) else {}
    section_map: dict[str, list[str]] = {
        "Executive Summary": [
            str(summary.get("headline_th", "")),
            str(summary.get("board_statement_th", "")),
        ],
        "Board Metrics": [
            f"validated_findings={board_metrics.get('validated_findings', 0)}",
            f"high_risk_findings={board_metrics.get('high_risk_findings', 0)}",
            f"automation_coverage_pct={board_metrics.get('automation_coverage_pct', 0)}",
            f"noise_reduction_pct={board_metrics.get('noise_reduction_pct', 0)}",
            f"estimated_manual_effort_saved_usd={board_metrics.get('estimated_manual_effort_saved_usd', 0)}",
        ],
        "Trend Summary": [
            f"trend_points={trend.get('summary', {}).get('trend_points', 0)}",
            f"direction={trend.get('summary', {}).get('direction', 'unknown')}",
            f"validated_findings_delta={trend.get('summary', {}).get('validated_findings_delta', 0)}",
            f"automation_coverage_delta_pct={trend.get('summary', {}).get('automation_coverage_delta_pct', 0)}",
            f"noise_reduction_delta_pct={trend.get('summary', {}).get('noise_reduction_delta_pct', 0)}",
            f"estimated_manual_effort_saved_delta_usd={trend.get('summary', {}).get('estimated_manual_effort_saved_delta_usd', 0)}",
        ],
        "Top Value Drivers": [
            f"{driver.get('driver', '')}: {driver.get('statement_th', '')}"
            for driver in details.get("top_value_drivers", [])[:5]
        ]
        or ["No value driver summary available."],
        "Risk Signals": [
            f"high_risk_findings={board_metrics.get('high_risk_findings', 0)}",
            f"suspicious_events={board_metrics.get('suspicious_events', 0)}",
            f"auto_mitigated_events={board_metrics.get('auto_mitigated_events', 0)}",
            f"detection_rules={board_metrics.get('detection_rules', 0)}",
            f"purple_reports={board_metrics.get('purple_reports', 0)}",
        ],
    }
    if include_portfolio:
        section_map["Portfolio Roll-up"] = [
            f"sites_with_snapshots={portfolio.get('summary', {}).get('sites_with_snapshots', 0)}",
            f"total_validated_findings={portfolio.get('summary', {}).get('total_validated_findings', 0)}",
            f"total_estimated_manual_effort_saved_usd={portfolio.get('summary', {}).get('total_estimated_manual_effort_saved_usd', 0)}",
            f"average_automation_coverage_pct={portfolio.get('summary', {}).get('average_automation_coverage_pct', 0)}",
            f"average_noise_reduction_pct={portfolio.get('summary', {}).get('average_noise_reduction_pct', 0)}",
            f"highest_value_site_code={portfolio.get('summary', {}).get('highest_value_site_code', '')}",
        ]
    return section_map


def _render_pdf_bytes(title: str, sections: list[dict[str, Any]], footer_label: str) -> bytes:
    lines: list[str] = [_ascii_safe(title), ""]
    for section in sections:
        lines.append(_ascii_safe(section["section"]))
        for item in section["content"]:
            lines.append(f"- {_ascii_safe(item)}")
        lines.append("")
    if footer_label:
        lines.append(_ascii_safe(footer_label))

    pages = _chunk_lines(lines, 42)
    objects: list[bytes] = []

    def _append_object(payload: str) -> int:
        objects.append(payload.encode("latin-1"))
        return len(objects)

    font_id = _append_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    content_ids: list[int] = []
    placeholder_pages_id = len(objects) + 1

    for page_lines in pages:
        content_lines = ["BT", "/F1 11 Tf", "50 780 Td", "14 TL"]
        for index, line in enumerate(page_lines):
            escaped = _escape_pdf_text(line)
            if index == 0:
                content_lines.append(f"({escaped}) Tj")
            else:
                content_lines.append(f"T* ({escaped}) Tj")
        content_lines.append("ET")
        stream = "\n".join(content_lines).encode("latin-1")
        content_id = _append_object(f"<< /Length {len(stream)} >>\nstream\n{stream.decode('latin-1')}\nendstream")
        content_ids.append(content_id)
        page_id = _append_object(
            f"<< /Type /Page /Parent {placeholder_pages_id} 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_id = _append_object(f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>")
    catalog_id = _append_object(f"<< /Type /Catalog /Pages {pages_id} 0 R >>")

    output = io.BytesIO()
    output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, payload in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode("latin-1"))
        if index == pages_id:
            kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
            payload = f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode("latin-1")
        elif index in page_ids:
            content_index = page_ids.index(index)
            payload = (
                f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_ids[content_index]} 0 R >>"
            ).encode("latin-1")
        output.write(payload)
        output.write(b"\nendobj\n")
    xref_offset = output.tell()
    output.write(f"xref\n0 {len(objects)+1}\n".encode("latin-1"))
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
    output.write(
        (
            f"trailer\n<< /Size {len(objects)+1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode("latin-1")
    )
    return output.getvalue()


def _ppt_text_runs(lines: list[str]) -> str:
    paragraphs = []
    for line in lines:
        safe = xml_escape(str(line or ""))
        paragraphs.append(
            "<a:p><a:r><a:rPr lang=\"en-US\" sz=\"1800\"/><a:t>"
            + safe
            + "</a:t></a:r></a:p>"
        )
    return "".join(paragraphs or ["<a:p><a:endParaRPr lang=\"en-US\"/></a:p>"])


def _ppt_slide_xml(title: str, bullets: list[str]) -> str:
    title_runs = _ppt_text_runs([title])
    bullet_runs = _ppt_text_runs(bullets)
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<p:sld xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">"
        "<p:cSld><p:spTree>"
        "<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
        "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/><a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
        "<p:sp><p:nvSpPr><p:cNvPr id=\"2\" name=\"Title\"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>"
        "<p:spPr><a:xfrm><a:off x=\"457200\" y=\"228600\"/><a:ext cx=\"8229600\" cy=\"914400\"/></a:xfrm></p:spPr>"
        "<p:txBody><a:bodyPr/><a:lstStyle/>"
        + title_runs
        + "</p:txBody></p:sp>"
        "<p:sp><p:nvSpPr><p:cNvPr id=\"3\" name=\"Content\"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>"
        "<p:spPr><a:xfrm><a:off x=\"457200\" y=\"1371600\"/><a:ext cx=\"8229600\" cy=\"4572000\"/></a:xfrm></p:spPr>"
        "<p:txBody><a:bodyPr wrap=\"square\"/><a:lstStyle/>"
        + bullet_runs
        + "</p:txBody></p:sp>"
        "</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"
    )


def _render_pptx_bytes(title: str, slides: list[dict[str, Any]], footer_label: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        slide_names = [f"ppt/slides/slide{index}.xml" for index in range(1, len(slides) + 1)]
        archive.writestr(
            "[Content_Types].xml",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
                "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
                "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
                "<Override PartName=\"/ppt/presentation.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml\"/>"
                "<Override PartName=\"/ppt/slideMasters/slideMaster1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml\"/>"
                "<Override PartName=\"/ppt/slideLayouts/slideLayout1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml\"/>"
                "<Override PartName=\"/ppt/theme/theme1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.theme+xml\"/>"
                + "".join(
                    f"<Override PartName=\"/{name}\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slide+xml\"/>"
                    for name in slide_names
                )
                + "<Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package.core-properties+xml\"/>"
                "<Override PartName=\"/docProps/app.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.extended-properties+xml\"/>"
                "</Types>"
            ),
        )
        archive.writestr(
            "_rels/.rels",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"ppt/presentation.xml\"/>"
                "<Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties\" Target=\"docProps/core.xml\"/>"
                "<Relationship Id=\"rId3\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties\" Target=\"docProps/app.xml\"/>"
                "</Relationships>"
            ),
        )
        archive.writestr(
            "docProps/app.xml",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<Properties xmlns=\"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties\" "
                "xmlns:vt=\"http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes\">"
                "<Application>BRP Cyber</Application><PresentationFormat>On-screen Show</PresentationFormat>"
                f"<Slides>{len(slides)}</Slides><Notes>0</Notes><HiddenSlides>0</HiddenSlides><MMClips>0</MMClips>"
                "<ScaleCrop>false</ScaleCrop><HeadingPairs><vt:vector size=\"2\" baseType=\"variant\">"
                "<vt:variant><vt:lpstr>Theme</vt:lpstr></vt:variant><vt:variant><vt:i4>1</vt:i4></vt:variant>"
                "</vt:vector></HeadingPairs><TitlesOfParts><vt:vector size=\"1\" baseType=\"lpstr\"><vt:lpstr>"
                + xml_escape(title)
                + "</vt:lpstr></vt:vector></TitlesOfParts></Properties>"
            ),
        )
        archive.writestr(
            "docProps/core.xml",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<cp:coreProperties xmlns:cp=\"http://schemas.openxmlformats.org/package/2006/metadata/core-properties\" "
                "xmlns:dc=\"http://purl.org/dc/elements/1.1/\" "
                "xmlns:dcterms=\"http://purl.org/dc/terms/\" "
                "xmlns:dcmitype=\"http://purl.org/dc/dcmitype/\" "
                "xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">"
                f"<dc:title>{xml_escape(title)}</dc:title><dc:creator>BRP Cyber</dc:creator>"
                f"<cp:lastModifiedBy>{xml_escape(footer_label or 'BRP Cyber')}</cp:lastModifiedBy>"
                f"<dcterms:created xsi:type=\"dcterms:W3CDTF\">{datetime.now(timezone.utc).isoformat()}</dcterms:created>"
                f"<dcterms:modified xsi:type=\"dcterms:W3CDTF\">{datetime.now(timezone.utc).isoformat()}</dcterms:modified>"
                "</cp:coreProperties>"
            ),
        )
        archive.writestr(
            "ppt/presentation.xml",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<p:presentation xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
                "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
                "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">"
                "<p:sldMasterIdLst><p:sldMasterId id=\"2147483648\" r:id=\"rId1\"/></p:sldMasterIdLst>"
                "<p:sldIdLst>"
                + "".join(f"<p:sldId id=\"{256+index}\" r:id=\"rId{index+2}\"/>" for index in range(len(slides)))
                + "</p:sldIdLst><p:sldSz cx=\"9144000\" cy=\"6858000\"/><p:notesSz cx=\"6858000\" cy=\"9144000\"/></p:presentation>"
            ),
        )
        archive.writestr(
            "ppt/_rels/presentation.xml.rels",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster\" Target=\"slideMasters/slideMaster1.xml\"/>"
                + "".join(
                    f"<Relationship Id=\"rId{index+2}\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide\" Target=\"slides/slide{index+1}.xml\"/>"
                    for index in range(len(slides))
                )
                + "</Relationships>"
            ),
        )
        archive.writestr(
            "ppt/slideMasters/slideMaster1.xml",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<p:sldMaster xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
                "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
                "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">"
                "<p:cSld name=\"BRP Master\"><p:spTree>"
                "<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
                "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/><a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
                "</p:spTree></p:cSld>"
                "<p:clrMap bg1=\"lt1\" tx1=\"dk1\" bg2=\"lt2\" tx2=\"dk2\" accent1=\"accent1\" accent2=\"accent2\" accent3=\"accent3\" accent4=\"accent4\" accent5=\"accent5\" accent6=\"accent6\" hlink=\"hlink\" folHlink=\"folHlink\"/>"
                "<p:sldLayoutIdLst><p:sldLayoutId id=\"2147483649\" r:id=\"rId1\"/></p:sldLayoutIdLst>"
                "<p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>"
            ),
        )
        archive.writestr(
            "ppt/slideMasters/_rels/slideMaster1.xml.rels",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" Target=\"../slideLayouts/slideLayout1.xml\"/>"
                "<Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme\" Target=\"../theme/theme1.xml\"/>"
                "</Relationships>"
            ),
        )
        archive.writestr(
            "ppt/slideLayouts/slideLayout1.xml",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<p:sldLayout xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
                "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
                "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\" type=\"titleOnly\" preserve=\"1\">"
                "<p:cSld name=\"Title Only\"><p:spTree>"
                "<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
                "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/><a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
                "</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>"
            ),
        )
        archive.writestr(
            "ppt/theme/theme1.xml",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<a:theme xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" name=\"BRP Theme\">"
                "<a:themeElements><a:clrScheme name=\"BRP\">"
                "<a:dk1><a:srgbClr val=\"110B0A\"/></a:dk1><a:lt1><a:srgbClr val=\"FFFFFF\"/></a:lt1>"
                "<a:dk2><a:srgbClr val=\"3A2A26\"/></a:dk2><a:lt2><a:srgbClr val=\"F8F5F3\"/></a:lt2>"
                "<a:accent1><a:srgbClr val=\"F76C45\"/></a:accent1><a:accent2><a:srgbClr val=\"DD6E42\"/></a:accent2>"
                "<a:accent3><a:srgbClr val=\"C84D2D\"/></a:accent3><a:accent4><a:srgbClr val=\"8F5D52\"/></a:accent4>"
                "<a:accent5><a:srgbClr val=\"6A4A42\"/></a:accent5><a:accent6><a:srgbClr val=\"E8C0B4\"/></a:accent6>"
                "<a:hlink><a:srgbClr val=\"0000FF\"/></a:hlink><a:folHlink><a:srgbClr val=\"800080\"/></a:folHlink>"
                "</a:clrScheme><a:fontScheme name=\"BRP\"><a:majorFont><a:latin typeface=\"Aptos Display\"/></a:majorFont>"
                "<a:minorFont><a:latin typeface=\"Aptos\"/></a:minorFont></a:fontScheme>"
                "<a:fmtScheme name=\"BRP\"><a:fillStyleLst/><a:lnStyleLst/><a:effectStyleLst/><a:bgFillStyleLst/></a:fmtScheme>"
                "</a:themeElements></a:theme>"
            ),
        )
        for index, slide in enumerate(slides, start=1):
            archive.writestr(f"ppt/slides/slide{index}.xml", _ppt_slide_xml(str(slide["title"]), [str(item) for item in slide["bullets"]]))
            archive.writestr(
                f"ppt/slides/_rels/slide{index}.xml.rels",
                (
                    "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                    "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                    "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" Target=\"../slideLayouts/slideLayout1.xml\"/>"
                    "</Relationships>"
                ),
            )
    return buf.getvalue()


def generate_purple_roi_dashboard(
    db: Session,
    *,
    site_id: UUID,
    lookback_days: int = 30,
    analyst_hourly_cost_usd: float = 18.0,
    analyst_minutes_per_alert: int = 12,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}

    red_scans = db.scalars(
        select(RedScanRun).where(RedScanRun.site_id == site.id).order_by(desc(RedScanRun.created_at)).limit(200)
    ).all()
    exploit_runs = db.scalars(
        select(RedExploitPathRun).where(RedExploitPathRun.site_id == site.id).order_by(desc(RedExploitPathRun.created_at)).limit(200)
    ).all()
    blue_events = db.scalars(
        select(BlueEventLog).where(BlueEventLog.site_id == site.id).order_by(desc(BlueEventLog.created_at)).limit(500)
    ).all()
    purple_reports = db.scalars(
        select(PurpleInsightReport).where(PurpleInsightReport.site_id == site.id).order_by(desc(PurpleInsightReport.created_at)).limit(100)
    ).all()
    detection_rules = db.scalars(
        select(BlueDetectionRule).where(BlueDetectionRule.site_id == site.id).order_by(desc(BlueDetectionRule.updated_at)).limit(200)
    ).all()

    suspicious_events = [event for event in blue_events if event.ai_severity in {"medium", "high"}]
    auto_mitigated = [event for event in suspicious_events if event.status == "applied"]
    filtered_noise = [event for event in blue_events if event.ai_severity == "low" or event.ai_recommendation == "ignore"]

    validated_findings = len([run for run in exploit_runs if int(run.risk_score or 0) >= 40]) + len(
        [scan for scan in red_scans if "risk=high" in scan.ai_summary.lower() or "risk=medium" in scan.ai_summary.lower()]
    )
    high_risk_findings = len([run for run in exploit_runs if int(run.risk_score or 0) >= 70])
    automation_coverage_pct = round((len(auto_mitigated) / len(suspicious_events)) * 100, 2) if suspicious_events else 0.0
    noise_reduction_pct = round((len(filtered_noise) / len(blue_events)) * 100, 2) if blue_events else 0.0
    analyst_hours_saved = round((len(filtered_noise) * max(1, analyst_minutes_per_alert)) / 60.0, 2)
    estimated_manual_effort_saved_usd = round(analyst_hours_saved * max(1.0, float(analyst_hourly_cost_usd)), 2)

    board_metrics = {
        "validated_findings": validated_findings,
        "high_risk_findings": high_risk_findings,
        "suspicious_events": len(suspicious_events),
        "auto_mitigated_events": len(auto_mitigated),
        "filtered_noise_events": len(filtered_noise),
        "automation_coverage_pct": automation_coverage_pct,
        "noise_reduction_pct": noise_reduction_pct,
        "analyst_hours_saved": analyst_hours_saved,
        "estimated_manual_effort_saved_usd": estimated_manual_effort_saved_usd,
        "detection_rules": len(detection_rules),
        "purple_reports": len(purple_reports),
    }
    top_value_drivers = [
        {
            "driver": "Validated risk reduction",
            "value": validated_findings,
            "statement_th": "ยืนยัน finding ที่เจาะได้จริง ทำให้ทีมแก้ไขตามความเสี่ยงที่พิสูจน์แล้ว",
        },
        {
            "driver": "SOC effort saved",
            "value": analyst_hours_saved,
            "statement_th": "AI ช่วยลดเวลาที่ analyst ต้องไล่ดู noise และ alert ที่ไม่สำคัญ",
        },
        {
            "driver": "Automation coverage",
            "value": automation_coverage_pct,
            "statement_th": "อัตราการตอบสนองอัตโนมัติสะท้อนว่าทีม Blue ลดเวลาในการยับยั้งเหตุการณ์ได้แค่ไหน",
        },
    ]
    headline_th = (
        f"ROI Dashboard ของ {site.display_name}: ลดงาน manual ได้ประมาณ {analyst_hours_saved} ชั่วโมง "
        f"และยืนยันความเสี่ยงที่สำคัญได้ {validated_findings} รายการในรอบ {lookback_days} วัน."
    )
    board_statement_th = (
        f"งบ security ที่ใช้ไปกำลังเปลี่ยนเป็นผลลัพธ์ที่วัดได้: automation={automation_coverage_pct}% "
        f"noise reduction={noise_reduction_pct}% cost_saved~${estimated_manual_effort_saved_usd}."
    )
    summary = {
        "site_id": str(site.id),
        "site_code": site.site_code,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "headline_th": headline_th,
        "board_statement_th": board_statement_th,
        "board_metrics": board_metrics,
    }
    details = {
        "top_value_drivers": top_value_drivers,
        "assumptions": {
            "lookback_days": lookback_days,
            "analyst_hourly_cost_usd": analyst_hourly_cost_usd,
            "analyst_minutes_per_alert": analyst_minutes_per_alert,
        },
        "operational_counts": {
            "red_scans": len(red_scans),
            "exploit_runs": len(exploit_runs),
            "blue_events": len(blue_events),
            "purple_reports": len(purple_reports),
            "detection_rules": len(detection_rules),
        },
    }

    snapshot = PurpleRoiDashboardSnapshot(
        site_id=site.id,
        lookback_days=max(1, min(int(lookback_days), 365)),
        status="completed",
        summary_json=_as_json(summary),
        details_json=_as_json(details),
        created_at=datetime.now(timezone.utc),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {"status": "completed", "site_id": str(site.id), "site_code": site.site_code, "snapshot": _snapshot_row(snapshot)}


def list_purple_roi_snapshots(db: Session, *, site_id: UUID, limit: int = 20) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}
    rows = db.scalars(
        select(PurpleRoiDashboardSnapshot)
        .where(PurpleRoiDashboardSnapshot.site_id == site.id)
        .order_by(desc(PurpleRoiDashboardSnapshot.created_at))
        .limit(max(1, min(limit, 200)))
    ).all()
    return {"status": "ok", "count": len(rows), "rows": [_snapshot_row(row) for row in rows]}


def list_purple_roi_trends(
    db: Session,
    *,
    site_id: UUID,
    limit: int = 12,
    metric_focus: str = "",
    min_automation_coverage_pct: float = 0.0,
    min_noise_reduction_pct: float = 0.0,
) -> dict[str, Any]:
    snapshot_result = list_purple_roi_snapshots(db, site_id=site_id, limit=max(2, min(limit, 36)))
    if snapshot_result.get("status") != "ok":
        return snapshot_result

    rows = [row for row in snapshot_result.get("rows", [])]
    trend_rows = [_trend_row(row) for row in rows]
    normalized_metric_focus = str(metric_focus or "").strip().lower()
    if normalized_metric_focus not in {"", "validated_findings", "automation_coverage_pct", "noise_reduction_pct", "estimated_manual_effort_saved_usd", "high_risk_findings"}:
        normalized_metric_focus = ""
    filtered_rows = [
        row
        for row in trend_rows
        if float(row.get("automation_coverage_pct", 0.0) or 0.0) >= float(min_automation_coverage_pct or 0.0)
        and float(row.get("noise_reduction_pct", 0.0) or 0.0) >= float(min_noise_reduction_pct or 0.0)
    ]
    if normalized_metric_focus:
        filtered_rows.sort(key=lambda row: float(row.get(normalized_metric_focus, 0.0) or 0.0), reverse=True)
    else:
        filtered_rows.sort(key=lambda row: str(row.get("created_at", "")), reverse=True)
    latest = filtered_rows[0] if filtered_rows else None
    previous = filtered_rows[1] if len(filtered_rows) > 1 else None

    def _delta(metric: str) -> float:
        if not latest or not previous:
            return 0.0
        return round(float(latest.get(metric, 0.0)) - float(previous.get(metric, 0.0)), 2)

    summary = {
        "trend_points": len(filtered_rows),
        "total_points_before_filter": len(trend_rows),
        "filtered_out_count": max(0, len(trend_rows) - len(filtered_rows)),
        "latest_created_at": latest.get("created_at", "") if latest else "",
        "metric_focus": normalized_metric_focus,
        "validated_findings_delta": _delta("validated_findings"),
        "automation_coverage_delta_pct": _delta("automation_coverage_pct"),
        "noise_reduction_delta_pct": _delta("noise_reduction_pct"),
        "estimated_manual_effort_saved_delta_usd": _delta("estimated_manual_effort_saved_usd"),
        "applied_filters": {
            "metric_focus": normalized_metric_focus,
            "min_automation_coverage_pct": round(float(min_automation_coverage_pct or 0.0), 2),
            "min_noise_reduction_pct": round(float(min_noise_reduction_pct or 0.0), 2),
        },
        "direction": (
            "improving"
            if _delta("automation_coverage_pct") >= 0 and _delta("noise_reduction_pct") >= 0
            else "mixed"
        ),
    }
    return {
        "status": "ok",
        "site_id": str(site_id),
        "count": len(filtered_rows),
        "summary": summary,
        "rows": filtered_rows,
    }


def build_purple_roi_portfolio_rollup(
    db: Session,
    *,
    tenant_code: str = "",
    site_code: str = "",
    status: str = "",
    min_automation_coverage_pct: float = 0.0,
    min_noise_reduction_pct: float = 0.0,
    sort_by: str = "estimated_manual_effort_saved_usd",
    limit: int = 200,
) -> dict[str, Any]:
    stmt = select(Site).order_by(Site.display_name.asc()).limit(max(1, min(limit, 500)))
    if tenant_code:
        stmt = (
            select(Site)
            .join(Tenant, Site.tenant_id == Tenant.id)
            .where(Tenant.tenant_code == tenant_code)
            .order_by(Site.display_name.asc())
            .limit(max(1, min(limit, 500)))
        )
    sites = db.scalars(stmt).all()
    rows: list[dict[str, Any]] = []
    for site in sites:
        latest = db.scalar(
            select(PurpleRoiDashboardSnapshot)
            .where(PurpleRoiDashboardSnapshot.site_id == site.id)
            .order_by(desc(PurpleRoiDashboardSnapshot.created_at))
            .limit(1)
        )
        tenant = _resolve_tenant(db, site)
        if latest is None:
            rows.append(
                {
                    "tenant_code": getattr(tenant, "tenant_code", ""),
                    "site_id": str(site.id),
                    "site_code": site.site_code,
                    "display_name": site.display_name,
                    "status": "no_snapshot",
                    "validated_findings": 0.0,
                    "automation_coverage_pct": 0.0,
                    "noise_reduction_pct": 0.0,
                    "estimated_manual_effort_saved_usd": 0.0,
                    "high_risk_findings": 0.0,
                    "created_at": "",
                    "headline_th": "",
                    "board_statement_th": "",
                }
            )
            continue
        snapshot = _snapshot_row(latest)
        summary = snapshot.get("summary", {})
        rows.append(
            {
                "tenant_code": getattr(tenant, "tenant_code", ""),
                "site_id": str(site.id),
                "site_code": site.site_code,
                "display_name": site.display_name,
                "status": snapshot.get("status", "completed"),
                "validated_findings": _metric_number(snapshot, "validated_findings"),
                "automation_coverage_pct": _metric_number(snapshot, "automation_coverage_pct"),
                "noise_reduction_pct": _metric_number(snapshot, "noise_reduction_pct"),
                "estimated_manual_effort_saved_usd": _metric_number(snapshot, "estimated_manual_effort_saved_usd"),
                "high_risk_findings": _metric_number(snapshot, "high_risk_findings"),
                "created_at": snapshot.get("created_at", ""),
                "headline_th": str(summary.get("headline_th", "")) if isinstance(summary, dict) else "",
                "board_statement_th": str(summary.get("board_statement_th", "")) if isinstance(summary, dict) else "",
            }
        )

    normalized_site_code = site_code.strip().lower()
    normalized_status = status.strip().lower()
    normalized_sort_by = str(sort_by or "estimated_manual_effort_saved_usd").strip()
    if normalized_sort_by not in {"estimated_manual_effort_saved_usd", "validated_findings", "automation_coverage_pct", "noise_reduction_pct", "high_risk_findings"}:
        normalized_sort_by = "estimated_manual_effort_saved_usd"
    filtered_rows = [
        row
        for row in rows
        if (not normalized_site_code or normalized_site_code in str(row.get("site_code", "")).lower())
        and (not normalized_status or str(row.get("status", "")).lower() == normalized_status)
        and float(row.get("automation_coverage_pct", 0.0) or 0.0) >= float(min_automation_coverage_pct or 0.0)
        and float(row.get("noise_reduction_pct", 0.0) or 0.0) >= float(min_noise_reduction_pct or 0.0)
    ]
    filtered_rows.sort(key=lambda item: float(item.get(normalized_sort_by, 0.0) or 0.0), reverse=True)
    sites_with_snapshots = [row for row in filtered_rows if row["status"] != "no_snapshot"]
    snapshot_count = len(sites_with_snapshots)
    summary = {
        "tenant_code": tenant_code,
        "total_sites": len(filtered_rows),
        "total_sites_before_filter": len(rows),
        "sites_with_snapshots": snapshot_count,
        "no_snapshot_sites": len(filtered_rows) - snapshot_count,
        "total_validated_findings": round(sum(float(row["validated_findings"]) for row in sites_with_snapshots), 2),
        "total_estimated_manual_effort_saved_usd": round(
            sum(float(row["estimated_manual_effort_saved_usd"]) for row in sites_with_snapshots), 2
        ),
        "average_automation_coverage_pct": round(
            sum(float(row["automation_coverage_pct"]) for row in sites_with_snapshots) / snapshot_count, 2
        )
        if snapshot_count
        else 0.0,
        "average_noise_reduction_pct": round(
            sum(float(row["noise_reduction_pct"]) for row in sites_with_snapshots) / snapshot_count, 2
        )
        if snapshot_count
        else 0.0,
        "highest_value_site_code": filtered_rows[0]["site_code"] if filtered_rows else "",
        "sort_by": normalized_sort_by,
        "applied_filters": {
            "site_code": normalized_site_code,
            "status": normalized_status,
            "min_automation_coverage_pct": round(float(min_automation_coverage_pct or 0.0), 2),
            "min_noise_reduction_pct": round(float(min_noise_reduction_pct or 0.0), 2),
        },
    }
    return {
        "status": "ok",
        "tenant_code": tenant_code,
        "count": len(filtered_rows),
        "summary": summary,
        "rows": filtered_rows,
    }


def export_purple_roi_board_pack(
    db: Session,
    *,
    site_id: UUID,
    export_format: str = "pdf",
    template_pack: str = "roi_board_minimal",
    title_override: str = "",
    include_portfolio: bool = True,
    tenant_code: str = "",
    site_limit: int = 50,
) -> dict[str, Any]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}

    latest = db.scalar(
        select(PurpleRoiDashboardSnapshot)
        .where(PurpleRoiDashboardSnapshot.site_id == site.id)
        .order_by(desc(PurpleRoiDashboardSnapshot.created_at))
        .limit(1)
    )
    if latest is None:
        return {"status": "no_snapshot", "site_id": str(site.id), "site_code": site.site_code}

    snapshot = _snapshot_row(latest)
    summary = snapshot.get("summary", {})
    details = snapshot.get("details", {})
    trend = list_purple_roi_trends(db, site_id=site.id, limit=12)
    resolved_tenant = _resolve_tenant(db, site)
    effective_tenant_code = tenant_code or getattr(resolved_tenant, "tenant_code", "")
    template = _find_roi_template_pack(template_pack)
    portfolio = (
        build_purple_roi_portfolio_rollup(db, tenant_code=effective_tenant_code, limit=site_limit)
        if include_portfolio
        else {"status": "disabled", "count": 0, "summary": {}, "rows": []}
    )
    title = title_override.strip() or f"BRP Cyber ROI Board Pack - {site.display_name}"
    section_map = _build_roi_section_map(
        summary=summary if isinstance(summary, dict) else {},
        details=details if isinstance(details, dict) else {},
        trend=trend,
        portfolio=portfolio,
        include_portfolio=include_portfolio,
    )
    ordered_names = [name for name in template.get("section_order", []) if name in section_map]
    if include_portfolio and "Portfolio Roll-up" in section_map and "Portfolio Roll-up" not in ordered_names:
        ordered_names.append("Portfolio Roll-up")
    sections = [{"section": name, "content": section_map[name]} for name in ordered_names]
    slides = [
        {
            "title": title,
            "bullets": [
                str(template.get("cover_label", "Executive Review")),
                str(summary.get("headline_th", "")),
                str(summary.get("board_statement_th", "")),
            ],
        }
    ] + [{"title": section["section"], "bullets": section["content"]} for section in sections]
    preview_text = "\n".join(
        [title, f"template_pack={template['pack_code']} audience={template['audience']}"]
        + [f"{section['section']}: {' | '.join(section['content'])}" for section in sections]
    )
    normalized_format = str(export_format or "pdf").strip().lower()
    if normalized_format == "ppt":
        binary_bytes = _render_pptx_bytes(title, slides, str(template.get("footer_label", "")))
        download_filename = f"{site.site_code}-{_safe_filename_part(template['pack_code'])}-roi-board-pack.pptx"
        mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    else:
        normalized_format = "pdf"
        binary_bytes = _render_pdf_bytes(title, sections, str(template.get("footer_label", "")))
        download_filename = f"{site.site_code}-{_safe_filename_part(template['pack_code'])}-roi-board-pack.pdf"
        mime_type = "application/pdf"
    artifact_base64 = base64.b64encode(binary_bytes).decode("ascii")
    return {
        "status": "ok",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "export": {
            "export_format": normalized_format,
            "renderer": "native_binary",
            "title": title,
            "filename": download_filename,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "snapshot_id": snapshot.get("snapshot_id", ""),
            "includes_portfolio": bool(include_portfolio),
            "portfolio_tenant_code": effective_tenant_code,
            "template_pack": template,
            "mime_type": mime_type,
            "byte_size": len(binary_bytes),
            "content_base64": artifact_base64,
            "sections": sections,
            "slides": slides,
            "preview_text": preview_text,
        },
    }
