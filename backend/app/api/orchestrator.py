from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.orchestrator import (
    apply_strategy_profile,
    approve_pending_action,
    approve_pending_rollout_decision,
    activate_tenant_orchestration,
    activate_pilot_session,
    deactivate_tenant_orchestration,
    deactivate_pilot_session,
    evaluate_tenant_rollout_posture,
    get_kpi_trend,
    get_tenant_activation_state,
    get_tenant_orchestration_state,
    list_activation_states,
    list_pending_rollout_decisions,
    list_pilot_sessions,
    pause_tenant_orchestration,
    pilot_incidents,
    rollout_decision_history,
    rollout_evidence_history,
    verify_rollout_evidence_chain,
    get_pilot_session_status,
    get_tenant_rate_budget,
    get_tenant_rate_budget_usage,
    get_tenant_rollout_profile,
    get_tenant_rollout_policy,
    get_tenant_scheduler_profile,
    get_tenant_safety_policy,
    get_rollout_guard_state,
    run_activation_scheduler_tick,
    run_multi_cycle,
    run_orchestration_cycle,
    set_tenant_approval_mode,
    upsert_tenant_rate_budget,
    upsert_tenant_rollout_profile,
    upsert_tenant_rollout_policy,
    upsert_tenant_scheduler_profile,
    upsert_tenant_safety_policy,
)
from app.services.autonomous_runtime import autonomous_runtime
from app.services.pilot_operator_auth import operator_allows_tenant, operator_has_scope, verify_pilot_operator_token
from app.services.policy_store import set_blue_policy
from schemas.orchestration import (
    ApprovalDecisionRequest,
    ApprovalModeRequest,
    BluePolicyUpdateRequest,
    OrchestrationActivationRequest,
    OrchestrationCycleRequest,
    OrchestrationMultiCycleRequest,
    OrchestrationRateBudgetRequest,
    OrchestrationRolloutProfileRequest,
    OrchestrationSchedulerProfileRequest,
    OrchestrationSafetyPolicyRequest,
    PilotActivationRequest,
    TenantStrategyRequest,
)

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])
bearer = HTTPBearer(auto_error=False)


def require_pilot_operator(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict[str, object]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=403, detail="forbidden")
    verified = verify_pilot_operator_token(credentials.credentials)
    if not verified.get("valid"):
        raise HTTPException(status_code=403, detail=f"forbidden_operator:{verified.get('reason', 'invalid')}")
    return verified


@router.post("/cycle")
def cycle(payload: OrchestrationCycleRequest) -> dict[str, object]:
    return run_orchestration_cycle(payload)


@router.post("/cycles/run")
def cycles_run(payload: OrchestrationMultiCycleRequest) -> dict[str, object]:
    return run_multi_cycle(payload)


@router.get("/state/{tenant_id}")
def state(tenant_id: UUID) -> dict[str, object]:
    return get_tenant_orchestration_state(tenant_id)


@router.get("/kpi-trend/{tenant_id}")
def kpi_trend(tenant_id: UUID, limit: int = 100) -> dict[str, object]:
    trend = get_kpi_trend(tenant_id, limit=limit)
    return {"tenant_id": str(tenant_id), "count": len(trend), "trend": trend}


@router.post("/strategy")
def strategy(payload: TenantStrategyRequest) -> dict[str, object]:
    return apply_strategy_profile(payload.tenant_id, payload.strategy_profile)


@router.post("/blue-policy")
def update_blue_policy(payload: BluePolicyUpdateRequest) -> dict[str, object]:
    policy = set_blue_policy(
        payload.tenant_id,
        failed_login_threshold_per_minute=payload.failed_login_threshold_per_minute,
        failure_window_seconds=payload.failure_window_seconds,
        incident_cooldown_seconds=payload.incident_cooldown_seconds,
    )
    return {"tenant_id": str(payload.tenant_id), "blue_policy": policy}


@router.post("/approval-mode")
def approval_mode(payload: ApprovalModeRequest) -> dict[str, object]:
    return set_tenant_approval_mode(payload.tenant_id, payload.enabled)


@router.post("/approve")
def approve(payload: ApprovalDecisionRequest) -> dict[str, object]:
    return approve_pending_action(payload.tenant_id, payload.action_id, payload.approve)


