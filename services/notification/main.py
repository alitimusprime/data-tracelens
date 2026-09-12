import json
import logging
import os
from contextlib import suppress
from typing import Any

import nats
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.trace import SpanKind

from services.common.api import router as common_router
from services.common.observability import instrument_app

SERVICE_NAME = "notification"
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")
NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

app = FastAPI(title="Demo Notification Service", version=SERVICE_VERSION)
app.include_router(common_router)
instrument_app(app, SERVICE_NAME, SERVICE_VERSION)
delivered: list[dict] = []


async def handle_message(message: Any) -> None:
    context = extract(dict(message.headers or {}))
    with tracer.start_as_current_span(
        "notification.send",
        context=context,
        kind=SpanKind.CONSUMER,
        attributes={
            "messaging.system": "nats",
            "messaging.destination.name": "orders.completed",
            "messaging.operation.name": "process",
        },
    ):
        event = json.loads(message.data.decode())
        delivered.append(
            {
                "order_id": event["order_id"],
                "customer_id": event["customer_id"],
                "status": "delivered",
            }
        )
        logger.info("Order notification delivered", extra={"event": "notification_delivered"})
        await message.ack()


@app.on_event("startup")
async def subscribe() -> None:
    try:
        connection = await nats.connect(NATS_URL, connect_timeout=2, max_reconnect_attempts=-1)
        jetstream = connection.jetstream()
        with suppress(Exception):
            await jetstream.add_stream(name="ORDERS", subjects=["orders.completed"])
        await jetstream.subscribe(
            "orders.completed",
            durable="notification-service",
            cb=handle_message,
            manual_ack=True,
        )
        app.state.nats = connection
    except Exception:
        logger.exception(
            "Notification consumer could not start", extra={"event": "nats_unavailable"}
        )


@app.on_event("shutdown")
async def close_nats() -> None:
    connection = getattr(app.state, "nats", None)
    if connection:
        await connection.drain()


@app.get("/notifications")
def recent_notifications() -> list[dict]:
    return delivered[-25:]
