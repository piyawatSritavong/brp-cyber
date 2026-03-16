import logging

import httpx

from app.core.config import settings
from app.services.dead_letter import write_dead_letter
from app.services.retry import run_with_retry

logger = logging.getLogger("brp_cyber.notifier")


def send_telegram_message(message: str) -> bool:
    payload = {"message": message}

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.info("telegram_stub", extra=payload)
        return True

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    request_payload = {"chat_id": settings.telegram_chat_id, "text": message}

    def _call() -> bool:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(url, json=request_payload)
            response.raise_for_status()
        return True

    try:
        return run_with_retry(
            _call,
            attempts=settings.response_retry_attempts,
            backoff_seconds=settings.response_retry_backoff_seconds,
        )
    except Exception as exc:
        logger.exception("telegram_send_failed")
        write_dead_letter("notifier", "send_telegram_message", payload, str(exc))
        return False


def send_line_message(message: str) -> bool:
    payload = {"message": message}

    if not settings.line_notify_webhook_url:
        logger.info("line_stub", extra=payload)
        return True

    headers = {"Content-Type": "application/json"}
    if settings.line_notify_bearer_token:
        headers["Authorization"] = f"Bearer {settings.line_notify_bearer_token}"

    def _call() -> bool:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(settings.line_notify_webhook_url, json={"message": message}, headers=headers)
            response.raise_for_status()
        return True

    try:
        return run_with_retry(
            _call,
            attempts=settings.response_retry_attempts,
            backoff_seconds=settings.response_retry_backoff_seconds,
        )
    except Exception as exc:
        logger.exception("line_send_failed")
        write_dead_letter("notifier", "send_line_message", payload, str(exc))
        return False


def send_webhook_message(url: str, payload: dict[str, object], *, bearer_token: str = "") -> bool:
    request_url = str(url or "").strip()
    request_payload = dict(payload or {})

    if not request_url:
        logger.info("webhook_stub", extra={"payload": request_payload})
        return True

    headers = {"Content-Type": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    def _call() -> bool:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(request_url, json=request_payload, headers=headers)
            response.raise_for_status()
        return True

    try:
        return run_with_retry(
            _call,
            attempts=settings.response_retry_attempts,
            backoff_seconds=settings.response_retry_backoff_seconds,
        )
    except Exception as exc:
        logger.exception("webhook_send_failed")
        write_dead_letter("notifier", "send_webhook_message", {"url": request_url, "payload": request_payload}, str(exc))
        return False
