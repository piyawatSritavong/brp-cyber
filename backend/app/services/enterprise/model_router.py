from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.core.config import settings
from app.services.control_plane_orchestration_cost_guardrail import get_orchestration_cost_routing_override_mode
from app.services.enterprise.quotas import check_quota


@dataclass
class ModelRoutingDecision:
    task_type: str
    selected_model: str
    estimated_tokens: int
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "task_type": self.task_type,
            "selected_model": self.selected_model,
            "estimated_tokens": self.estimated_tokens,
            "reason": self.reason,
        }


def route_model(tenant_id: UUID, task_type: str, complexity: str, estimated_tokens: int) -> ModelRoutingDecision:
    try:
        routing_override = get_orchestration_cost_routing_override_mode(tenant_id)
    except Exception:
        routing_override = ""
    if routing_override == "fallback_only":
        return ModelRoutingDecision(
            task_type=task_type,
            selected_model=settings.model_fallback_when_over_quota,
            estimated_tokens=estimated_tokens,
            reason="cost_guardrail_fallback_override",
        )

    quota_state = check_quota(tenant_id, tokens=estimated_tokens)

    if not quota_state["allowed"]:
        return ModelRoutingDecision(
            task_type=task_type,
            selected_model=settings.model_fallback_when_over_quota,
            estimated_tokens=estimated_tokens,
            reason="quota_exceeded_fallback",
        )

    normalized = complexity.lower().strip()
    if task_type in {"purple_report", "strategy_analysis"} and normalized in {"high", "critical"}:
        return ModelRoutingDecision(
            task_type=task_type,
            selected_model=settings.model_reasoning,
            estimated_tokens=estimated_tokens,
            reason="high_complexity_reasoning_task",
        )

    return ModelRoutingDecision(
        task_type=task_type,
        selected_model=settings.model_processing,
        estimated_tokens=estimated_tokens,
        reason="slm_first_policy",
    )
