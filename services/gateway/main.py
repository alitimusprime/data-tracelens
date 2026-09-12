import logging
import os
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from services.common.api import router as common_router
from services.common.observability import instrument_app

SERVICE_NAME = "gateway"
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")
ORDER_URL = os.getenv("ORDER_URL", "http://order:8000")
logger = logging.getLogger(__name__)

app = FastAPI(title="Demo Gateway", version=SERVICE_VERSION)
app.include_router(common_router)
instrument_app(app, SERVICE_NAME, SERVICE_VERSION)


class OrderRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=80)
    sku: str = Field(default="SKU-RED-1", min_length=1, max_length=80)
    quantity: int = Field(default=1, ge=1, le=10)
    amount: float = Field(default=49.99, gt=0, le=10_000)


@app.post("/api/orders", status_code=201)
async def create_order(
    payload: OrderRequest,
    x_request_id: str | None = Header(default=None),
) -> dict:
    request_id = x_request_id or str(uuid.uuid4())
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(4.0)) as client:
            response = await client.post(
                f"{ORDER_URL}/orders",
                json=payload.model_dump(),
                headers={"X-Request-ID": request_id},
            )
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.warning("Order dependency timed out", extra={"event": "dependency_timeout"})
        raise HTTPException(status_code=504, detail="Order processing timed out") from exc
    except httpx.HTTPStatusError as exc:
        status = 503 if exc.response.status_code >= 500 else exc.response.status_code
        raise HTTPException(status_code=status, detail="Order could not be completed") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail="Order service unavailable") from exc
    result: dict[str, Any] = response.json()
    result["request_id"] = request_id
    return result


@app.get("/api/catalog")
def catalog() -> list[dict]:
    return [
        {"sku": "SKU-RED-1", "name": "Red telemetry mug", "price": 49.99},
        {"sku": "SKU-BLUE-1", "name": "Blue tracing notebook", "price": 29.99},
    ]
