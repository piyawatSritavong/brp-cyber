from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.enterprise.cost_meter import get_cost, record_cost
from app.services.enterprise.autoscaler import get_status as autoscaler_status
from app.services.enterprise.autoscaler import history as autoscaler_history
from app.services.enterprise.autoscaler import reconcile as autoscaler_reconcile
from app.services.enterprise.model_router import route_model
from app.services.enterprise.objective_gate import (
    evaluate_and_persist_objective_gate,
    evaluate_objective_gate,
    list_objective_gate_history,
    objective_gate_blockers,
    objective_gate_dashboard,
    objective_gate_remediation_plan,
)
from app.services.enterprise.quotas import add_usage, check_quota, get_quota, get_usage, set_quota
from app.services.enterprise.queueing import (
    autoscaling_recommendation,
    enqueue_scan_task,
    ensure_worker_groups,
    queue_partition_stats,
)
from app.services.enterprise.slo import get_slo_snapshot

router = APIRouter(prefix="/enterprise", tags=["enterprise"])


class QuotaUpdateRequest(BaseModel):
    tenant_id: UUID
    events_per_month: int = Field(ge=1)
    actions_per_day: int = Field(ge=1)
    tokens_per_month: int = Field(ge=1)


class UsageAddRequest(BaseModel):
    tenant_id: UUID
    events: int = Field(default=0, ge=0)
    actions: int = Field(default=0, ge=0)
    tokens: int = Field(default=0, ge=0)


class RouteRequest(BaseModel):
    tenant_id: UUID
    task_type: str = Field(min_length=2, max_length=64)
    complexity: str = Field(min_length=3, max_length=32)
    estimated_tokens: int = Field(ge=1, le=200000)


class CostRecordRequest(BaseModel):
    tenant_id: UUID
    tokens: int = Field(ge=1)
    model_name: str = Field(min_length=2, max_length=128)


class EnqueueTaskRequest(BaseModel):
    tenant_id: UUID
    task_type: str = Field(min_length=2, max_length=64)
    payload: dict[str, object] = Field(default_factory=dict)


@router.get("/quota/{tenant_id}")
def quota(tenant_id: UUID) -> dict[str, object]:
    return {"tenant_id": str(tenant_id), "quota": get_quota(tenant_id), "usage": get_usage(tenant_id)}


@router.post("/quota")
def quota_update(payload: QuotaUpdateRequest) -> dict[str, object]:
    q = set_quota(payload.tenant_id, payload.events_per_month, payload.actions_per_day, payload.tokens_per_month)
    return {"tenant_id": str(payload.tenant_id), "quota": q}


@router.post("/usage")
def usage_add(payload: UsageAddRequest) -> dict[str, object]:
    result = add_usage(payload.tenant_id, payload.events, payload.actions, payload.tokens)
    return {"tenant_id": str(payload.tenant_id), "usage": result}


@router.get("/quota/check/{tenant_id}")
def quota_check(tenant_id: UUID, events: int = 0, actions: int = 0, tokens: int = 0) -> dict[str, object]:
    return check_quota(tenant_id, events=events, actions=actions, tokens=tokens)


@router.post("/route")
def route(payload: RouteRequest) -> dict[str, object]:
    decision = route_model(payload.tenant_id, payload.task_type, payload.complexity, payload.estimated_tokens)
    return decision.as_dict()


@router.post("/cost/record")
def cost_record(payload: CostRecordRequest) -> dict[str, object]:
    return record_cost(payload.tenant_id, payload.tokens, payload.model_name)


@router.get("/cost/{tenant_id}")
def cost_get(tenant_id: UUID) -> dict[str, object]:
    return get_cost(tenant_id)


@router.get("/slo/{tenant_id}")
def slo_snapshot(tenant_id: UUID) -> dict[str, object]:
    return get_slo_snapshot(tenant_id)


@router.post("/queue/bootstrap")
def queue_bootstrap() -> dict[str, object]:
    return {"groups": ensure_worker_groups()}


@router.post("/queue/enqueue")
def queue_enqueue(payload: EnqueueTaskRequest) -> dict[str, object]:
    return enqueue_scan_task(payload.tenant_id, payload.task_type, payload.payload)


@router.get("/queue/stats")
def queue_stats() -> dict[str, object]:
    return queue_partition_stats()