@router.post("/activate")
def activate(payload: OrchestrationActivationRequest) -> dict[str, object]:
    return activate_tenant_orchestration(
        tenant_id=payload.tenant_id,
        target_asset=payload.target_asset,
        red_scenario_name=payload.red_scenario_name,
        red_events_count=payload.red_events_count,
        strategy_profile=payload.strategy_profile,
        cycle_interval_seconds=payload.cycle_interval_seconds,
        approval_mode=payload.approval_mode,
    )


@router.post("/pause/{tenant_id}")
def pause(tenant_id: UUID) -> dict[str, object]:
    return pause_tenant_orchestration(tenant_id)


@router.post("/deactivate/{tenant_id}")
def deactivate(tenant_id: UUID) -> dict[str, object]:
    return deactivate_tenant_orchestration(tenant_id)


@router.get("/activation/{tenant_id}")
def activation_state(tenant_id: UUID) -> dict[str, object]:
    return get_tenant_activation_state(tenant_id)


@router.get("/activations")
def activations(limit: int = 200) -> dict[str, object]:
    return list_activation_states(limit=limit)


@router.post("/tick")
def tick(limit: int = 200) -> dict[str, object]:
    return run_activation_scheduler_tick(limit=limit)


@router.get("/autonomous/status")
def autonomous_status() -> dict[str, object]:
    return autonomous_runtime.status()


@router.post("/autonomous/start")
def autonomous_start() -> dict[str, object]:
    return autonomous_runtime.start()


@router.post("/autonomous/stop")
def autonomous_stop() -> dict[str, object]:
    return autonomous_runtime.stop()


@router.post("/autonomous/run-once")
def autonomous_run_once() -> dict[str, object]:
    return autonomous_runtime.run_once()


@router.post("/pilot/activate")
def pilot_activate(payload: PilotActivationRequest) -> dict[str, object]:
    return activate_pilot_session(
        tenant_id=payload.tenant_id,
        target_asset=payload.target_asset,
        red_scenario_name=payload.red_scenario_name,
        red_events_count=payload.red_events_count,
        strategy_profile=payload.strategy_profile,
        cycle_interval_seconds=payload.cycle_interval_seconds,
        approval_mode=payload.approval_mode,
        require_objective_gate_pass=payload.require_objective_gate_pass,
        force=payload.force,
    )


@router.post("/pilot/deactivate/{tenant_id}")
def pilot_deactivate(tenant_id: UUID, reason: str = "manual_stop") -> dict[str, object]:
    return deactivate_pilot_session(tenant_id=tenant_id, reason=reason)


@router.get("/pilot/status/{tenant_id}")
def pilot_status(tenant_id: UUID) -> dict[str, object]:
    return get_pilot_session_status(tenant_id)


@router.get("/pilot/sessions")
def pilot_sessions(limit: int = 200) -> dict[str, object]:
    return list_pilot_sessions(limit=limit)


@router.post("/pilot/safety-policy")
def pilot_safety_policy_upsert(payload: OrchestrationSafetyPolicyRequest) -> dict[str, object]:
    return upsert_tenant_safety_policy(
        tenant_id=payload.tenant_id,
        max_consecutive_failures=payload.max_consecutive_failures,
        auto_stop_on_consecutive_failures=payload.auto_stop_on_consecutive_failures,
        objective_gate_check_each_tick=payload.objective_gate_check_each_tick,
        auto_stop_on_objective_gate_fail=payload.auto_stop_on_objective_gate_fail,
        notify_on_auto_stop=payload.notify_on_auto_stop,
    )


@router.get("/pilot/safety-policy/{tenant_id}")
def pilot_safety_policy_detail(tenant_id: UUID) -> dict[str, object]:
    return get_tenant_safety_policy(tenant_id)


@router.get("/pilot/incidents/{tenant_id}")
def pilot_incident_feed(tenant_id: UUID, limit: int = 100) -> dict[str, object]:
    return pilot_incidents(tenant_id, limit=limit)


@router.post("/pilot/rate-budget")
def pilot_rate_budget_upsert(payload: OrchestrationRateBudgetRequest) -> dict[str, object]:
    return upsert_tenant_rate_budget(
        tenant_id=payload.tenant_id,
        max_cycles_per_hour=payload.max_cycles_per_hour,
        max_red_events_per_hour=payload.max_red_events_per_hour,
        enforce_rate_budget=payload.enforce_rate_budget,
        auto_pause_on_budget_exceeded=payload.auto_pause_on_budget_exceeded,
        notify_on_budget_exceeded=payload.notify_on_budget_exceeded,
    )


