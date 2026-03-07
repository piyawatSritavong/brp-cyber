from fastapi import APIRouter

from app.services.event_store import persist_event
from schemas.events import DetectionEvent, PurpleReportEvent, RedEvent, ResponseEvent

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/red")
def ingest_red_event(payload: RedEvent) -> dict[str, str]:
    persist_event(payload)
    return {"status": "accepted", "event_type": payload.event_type}


@router.post("/detection")
def ingest_detection_event(payload: DetectionEvent) -> dict[str, str]:
    persist_event(payload)
    return {"status": "accepted", "event_type": payload.event_type}


@router.post("/response")
def ingest_response_event(payload: ResponseEvent) -> dict[str, str]:
    persist_event(payload)
    return {"status": "accepted", "event_type": payload.event_type}


@router.post("/purple-report")
def ingest_purple_event(payload: PurpleReportEvent) -> dict[str, str]:
    persist_event(payload)
    return {"status": "accepted", "event_type": payload.event_type}
