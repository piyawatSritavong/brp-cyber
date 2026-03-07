from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter

from app.services.purple_core import correlate_tenant_events, generate_daily_report, list_reports

router = APIRouter(prefix="/purple", tags=["purple"])


@router.get("/correlate/{tenant_id}")
def correlate(tenant_id: UUID, limit: int = 5000, date: str | None = None) -> dict[str, object]:
    report_date = None
    if date:
        parsed = datetime.strptime(date, "%Y-%m-%d")
        report_date = parsed.replace(tzinfo=timezone.utc)
    return correlate_tenant_events(tenant_id=tenant_id, limit=limit, report_date=report_date)


@router.post("/report/{tenant_id}/daily")
def create_daily_report(tenant_id: UUID, limit: int = 5000, date: str | None = None) -> dict[str, object]:
    report_date = None
    if date:
        parsed = datetime.strptime(date, "%Y-%m-%d")
        report_date = parsed.replace(tzinfo=timezone.utc)
    return generate_daily_report(tenant_id=tenant_id, limit=limit, report_date=report_date)


@router.get("/report/{tenant_id}")
def get_reports(tenant_id: UUID, limit: int = 30) -> dict[str, object]:
    reports = list_reports(tenant_id=tenant_id, limit=limit)
    return {"tenant_id": str(tenant_id), "count": len(reports), "reports": reports}
