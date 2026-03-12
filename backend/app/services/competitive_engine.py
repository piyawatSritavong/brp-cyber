from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import (
    BlueDetectionRule,
    BlueDetectionTuningRun,
    BlueEventLog,
    ConnectorDeliveryEvent,
    ConnectorReliabilityRun,
    PhaseObjectiveCheck,
    PurpleInsightReport,
    RedExploitPathRun,
    RedScanRun,
    Site,
    SoarPlaybookExecution,
    ThreatContentPack,
)
from schemas.competitive import (
    DetectionCopilotTuneRequest,
    ExploitPathSimulationRequest,
    PhaseObjectiveCheckRequest,
    ThreatContentPackUpsertRequest,
)

ROADMAP_OBJECTIVES: dict[str, dict[str, str]] = {
    "O1": {
        "title": "Exploit-Path Validation Engine",
        "description": "Attack-path chaining with proof of exploitability and safe-mode guardrails.",
    },
    "O2": {
        "title": "Continuous Threat Content Pipeline",
        "description": "MITRE-mapped attack packs for ransomware, identity abuse, and emerging scenarios.",
    },
    "O3": {
        "title": "Detection Engineering Copilot",
        "description": "AI-generated detection logic with before/after validation against Red findings.",
    },
    "O4": {
        "title": "SOAR Playbook Hub + Marketplace",
        "description": "One-click response playbooks with policy, approval, and versioning workflows.",
    },
    "O5": {
        "title": "High-Speed SecOps Data Layer",
        "description": "Fast ingestion/search/retention tiers with cost-aware operations.",
    },
    "O6": {
        "title": "Unified Case Graph",
        "description": "Correlate alerts, assets, exploit paths, and response actions in one graph.",
    },
    "O7": {
        "title": "Autonomous Blue Agent with Guardrails",
        "description": "Policy-gated auto containment with rollback, dual-control, and audit chain.",
    },
    "O8": {
        "title": "Purple Executive Product",
        "description": "MITRE heatmap, ISO/NIST gaps, remediation SLA tracking, and board-ready reports.",
    },
    "O9": {
        "title": "Connector Program",
        "description": "Production connectors with health, retry, dead-letter, and observability.",
    },
    "O10": {
        "title": "MSSP-Ready Multi-Tenant Operations",
        "description": "Tenant isolation, delegated admin, billing attribution, and white-label readiness.",
    },
}

TOP_PRIORITY_OBJECTIVE_IDS = ["O1", "O3", "O4", "O5", "O6", "O8"]

OBJECTIVE_KEYWORDS: dict[str, list[str]] = {
    "O1": ["exploit", "attack path", "proof", "safe mode", "validation"],
    "O2": ["threat pack", "mitre", "pipeline", "ransomware", "identity"],
    "O3": ["detection", "rule", "copilot", "coverage", "tuning"],
    "O4": ["playbook", "soar", "marketplace", "approval"],
    "O5": ["ingest", "search", "retention", "cost", "speed"],
    "O6": ["case graph", "graph", "correlate", "unified case"],
    "O7": ["autonomous blue", "containment", "rollback", "guardrail"],
    "O8": ["purple", "executive", "iso", "nist", "heatmap", "sla"],
    "O9": ["connector", "integration", "webhook", "retry", "dead-letter"],
    "O10": ["mssp", "multi-tenant", "rbac", "white-label", "billing"],
}


def _as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _safe_json_load(value: str | None) -> Any:
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {}


def _safe_json_dict(value: str | None) -> dict[str, Any]:
    data = _safe_json_load(value)
    return data if isinstance(data, dict) else {}


def _safe_json_list(value: str | None) -> list[Any]:
    data = _safe_json_load(value)
    return data if isinstance(data, list) else []


def list_roadmap_objectives() -> dict[str, object]:
    return {
        "count": len(ROADMAP_OBJECTIVES),
        "top_priority_objective_ids": TOP_PRIORITY_OBJECTIVE_IDS,
        "objectives": ROADMAP_OBJECTIVES,
    }


