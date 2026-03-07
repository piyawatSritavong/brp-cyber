from fastapi import APIRouter
from pydantic import BaseModel

from app.services.runtime_state import runtime_state

router = APIRouter(prefix="/guardrails", tags=["guardrails"])


class KillSwitchRequest(BaseModel):
    enabled: bool


@router.get("/kill-switch")
def get_kill_switch() -> dict[str, bool]:
    return {"enabled": runtime_state.is_kill_switch_enabled()}


@router.post("/kill-switch")
def set_kill_switch(payload: KillSwitchRequest) -> dict[str, bool]:
    runtime_state.set_kill_switch(payload.enabled)
    return {"enabled": runtime_state.is_kill_switch_enabled()}
