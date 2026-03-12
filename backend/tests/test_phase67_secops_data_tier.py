from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services import connector_credential_vault, secops_data_tier


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _SequencedDB:
    def __init__(self, scalar_values=None, scalar_batches=None):
        self.scalar_values = list(scalar_values or [])
        self.scalar_batches = list(scalar_batches or [])

    def scalar(self, _stmt):
        if not self.scalar_values:
            return None
        return self.scalar_values.pop(0)

    def scalars(self, _stmt):
        rows = self.scalar_batches.pop(0) if self.scalar_batches else []
        return _FakeScalarResult(rows)


@dataclass
class _ConnectorRow:
    payload_json: str
    error_message: str
    latency_ms: int
    event_type: str
    created_at: datetime


@dataclass
class _IntegrationRow:
    raw_payload_json: str
    normalized_payload_json: str
    created_at: datetime


@dataclass
class _BlueRow:
    payload_json: str
    ai_recommendation: str
    created_at: datetime


@dataclass
class _RotationEvent:
    tenant_id: object
    connector_source: str
    credential_name: str
    old_version: int
    new_version: int
    rotation_reason: str
    prev_signature: str
    signature: str
    created_at: datetime


@dataclass
class _CredentialRow:
    id: object
    tenant_id: object
    connector_source: str
    credential_name: str
    secret_version: int
    secret_fingerprint: str
    external_ref: str
    rotation_interval_days: int
    expires_at: datetime | None
    metadata_json: str
    is_active: bool
    last_rotated_at: datetime
    created_at: datetime
    updated_at: datetime


def _build_signed_rotation_event(
    *,
    tenant_id,
    connector_source: str,
    credential_name: str,
    old_version: int,
    new_version: int,
    rotation_reason: str,
    prev_signature: str,
    created_at: datetime,
) -> _RotationEvent:
    message = connector_credential_vault._canonical_rotation_message(
        created_at=created_at.isoformat(),
        tenant_id=str(tenant_id),
        connector_source=connector_source,
        credential_name=credential_name,
        old_version=old_version,
        new_version=new_version,
        rotation_reason=rotation_reason,
        prev_signature=prev_signature,
    )
    signature = connector_credential_vault._sign_rotation_message(message)
    return _RotationEvent(
        tenant_id=tenant_id,
        connector_source=connector_source,
        credential_name=credential_name,
        old_version=old_version,
        new_version=new_version,
        rotation_reason=rotation_reason,
        prev_signature=prev_signature,
        signature=signature,
        created_at=created_at,
    )


def test_verify_connector_rotation_chain_accepts_valid_signature_chain() -> None:
    tenant = SimpleNamespace(id=uuid4(), tenant_code="acb")
    now = datetime.now(timezone.utc)
    event1 = _build_signed_rotation_event(
        tenant_id=tenant.id,
        connector_source="splunk",
        credential_name="api_key",
        old_version=0,
        new_version=1,
        rotation_reason="initial_create",
        prev_signature="",
        created_at=now,
    )
    event2 = _build_signed_rotation_event(
        tenant_id=tenant.id,
        connector_source="splunk",
        credential_name="api_key",
        old_version=1,
        new_version=2,
        rotation_reason="scheduled_rotation",
        prev_signature=event1.signature,
        created_at=now + timedelta(seconds=10),
    )
    db = _SequencedDB(scalar_values=[tenant], scalar_batches=[[event1, event2]])

    result = connector_credential_vault.verify_connector_rotation_chain(
        db,
        tenant_code="acb",
        connector_source="splunk",
        credential_name="api_key",
    )
    assert result["valid"] is True
    assert result["count"] == 2
    assert result["last_signature"] == event2.signature


def test_verify_connector_rotation_chain_rejects_prev_signature_mismatch() -> None:
    tenant = SimpleNamespace(id=uuid4(), tenant_code="acb")
    now = datetime.now(timezone.utc)
    event1 = _build_signed_rotation_event(
        tenant_id=tenant.id,
        connector_source="splunk",
        credential_name="api_key",
        old_version=0,
        new_version=1,
        rotation_reason="initial_create",
        prev_signature="",
        created_at=now,
    )
    event2 = _build_signed_rotation_event(
        tenant_id=tenant.id,
        connector_source="splunk",
        credential_name="api_key",
        old_version=1,
        new_version=2,
        rotation_reason="scheduled_rotation",
        prev_signature="tampered_prev_signature",
        created_at=now + timedelta(seconds=10),
    )
    db = _SequencedDB(scalar_values=[tenant], scalar_batches=[[event1, event2]])

    result = connector_credential_vault.verify_connector_rotation_chain(
        db,
        tenant_code="acb",
        connector_source="splunk",
        credential_name="api_key",
    )
    assert result["valid"] is False
    assert result["reason"] == "prev_signature_mismatch"
    assert result["index"] == 1


