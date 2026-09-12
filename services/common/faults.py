import asyncio
import random
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, Field


class FaultMode(StrEnum):
    OFF = "off"
    ERROR = "error"
    LATENCY = "latency"


class FaultProfile(BaseModel):
    mode: FaultMode = FaultMode.OFF
    probability: float = Field(default=0.0, ge=0.0, le=1.0)
    delay_ms: int = Field(default=0, ge=0, le=30_000)
    label: str = "healthy"


class FaultInjected(RuntimeError):
    """Raised when a controlled demo failure should replace normal behavior."""


@dataclass
class FaultController:
    profile: FaultProfile

    async def apply(self) -> None:
        profile = self.profile
        if profile.mode == FaultMode.OFF or random.random() > profile.probability:
            return
        if profile.mode == FaultMode.LATENCY:
            await asyncio.sleep(profile.delay_ms / 1000)
            return
        if profile.mode == FaultMode.ERROR:
            raise FaultInjected(profile.label)

    def update(self, profile: FaultProfile) -> FaultProfile:
        self.profile = profile
        return self.profile

    def reset(self) -> FaultProfile:
        self.profile = FaultProfile()
        return self.profile


fault_controller = FaultController(FaultProfile())
