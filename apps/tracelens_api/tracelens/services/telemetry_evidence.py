from datetime import datetime
from typing import Any

import httpx


class TelemetryEvidenceService:
    """Read representative source telemetry without making it TraceLens state."""

    def __init__(self, tempo_url: str, loki_url: str) -> None:
        self.tempo_url = tempo_url.rstrip("/")
        self.loki_url = loki_url.rstrip("/")

    async def collect(
        self,
        service_name: str | None,
        started_at: datetime,
    ) -> dict[str, Any]:
        if not service_name:
            return {"traces": [], "logs": [], "partial": True}
        start_ns = int(started_at.timestamp() * 1_000_000_000)
        end_ns = int(datetime.now(started_at.tzinfo).timestamp() * 1_000_000_000)
        async with httpx.AsyncClient(timeout=4) as client:
            traces = await self._traces(client, service_name, start_ns, end_ns)
            logs = await self._logs(client, service_name, start_ns, end_ns)
        return {"traces": traces, "logs": logs, "partial": not traces or not logs}

    async def _traces(
        self,
        client: httpx.AsyncClient,
        service_name: str,
        start_ns: int,
        end_ns: int,
    ) -> list[dict[str, Any]]:
        try:
            response = await client.get(
                f"{self.tempo_url}/api/search",
                params={
                    "q": f'{{ resource.service.name = "{service_name}" }}',
                    "start": start_ns // 1_000_000_000,
                    "end": end_ns // 1_000_000_000,
                    "limit": 5,
                },
            )
            response.raise_for_status()
            return [
                {
                    "trace_id": item.get("traceID"),
                    "root_service": item.get("rootServiceName"),
                    "root_span": item.get("rootTraceName"),
                    "duration_ms": round(float(item.get("durationMs", 0)), 2),
                    "started_at": item.get("startTimeUnixNano"),
                }
                for item in response.json().get("traces", [])
            ]
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return []

    async def _logs(
        self,
        client: httpx.AsyncClient,
        service_name: str,
        start_ns: int,
        end_ns: int,
    ) -> list[dict[str, Any]]:
        try:
            response = await client.get(
                f"{self.loki_url}/loki/api/v1/query_range",
                params={
                    "query": f'{{service_name="{service_name}"}}',
                    "start": start_ns,
                    "end": end_ns,
                    "limit": 10,
                    "direction": "backward",
                },
            )
            response.raise_for_status()
            records: list[dict[str, Any]] = []
            for stream in response.json().get("data", {}).get("result", []):
                labels = stream.get("stream", {})
                for timestamp, line, *metadata in stream.get("values", []):
                    records.append(
                        {
                            "timestamp": timestamp,
                            "line": line,
                            "labels": labels,
                            "metadata": metadata[0] if metadata else {},
                        }
                    )
            return records[:10]
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return []