def test_tenant_data_tier_benchmark_returns_cost_and_risk_shape() -> None:
    now = datetime.now(timezone.utc)
    tenant = SimpleNamespace(id=uuid4(), tenant_code="acb")
    site_id = uuid4()
    connector_rows = [
        _ConnectorRow(payload_json="{}", error_message="", latency_ms=120, event_type="delivery_attempt", created_at=now),
        _ConnectorRow(payload_json="{}", error_message="timeout", latency_ms=420, event_type="dead_letter", created_at=now),
    ]
    integration_rows = [
        _IntegrationRow(raw_payload_json='{"raw":1}', normalized_payload_json='{"n":1}', created_at=now),
    ]
    blue_rows = [
        _BlueRow(payload_json='{"evt":"waf"}', ai_recommendation="block_ip", created_at=now),
    ]
    db = _SequencedDB(
        scalar_values=[tenant, 1200, 400, 300],
        scalar_batches=[
            [site_id],
            connector_rows,
            integration_rows,
            blue_rows,
            blue_rows,
        ],
    )

    result = secops_data_tier.tenant_data_tier_benchmark(db, tenant_code="acb", lookback_hours=24, sample_limit=2000)
    assert result["status"] == "ok"
    assert result["tenant_code"] == "acb"
    assert result["event_counts"]["total_events"] == 1900
    assert result["performance"]["dead_letter_count"] == 1
    assert result["cost"]["monthly_total_cost_usd"] >= 0
    assert result["risk"]["risk_tier"] in {"low", "medium", "high", "critical"}
    assert len(result["retention"]["event_trend_hourly"]) > 0


