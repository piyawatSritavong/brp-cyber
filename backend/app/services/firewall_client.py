import logging

import httpx

from app.core.config import settings
from app.services.dead_letter import write_dead_letter
from app.services.retry import run_with_retry

logger = logging.getLogger("brp_cyber.firewall")


def block_ip(tenant_id: str, source_ip: str, reason: str) -> bool:
    payload = {"tenant_id": tenant_id, "source_ip": source_ip, "reason": reason}

    if not settings.firewall_api_base_url:
        logger.info("firewall_stub_block", extra=payload)
        return True

    url = f"{settings.firewall_api_base_url.rstrip('/')}/block-ip"
    headers = {"content-type": "application/json"}
    if settings.firewall_api_key:
        headers["authorization"] = f"Bearer {settings.firewall_api_key}"

    def _call() -> bool:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
        return True

    try:
        return run_with_retry(
            _call,
            attempts=settings.response_retry_attempts,
            backoff_seconds=settings.response_retry_backoff_seconds,
        )
    except Exception as exc:
        logger.exception("firewall_block_failed", extra={"tenant_id": tenant_id, "source_ip": source_ip})
        write_dead_letter("firewall_client", "block_ip", payload, str(exc))
        return False
