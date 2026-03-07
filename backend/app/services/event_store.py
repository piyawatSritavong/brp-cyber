import json
import logging

from app.services.redis_client import redis_client
from schemas.events import AnySecurityEvent

logger = logging.getLogger("brp_cyber.event_store")

STREAM_KEY = "security_events"


def persist_event(event: AnySecurityEvent) -> None:
    payload = event.model_dump(mode="json")
    logger.info(
        "security_event",
        extra={
            "event_type": event.event_type,
            "tenant_id": str(event.metadata.tenant_id),
            "correlation_id": str(event.metadata.correlation_id),
            "trace_id": str(event.metadata.trace_id),
            "source": event.metadata.source,
            "timestamp": event.metadata.timestamp.isoformat(),
        },
    )

    redis_client.xadd(
        STREAM_KEY,
        {
            "event_type": event.event_type,
            "tenant_id": str(event.metadata.tenant_id),
            "correlation_id": str(event.metadata.correlation_id),
            "trace_id": str(event.metadata.trace_id),
            "payload": json.dumps(payload),
        },
        maxlen=200000,
        approximate=True,
    )
