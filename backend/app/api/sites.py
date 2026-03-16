from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.site_ops import (
    apply_blue_recommendation,
    generate_nist_csf_gap_template,
    generate_iso27001_gap_template,
    generate_purple_executive_scorecard,
    generate_purple_site_report,
    ingest_blue_site_event,
    list_blue_site_events,
    list_purple_site_reports,
    list_red_scans,
    list_sites,
    purple_executive_federation,
    run_red_site_scan,
    upsert_site,
)
from schemas.site_ops import (
    BlueRecommendationActionRequest,
    BlueSiteEventIngestRequest,
    RedSiteScanRequest,
    SiteUpsertRequest,
)

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("")
def sites(tenant_code: str = "", limit: int = 200, db: Session = Depends(get_db)) -> dict[str, object]:
    return list_sites(db, tenant_code=tenant_code, limit=limit)


@router.post("")
def site_upsert(payload: SiteUpsertRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    return upsert_site(db, payload)


@router.post("/{site_id}/red/scan")
def red_scan(site_id: UUID, payload: RedSiteScanRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    return run_red_site_scan(db, site_id, payload)


@router.get("/{site_id}/red/scans")
def red_scans(site_id: UUID, limit: int = 30, db: Session = Depends(get_db)) -> dict[str, object]:
    return list_red_scans(db, site_id, limit=limit)


@router.post("/{site_id}/blue/events")
def blue_event_ingest(site_id: UUID, payload: BlueSiteEventIngestRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    return ingest_blue_site_event(db, site_id, payload)


@router.get("/{site_id}/blue/events")
def blue_events(site_id: UUID, limit: int = 100, db: Session = Depends(get_db)) -> dict[str, object]:
    return list_blue_site_events(db, site_id, limit=limit)


@router.post("/{site_id}/blue/events/{event_id}/apply")
def blue_apply_action(
    site_id: UUID,
    event_id: UUID,
    payload: BlueRecommendationActionRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return apply_blue_recommendation(db, site_id, event_id, payload.action)


@router.post("/{site_id}/purple/analyze")
def purple_analyze(site_id: UUID, db: Session = Depends(get_db)) -> dict[str, object]:
    return generate_purple_site_report(db, site_id)


@router.get("/{site_id}/purple/reports")
def purple_reports(site_id: UUID, limit: int = 30, db: Session = Depends(get_db)) -> dict[str, object]:
    return list_purple_site_reports(db, site_id, limit=limit)


@router.get("/{site_id}/purple/iso27001-gap-template")
def purple_iso27001_gap_template(site_id: UUID, limit: int = 200, db: Session = Depends(get_db)) -> dict[str, object]:
    return generate_iso27001_gap_template(db, site_id, limit=limit)


@router.get("/{site_id}/purple/nist-csf-gap-template")
def purple_nist_csf_gap_template(site_id: UUID, limit: int = 200, db: Session = Depends(get_db)) -> dict[str, object]:
    return generate_nist_csf_gap_template(db, site_id, limit=limit)


@router.get("/{site_id}/purple/executive-scorecard")
def purple_executive_scorecard(
    site_id: UUID,
    lookback_runs: int = 30,
    lookback_events: int = 500,
    sla_target_seconds: int = 120,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return generate_purple_executive_scorecard(
        db,
        site_id,
        lookback_runs=lookback_runs,
        lookback_events=lookback_events,
        sla_target_seconds=sla_target_seconds,
    )


@router.get("/purple/executive-federation")
def purple_exec_federation(
    limit: int = 200,
    lookback_runs: int = 30,
    lookback_events: int = 500,
    sla_target_seconds: int = 120,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return purple_executive_federation(
        db,
        limit=limit,
        lookback_runs=lookback_runs,
        lookback_events=lookback_events,
        sla_target_seconds=sla_target_seconds,
    )
