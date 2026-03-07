from __future__ import annotations

import json
import logging
import os
import time
from uuid import UUID

from app.core.config import settings
from app.services.enterprise.quotas import add_usage
from app.services.enterprise.queueing import ensure_worker_groups, record_worker_progress, stream_names
from app.services.redis_client import redis_client

logger = logging.getLogger("brp_cyber.scan_worker")


def _consumer_name() -> str:
    return os.getenv("WORKER_ID", f"worker-{int(time.time())}")


def _process_message(fields: dict[str, str]) -> None:
    tenant_id = UUID(fields["tenant_id"])
    task_type = fields.get("task_type", "scan")
    payload = json.loads(fields.get("payload", "{}"))

    # Phase 5 baseline worker: usage accounting + structured logging hook.
    token_estimate = int(payload.get("estimated_tokens", 200))
    add_usage(tenant_id, events=1, actions=1, tokens=token_estimate)
    logger.info(
        "scan_task_processed",
        extra={"tenant_id": str(tenant_id), "task_type": task_type, "estimated_tokens": token_estimate},
    )


def run_forever() -> None:
    ensure_worker_groups()
    consumer = _consumer_name()

    while True:
        streams = {stream: ">" for stream in stream_names()}
        messages = redis_client.xreadgroup(
            groupname=settings.queue_worker_group,
            consumername=consumer,
            streams=streams,
            count=settings.queue_batch_size,
            block=3000,
        )

        if not messages:
            continue

        processed = 0
        errors = 0

        for stream, entries in messages:
            for message_id, fields in entries:
                try:
                    _process_message(fields)
                    redis_client.xack(stream, settings.queue_worker_group, message_id)
                    processed += 1
                except Exception:
                    logger.exception("scan_task_failed", extra={"stream": stream, "message_id": message_id})
                    errors += 1

        record_worker_progress(consumer, processed=processed, errors=errors)


if __name__ == "__main__":
    run_forever()
