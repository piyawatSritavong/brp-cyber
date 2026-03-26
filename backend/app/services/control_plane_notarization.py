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


def _normalize_hint(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text.replace("-", "_").replace(" ", "_")


def _collect_hint_values(raw: Any) -> set[str]:
    if isinstance(raw, str):
        return {_normalize_hint(item) for item in raw.split(",") if _normalize_hint(item)}
    if isinstance(raw, (list, tuple, set)):
        return {_normalize_hint(item) for item in raw if _normalize_hint(item)}
    if isinstance(raw, dict):
        hints: set[str] = set()
        for key in ("profile_id", "profile", "eidas_profile", "etsi_profile"):
            hints.update(_collect_hint_values(raw.get(key)))
        hints.update(_collect_hint_values(raw.get("profiles")))
        return hints
    return set()


def _provider_name(notarization: dict[str, Any], reference: dict[str, Any]) -> str:
    return str(
        notarization.get("provider_name")
        or reference.get("provider_name")
        or settings.control_plane_notarization_provider_name
        or notarization.get("provider", "")
    ).strip()


def _declared_compliance_hints(notarization: dict[str, Any], reference: dict[str, Any]) -> set[str]:
    hints: set[str] = set()

    for key in ("compliance_profile", "provider_profile", "eidas_profile", "etsi_profile", "trust_service_profile"):
        hints.update(_collect_hint_values(notarization.get(key)))
        hints.update(_collect_hint_values(reference.get(key)))

    for key in ("compliance_profiles", "profiles"):
        hints.update(_collect_hint_values(notarization.get(key)))
        hints.update(_collect_hint_values(reference.get(key)))

    compliance_block = reference.get("compliance", {})
    if isinstance(compliance_block, dict):
        for key in ("profile_id", "compliance_profile", "eidas_profile", "etsi_profile", "profiles"):
            hints.update(_collect_hint_values(compliance_block.get(key)))

    hints.update(_collect_hint_values(settings.control_plane_notarization_compliance_profiles))
    return {hint for hint in hints if hint}


def resolve_notarization_compliance_profile(notarization: dict[str, Any]) -> dict[str, Any]:
    provider = str(notarization.get("provider", "")).strip().lower()
    reference = notarization.get("reference", {})
    if not isinstance(reference, dict):
        reference = {}

    provider_name = _provider_name(notarization, reference)
    declared_profiles = sorted(_declared_compliance_hints(notarization, reference))

    timestamp_hints = {
        "qualified_timestamp",
        "eidas_qualified_timestamp",
        "etsi_timestamp",
        "timestamp_service",
        "qualified_electronic_timestamp",
    }
    seal_hints = {
        "qualified_signature",
        "qualified_seal",
        "eidas_qualified_signature_or_seal",
        "signature_or_seal_service",
        "etsi_signature",
        "etsi_seal",
    }

    if provider == "local_digest":
        return {
            "profile_id": "local_integrity_only",
            "provider": provider,
            "provider_name": provider_name or "local_digest",
            "trust_model": "self_attested",
            "mapping_status": "mapped",
            "declared_profiles": declared_profiles,
            "eidas": {"profile": "not_supported", "qualified": False},
            "etsi": {"profile": "none", "qualified": False},
            "capabilities": {
                "content_integrity": True,
                "independent_receipt": False,
                "external_timestamp": False,
                "qualified_signature_or_seal": False,
            },
            "notes": "Local SHA-256 digest provides internal integrity evidence only.",
        }

    if any(hint in timestamp_hints for hint in declared_profiles):
        return {
            "profile_id": "eidas_qualified_timestamp",
            "provider": provider,
            "provider_name": provider_name or provider,
            "trust_model": "external_provider_declared",
            "mapping_status": "provider_declared_profile",
            "declared_profiles": declared_profiles,
            "eidas": {"profile": "qualified_timestamp", "qualified": True},
            "etsi": {"profile": "timestamp_service", "qualified": True},
            "capabilities": {
                "content_integrity": True,
                "independent_receipt": True,
                "external_timestamp": True,
                "qualified_signature_or_seal": False,
            },
            "notes": "External provider declared support for qualified timestamp-style notarization.",
        }

    if any(hint in seal_hints for hint in declared_profiles):
        return {
            "profile_id": "eidas_qualified_signature_or_seal",
            "provider": provider,
            "provider_name": provider_name or provider,
            "trust_model": "external_provider_declared",
            "mapping_status": "provider_declared_profile",
            "declared_profiles": declared_profiles,
            "eidas": {"profile": "qualified_signature_or_seal", "qualified": True},
            "etsi": {"profile": "signature_or_seal_service", "qualified": True},
            "capabilities": {
                "content_integrity": True,
                "independent_receipt": True,
                "external_timestamp": True,
                "qualified_signature_or_seal": True,
            },
            "notes": "External provider declared signature/seal-grade trust-service coverage.",
        }

    return {
        "profile_id": "external_provider_declared",
        "provider": provider,
        "provider_name": provider_name or provider,
        "trust_model": "external_provider_declared",
        "mapping_status": "provider_declared",
        "declared_profiles": declared_profiles,
        "eidas": {"profile": "provider_declared", "qualified": False},
        "etsi": {"profile": "provider_declared", "qualified": False},
        "capabilities": {
            "content_integrity": True,
            "independent_receipt": bool(notarization.get("receipt_id")),
            "external_timestamp": False,
            "qualified_signature_or_seal": False,
        },
        "notes": "External provider is configured, but no stronger eIDAS/ETSI profile was declared.",
    }


@dataclass
class LocalDigestNotarizationAdapter:
    def notarize(self, payload: dict[str, Any]) -> dict[str, Any]:
        raw = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        receipt_id = f"local-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        return {
            "status": "notarized",
            "provider": "local_digest",
            "provider_name": "local_digest",
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
            "provider_name": str(body.get("provider_name", settings.control_plane_notarization_provider_name or "webhook")),
            "receipt_id": str(body.get("receipt_id", "")),
            "compliance_profile": body.get("compliance_profile"),
            "compliance_profiles": body.get("compliance_profiles"),
            "eidas_profile": body.get("eidas_profile"),
            "etsi_profile": body.get("etsi_profile"),
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
    result = adapter.notarize(payload)
    result["compliance_profile"] = resolve_notarization_compliance_profile(result)
    return result
