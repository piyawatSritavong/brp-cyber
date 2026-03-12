from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ConnectorCredentialRotationEvent, ConnectorCredentialVault, Tenant


def _as_json(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _safe_json_load(value: str | None) -> dict[str, object]:
    if not value:
        return {}
    try:
        payload = json.loads(value)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _vault_key_bytes() -> bytes:
    material = (settings.connector_vault_master_key or settings.control_plane_bootstrap_token or "brp-connector-vault").encode("utf-8")
    return hashlib.sha256(material).digest()


def _evidence_key_bytes() -> bytes:
    material = (settings.connector_rotation_evidence_hmac_key or "brp-connector-rotation").encode("utf-8")
    return hashlib.sha256(material).digest()


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(data[i] ^ key[i % len(key)] for i in range(len(data)))


def encrypt_secret(secret_value: str) -> str:
    payload = secret_value.encode("utf-8")
    encrypted = _xor_bytes(payload, _vault_key_bytes())
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def decrypt_secret(secret_ciphertext: str) -> str:
    decoded = base64.urlsafe_b64decode(secret_ciphertext.encode("ascii"))
    plain = _xor_bytes(decoded, _vault_key_bytes())
    return plain.decode("utf-8")


def _secret_fingerprint(secret_value: str) -> str:
    return hashlib.sha256(secret_value.encode("utf-8")).hexdigest()


def _canonical_rotation_message(
    *,
    created_at: str,
    tenant_id: str,
    connector_source: str,
    credential_name: str,
    old_version: int,
    new_version: int,
    rotation_reason: str,
    prev_signature: str,
) -> str:
    return (
        f"{created_at}|{tenant_id}|{connector_source}|{credential_name}|"
        f"{old_version}|{new_version}|{rotation_reason}|{prev_signature}"
    )


def _sign_rotation_message(message: str) -> str:
    return hmac.new(_evidence_key_bytes(), message.encode("utf-8"), hashlib.sha256).hexdigest()


def _credential_row(row: ConnectorCredentialVault) -> dict[str, object]:
    metadata = _safe_json_load(row.metadata_json)
    expires_at = row.expires_at.isoformat() if row.expires_at else ""
    return {
        "credential_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "connector_source": row.connector_source,
        "credential_name": row.credential_name,
        "secret_version": row.secret_version,
        "secret_fingerprint_prefix": row.secret_fingerprint[:10],
        "external_ref": row.external_ref,
        "rotation_interval_days": row.rotation_interval_days,
        "expires_at": expires_at,
        "metadata": metadata,
        "is_active": bool(row.is_active),
        "last_rotated_at": row.last_rotated_at.isoformat() if row.last_rotated_at else "",
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    }


def _rotation_event_row(row: ConnectorCredentialRotationEvent) -> dict[str, object]:
    return {
        "event_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "connector_source": row.connector_source,
        "credential_name": row.credential_name,
        "actor": row.actor,
        "rotation_reason": row.rotation_reason,
        "old_version": row.old_version,
        "new_version": row.new_version,
        "prev_signature": row.prev_signature,
        "signature": row.signature,
        "details": _safe_json_load(row.details_json),
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }


def _create_rotation_event(
    db: Session,
    *,
    tenant_id: Any,
    connector_source: str,
    credential_name: str,
    actor: str,
    rotation_reason: str,
    old_version: int,
    new_version: int,
    details: dict[str, object],
) -> ConnectorCredentialRotationEvent:
    previous = db.scalar(
        select(ConnectorCredentialRotationEvent)
        .where(
            ConnectorCredentialRotationEvent.tenant_id == tenant_id,
            ConnectorCredentialRotationEvent.connector_source == connector_source,
            ConnectorCredentialRotationEvent.credential_name == credential_name,
        )
        .order_by(desc(ConnectorCredentialRotationEvent.created_at))
        .limit(1)
    )
    prev_signature = previous.signature if previous else ""
    created_at = datetime.now(timezone.utc)
    message = _canonical_rotation_message(
        created_at=created_at.isoformat(),
        tenant_id=str(tenant_id),
        connector_source=connector_source,
        credential_name=credential_name,
        old_version=old_version,
        new_version=new_version,
        rotation_reason=rotation_reason,
        prev_signature=prev_signature,
    )
    signature = _sign_rotation_message(message)
    event = ConnectorCredentialRotationEvent(
        tenant_id=tenant_id,
        connector_source=connector_source,
        credential_name=credential_name,
        actor=actor[:128],
        rotation_reason=rotation_reason[:255],
        old_version=max(0, int(old_version)),
        new_version=max(1, int(new_version)),
        prev_signature=prev_signature,
        signature=signature,
        details_json=_as_json(details),
        created_at=created_at,
    )
    db.add(event)
    return event


def upsert_connector_credential(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str,
    credential_name: str,
    secret_value: str,
    rotation_interval_days: int = 30,
    external_ref: str = "",
    expires_at: datetime | None = None,
    metadata: dict[str, object] | None = None,
    actor: str = "policy_editor",
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}
    source = connector_source.strip().lower() or "generic"
    name = credential_name.strip().lower() or "default"
    interval_days = max(1, min(int(rotation_interval_days), 365))
    now = datetime.now(timezone.utc)
    expiration = expires_at or (now + timedelta(days=interval_days))
    fingerprint = _secret_fingerprint(secret_value)
    cipher = encrypt_secret(secret_value)
    meta = metadata or {}

    row = db.scalar(
        select(ConnectorCredentialVault).where(
            ConnectorCredentialVault.tenant_id == tenant.id,
            ConnectorCredentialVault.connector_source == source,
            ConnectorCredentialVault.credential_name == name,
        )
    )
    if row:
        old_version = row.secret_version
        changed = row.secret_fingerprint != fingerprint or row.external_ref != external_ref
        if changed:
            row.secret_version = max(1, old_version + 1)
            row.secret_fingerprint = fingerprint
            row.secret_ciphertext = cipher
            row.last_rotated_at = now
            _create_rotation_event(
                db,
                tenant_id=tenant.id,
                connector_source=source,
                credential_name=name,
                actor=actor,
                rotation_reason="manual_upsert",
                old_version=old_version,
                new_version=row.secret_version,
                details={"source": "upsert", "changed": True},
            )
        row.external_ref = external_ref[:255]
        row.rotation_interval_days = interval_days
        row.expires_at = expiration
        row.metadata_json = _as_json(meta)
        row.is_active = True
        row.updated_at = now
        db.commit()
        db.refresh(row)
        return {"status": "updated", "credential": _credential_row(row)}

    created = ConnectorCredentialVault(
        tenant_id=tenant.id,
        connector_source=source,
        credential_name=name,
        secret_ciphertext=cipher,
        secret_fingerprint=fingerprint,
        secret_version=1,
        external_ref=external_ref[:255],
        rotation_interval_days=interval_days,
        expires_at=expiration,
        metadata_json=_as_json(meta),
        is_active=True,
        last_rotated_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(created)
    db.flush()
    _create_rotation_event(
        db,
        tenant_id=tenant.id,
        connector_source=source,
        credential_name=name,
        actor=actor,
        rotation_reason="initial_create",
        old_version=0,
        new_version=1,
        details={"source": "upsert", "changed": True},
    )
    db.commit()
    db.refresh(created)
    return {"status": "created", "credential": _credential_row(created)}


def list_connector_credentials(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str = "",
    limit: int = 200,
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"count": 0, "rows": []}
    stmt = (
        select(ConnectorCredentialVault)
        .where(ConnectorCredentialVault.tenant_id == tenant.id)
        .order_by(desc(ConnectorCredentialVault.updated_at))
        .limit(max(1, min(limit, 2000)))
    )
    if connector_source:
        stmt = stmt.where(ConnectorCredentialVault.connector_source == connector_source.strip().lower())
    rows = db.scalars(stmt).all()
    return {"count": len(rows), "rows": [_credential_row(row) for row in rows]}


def rotate_connector_credential(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str,
    credential_name: str,
    new_secret_value: str = "",
    rotation_reason: str = "scheduled_rotation",
    actor: str = "approver",
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}
    source = connector_source.strip().lower() or "generic"
    name = credential_name.strip().lower() or "default"
    row = db.scalar(
        select(ConnectorCredentialVault).where(
            ConnectorCredentialVault.tenant_id == tenant.id,
            ConnectorCredentialVault.connector_source == source,
            ConnectorCredentialVault.credential_name == name,
        )
    )
    if not row:
        return {"status": "credential_not_found", "tenant_code": tenant_code, "connector_source": source, "credential_name": name}

    secret_value = new_secret_value.strip() or secrets.token_urlsafe(32)
    old_version = row.secret_version
    row.secret_version = max(1, row.secret_version + 1)
    row.secret_fingerprint = _secret_fingerprint(secret_value)
    row.secret_ciphertext = encrypt_secret(secret_value)
    row.last_rotated_at = datetime.now(timezone.utc)
    row.updated_at = row.last_rotated_at
    row.expires_at = row.last_rotated_at + timedelta(days=max(1, row.rotation_interval_days))
    row.is_active = True
    _create_rotation_event(
        db,
        tenant_id=tenant.id,
        connector_source=source,
        credential_name=name,
        actor=actor,
        rotation_reason=rotation_reason,
        old_version=old_version,
        new_version=row.secret_version,
        details={"source": "rotate", "generated_secret": not bool(new_secret_value.strip())},
    )
    db.commit()
    db.refresh(row)
    return {
        "status": "rotated",
        "credential": _credential_row(row),
        "generated_secret": not bool(new_secret_value.strip()),
    }


def list_connector_rotation_events(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str = "",
    credential_name: str = "",
    limit: int = 200,
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"count": 0, "rows": []}
    stmt = (
        select(ConnectorCredentialRotationEvent)
        .where(ConnectorCredentialRotationEvent.tenant_id == tenant.id)
        .order_by(desc(ConnectorCredentialRotationEvent.created_at))
        .limit(max(1, min(limit, 5000)))
    )
    if connector_source:
        stmt = stmt.where(ConnectorCredentialRotationEvent.connector_source == connector_source.strip().lower())
    if credential_name:
        stmt = stmt.where(ConnectorCredentialRotationEvent.credential_name == credential_name.strip().lower())
    rows = db.scalars(stmt).all()
    return {"count": len(rows), "rows": [_rotation_event_row(row) for row in rows]}


def verify_connector_rotation_chain(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str = "",
    credential_name: str = "",
    limit: int = 5000,
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"valid": False, "reason": "tenant_not_found", "tenant_code": tenant_code}
    stmt = (
        select(ConnectorCredentialRotationEvent)
        .where(ConnectorCredentialRotationEvent.tenant_id == tenant.id)
        .order_by(asc(ConnectorCredentialRotationEvent.created_at))
        .limit(max(1, min(limit, 10000)))
    )
    if connector_source:
        stmt = stmt.where(ConnectorCredentialRotationEvent.connector_source == connector_source.strip().lower())
    if credential_name:
        stmt = stmt.where(ConnectorCredentialRotationEvent.credential_name == credential_name.strip().lower())
    rows = db.scalars(stmt).all()

    prev_signature = ""
    for index, row in enumerate(rows):
        if row.prev_signature != prev_signature:
            return {
                "valid": False,
                "index": index,
                "reason": "prev_signature_mismatch",
                "expected_prev_signature": prev_signature,
                "actual_prev_signature": row.prev_signature,
            }
        message = _canonical_rotation_message(
            created_at=row.created_at.isoformat() if row.created_at else "",
            tenant_id=str(row.tenant_id),
            connector_source=row.connector_source,
            credential_name=row.credential_name,
            old_version=row.old_version,
            new_version=row.new_version,
            rotation_reason=row.rotation_reason,
            prev_signature=row.prev_signature,
        )
        expected_signature = _sign_rotation_message(message)
        if expected_signature != row.signature:
            return {
                "valid": False,
                "index": index,
                "reason": "signature_mismatch",
            }
        prev_signature = row.signature

    return {
        "valid": True,
        "count": len(rows),
        "last_signature": prev_signature,
    }


def _hygiene_tier(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _hygiene_recommendation(tier: str) -> str:
    if tier == "critical":
        return "Rotate now, verify connector authentication, and run post-rotation health validation."
    if tier == "high":
        return "Rotate within 24 hours and validate delivery path against retry/dead-letter signals."
    if tier == "medium":
        return "Plan scheduled rotation in maintenance window and tighten expiration thresholds."
    return "Credential posture healthy. Continue periodic hygiene checks."


def _credential_hygiene_row(
    row: ConnectorCredentialVault,
    *,
    now: datetime,
    warning_days: int,
) -> dict[str, object]:
    expires_at = row.expires_at
    expires_in_days: int | None = None
    if expires_at:
        expires_in_days = int((expires_at - now).total_seconds() // 86400)

    baseline_ts = row.last_rotated_at or row.updated_at or row.created_at or now
    age_days = max(0, int((now - baseline_ts).total_seconds() // 86400))
    rotation_due = age_days >= max(1, int(row.rotation_interval_days))
    expires_soon = expires_in_days is not None and expires_in_days <= warning_days
    expired = expires_at is not None and expires_at <= now
    inactive = not bool(row.is_active)

    severity = "low"
    if inactive or expired:
        severity = "critical"
    elif expires_soon:
        severity = "high"
    elif rotation_due:
        severity = "medium"

    score_map = {"low": 10, "medium": 45, "high": 75, "critical": 95}
    risk_score = int(score_map.get(severity, 10))
    if expired:
        risk_score = 100

    return {
        "credential_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "connector_source": row.connector_source,
        "credential_name": row.credential_name,
        "secret_version": int(row.secret_version),
        "is_active": bool(row.is_active),
        "rotation_interval_days": int(row.rotation_interval_days),
        "age_days": age_days,
        "expires_at": expires_at.isoformat() if expires_at else "",
        "expires_in_days": expires_in_days,
        "rotation_due": rotation_due,
        "expires_soon": bool(expires_soon),
        "expired": bool(expired),
        "severity": severity,
        "risk_score": risk_score,
        "recommendation": _hygiene_recommendation(severity),
    }


def evaluate_connector_credential_hygiene(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str = "",
    limit: int = 200,
    warning_days: int = 7,
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}
    now = datetime.now(timezone.utc)
    warn_days = max(1, min(int(warning_days), 90))
    stmt = (
        select(ConnectorCredentialVault)
        .where(ConnectorCredentialVault.tenant_id == tenant.id)
        .order_by(desc(ConnectorCredentialVault.updated_at))
        .limit(max(1, min(limit, 2000)))
    )
    if connector_source:
        stmt = stmt.where(ConnectorCredentialVault.connector_source == connector_source.strip().lower())
    rows = db.scalars(stmt).all()
    hygiene_rows = [_credential_hygiene_row(row, now=now, warning_days=warn_days) for row in rows]

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    expired_count = 0
    due_count = 0
    max_risk_score = 0
    weighted_total = 0
    for row in hygiene_rows:
        severity = str(row.get("severity", "low"))
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        if bool(row.get("expired", False)):
            expired_count += 1
        if bool(row.get("rotation_due", False)) or bool(row.get("expires_soon", False)):
            due_count += 1
        score = int(row.get("risk_score", 0))
        weighted_total += score
        max_risk_score = max(max_risk_score, score)
    average_score = int(round(weighted_total / len(hygiene_rows))) if hygiene_rows else 0
    overall_score = max(max_risk_score, average_score)
    tier = _hygiene_tier(overall_score)

    return {
        "status": "ok",
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.tenant_code,
        "count": len(hygiene_rows),
        "summary": {
            "severity_counts": severity_counts,
            "expired_count": expired_count,
            "rotation_due_count": due_count,
            "warning_days": warn_days,
        },
        "risk": {
            "risk_score": overall_score,
            "risk_tier": tier,
            "recommendation": _hygiene_recommendation(tier),
        },
        "rows": hygiene_rows,
        "generated_at": now.isoformat(),
    }


def auto_rotate_due_credentials(
    db: Session,
    *,
    tenant_code: str,
    connector_source: str = "",
    warning_days: int = 7,
    max_rotate: int = 20,
    dry_run: bool = True,
    actor: str = "credential_guard_ai",
) -> dict[str, object]:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_code == tenant_code))
    if not tenant:
        return {"status": "tenant_not_found", "tenant_code": tenant_code}

    now = datetime.now(timezone.utc)
    warn_days = max(1, min(int(warning_days), 90))
    rotate_limit = max(1, min(int(max_rotate), 200))

    stmt = (
        select(ConnectorCredentialVault)
        .where(ConnectorCredentialVault.tenant_id == tenant.id)
        .order_by(desc(ConnectorCredentialVault.updated_at))
        .limit(2000)
    )
    if connector_source:
        stmt = stmt.where(ConnectorCredentialVault.connector_source == connector_source.strip().lower())
    rows = db.scalars(stmt).all()
    hygiene_rows = [_credential_hygiene_row(row, now=now, warning_days=warn_days) for row in rows if bool(row.is_active)]
    candidates = [
        row
        for row in hygiene_rows
        if bool(row.get("expired", False))
        or bool(row.get("expires_soon", False))
        or bool(row.get("rotation_due", False))
    ]
    severity_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    candidates.sort(
        key=lambda row: (
            severity_rank.get(str(row.get("severity", "low")), 0),
            -int(row.get("risk_score", 0)),
            -(9999 if row.get("expires_in_days") is None else int(row.get("expires_in_days", 0))),
        ),
        reverse=True,
    )
    selected = candidates[:rotate_limit]

    actions: list[dict[str, object]] = []
    executed_count = 0
    planned_count = 0
    failed_count = 0

    for candidate in selected:
        connector = str(candidate.get("connector_source", ""))
        name = str(candidate.get("credential_name", ""))
        if dry_run:
            planned_count += 1
            actions.append(
                {
                    "connector_source": connector,
                    "credential_name": name,
                    "status": "planned",
                    "reason": "dry_run",
                    "severity": candidate.get("severity", "medium"),
                }
            )
            continue
        result = rotate_connector_credential(
            db,
            tenant_code=tenant_code,
            connector_source=connector,
            credential_name=name,
            new_secret_value="",
            rotation_reason="hygiene_auto_rotation",
            actor=actor,
        )
        if result.get("status") == "rotated":
            executed_count += 1
        else:
            failed_count += 1
        actions.append(
            {
                "connector_source": connector,
                "credential_name": name,
                "status": result.get("status", "unknown"),
                "severity": candidate.get("severity", "medium"),
            }
        )

    return {
        "status": "ok",
        "tenant_id": str(tenant.id),
        "tenant_code": tenant.tenant_code,
        "dry_run": bool(dry_run),
        "warning_days": warn_days,
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "planned_count": planned_count,
        "executed_count": executed_count,
        "failed_count": failed_count,
        "actions": actions,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def federation_connector_credential_hygiene(
    db: Session,
    *,
    limit: int = 200,
    warning_days: int = 7,
) -> dict[str, object]:
    max_rows = max(1, min(int(limit), 500))
    tenants = db.scalars(select(Tenant).order_by(desc(Tenant.created_at)).limit(max_rows)).all()

    rows: list[dict[str, object]] = []
    tier_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    total_credentials = 0
    total_due = 0
    total_expired = 0
    for tenant in tenants:
        snapshot = evaluate_connector_credential_hygiene(
            db,
            tenant_code=tenant.tenant_code,
            warning_days=warning_days,
            limit=2000,
        )
        if snapshot.get("status") != "ok":
            continue
        summary = snapshot.get("summary", {})
        risk = snapshot.get("risk", {})
        count = int(snapshot.get("count", 0))
        due_count = int(summary.get("rotation_due_count", 0))
        expired_count = int(summary.get("expired_count", 0))
        tier = str(risk.get("risk_tier", "low"))
        row = {
            "tenant_id": str(tenant.id),
            "tenant_code": tenant.tenant_code,
            "credential_count": count,
            "rotation_due_count": due_count,
            "expired_count": expired_count,
            "risk_score": int(risk.get("risk_score", 0)),
            "risk_tier": tier,
            "recommendation": str(risk.get("recommendation", "")),
        }
        rows.append(row)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        total_credentials += count
        total_due += due_count
        total_expired += expired_count

    rows.sort(key=lambda item: (item["risk_score"], item["expired_count"], item["rotation_due_count"]), reverse=True)
    return {
        "count": len(rows),
        "tier_counts": tier_counts,
        "summary": {
            "total_credentials": total_credentials,
            "total_rotation_due": total_due,
            "total_expired": total_expired,
        },
        "rows": rows,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
