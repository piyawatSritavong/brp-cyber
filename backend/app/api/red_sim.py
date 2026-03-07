from fastapi import APIRouter

from app.services.red_simulator import list_scenarios, process_due_schedules, run_simulation, schedule_simulation
from schemas.red_sim import RedSimulationRunRequest, RedSimulationScheduleRequest

router = APIRouter(prefix="/red-sim", tags=["red-sim"])


@router.get("/scenarios")
def scenarios() -> dict[str, object]:
    return list_scenarios()


@router.post("/run")
def run(payload: RedSimulationRunRequest) -> dict[str, object]:
    return run_simulation(payload)


@router.post("/schedule")
def schedule(payload: RedSimulationScheduleRequest) -> dict[str, str]:
    return schedule_simulation(payload)


@router.post("/tick")
def tick(limit: int = 100) -> dict[str, int]:
    return process_due_schedules(limit=limit)