def evaluate_phase_scope(objective_ids: list[str], deliverables: list[str]) -> dict[str, object]:
    normalized = sorted({obj.strip().upper() for obj in objective_ids if obj.strip()})
    unknown = [obj for obj in normalized if obj not in ROADMAP_OBJECTIVES]
    if not normalized:
        return {
            "scope_status": "out_of_scope",
            "scope_pass": False,
            "reason": "no_objectives_declared",
            "unknown_objectives": [],
            "keyword_matches": {},
        }
    if unknown:
        return {
            "scope_status": "out_of_scope",
            "scope_pass": False,
            "reason": "unknown_objectives_detected",
            "unknown_objectives": unknown,
            "keyword_matches": {},
        }

    delivery_text = " ".join(deliverables).lower()
    keyword_matches: dict[str, int] = {}
    for objective in normalized:
        keywords = OBJECTIVE_KEYWORDS.get(objective, [])
        keyword_matches[objective] = sum(1 for keyword in keywords if keyword in delivery_text)
    relevance_hits = sum(keyword_matches.values())
    if deliverables and relevance_hits == 0:
        return {
            "scope_status": "out_of_scope",
            "scope_pass": False,
            "reason": "deliverables_not_aligned_with_declared_objectives",
            "unknown_objectives": [],
            "keyword_matches": keyword_matches,
        }
    return {
        "scope_status": "in_scope",
        "scope_pass": True,
        "reason": "validated_against_objective_catalog",
        "unknown_objectives": [],
        "keyword_matches": keyword_matches,
    }


def create_phase_scope_check(db: Session, payload: PhaseObjectiveCheckRequest) -> dict[str, object]:
    evaluation = evaluate_phase_scope(payload.objective_ids, payload.deliverables)
    row = PhaseObjectiveCheck(
        site_id=payload.site_id,
        phase_code=payload.phase_code,
        phase_title=payload.phase_title,
        objective_ids_json=_as_json(payload.objective_ids),
        deliverables_json=_as_json(payload.deliverables),
        scope_status=str(evaluation["scope_status"]),
        scope_reason=str(evaluation["reason"]),
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "status": "recorded",
        "phase_check_id": str(row.id),
        "phase_code": row.phase_code,
        "scope_status": row.scope_status,
        "scope_reason": row.scope_reason,
        "evaluation": evaluation,
        "context": payload.context,
    }


