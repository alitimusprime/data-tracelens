import hashlib
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from services.common.api import router as common_router
from services.common.faults import FaultInjected, fault_controller
from services.common.observability import instrument_app

SERVICE_NAME = "payment"
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.1.0")
app = FastAPI(title="Demo Payment Service", version=SERVICE_VERSION)
app.include_router(common_router)
instrument_app(app, SERVICE_NAME, SERVICE_VERSION)


class ChargeRequest(BaseModel):
    order_id: str
    customer_id: str
    amount: float = Field(gt=0, le=10_000)


@app.post("/payments/charges")
async def charge(payload: ChargeRequest) -> dict:
    try:
        await fault_controller.apply()
    except FaultInjected as exc:
        raise HTTPException(status_code=502, detail=f"Payment processor fault: {exc}") from exc
    digest = hashlib.sha256(payload.order_id.encode()).hexdigest()[:12]
    return {
        "payment_id": f"pay-{digest}",
        "order_id": payload.order_id,
        "status": "authorized",
        "amount": payload.amount,
    }
