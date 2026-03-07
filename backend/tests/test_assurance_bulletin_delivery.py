from __future__ import annotations

from app.services import control_plane_assurance_bulletin_delivery as bd


class FakeRedis:
    def __init__(self) -> None:
        self.strings: dict[str, str] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = {}
        self.counter = 0

    def set(self, key: str, value: str) -> bool:
        self.strings[key] = value
        return True

    def get(self, key: str) -> str | None:
        return self.strings.get(key)

    def xadd(self, key: str, fields: dict[str, str], maxlen: int | None = None, approximate: bool = True) -> str:
        self.counter += 1
        eid = f"{self.counter}-0"
        self.streams.setdefault(key, []).append((eid, fields))
        return eid

    def xrevrange(self, key: str, count: int = 100):
        return list(reversed(self.streams.get(key, [])))[:count]


def test_distribution_policy_and_delivery() -> None:
    fake = FakeRedis()
    bd.redis_client = fake

    upsert = bd.upsert_bulletin_distribution_policy(
        "acb",
        {
            "enabled": True,
            "signed_only": True,
            "webhook_url": "https://example.com/hook",
            "auth_header": "Bearer test",
            "timeout_seconds": 3.0,
            "retry_attempts": 2,
            "retry_backoff_seconds": 0.1,
        },
    )
    assert upsert["status"] == "upserted"

    bd.signed_tenant_risk_bulletin_status = lambda tenant_code, limit=1: {
        "tenant_code": tenant_code,
        "rows": [
            {
                "id": "1-0",
                "generated_at": "2026-01-01T00:00:00+00:00",
                "payload_hash": "abc",
                "signature": "sig",
                "scope": "assurance_tenant_bulletin:acb",
            }
        ],
    }
    bd._send_webhook = lambda webhook_url, payload, auth_header, timeout_seconds: (200, "ok")

    result = bd.deliver_signed_tenant_bulletin("acb", limit=1)
    assert result["status"] == "delivered"
    assert result["http_status"] == 200

    receipts = bd.bulletin_delivery_receipts("acb", limit=10)
    assert receipts["count"] == 1


def test_delivery_retry_path() -> None:
    fake = FakeRedis()
    bd.redis_client = fake

    bd.upsert_bulletin_distribution_policy(
        "acb",
        {
            "enabled": True,
            "signed_only": True,
            "webhook_url": "https://example.com/hook",
            "retry_attempts": 3,
            "retry_backoff_seconds": 0.1,
        },
    )
    bd.signed_tenant_risk_bulletin_status = lambda tenant_code, limit=1: {"tenant_code": tenant_code, "rows": [{"id": "1-0", "signature": "sig"}]}

    calls = {"n": 0}

    def _send(webhook_url, payload, auth_header, timeout_seconds):
        calls["n"] += 1
        if calls["n"] < 3:
            return 503, "retry"
        return 200, "ok"

    bd._send_webhook = _send
    result = bd.deliver_signed_tenant_bulletin("acb", limit=1)
    assert result["status"] == "delivered"
    assert calls["n"] == 3


def test_delivery_not_configured() -> None:
    fake = FakeRedis()
    bd.redis_client = fake
    bd.upsert_bulletin_distribution_policy("acb", {"enabled": True, "signed_only": True})
    bd.signed_tenant_risk_bulletin_status = lambda tenant_code, limit=1: {"tenant_code": tenant_code, "rows": [{"id": "1-0", "signature": "sig"}]}

    result = bd.deliver_signed_tenant_bulletin("acb", limit=1)
    assert result["status"] == "not_configured"