@router.get("/pilot/rate-budget/{tenant_id}")
def pilot_rate_budget_detail(tenant_id: UUID) -> dict[str, object]:
    return get_tenant_rate_budget(tenant_id)


@router.get("/pilot/rate-budget/{tenant_id}/usage")
def pilot_rate_budget_usage(tenant_id: UUID, hour_epoch: int | None = None) -> dict[str, object]:
    return get_tenant_rate_budget_usage(tenant_id, hour_epoch=hour_epoch)


@router.post("/pilot/scheduler-profile")
def pilot_scheduler_profile_upsert(payload: OrchestrationSchedulerProfileRequest) -> dict[str, object]:
    return upsert_tenant_scheduler_profile(
        tenant_id=payload.tenant_id,
        priority_tier=payload.priority_tier,
        starvation_incident_threshold=payload.starvation_incident_threshold,
        notify_on_starvation=payload.notify_on_starvation,
    )


@router.get("/pilot/scheduler-profile/{tenant_id}")
def pilot_scheduler_profile_detail(tenant_id: UUID) -> dict[str, object]:
    return get_tenant_scheduler_profile(tenant_id)


@router.post("/pilot/rollout-profile")
def pilot_rollout_profile_upsert(payload: OrchestrationRolloutProfileRequest) -> dict[str, object]:
    return upsert_tenant_rollout_profile(
        tenant_id=payload.tenant_id,
        rollout_stage=payload.rollout_stage,
        canary_percent=payload.canary_percent,
        hold=payload.hold,
        notify_on_hold=payload.notify_on_hold,
    )


@router.get("/pilot/rollout-profile/{tenant_id}")
def pilot_rollout_profile_detail(tenant_id: UUID) -> dict[str, object]:
    return get_tenant_rollout_profile(tenant_id)


@router.post("/pilot/rollout-policy/upsert")
def pilot_rollout_policy_upsert(
    tenant_id: UUID,
    auto_promote_enabled: bool = True,
    auto_demote_enabled: bool = True,
    require_approval_for_promote: bool = False,
    require_approval_for_demote: bool = True,
    require_dual_control_for_promote: bool = False,
    require_dual_control_for_demote: bool = False,
) -> dict[str, object]:
    return upsert_tenant_rollout_policy(
        tenant_id,
        auto_promote_enabled=auto_promote_enabled,
        auto_demote_enabled=auto_demote_enabled,
        require_approval_for_promote=require_approval_for_promote,
        require_approval_for_demote=require_approval_for_demote,
        require_dual_control_for_promote=require_dual_control_for_promote,
        require_dual_control_for_demote=require_dual_control_for_demote,
    )


@router.get("/pilot/rollout-policy/{tenant_id}")
def pilot_rollout_policy_detail(tenant_id: UUID) -> dict[str, object]:
    return get_tenant_rollout_policy(tenant_id)


@router.post("/pilot/rollout/evaluate/{tenant_id}")
def pilot_rollout_evaluate(tenant_id: UUID, apply: bool = True) -> dict[str, object]:
    return evaluate_tenant_rollout_posture(tenant_id, apply=apply)


@router.get("/pilot/rollout/decisions/{tenant_id}")
def pilot_rollout_decisions(tenant_id: UUID, limit: int = 100) -> dict[str, object]:
    return rollout_decision_history(tenant_id, limit=limit)


@router.get("/pilot/rollout/evidence/{tenant_id}")
def pilot_rollout_evidence(tenant_id: UUID, limit: int = 100) -> dict[str, object]:
    return rollout_evidence_history(tenant_id, limit=limit)


@router.get("/pilot/rollout/evidence/verify/{tenant_id}")
def pilot_rollout_evidence_verify(tenant_id: UUID, limit: int = 1000) -> dict[str, object]:
    return verify_rollout_evidence_chain(tenant_id, limit=limit)


@router.get("/pilot/rollout/pending/{tenant_id}")
def pilot_rollout_pending(tenant_id: UUID, limit: int = 100) -> dict[str, object]:
    return list_pending_rollout_decisions(tenant_id, limit=limit)


@router.post("/pilot/rollout/pending/approve")
def pilot_rollout_pending_approve(
    tenant_id: UUID,
    decision_id: str,
    approve: bool = True,
    reviewer: str = "operator",
) -> dict[str, object]:
    return approve_pending_rollout_decision(tenant_id, decision_id, approve=approve, reviewer=reviewer)


