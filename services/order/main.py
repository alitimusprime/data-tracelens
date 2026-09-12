import asyncio
import json
import logging
import os
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

import httpx
import nats
from fastapi import FastAPI, Header, HTTPException
from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.trace import SpanKind
from pydantic import BaseModel, Field

from services.common.api import router as common_router
from services.common.observability import instrument_app

SERVICE_NAME = "order"
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://inventory:8000")
PAYMENT_URL = os.getenv("PAYMENT_URL", "http://payment:8000")
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
nats_lock = asyncio.Lock()

app = FastAPI(title="Demo Order Service", version=SERVICE_VERSION)
app.include_router(common_router)
instrument_app(app, SERVICE_NAME, SERVICE_VERSION)
orders: dict[str, dict] = {}


class OrderRequest(BaseModel):
    customer_id: str
    sku: str
    quantity: int = Field(ge=1, le=10)
    amount: float = Field(gt=0, le=10_000)


async def _publish_order_event(event: dict) -> bool:
    try:
        jetstream = await _jetstream()
        with tracer.start_as_current_span(
            "orders.completed publish",
            kind=SpanKind.PRODUCER,
            attributes={
                "messaging.system": "nats",
                "messaging.destination.name": "orders.completed",
                "messaging.operation.name": "publish",
            },
        ):
            headers: dict[str, str] = {}
            inject(headers)
            await jetstream.publish(
                "orders.completed",
                json.dumps(event).encode(),
                headers=headers,
            )
        return True
    except Exception:
        logger.exception("Order event publication failed", extra={"event": "nats_publish_failed"})
        return False


async def _jetstream() -> Any:
    connection = getattr(app.state, "nats", None)
    if connection and connection.is_connected:
        return connection.jetstream()
    async with nats_lock:
        connection = getattr(app.state, "nats", None)
        if not connection or not connection.is_connected:
            connection = await nats.connect(
                NATS_URL,
                connect_timeout=2,
                max_reconnect_attempts=-1,
            )
            app.state.nats = connection
        jetstream = connection.jetstream()
        with suppress(Exception):
            await jetstream.add_stream(name="ORDERS", subjects=["orders.completed"])
        return jetstream


@app.on_event("shutdown")
async def close_nats() -> None:
    connection = getattr(app.state, "nats", None)
    if connection:
        await connection.drain()


@app.post("/orders", status_code=201)
async def create_order(
    payload: OrderRequest,
    x_request_id: str | None = Header(default=None),
) -> dict:
    order_id = str(uuid.uuid4())
    request_id = x_request_id or str(uuid.uuid4())
    headers = {"X-Request-ID": request_id}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.5)) as client:
            inventory = await client.post(
                f"{INVENTORY_URL}/inventory/reservations",
                json={"order_id": order_id, "sku": payload.sku, "quantity": payload.quantity},
                headers=headers,
            )
            inventory.raise_for_status()
            payment = await client.post(
                f"{PAYMENT_URL}/payments/charges",
                json={
                    "order_id": order_id,
                    "customer_id": payload.customer_id,
                    "amount": payload.amount,
                },
                headers=headers,
            )
            payment.raise_for_status()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="A required dependency timed out") from exc
    except httpx.HTTPStatusError as exc:
        status = 502 if exc.response.status_code >= 500 else exc.response.status_code
        raise HTTPException(
            status_code=status, detail="A required dependency rejected the order"
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="A required dependency is unavailable") from exc

    completed_at = datetime.now(UTC).isoformat()
    order = {
        "order_id": order_id,
        "request_id": request_id,
        "status": "completed",
        "completed_at": completed_at,
        "payment_id": payment.json()["payment_id"],
        "reservation_id": inventory.json()["reservation_id"],
    }
    orders[order_id] = order
    order["notification_queued"] = await _publish_order_event(
        {**order, "customer_id": payload.customer_id}
    )
    return order


@app.get("/orders/{order_id}")
def get_order(order_id: str) -> dict:
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="Order not found")
    return orders[order_id]
