from fastapi import APIRouter

from app.services.blue_detection import process_auth_login_event, process_system_auth_event, process_waf_http_event
from app.services.redis_client import redis_client
from schemas.ingest import AuthLoginEvent, SystemAuthEvent, WafHttpEvent

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/auth-login")
def ingest_auth_login(payload: AuthLoginEvent) -> dict[str, str]:
    result = process_auth_login_event(payload)
    return {"status": result["status"], "reason": result["reason"]}


@router.post("/system-auth")
def ingest_system_auth(payload: SystemAuthEvent) -> dict[str, str]:
    result = process_system_auth_event(payload)
    return {"status": result["status"], "reason": result["reason"]}


@router.post("/waf-http")
def ingest_waf_http(payload: WafHttpEvent) -> dict[str, str]:
    result = process_waf_http_event(payload)
    return {"status": result["status"], "reason": result["reason"]}


@router.get("/incidents/{tenant_id}")
def get_incidents(tenant_id: str, limit: int = 100) -> dict[str, object]:
    capped_limit = min(max(limit, 1), 500)
    key = f"incidents:{tenant_id}"
    entries = redis_client.xrevrange(key, count=capped_limit)

    incidents = []
    for event_id, fields in entries:
        incident = {"id": event_id}
        incident.update(fields)
        incidents.append(incident)

    return {"tenant_id": tenant_id, "count": len(incidents), "incidents": incidents}


@router.get("/dead-letters")
def get_dead_letters(limit: int = 100) -> dict[str, object]:
    capped_limit = min(max(limit, 1), 500)
    entries = redis_client.xrevrange("dead_letter_events", count=capped_limit)

    dead_letters = []
    for event_id, fields in entries:
        item = {"id": event_id}
        item.update(fields)
        dead_letters.append(item)

    return {"count": len(dead_letters), "dead_letters": dead_letters}
