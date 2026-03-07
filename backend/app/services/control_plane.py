from __future__ import annotations

import hashlib
import secrets
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import Tenant, TenantApiKey
from app.services.enterprise.objective_gate import evaluate_and_persist_objective_gate, objective_gate_remediation_plan
from app.services.enterprise.quotas import set_quota
from app.services.orchestrator import apply_strategy_profile
from schemas.control_plane import TenantOnboardRequest, TenantQuotaBootstrap


ACTIVE = "active"
SUSPENDED = "suspended"


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _generate_api_key() -> tuple[str, str, str]:
    raw_key = f"brp_{secrets.token_urlsafe(24)}"
    key_id = f"key_{uuid4().hex[:12]}"
    return key_id, raw_key, _hash_key(raw_key)


def onboard_tenant(db: Session, payload: TenantOnboardRequest, quota: TenantQuotaBootstrap) -> dict[str, object]:
    existing = db.query(Tenant).filter(Tenant.tenant_code == payload.tenant_code).first()
    if existing:
        return {
            "status": "exists",
            "tenant_id": str(existing.id),
            "tenant_code": existing.tenant_code,
            "display_name": existing.display_name,
        }

    tenant = Tenant(tenant_code=payload.tenant_code, display_name=payload.display_name, status=ACTIVE)
    db.add(tenant)
    db.flush()

    key_id, raw_key, key_hash = _generate_api_key()
    api_key = TenantApiKey(tenant_id=tenant.id, key_id=key_id, key_hash=key_hash, is_active=True)
    db.add(api_key)
    db.commit()
    db.refresh(tenant)

    set_quota(
        tenant.id,
        events_per_month=quota.events_per_month,
        actions_per_day=quota.actions_per_day,
        tokens_per_month=quota.tokens_per_month,
    )
    apply_strategy_profile(tenant.id, payload.strategy_profile)

    return {
        "status": "created",
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.tenant_code,
        "display_name": tenant.display_name,
        "strategy_profile": payload.strategy_profile,
        "api_key_id": key_id,
        "api_key_secret": raw_key,
        "note": "Store api_key_secret now; it is not retrievable later.",
    }


def tenant_detail_by_id(db: Session, tenant_id) -> dict[str, object]:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        return {"status": "not_found", "tenant_id": str(tenant_id)}

    return {
        "status": "ok",
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.tenant_code,
        "display_name": tenant.display_name,
        "status_value": tenant.status,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else "",
    }


def update_tenant_status(
    db: Session,
    tenant_code: str,
    status: str,
    bypass_objective_gate: bool = False,
) -> dict[str, object]:
    tenant = db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}

    if status == "production" and not bypass_objective_gate:
        gate = evaluate_and_persist_objective_gate(tenant.id)
        if not gate.get("overall_pass"):
            return {
                "status": "blocked_by_objective_gate",
                "tenant_id": str(tenant.id),
                "tenant_code": tenant.tenant_code,
                "requested_status": status,
                "objective_gate": gate,
                "remediation": objective_gate_remediation_plan(gate),
            }

    tenant.status = status
    db.commit()
    db.refresh(tenant)

    return {
        "status": "updated",
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.tenant_code,
        "status_value": tenant.status,
        "objective_gate_enforced": status == "production" and not bypass_objective_gate,
    }


def rotate_tenant_api_key(db: Session, tenant_code: str) -> dict[str, object]:
    tenant = db.query(Tenant).filter(Tenant.tenant_code == tenant_code).first()
    if not tenant:
        return {"status": "not_found", "tenant_code": tenant_code}

    active_keys = db.query(TenantApiKey).filter(TenantApiKey.tenant_id == tenant.id, TenantApiKey.is_active.is_(True)).all()
    for key in active_keys:
        key.is_active = False

    key_id, raw_key, key_hash = _generate_api_key()
    api_key = TenantApiKey(tenant_id=tenant.id, key_id=key_id, key_hash=key_hash, is_active=True)
    db.add(api_key)
    db.commit()

    return {
        "status": "rotated",
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.tenant_code,
        "new_api_key_id": key_id,
        "new_api_key_secret": raw_key,
        "deactivated_keys": len(active_keys),
        "note": "Store new_api_key_secret now; it is not retrievable later.",
    }
