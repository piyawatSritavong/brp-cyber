from uuid import UUID

from fastapi import APIRouter

from app.services.purple_core import (
    correlate_tenant_events,
    export_report_artifact,
    generate_daily_report,
    purple_report_export_status,
    query_reports,
)

router = APIRouter(prefix="/purple", tags=["purple"])


@router.get("/correlate/{tenant_id}")
def correlate(
    tenant_id: UUID,
    limit: int = 5000,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    attack_type: str = "",
    detection_status: str = "",
    page: int = 1,
    page_size: int = 0,
) -> dict[str, object]:
    return correlate_tenant_events(
        tenant_id=tenant_id,
        limit=limit,
        report_date=date,
        date_from=date_from,
        date_to=date_to,
        attack_type=attack_type,
        detection_status=detection_status,
        page=page,
        page_size=page_size,
    )


@router.post("/report/{tenant_id}/daily")
def create_daily_report(
    tenant_id: UUID,
    limit: int = 5000,
    date: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, object]:
    return generate_daily_report(
        tenant_id=tenant_id,
        limit=limit,
        report_date=date,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/report/{tenant_id}")
def get_reports(
    tenant_id: UUID,
    limit: int = 30,
    page: int = 1,
    page_size: int = 0,
    date_from: str | None = None,
    date_to: str | None = None,
    min_detection_coverage: float | None = None,
    max_mttr_seconds: float | None = None,
    report_id: str = "",
) -> dict[str, object]:
    return query_reports(
        tenant_id=tenant_id,
        limit=limit,
        page=page,
        page_size=page_size,
        date_from=date_from,
        date_to=date_to,
        min_detection_coverage=min_detection_coverage,
        max_mttr_seconds=max_mttr_seconds,
        report_id=report_id,
    )


@router.post("/report/{tenant_id}/export")
def export_report(
    tenant_id: UUID,
    report_id: str = "",
    export_format: str = "json",
    destination_dir: str = "",
    limit: int = 5000,
) -> dict[str, object]:
    return export_report_artifact(
        tenant_id=tenant_id,
        report_id=report_id,
        export_format=export_format,
        destination_dir=destination_dir,
        limit=limit,
    )


@router.get("/report/{tenant_id}/export/status")
def report_export_status(tenant_id: UUID, limit: int = 100) -> dict[str, object]:
    return purple_report_export_status(tenant_id=tenant_id, limit=limit)
