import json
import logging
import os
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app

REQUESTS = Counter(
    "tracelens_http_requests_total",
    "Completed HTTP requests",
    ["service", "method", "route", "status"],
)
LATENCY = Histogram(
    "tracelens_http_request_duration_seconds",
    "HTTP request duration",
    ["service", "method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
IN_FLIGHT = Gauge(
    "tracelens_http_requests_in_flight",
    "Requests currently being processed",
    ["service"],
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        span = trace.get_current_span().get_span_context()
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": os.getenv("SERVICE_NAME", "unknown"),
            "message": record.getMessage(),
        }
        if span.is_valid:
            payload["trace_id"] = format(span.trace_id, "032x")
            payload["span_id"] = format(span.span_id, "016x")
        if hasattr(record, "event"):
            payload["event"] = record.event
        return json.dumps(payload, default=str)


def configure_logging(resource: Resource | None = None, endpoint: str | None = None) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    if resource and endpoint:
        log_provider = LoggerProvider(resource=resource)
        log_provider.add_log_record_processor(
            BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{endpoint.rstrip('/')}/v1/logs"))
        )
        root.addHandler(LoggingHandler(level=logging.NOTSET, logger_provider=log_provider))
    root.setLevel(os.getenv("LOG_LEVEL", "INFO"))


def configure_observability(service_name: str, service_version: str) -> None:
    if os.getenv("OTEL_SDK_DISABLED", "false").lower() == "true":
        configure_logging()
        return
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": os.getenv("ENVIRONMENT", "local"),
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces"))
    )
    trace.set_tracer_provider(provider)
    configure_logging(resource, endpoint)


def instrument_app(app: FastAPI, service_name: str, service_version: str) -> None:
    configure_observability(service_name, service_version)
    HTTPXClientInstrumentor().instrument()
    FastAPIInstrumentor.instrument_app(app)
    app.mount("/metrics", make_asgi_app())

    @app.middleware("http")
    async def metrics_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)
        started = time.perf_counter()
        IN_FLIGHT.labels(service=service_name).inc()
        response: Response
        try:
            response = await call_next(request)
        except Exception:
            duration = time.perf_counter() - started
            route = _route_template(request)
            LATENCY.labels(service_name, request.method, route).observe(duration)
            REQUESTS.labels(service_name, request.method, route, "500").inc()
            raise
        finally:
            IN_FLIGHT.labels(service=service_name).dec()

        duration = time.perf_counter() - started
        route = _route_template(request)
        LATENCY.labels(service_name, request.method, route).observe(duration)
        REQUESTS.labels(service_name, request.method, route, str(response.status_code)).inc()
        response.headers["X-Service-Version"] = service_version
        return response


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", request.url.path)
