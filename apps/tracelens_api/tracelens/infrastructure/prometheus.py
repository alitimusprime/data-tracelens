from datetime import UTC, datetime, timedelta

import httpx

from tracelens.domain.signals import SignalWindow


class PrometheusClient:
    def __init__(self, base_url: str, timeout: float = 4.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def collect(self, service_name: str, window_seconds: int = 60) -> SignalWindow:
        window_end = datetime.now(UTC)
        window_start = window_end - timedelta(seconds=window_seconds)
        try:
            request_rate = self._query(
                f'sum(rate(tracelens_http_requests_total{{service="{service_name}"}}[1m]))'
            )
            total = self._query(
                f'sum(increase(tracelens_http_requests_total{{service="{service_name}"}}[1m]))'
            )
            errors = self._query(
                f'sum(increase(tracelens_http_requests_total{{service="{service_name}",status=~"5.."}}[1m]))'
            )
            p95_seconds = self._query(
                "histogram_quantile(0.95, "
                "sum(rate(tracelens_http_request_duration_seconds_bucket"
                f'{{service="{service_name}"}}[1m])) '
                "by (le))"
            )
            availability = self._query(f'max(up{{job="demo-services",service="{service_name}"}})')
        except (httpx.HTTPError, ValueError, KeyError):
            return SignalWindow(
                service_name=service_name,
                window_start=window_start,
                window_end=window_end,
                request_rate=0,
                error_rate=0,
                p95_latency_ms=0,
                availability=0,
                sample_count=0,
                missing=True,
            )
        return SignalWindow(
            service_name=service_name,
            window_start=window_start,
            window_end=window_end,
            request_rate=request_rate,
            error_rate=(errors / total) if total > 0 else 0,
            p95_latency_ms=p95_seconds * 1000,
            availability=availability,
            sample_count=int(total),
            missing=False,
        )

    def _query(self, expression: str) -> float:
        response = httpx.get(
            f"{self.base_url}/api/v1/query",
            params={"query": expression},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise ValueError("Prometheus query failed")
        result = payload.get("data", {}).get("result", [])
        if not result:
            return 0.0
        value = result[0].get("value", [None, "0"])[1]
        if value in ("NaN", "+Inf", "-Inf", None):
            return 0.0
        return float(value)
