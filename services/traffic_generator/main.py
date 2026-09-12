import asyncio
import logging
import os
import random
import uuid

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

from services.common.api import router as common_router
from services.common.observability import instrument_app

SERVICE_NAME = "traffic-generator"
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway:8000")
logger = logging.getLogger(__name__)

app = FastAPI(title="Demo Traffic Generator", version=SERVICE_VERSION)
app.include_router(common_router)
instrument_app(app, SERVICE_NAME, SERVICE_VERSION)


class TrafficConfig(BaseModel):
    enabled: bool = True
    requests_per_second: float = Field(default=1.0, ge=0.1, le=20)


config = TrafficConfig(requests_per_second=float(os.getenv("TRAFFIC_RPS", "1.0")))


@app.get("/traffic", response_model=TrafficConfig)
def get_traffic() -> TrafficConfig:
    return config


@app.post("/traffic", response_model=TrafficConfig)
def set_traffic(value: TrafficConfig) -> TrafficConfig:
    global config
    config = value
    return config


async def generate() -> None:
    while True:
        if not config.enabled:
            await asyncio.sleep(1)
            continue
        payload = {
            "customer_id": f"demo-{random.randint(1, 100)}",
            "sku": random.choice(["SKU-RED-1", "SKU-BLUE-1"]),
            "quantity": 1,
            "amount": random.choice([29.99, 49.99]),
        }
        try:
            async with httpx.AsyncClient(timeout=6) as client:
                await client.post(
                    f"{GATEWAY_URL}/api/orders",
                    json=payload,
                    headers={"X-Request-ID": str(uuid.uuid4())},
                )
        except Exception:
            logger.warning("Generated request failed", extra={"event": "traffic_request_failed"})
        await asyncio.sleep(1 / config.requests_per_second)


@app.on_event("startup")
async def start_generator() -> None:
    app.state.task = asyncio.create_task(generate())


@app.on_event("shutdown")
async def stop_generator() -> None:
    app.state.task.cancel()