@router.get("/pilot/rollout/guard/{tenant_id}")
def pilot_rollout_guard(tenant_id: UUID) -> dict[str, object]:
    return get_rollout_guard_state(tenant_id)


@router.post("/pilot/secure/activate")
def pilot_secure_activate(
    payload: PilotActivationRequest,
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:write"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return activate_pilot_session(
        tenant_id=payload.tenant_id,
        target_asset=payload.target_asset,
        red_scenario_name=payload.red_scenario_name,
        red_events_count=payload.red_events_count,
        strategy_profile=payload.strategy_profile,
        cycle_interval_seconds=payload.cycle_interval_seconds,
        approval_mode=payload.approval_mode,
        require_objective_gate_pass=payload.require_objective_gate_pass,
        force=payload.force,
    )


@router.post("/pilot/secure/deactivate/{tenant_id}")
def pilot_secure_deactivate(
    tenant_id: UUID,
    reason: str = "manual_stop",
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:write"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return deactivate_pilot_session(tenant_id=tenant_id, reason=reason)


@router.get("/pilot/secure/status/{tenant_id}")
def pilot_secure_status(
    tenant_id: UUID,
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:read"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return get_pilot_session_status(tenant_id)


@router.get("/pilot/secure/incidents/{tenant_id}")
def pilot_secure_incidents(
    tenant_id: UUID,
    limit: int = 100,
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:read"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return pilot_incidents(tenant_id, limit=limit)


@router.get("/pilot/secure/rate-budget/{tenant_id}/usage")
def pilot_secure_rate_budget_usage(
    tenant_id: UUID,
    hour_epoch: int | None = None,
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:read"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return get_tenant_rate_budget_usage(tenant_id, hour_epoch=hour_epoch)


@router.get("/pilot/secure/scheduler-profile/{tenant_id}")
def pilot_secure_scheduler_profile(
    tenant_id: UUID,
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:read"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return get_tenant_scheduler_profile(tenant_id)


@router.get("/pilot/secure/rollout-profile/{tenant_id}")
def pilot_secure_rollout_profile(
    tenant_id: UUID,
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:read"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return get_tenant_rollout_profile(tenant_id)


@router.get("/pilot/secure/rollout-policy/{tenant_id}")
def pilot_secure_rollout_policy(
    tenant_id: UUID,
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:read"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return get_tenant_rollout_policy(tenant_id)


@router.get("/pilot/secure/rollout/decisions/{tenant_id}")
def pilot_secure_rollout_decisions(
    tenant_id: UUID,
    limit: int = 100,
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:read"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return rollout_decision_history(tenant_id, limit=limit)


@router.get("/pilot/secure/rollout/evidence/{tenant_id}")
def pilot_secure_rollout_evidence(
    tenant_id: UUID,
    limit: int = 100,
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:read"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return rollout_evidence_history(tenant_id, limit=limit)


@router.get("/pilot/secure/rollout/evidence/verify/{tenant_id}")
def pilot_secure_rollout_evidence_verify(
    tenant_id: UUID,
    limit: int = 1000,
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:read"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return verify_rollout_evidence_chain(tenant_id, limit=limit)


@router.get("/pilot/secure/rollout/pending/{tenant_id}")
def pilot_secure_rollout_pending(
    tenant_id: UUID,
    limit: int = 100,
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:read"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return list_pending_rollout_decisions(tenant_id, limit=limit)


@router.post("/pilot/secure/rollout/pending/approve")
def pilot_secure_rollout_pending_approve(
    tenant_id: UUID,
    decision_id: str,
    approve: bool = True,
    reviewer: str = "operator",
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:write"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return approve_pending_rollout_decision(tenant_id, decision_id, approve=approve, reviewer=reviewer)


@router.get("/pilot/secure/rollout/guard/{tenant_id}")
def pilot_secure_rollout_guard(
    tenant_id: UUID,
    x_tenant_code: str = Header(default="", alias="X-Tenant-Code"),
    operator: dict[str, object] = Depends(require_pilot_operator),
) -> dict[str, object]:
    tenant_code = x_tenant_code.strip().lower()
    if not tenant_code:
        raise HTTPException(status_code=400, detail="missing_tenant_code")
    if not operator_allows_tenant(operator, tenant_code):
        raise HTTPException(status_code=403, detail="forbidden_operator:tenant_scope")
    if not operator_has_scope(operator, "pilot:read"):
        raise HTTPException(status_code=403, detail="forbidden_operator:scope")
    return get_rollout_guard_state(tenant_id)
