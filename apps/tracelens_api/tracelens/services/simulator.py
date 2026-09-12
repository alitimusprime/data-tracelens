from datetime import UTC, datetime
from typing import TypedDict

import httpx
from sqlalchemy.orm import Session

from tracelens.infrastructure.events import EventPublisher
from tracelens.infrastructure.models import DeploymentRecord


class ScenarioDefinition(TypedDict):
    id: str
    name: str
    description: str
    service: str
    expected: str
    profile: dict[str, object]
    deployment: bool


SCENARIOS: dict[str, ScenarioDefinition] = {
    "payment-latency": {
        "id": "payment-latency",
        "name": "Payment latency regression",
        "description": "Adds 2.2 seconds to every payment authorization.",
        "service": "payment",
        "expected": (
            "Payment and upstream latency rise, traces point downstream, and a deployment "
            "event strengthens the payment hypothesis."
        ),
        "profile": {
            "mode": "latency",
            "probability": 1.0,
            "delay_ms": 2200,
            "label": "payment-v0.2.0 latency regression",
        },
        "deployment": True,
    },
    "inventory-outage": {
        "id": "inventory-outage",
        "name": "Inventory outage",
        "description": "Rejects every inventory reservation with a controlled 503.",
        "service": "inventory",
        "expected": (
            "Inventory errors propagate to Order and Gateway while Payment remains healthy."
        ),
        "profile": {
            "mode": "error",
            "probability": 1.0,
            "delay_ms": 0,
            "label": "inventory dependency unavailable",
        },
        "deployment": False,
    },
    "payment-intermittent": {
        "id": "payment-intermittent",
        "name": "Intermittent payment failures",
        "description": "Fails approximately 35 percent of payment requests.",
        "service": "payment",
        "expected": (
            "A partial error-rate degradation appears without a full outage, and confidence "
            "grows as evidence accumulates."
        ),
        "profile": {
            "mode": "error",
            "probability": 0.35,
            "delay_ms": 0,
            "label": "intermittent processor rejection",
        },
        "deployment": False,
    },
}

SERVICE_URLS = {
    "payment": "http://payment:8000",
    "inventory": "http://inventory:8000",
}


class SimulatorService:
    def __init__(self, session: Session, publisher: EventPublisher) -> None:
        self.session = session
        self.publisher = publisher

    async def start(self, scenario_id: str) -> dict:
        scenario = SCENARIOS[scenario_id]
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                f"{SERVICE_URLS[scenario['service']]}/internal/faults",
                json=scenario["profile"],
            )
            response.raise_for_status()
            await client.post(
                "http://traffic-generator:8000/traffic",
                json={"enabled": True, "requests_per_second": 2.0},
            )
        if scenario["deployment"]:
            self.session.add(
                DeploymentRecord(
                    service_name=scenario["service"],
                    version="0.2.0-demo",
                    commit_sha="demo-bad-latency",
                    change_summary="Simulated deployment that introduces payment latency",
                    simulated=True,
                )
            )
            self.session.commit()
        payload = {
            "scenario_id": scenario_id,
            "status": "running",
            "started_at": datetime.now(UTC).isoformat(),
        }
        self.publisher.publish("scenario.changed", payload)
        return payload

    async def stop(self, scenario_id: str) -> dict:
        scenario = SCENARIOS[scenario_id]
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.delete(f"{SERVICE_URLS[scenario['service']]}/internal/faults")
            response.raise_for_status()
            await client.post(
                "http://traffic-generator:8000/traffic",
                json={"enabled": True, "requests_per_second": 1.0},
            )
        payload = {
            "scenario_id": scenario_id,
            "status": "stopped",
            "stopped_at": datetime.now(UTC).isoformat(),
        }
        self.publisher.publish("scenario.changed", payload)
        return payload
