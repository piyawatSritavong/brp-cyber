from __future__ import annotations

import hashlib
import hmac

from app.core.config import settings
from app.services.integration_layer import list_supported_adapters, normalize_to_ocsf, verify_webhook_signature


def test_normalize_cloudflare_event_maps_to_ocsf_shape() -> None:
    payload = {
        "ClientIP": "203.0.113.10",
        "ClientRequestURI": "/admin-login",
        "EdgeResponseStatus": 403,
        "message": "WAF blocked request",
    }
    normalized = normalize_to_ocsf("cloudflare", "waf_event", payload)
    assert normalized["schema"] == "ocsf-1.1-compatible"
    assert normalized["adapter"] == "cloudflare"
    assert normalized["severity"] == "high"
    assert normalized["event_kind"] == "waf_event"
    assert normalized["actor"]["ip"] == "203.0.113.10"


def test_verify_webhook_signature_with_hmac_secret() -> None:
    original_secret = settings.integration_webhook_hmac_secret
    try:
        settings.integration_webhook_hmac_secret = "test-secret"
        body = b'{"hello":"world"}'
        signature = hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
        assert verify_webhook_signature(body, signature) is True
        assert verify_webhook_signature(body, "invalid") is False
    finally:
        settings.integration_webhook_hmac_secret = original_secret


def test_list_supported_adapters_contains_expected_sources() -> None:
    adapters = list_supported_adapters()
    assert adapters["count"] >= 5
    adapter_keys = set(adapters["adapters"].keys())
    assert {"generic", "cloudflare", "wazuh", "splunk", "crowdstrike"}.issubset(adapter_keys)