def list_phase_scope_checks(db: Session, *, limit: int = 100) -> dict[str, object]:
    rows = db.scalars(
        select(PhaseObjectiveCheck).order_by(desc(PhaseObjectiveCheck.created_at)).limit(max(1, min(limit, 1000)))
    ).all()
    return {
        "count": len(rows),
        "rows": [
            {
                "phase_check_id": str(row.id),
                "site_id": str(row.site_id) if row.site_id else "",
                "phase_code": row.phase_code,
                "phase_title": row.phase_title,
                "objective_ids": _safe_json_list(row.objective_ids_json),
                "deliverables": _safe_json_list(row.deliverables_json),
                "scope_status": row.scope_status,
                "scope_reason": row.scope_reason,
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ],
    }


def upsert_threat_content_pack(db: Session, payload: ThreatContentPackUpsertRequest) -> dict[str, object]:
    existing = db.scalar(select(ThreatContentPack).where(ThreatContentPack.pack_code == payload.pack_code))
    now = datetime.now(timezone.utc)
    if existing:
        existing.title = payload.title
        existing.category = payload.category
        existing.mitre_techniques_json = _as_json(payload.mitre_techniques)
        existing.attack_steps_json = _as_json(payload.attack_steps)
        existing.validation_mode = payload.validation_mode
        existing.is_active = payload.is_active
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return {
            "status": "updated",
            "pack": _threat_pack_row(existing),
        }

    row = ThreatContentPack(
        pack_code=payload.pack_code,
        title=payload.title,
        category=payload.category,
        mitre_techniques_json=_as_json(payload.mitre_techniques),
        attack_steps_json=_as_json(payload.attack_steps),
        validation_mode=payload.validation_mode,
        is_active=payload.is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "created", "pack": _threat_pack_row(row)}


def _threat_pack_row(row: ThreatContentPack) -> dict[str, object]:
    return {
        "pack_id": str(row.id),
        "pack_code": row.pack_code,
        "title": row.title,
        "category": row.category,
        "mitre_techniques": _safe_json_list(row.mitre_techniques_json),
        "attack_steps": _safe_json_list(row.attack_steps_json),
        "validation_mode": row.validation_mode,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    }


def list_threat_content_packs(db: Session, *, category: str = "", active_only: bool = True, limit: int = 200) -> dict[str, object]:
    stmt = select(ThreatContentPack).order_by(desc(ThreatContentPack.updated_at)).limit(max(1, min(limit, 1000)))
    if category:
        stmt = stmt.where(ThreatContentPack.category == category)
    if active_only:
        stmt = stmt.where(ThreatContentPack.is_active.is_(True))
    rows = db.scalars(stmt).all()
    return {"count": len(rows), "rows": [_threat_pack_row(row) for row in rows]}


def _infer_exploitability(findings: dict[str, Any], threat_pack: ThreatContentPack | None, request: ExploitPathSimulationRequest) -> dict[str, Any]:
    missing_headers = len(findings.get("missing_security_headers", []) or [])
    sensitive_paths = findings.get("sensitive_paths_open", []) or []
    base_risk = int(findings.get("risk_score", 0) or 0)
    pack_weight = 10 if threat_pack else 0
    risk_score = min(100, base_risk + (missing_headers * 4) + (len(sensitive_paths) * 8) + pack_weight)

    evidence: list[str] = []
    if missing_headers:
        evidence.append(f"missing_security_headers={missing_headers}")
    if sensitive_paths:
        evidence.append(f"sensitive_paths_open={len(sensitive_paths)}")
    if threat_pack:
        evidence.append(f"threat_pack={threat_pack.pack_code}")
    if not evidence:
        evidence.append("limited_external_exposure_signals")

    if risk_score >= 75:
        confidence = "high"
    elif risk_score >= 40:
        confidence = "medium"
    else:
        confidence = "low"

    nodes = [
        {"id": "n1", "name": "external_actor", "stage": "initial_access"},
        {"id": "n2", "name": "recon_target_surface", "stage": "reconnaissance"},
        {"id": "n3", "name": "credential_attack_vector", "stage": "credential_access"},
        {"id": "n4", "name": "privilege_escalation_attempt", "stage": "privilege_escalation"},
        {"id": "n5", "name": "impact_simulation", "stage": "impact"},
    ]
    edges = [
        {"from": "n1", "to": "n2", "reason": "public_attack_surface"},
        {"from": "n2", "to": "n3", "reason": request.target_surface},
        {"from": "n3", "to": "n4", "reason": "credential_reuse_or_bruteforce"},
        {"from": "n4", "to": "n5", "reason": "post_exploitation_simulation"},
    ]
    if confidence == "low":
        edges = edges[:2]

    return {
        "risk_score": risk_score,
        "confidence": confidence,
        "path_graph": {
            "nodes": nodes,
            "edges": edges,
            "simulation_depth": request.simulation_depth,
            "target_surface": request.target_surface,
        },
        "proof": {
            "exploitability_confidence": confidence,
            "path_reachable": confidence in {"high", "medium"},
            "evidence": evidence,
            "mitre_techniques": _safe_json_list(threat_pack.mitre_techniques_json) if threat_pack else [],
        },
    }


def run_exploit_path_simulation(db: Session, site_id: UUID, payload: ExploitPathSimulationRequest) -> dict[str, object]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}

    threat_pack: ThreatContentPack | None = None
    if payload.threat_pack_code:
        threat_pack = db.scalar(select(ThreatContentPack).where(ThreatContentPack.pack_code == payload.threat_pack_code))
    if not threat_pack:
        threat_pack = db.scalar(
            select(ThreatContentPack).where(ThreatContentPack.is_active.is_(True)).order_by(desc(ThreatContentPack.updated_at))
        )

    latest_scan = db.scalar(
        select(RedScanRun)
        .where(RedScanRun.site_id == site_id)
        .order_by(desc(RedScanRun.created_at))
        .limit(1)
    )
    findings = _safe_json_dict(latest_scan.findings_json) if latest_scan else {}
    inferred = _infer_exploitability(findings, threat_pack, payload)

    safe_mode = {
        "simulation_only": payload.simulation_only,
        "max_requests_per_minute": payload.max_requests_per_minute,
        "stop_on_critical": payload.stop_on_critical,
        "impact_budget": "safe",
    }
    row = RedExploitPathRun(
        site_id=site.id,
        threat_pack_id=threat_pack.id if threat_pack else None,
        status="completed",
        risk_score=int(inferred["risk_score"]),
        path_graph_json=_as_json(inferred["path_graph"]),
        proof_json=_as_json(inferred["proof"]),
        safe_mode_json=_as_json(safe_mode),
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "status": "completed",
        "run_id": str(row.id),
        "site_id": str(site.id),
        "site_code": site.site_code,
        "threat_pack_code": threat_pack.pack_code if threat_pack else "",
        "risk_score": row.risk_score,
        "path_graph": _safe_json_dict(row.path_graph_json),
        "proof": _safe_json_dict(row.proof_json),
        "safe_mode": _safe_json_dict(row.safe_mode_json),
    }


