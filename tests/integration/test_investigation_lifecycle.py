from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from tracelens.domain.signals import SignalWindow
from tracelens.infrastructure.database import Base
from tracelens.infrastructure.models import IncidentRecord
from tracelens.services.catalog import ensure_catalog
from tracelens.services.investigation import InvestigationService


class RecordingPublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def publish(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))


def window(service: str, latency: float) -> SignalWindow:
    now = datetime.now(UTC)
    return SignalWindow(
        service_name=service,
        window_start=now - timedelta(minutes=1),
        window_end=now,
        request_rate=2,
        error_rate=0,
        p95_latency_ms=latency,
        availability=1,
        sample_count=120,
    )


def test_correlated_incident_opens_ranks_and_resolves() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    publisher = RecordingPublisher()
    with Session(engine, expire_on_commit=False) as session:
        ensure_catalog(session)
        investigation = InvestigationService(session, publisher)  # type: ignore[arg-type]
        investigation.process(window("payment", 2200))
        investigation.process(window("order", 2250))

        incidents = session.scalars(select(IncidentRecord)).all()
        assert len(incidents) == 1
        incident = incidents[0]
        assert incident.status == "investigating"
        assert incident.probable_root_cause == "payment"
        assert {item.service_name for item in incident.anomalies} == {"payment", "order"}

        investigation.process(window("payment", 120))
        investigation.process(window("order", 130))
        assert incident.status == "investigating"
        investigation.process(window("payment", 120))
        investigation.process(window("order", 130))
        session.refresh(incident)
        assert incident.status == "resolved"
        assert incident.resolved_at is not None
        assert any(event[0] == "incident.changed" for event in publisher.events)
