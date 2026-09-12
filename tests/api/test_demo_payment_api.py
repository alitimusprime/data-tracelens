import os

from fastapi.testclient import TestClient

os.environ.setdefault("SERVICE_NAME", "payment")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from services.common.faults import FaultMode, FaultProfile, fault_controller  # noqa: E402
from services.payment.main import app  # noqa: E402

client = TestClient(app)


def test_payment_authorization_is_deterministic() -> None:
    fault_controller.reset()
    response = client.post(
        "/payments/charges",
        json={"order_id": "order-123", "customer_id": "demo-1", "amount": 49.99},
    )
    assert response.status_code == 200
    assert response.json()["payment_id"] == "pay-3b6a198e6f18"
    assert response.json()["status"] == "authorized"


def test_controlled_payment_fault_returns_safe_error() -> None:
    fault_controller.update(FaultProfile(mode=FaultMode.ERROR, probability=1, label="test"))
    try:
        response = client.post(
            "/payments/charges",
            json={"order_id": "order-456", "customer_id": "demo-1", "amount": 29.99},
        )
        assert response.status_code == 502
        assert response.json()["detail"] == "Payment processor fault: test"
    finally:
        fault_controller.reset()
