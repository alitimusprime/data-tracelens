from sqlalchemy.orm import Session

from tracelens.infrastructure.models import ServiceRecord

CATALOG = [
    {
        "name": "gateway",
        "display_name": "API Gateway",
        "endpoint": "http://gateway:8000",
        "dependencies": ["order"],
    },
    {
        "name": "order",
        "display_name": "Order Service",
        "endpoint": "http://order:8000",
        "dependencies": ["inventory", "payment", "notification"],
    },
    {
        "name": "inventory",
        "display_name": "Inventory Service",
        "endpoint": "http://inventory:8000",
        "dependencies": [],
    },
    {
        "name": "payment",
        "display_name": "Payment Service",
        "endpoint": "http://payment:8000",
        "dependencies": [],
    },
    {
        "name": "notification",
        "display_name": "Notification Service",
        "endpoint": "http://notification:8000",
        "dependencies": [],
    },
]


def ensure_catalog(session: Session) -> None:
    for item in CATALOG:
        if not session.get(ServiceRecord, item["name"]):
            session.add(ServiceRecord(**item))
    session.commit()