@router.get("/queue/autoscale")
def queue_autoscale(current_workers: int = 1) -> dict[str, object]:
    return autoscaling_recommendation(current_workers=current_workers)


@router.post("/autoscaler/reconcile")
def autoscaler_reconcile_endpoint(current_workers: int | None = None) -> dict[str, object]:
    return autoscaler_reconcile(current_workers=current_workers)


@router.get("/autoscaler/status")
def autoscaler_status_endpoint() -> dict[str, object]:
    return autoscaler_status()


@router.get("/autoscaler/history")
def autoscaler_history_endpoint(limit: int = 100) -> dict[str, object]:
    rows = autoscaler_history(limit=limit)
    return {"count": len(rows), "history": rows}


@router.get("/objective-gate/{tenant_id}")
def objective_gate(
    tenant_id: UUID,
    lookback_cycles: int = 20,
    trend_limit: int = 20,
    min_detection_coverage: float = 0.9,
    min_blocked_before_impact_rate: float = 0.6,
    min_trend_improvement_ratio: float = 0.6,
    max_monthly_cost_usd: float = 50.0,
    persist_snapshot: bool = True,
) -> dict[str, object]:
    evaluator = evaluate_and_persist_objective_gate if persist_snapshot else evaluate_objective_gate
    return evaluator(
        tenant_id=tenant_id,
        lookback_cycles=lookback_cycles,
        trend_limit=trend_limit,
        min_detection_coverage=min_detection_coverage,
        min_blocked_before_impact_rate=min_blocked_before_impact_rate,
        min_trend_improvement_ratio=min_trend_improvement_ratio,
        max_monthly_cost_usd=max_monthly_cost_usd,
    )


@router.get("/objective-gate-history/{tenant_id}")
def objective_gate_history(tenant_id: UUID, limit: int = 100) -> dict[str, object]:
    rows = list_objective_gate_history(tenant_id, limit=limit)
    return {"count": len(rows), "rows": rows}


@router.get("/objective-gate-remediation/{tenant_id}")
def objective_gate_remediation(
    tenant_id: UUID,
    lookback_cycles: int = 20,
    trend_limit: int = 20,
    min_detection_coverage: float = 0.9,
    min_blocked_before_impact_rate: float = 0.6,
    min_trend_improvement_ratio: float = 0.6,
    max_monthly_cost_usd: float = 50.0,
) -> dict[str, object]:
    evaluation = evaluate_and_persist_objective_gate(
        tenant_id=tenant_id,
        lookback_cycles=lookback_cycles,
        trend_limit=trend_limit,
        min_detection_coverage=min_detection_coverage,
        min_blocked_before_impact_rate=min_blocked_before_impact_rate,
        min_trend_improvement_ratio=min_trend_improvement_ratio,
        max_monthly_cost_usd=max_monthly_cost_usd,
    )
    return {
        "tenant_id": str(tenant_id),
        "evaluation": evaluation,
        "remediation": objective_gate_remediation_plan(evaluation),
    }


@router.get("/objective-gate-blockers/{tenant_id}")
def objective_gate_blockers_endpoint(
    tenant_id: UUID,
    lookback_cycles: int = 20,
    trend_limit: int = 20,
    min_detection_coverage: float = 0.9,
    min_blocked_before_impact_rate: float = 0.6,
    min_trend_improvement_ratio: float = 0.6,
    max_monthly_cost_usd: float = 50.0,
) -> dict[str, object]:
    evaluation = evaluate_and_persist_objective_gate(
        tenant_id=tenant_id,
        lookback_cycles=lookback_cycles,
        trend_limit=trend_limit,
        min_detection_coverage=min_detection_coverage,
        min_blocked_before_impact_rate=min_blocked_before_impact_rate,
        min_trend_improvement_ratio=min_trend_improvement_ratio,
        max_monthly_cost_usd=max_monthly_cost_usd,
    )
    return {
        "tenant_id": str(tenant_id),
        "evaluation": evaluation,
        "blockers": objective_gate_blockers(evaluation),
    }


@router.get("/objective-gate-dashboard")
def objective_gate_dashboard_endpoint(limit: int = 100) -> dict[str, object]:
    return objective_gate_dashboard(limit=limit)
