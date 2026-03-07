from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx

from app.core.config import settings


class NotarizationAdapter(Protocol):
    def notarize(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...


@dataclass
class LocalDigestNotarizationAdapter:
    def notarize(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        receipt_id = f"local-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        return {
            "status": "notarized",
            "provider": "local_digest",
            "receipt_id": receipt_id,
            "digest_sha256": digest,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@dataclass
class WebhookNotarizationAdapter:
    url: str
    api_key: str

    def notarize(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"content-type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        with httpx.Client(timeout=20.0) as client:
            response = client.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json() if response.content else {}

        return {
            "status": "notarized",
            "provider": "webhook",
            "receipt_id": str(body.get("receipt_id", "")),
            "reference": body,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def load_notarization_adapter() -> NotarizationAdapter:
    provider = settings.control_plane_notarization_provider.lower().strip()
    if provider == "webhook":
        if not settings.control_plane_notarization_webhook_url:
            raise RuntimeError("notarization_webhook_url_not_configured")
        return WebhookNotarizationAdapter(
            url=settings.control_plane_notarization_webhook_url,
            api_key=settings.control_plane_notarization_api_key,
        )
    return LocalDigestNotarizationAdapter()


def notarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    adapter = load_notarization_adapter()
    return adapter.notarize(payload)
