import asyncio
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from services.common.api import router as common_router
from services.common.faults import FaultInjected, fault_controller
from services.common.observability import instrument_app

SERVICE_NAME = "inventory"
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")
app = FastAPI(title="Demo Inventory Service", version=SERVICE_VERSION)
app.include_router(common_router)
instrument_app(app, SERVICE_NAME, SERVICE_VERSION)

stock = {"SKU-RED-1": 10_000, "SKU-BLUE-1": 10_000}
stock_lock = asyncio.Lock()


class ReservationRequest(BaseModel):
    order_id: str
    sku: str
    quantity: int = Field(ge=1, le=10)


@app.post("/inventory/reservations")
async def reserve(payload: ReservationRequest) -> dict:
    try:
        await fault_controller.apply()
    except FaultInjected as exc:
        raise HTTPException(status_code=503, detail=f"Inventory fault: {exc}") from exc
    async with stock_lock:
        available = stock.get(payload.sku, 0)
        if available < payload.quantity:
            raise HTTPException(status_code=409, detail="Insufficient stock")
        stock[payload.sku] = available - payload.quantity
    return {
        "reservation_id": f"res-{payload.order_id}",
        "order_id": payload.order_id,
        "status": "reserved",
        "remaining": stock[payload.sku],
    }


@app.get("/inventory/{sku}")
def get_stock(sku: str) -> dict:
    return {"sku": sku, "available": stock.get(sku, 0)}
