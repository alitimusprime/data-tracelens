from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from services.common.faults import FaultProfile, fault_controller
from services.common.settings import get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}


@router.get("/internal/faults", response_model=FaultProfile)
def get_fault() -> FaultProfile:
    return fault_controller.profile


@router.post("/internal/faults", response_model=FaultProfile)
def set_fault(profile: FaultProfile) -> FaultProfile:
    if not get_settings().simulator_enabled:
        raise HTTPException(status_code=404, detail="Simulator is disabled")
    return fault_controller.update(profile)


@router.delete("/internal/faults", response_model=FaultProfile)
def clear_fault() -> FaultProfile:
    if not get_settings().simulator_enabled:
        raise HTTPException(status_code=404, detail="Simulator is disabled")
    return fault_controller.reset()
