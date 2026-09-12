import logging
import time

from sqlalchemy import select

from services.common.observability import configure_observability
from tracelens.config import get_settings
from tracelens.infrastructure.database import SessionLocal
from tracelens.infrastructure.events import EventPublisher
from tracelens.infrastructure.models import ServiceRecord
from tracelens.infrastructure.prometheus import PrometheusClient
from tracelens.services.catalog import ensure_catalog
from tracelens.services.investigation import InvestigationService

logger = logging.getLogger(__name__)


def run() -> None:
    settings = get_settings()
    configure_observability("tracelens-analyzer", "0.1.0")
    prometheus = PrometheusClient(settings.prometheus_url)
    publisher = EventPublisher(settings.redis_url)
    logger.info("Analysis worker started")
    while True:
        try:
            with SessionLocal() as session:
                ensure_catalog(session)
                service_names = session.scalars(select(ServiceRecord.name)).all()
                investigation = InvestigationService(
                    session,
                    publisher,
                    settings.incident_correlation_window_seconds,
                )
                for service_name in service_names:
                    investigation.process(prometheus.collect(service_name))
        except Exception:
            logger.exception("Analysis cycle failed")
        time.sleep(settings.analysis_interval_seconds)


if __name__ == "__main__":
    run()