def test_federation_data_tier_benchmark_aggregates_multi_tenant(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    tenants = [
        SimpleNamespace(id=uuid4(), tenant_code="acb", created_at=now),
        SimpleNamespace(id=uuid4(), tenant_code="zeta", created_at=now - timedelta(minutes=1)),
    ]
    db = _SequencedDB(scalar_batches=[tenants])

    def _fake_tenant_benchmark(_db, *, tenant_code: str, lookback_hours: int = 24):
        if tenant_code == "acb":
            return {
                "status": "ok",
                "tenant_id": str(tenants[0].id),
                "performance": {"throughput_eps": 320.0, "ingest_avg_latency_ms": 120.0, "search_latency_p95_ms": 150.0},
                "cost": {"monthly_total_cost_usd": 22.5},
                "risk": {"risk_score": 22, "risk_tier": "low", "recommendation": "healthy"},
            }
        return {
            "status": "ok",
            "tenant_id": str(tenants[1].id),
            "performance": {"throughput_eps": 110.0, "ingest_avg_latency_ms": 380.0, "search_latency_p95_ms": 480.0},
            "cost": {"monthly_total_cost_usd": 68.0},
            "risk": {"risk_score": 85, "risk_tier": "critical", "recommendation": "tighten"},
        }

    monkeypatch.setattr(secops_data_tier, "tenant_data_tier_benchmark", _fake_tenant_benchmark)

    result = secops_data_tier.federation_data_tier_benchmark(db, lookback_hours=24, limit=200)
    assert result["count"] == 2
    assert result["rows"][0]["tenant_code"] == "zeta"
    assert result["rows"][0]["risk_tier"] == "critical"
    assert result["tier_counts"]["critical"] == 1
    assert result["summary"]["total_monthly_cost_usd"] == 90.5


def test_evaluate_connector_credential_hygiene_marks_due_and_expired() -> None:
    now = datetime.now(timezone.utc)
    tenant = SimpleNamespace(id=uuid4(), tenant_code="acb")
    rows = [
        _CredentialRow(
            id=uuid4(),
            tenant_id=tenant.id,
            connector_source="splunk",
            credential_name="api_key",
            secret_version=2,
            secret_fingerprint="f" * 64,
            external_ref="",
            rotation_interval_days=30,
            expires_at=now - timedelta(days=1),
            metadata_json="{}",
            is_active=True,
            last_rotated_at=now - timedelta(days=31),
            created_at=now - timedelta(days=100),
            updated_at=now - timedelta(days=10),
        ),
        _CredentialRow(
            id=uuid4(),
            tenant_id=tenant.id,
            connector_source="sentinel",
            credential_name="token",
            secret_version=1,
            secret_fingerprint="a" * 64,
            external_ref="",
            rotation_interval_days=15,
            expires_at=now + timedelta(days=3),
            metadata_json="{}",
            is_active=True,
            last_rotated_at=now - timedelta(days=10),
            created_at=now - timedelta(days=20),
            updated_at=now - timedelta(days=1),
        ),
    ]
    db = _SequencedDB(scalar_values=[tenant], scalar_batches=[rows])
    result = connector_credential_vault.evaluate_connector_credential_hygiene(
        db,
        tenant_code="acb",
        warning_days=7,
        limit=200,
    )
    assert result["status"] == "ok"
    assert result["count"] == 2
    assert result["summary"]["expired_count"] == 1
    assert result["summary"]["rotation_due_count"] >= 1
    assert result["risk"]["risk_tier"] in {"high", "critical"}


def test_auto_rotate_due_credentials_respects_dry_run_and_apply(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    tenant = SimpleNamespace(id=uuid4(), tenant_code="acb")
    rows = [
        _CredentialRow(
            id=uuid4(),
            tenant_id=tenant.id,
            connector_source="splunk",
            credential_name="api_key",
            secret_version=2,
            secret_fingerprint="f" * 64,
            external_ref="",
            rotation_interval_days=30,
            expires_at=now - timedelta(days=1),
            metadata_json="{}",
            is_active=True,
            last_rotated_at=now - timedelta(days=31),
            created_at=now - timedelta(days=100),
            updated_at=now - timedelta(days=10),
        )
    ]

    dry_db = _SequencedDB(scalar_values=[tenant], scalar_batches=[rows])
    dry_result = connector_credential_vault.auto_rotate_due_credentials(
        dry_db,
        tenant_code="acb",
        warning_days=7,
        dry_run=True,
        max_rotate=20,
        actor="test_actor",
    )
    assert dry_result["status"] == "ok"
    assert dry_result["candidate_count"] == 1
    assert dry_result["planned_count"] == 1
    assert dry_result["executed_count"] == 0

    calls = []

    def _fake_rotate(_db, **kwargs):
        calls.append(kwargs)
        return {"status": "rotated", "credential": {"secret_version": 3}, "generated_secret": True}

    monkeypatch.setattr(connector_credential_vault, "rotate_connector_credential", _fake_rotate)
    apply_db = _SequencedDB(scalar_values=[tenant], scalar_batches=[rows])
    apply_result = connector_credential_vault.auto_rotate_due_credentials(
        apply_db,
        tenant_code="acb",
        warning_days=7,
        dry_run=False,
        max_rotate=20,
        actor="test_actor",
    )
    assert apply_result["status"] == "ok"
    assert apply_result["executed_count"] == 1
    assert len(calls) == 1
    assert calls[0]["connector_source"] == "splunk"


def test_federation_connector_credential_hygiene_aggregates_rows(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    tenants = [
        SimpleNamespace(id=uuid4(), tenant_code="acb", created_at=now),
        SimpleNamespace(id=uuid4(), tenant_code="zeta", created_at=now - timedelta(minutes=1)),
    ]
    db = _SequencedDB(scalar_batches=[tenants])

    def _fake_hygiene(_db, *, tenant_code: str, connector_source: str = "", warning_days: int = 7, limit: int = 200):
        if tenant_code == "acb":
            return {
                "status": "ok",
                "count": 2,
                "summary": {"rotation_due_count": 1, "expired_count": 0, "severity_counts": {}, "warning_days": warning_days},
                "risk": {"risk_score": 35, "risk_tier": "medium", "recommendation": "plan"},
            }
        return {
            "status": "ok",
            "count": 3,
            "summary": {"rotation_due_count": 3, "expired_count": 1, "severity_counts": {}, "warning_days": warning_days},
            "risk": {"risk_score": 92, "risk_tier": "critical", "recommendation": "rotate now"},
        }

    monkeypatch.setattr(connector_credential_vault, "evaluate_connector_credential_hygiene", _fake_hygiene)
    result = connector_credential_vault.federation_connector_credential_hygiene(db, limit=200, warning_days=7)
    assert result["count"] == 2
    assert result["rows"][0]["tenant_code"] == "zeta"
    assert result["tier_counts"]["critical"] == 1
    assert result["summary"]["total_credentials"] == 5