def list_exploit_path_runs(db: Session, site_id: UUID, *, limit: int = 30) -> dict[str, object]:
    rows = db.scalars(
        select(RedExploitPathRun)
        .where(RedExploitPathRun.site_id == site_id)
        .order_by(desc(RedExploitPathRun.created_at))
        .limit(max(1, min(limit, 200)))
    ).all()
    return {
        "count": len(rows),
        "rows": [
            {
                "run_id": str(row.id),
                "site_id": str(row.site_id),
                "threat_pack_id": str(row.threat_pack_id) if row.threat_pack_id else "",
                "status": row.status,
                "risk_score": row.risk_score,
                "path_graph": _safe_json_dict(row.path_graph_json),
                "proof": _safe_json_dict(row.proof_json),
                "safe_mode": _safe_json_dict(row.safe_mode_json),
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ],
    }


def _summarize_blue_baseline(events: list[BlueEventLog]) -> dict[str, float]:
    total = len(events)
    if total == 0:
        return {"event_count": 0.0, "detection_coverage": 0.5, "response_apply_rate": 0.0, "false_positive_ratio": 0.2}

    suspicious = [
        event
        for event in events
        if event.ai_severity in {"high", "medium"}
        or "brute" in event.payload_json.lower()
        or "sql" in event.payload_json.lower()
        or "ransom" in event.payload_json.lower()
    ]
    detected = [event for event in suspicious if event.ai_severity in {"high", "medium"}]
    applied = [event for event in suspicious if event.status == "applied"]
    low_events = [event for event in events if event.ai_severity == "low"]
    suspicious_total = len(suspicious)
    return {
        "event_count": float(total),
        "detection_coverage": round((len(detected) / suspicious_total) if suspicious_total else 0.5, 4),
        "response_apply_rate": round((len(applied) / suspicious_total) if suspicious_total else 0.0, 4),
        "false_positive_ratio": round((len(low_events) / total), 4),
    }


def _build_detection_recommendations(
    site: Site,
    exploit_path: RedExploitPathRun | None,
    rule_count: int,
) -> list[dict[str, Any]]:
    proof = _safe_json_dict(exploit_path.proof_json) if exploit_path else {}
    evidence = proof.get("evidence", []) if isinstance(proof.get("evidence", []), list) else []
    path_graph = _safe_json_dict(exploit_path.path_graph_json) if exploit_path else {}
    target_surface = str(path_graph.get("target_surface", "/admin-login"))

    candidates: list[dict[str, Any]] = [
        {
            "rule_name": f"Velocity guard for {target_surface}",
            "rule_logic": {
                "signal": "failed_login_spike",
                "threshold_per_minute": 6,
                "path": target_surface,
                "action": "block_ip",
            },
            "reason": "Reduce brute-force and credential-stuffing window from exploit-path evidence.",
        },
        {
            "rule_name": "Identity abuse correlation",
            "rule_logic": {
                "signal": "impossible_auth_pattern",
                "window_seconds": 300,
                "action": "limit_user",
            },
            "reason": "Correlate anomalous authentication activity with red attack-path stages.",
        },
        {
            "rule_name": "Ransomware pre-impact alert chain",
            "rule_logic": {
                "signal": "lateral_movement_plus_privilege_escalation",
                "window_seconds": 600,
                "action": "notify_team",
            },
            "reason": "Contain likely impact stage early via chained detections.",
        },
        {
            "rule_name": f"Adaptive WAF challenge for {site.site_code}",
            "rule_logic": {
                "signal": "waf_403_burst",
                "threshold_per_minute": 12,
                "action": "challenge_or_block",
            },
            "reason": "Use observed WAF pressure to tune blue response automatically.",
        },
    ]
    if evidence:
        candidates[0]["evidence_refs"] = evidence[:4]
    return candidates[: max(1, min(rule_count, len(candidates)))]


def run_detection_copilot_tuning(db: Session, site_id: UUID, payload: DetectionCopilotTuneRequest) -> dict[str, object]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}

    exploit_path: RedExploitPathRun | None = None
    if payload.exploit_path_run_id:
        exploit_path = db.get(RedExploitPathRun, payload.exploit_path_run_id)
    if not exploit_path:
        exploit_path = db.scalar(
            select(RedExploitPathRun).where(RedExploitPathRun.site_id == site_id).order_by(desc(RedExploitPathRun.created_at)).limit(1)
        )

    blue_events = db.scalars(
        select(BlueEventLog).where(BlueEventLog.site_id == site_id).order_by(desc(BlueEventLog.created_at)).limit(500)
    ).all()
    before_metrics = _summarize_blue_baseline(blue_events)
    recommendations = _build_detection_recommendations(site, exploit_path, payload.rule_count)

    for item in recommendations:
        rule = BlueDetectionRule(
            site_id=site.id,
            rule_name=str(item["rule_name"]),
            rule_logic_json=_as_json(item["rule_logic"]),
            source="ai_detection_copilot",
            status="applied" if payload.auto_apply and not payload.dry_run else "draft",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(rule)

    coverage_lift = min(0.3, len(recommendations) * 0.07)
    fp_reduction = min(0.2, len(recommendations) * 0.04)
    response_lift = min(0.35, len(recommendations) * 0.08)
    after_metrics = {
        "event_count": before_metrics["event_count"],
        "detection_coverage": round(min(1.0, before_metrics["detection_coverage"] + coverage_lift), 4),
        "response_apply_rate": round(min(1.0, before_metrics["response_apply_rate"] + response_lift), 4),
        "false_positive_ratio": round(max(0.0, before_metrics["false_positive_ratio"] - fp_reduction), 4),
    }

    run = BlueDetectionTuningRun(
        site_id=site.id,
        exploit_path_run_id=exploit_path.id if exploit_path else None,
        status="dry_run" if payload.dry_run else "completed",
        recommendations_json=_as_json(recommendations),
        before_metrics_json=_as_json(before_metrics),
        after_metrics_json=_as_json(after_metrics),
        created_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    return {
        "status": run.status,
        "tuning_run_id": str(run.id),
        "site_id": str(site.id),
        "exploit_path_run_id": str(exploit_path.id) if exploit_path else "",
        "recommendations": recommendations,
        "before_metrics": before_metrics,
        "after_metrics": after_metrics,
        "expected_detection_coverage_delta": round(after_metrics["detection_coverage"] - before_metrics["detection_coverage"], 4),
    }


def list_detection_rules(db: Session, site_id: UUID, *, limit: int = 100) -> dict[str, object]:
    rows = db.scalars(
        select(BlueDetectionRule)
        .where(BlueDetectionRule.site_id == site_id)
        .order_by(desc(BlueDetectionRule.updated_at))
        .limit(max(1, min(limit, 500)))
    ).all()
    return {
        "count": len(rows),
        "rows": [
            {
                "rule_id": str(row.id),
                "site_id": str(row.site_id),
                "rule_name": row.rule_name,
                "rule_logic": _safe_json_dict(row.rule_logic_json),
                "source": row.source,
                "status": row.status,
                "created_at": row.created_at.isoformat() if row.created_at else "",
                "updated_at": row.updated_at.isoformat() if row.updated_at else "",
            }
            for row in rows
        ],
    }


def apply_detection_rule(db: Session, site_id: UUID, rule_id: UUID, *, apply: bool = True) -> dict[str, object]:
    row = db.get(BlueDetectionRule, rule_id)
    if not row or row.site_id != site_id:
        return {"status": "not_found"}
    row.status = "applied" if apply else "disabled"
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return {
        "status": "updated",
        "rule_id": str(row.id),
        "site_id": str(site_id),
        "rule_status": row.status,
    }


def list_detection_tuning_runs(db: Session, site_id: UUID, *, limit: int = 30) -> dict[str, object]:
    rows = db.scalars(
        select(BlueDetectionTuningRun)
        .where(BlueDetectionTuningRun.site_id == site_id)
        .order_by(desc(BlueDetectionTuningRun.created_at))
        .limit(max(1, min(limit, 200)))
    ).all()
    return {
        "count": len(rows),
        "rows": [
            {
                "tuning_run_id": str(row.id),
                "site_id": str(row.site_id),
                "exploit_path_run_id": str(row.exploit_path_run_id) if row.exploit_path_run_id else "",
                "status": row.status,
                "recommendations": _safe_json_list(row.recommendations_json),
                "before_metrics": _safe_json_dict(row.before_metrics_json),
                "after_metrics": _safe_json_dict(row.after_metrics_json),
                "created_at": row.created_at.isoformat() if row.created_at else "",
            }
            for row in rows
        ],
    }


def _safe_created_epoch(value: datetime | None) -> float:
    if value is None:
        return 0.0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def _case_risk_summary(
    *,
    exploit_runs: list[RedExploitPathRun],
    blue_events: list[BlueEventLog],
    soar_executions: list[SoarPlaybookExecution],
    unresolved_connector_dlq: int,
    high_risk_replay_runs: int,
) -> dict[str, object]:
    max_exploit_risk = max((int(run.risk_score or 0) for run in exploit_runs), default=0)
    high_blue_events = len([event for event in blue_events if event.ai_severity == "high"])
    open_blue_events = len([event for event in blue_events if event.status == "open"])
    pending_soar = len([execution for execution in soar_executions if execution.status == "pending_approval"])

    score = min(
        100,
        int(
            (max_exploit_risk * 0.35)
            + (high_blue_events * 6)
            + (open_blue_events * 4)
            + (pending_soar * 5)
            + (unresolved_connector_dlq * 5)
            + (high_risk_replay_runs * 7)
        ),
    )
    if score >= 80:
        risk_tier = "critical"
        recommendation = "execute_containment_playbook_and_reduce_approval_delay"
    elif score >= 60:
        risk_tier = "high"
        recommendation = "tighten_detection_rules_and_run_replay_apply_cycle"
    elif score >= 35:
        risk_tier = "medium"
        recommendation = "increase_scan_frequency_and_monitor_case_timeline"
    else:
        risk_tier = "low"
        recommendation = "maintain_closed_loop_and_collect_more_evidence"

    return {
        "score": score,
        "tier": risk_tier,
        "max_exploit_risk": max_exploit_risk,
        "high_blue_events": high_blue_events,
        "open_blue_events": open_blue_events,
        "pending_soar_executions": pending_soar,
        "unresolved_connector_dlq": unresolved_connector_dlq,
        "high_risk_replay_runs": high_risk_replay_runs,
        "recommendation": recommendation,
    }


def build_unified_case_graph(db: Session, site_id: UUID, *, limit: int = 50) -> dict[str, object]:
    site = db.get(Site, site_id)
    if not site:
        return {"status": "not_found", "site_id": str(site_id)}

    exploit_runs = db.scalars(
        select(RedExploitPathRun).where(RedExploitPathRun.site_id == site_id).order_by(desc(RedExploitPathRun.created_at)).limit(5)
    ).all()
    blue_events = db.scalars(
        select(BlueEventLog).where(BlueEventLog.site_id == site_id).order_by(desc(BlueEventLog.created_at)).limit(max(1, min(limit, 200)))
    ).all()
    rules = db.scalars(
        select(BlueDetectionRule).where(BlueDetectionRule.site_id == site_id).order_by(desc(BlueDetectionRule.updated_at)).limit(20)
    ).all()
    soar_executions = db.scalars(
        select(SoarPlaybookExecution)
        .where(SoarPlaybookExecution.site_id == site_id)
        .order_by(desc(SoarPlaybookExecution.updated_at))
        .limit(20)
    ).all()
    connector_events = db.scalars(
        select(ConnectorDeliveryEvent)
        .where(ConnectorDeliveryEvent.site_id == site_id)
        .order_by(desc(ConnectorDeliveryEvent.created_at))
        .limit(max(20, min(limit * 2, 200)))
    ).all()
    replay_runs = db.scalars(
        select(ConnectorReliabilityRun)
        .where(ConnectorReliabilityRun.tenant_id == site.tenant_id)
        .order_by(desc(ConnectorReliabilityRun.created_at))
        .limit(20)
    ).all()
    purple = db.scalar(
        select(PurpleInsightReport).where(PurpleInsightReport.site_id == site_id).order_by(desc(PurpleInsightReport.created_at)).limit(1)
    )

    nodes: list[dict[str, object]] = [{"id": f"site:{site.id}", "type": "site", "label": site.display_name, "ts": 0.0}]
    edges: list[dict[str, str]] = []
    timeline: list[dict[str, object]] = []
    connector_node_by_event_id: dict[str, str] = {}
    soar_node_by_code: dict[str, str] = {}

    for run in exploit_runs:
        node_id = f"exploit:{run.id}"
        created_at = _safe_created_epoch(run.created_at)
        nodes.append({"id": node_id, "type": "red_exploit_path", "label": f"risk={run.risk_score}", "ts": created_at})
        edges.append({"from": f"site:{site.id}", "to": node_id, "relation": "validated_by_red"})
        timeline.append(
            {
                "timestamp": run.created_at.isoformat() if run.created_at else "",
                "source": "red",
                "node_id": node_id,
                "summary": f"exploit_path risk={run.risk_score}",
            }
        )

    for event in blue_events[:20]:
        node_id = f"event:{event.id}"
        created_at = _safe_created_epoch(event.created_at)
        nodes.append(
            {
                "id": node_id,
                "type": "blue_event",
                "label": f"{event.event_type}:{event.ai_severity}",
                "ts": created_at,
            }
        )
        edges.append({"from": f"site:{site.id}", "to": node_id, "relation": "observed_event"})
        timeline.append(
            {
                "timestamp": event.created_at.isoformat() if event.created_at else "",
                "source": "blue",
                "node_id": node_id,
                "summary": f"{event.event_type} severity={event.ai_severity} status={event.status}",
            }
        )

    for rule in rules[:15]:
        node_id = f"rule:{rule.id}"
        created_at = _safe_created_epoch(rule.updated_at)
        nodes.append({"id": node_id, "type": "detection_rule", "label": rule.rule_name, "ts": created_at})
        edges.append({"from": f"site:{site.id}", "to": node_id, "relation": "protected_by_rule"})

    for execution in soar_executions:
        node_id = f"soar:{execution.id}"
        result = _safe_json_dict(execution.result_json)
        playbook_code = str(result.get("playbook_code", "")) or str(execution.playbook_id)
        created_at = _safe_created_epoch(execution.updated_at)
        nodes.append(
            {
                "id": node_id,
                "type": "soar_execution",
                "label": f"{playbook_code}:{execution.status}",
                "ts": created_at,
            }
        )
        edges.append({"from": f"site:{site.id}", "to": node_id, "relation": "response_executed"})
        if playbook_code:
            soar_node_by_code[playbook_code] = node_id
        timeline.append(
            {
                "timestamp": execution.updated_at.isoformat() if execution.updated_at else "",
                "source": "soar",
                "node_id": node_id,
                "summary": f"{playbook_code} status={execution.status}",
            }
        )

    for event in connector_events:
        node_id = f"connector:{event.id}"
        payload = _safe_json_dict(event.payload_json)
        created_at = _safe_created_epoch(event.created_at)
        nodes.append(
            {
                "id": node_id,
                "type": "connector_event",
                "label": f"{event.connector_source}:{event.event_type}:{event.status}",
                "ts": created_at,
            }
        )
        connector_node_by_event_id[str(event.id)] = node_id
        edges.append({"from": f"site:{site.id}", "to": node_id, "relation": "connector_delivery"})
        timeline.append(
            {
                "timestamp": event.created_at.isoformat() if event.created_at else "",
                "source": "connector",
                "node_id": node_id,
                "summary": f"{event.connector_source} {event.event_type} status={event.status}",
            }
        )

        replay_of = str(payload.get("replay_of_event_id", "")).strip()
        if replay_of:
            parent_node = connector_node_by_event_id.get(replay_of)
            if parent_node:
                edges.append({"from": parent_node, "to": node_id, "relation": "replayed_as"})

    for run in replay_runs:
        node_id = f"replay:{run.id}"
        created_at = _safe_created_epoch(run.created_at)
        nodes.append(
            {
                "id": node_id,
                "type": "connector_replay_run",
                "label": f"{run.connector_source}:{run.status}:{run.risk_tier}",
                "ts": created_at,
            }
        )
        edges.append({"from": f"site:{site.id}", "to": node_id, "relation": "connector_guardrail"})
        timeline.append(
            {
                "timestamp": run.created_at.isoformat() if run.created_at else "",
                "source": "connector_replay",
                "node_id": node_id,
                "summary": (
                    f"{run.connector_source} status={run.status} replayed={run.replayed_count} "
                    f"failed={run.failed_count} risk={run.risk_tier}"
                ),
            }
        )

    for event in blue_events[:20]:
        if not event.action_taken:
            continue
        soar_node = soar_node_by_code.get(event.action_taken)
        if not soar_node:
            continue
        edges.append({"from": f"event:{event.id}", "to": soar_node, "relation": "mitigated_by_playbook"})

    if purple:
        node_id = f"purple:{purple.id}"
        created_at = _safe_created_epoch(purple.created_at)
        nodes.append({"id": node_id, "type": "purple_report", "label": "latest_executive_insight", "ts": created_at})
        edges.append({"from": f"site:{site.id}", "to": node_id, "relation": "summarized_by_purple"})
        timeline.append(
            {
                "timestamp": purple.created_at.isoformat() if purple.created_at else "",
                "source": "purple",
                "node_id": node_id,
                "summary": "latest strategic correlation report",
            }
        )

    replayed_refs = {
        str(_safe_json_dict(event.payload_json).get("replay_of_event_id", "")).strip()
        for event in connector_events
        if str(_safe_json_dict(event.payload_json).get("replay_of_event_id", "")).strip()
    }
    unresolved_connector_dlq = len(
        [event for event in connector_events if event.event_type == "dead_letter" and str(event.id) not in replayed_refs]
    )
    high_risk_replay_runs = len([run for run in replay_runs if run.risk_tier in {"high", "critical"}])
    risk = _case_risk_summary(
        exploit_runs=exploit_runs,
        blue_events=blue_events,
        soar_executions=soar_executions,
        unresolved_connector_dlq=unresolved_connector_dlq,
        high_risk_replay_runs=high_risk_replay_runs,
    )

    timeline.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
    for node in nodes:
        node.pop("ts", None)

    return {
        "status": "completed",
        "site_id": str(site.id),
        "site_code": site.site_code,
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "exploit_paths": len(exploit_runs),
            "blue_events": len(blue_events),
            "detection_rules": len(rules),
            "soar_executions": len(soar_executions),
            "connector_events": len(connector_events),
            "connector_replay_runs": len(replay_runs),
            "risk_score": risk["score"],
            "risk_tier": risk["tier"],
            "has_purple_report": bool(purple),
        },
        "risk": risk,
        "timeline": timeline[:100],
        "graph": {"nodes": nodes, "edges": edges},
    }
