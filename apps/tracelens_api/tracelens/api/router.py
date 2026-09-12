import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from tracelens.config import get_settings
from tracelens.infrastructure.database import get_session
from tracelens.infrastructure.events import EventPublisher, subscribe
from tracelens.infrastructure.models import (
    AnomalyRecord,
    DeploymentRecord,
    IncidentEventRecord,
    IncidentRecord,
    ServiceRecord,
    SignalSnapshotRecord,
)
from tracelens.services.ai_investigator import explain_with_optional_ai
from tracelens.services.simulator import SCENARIOS, SimulatorService
from tracelens.services.telemetry_evidence import TelemetryEvidenceService

router = APIRouter(prefix="/api")
settings = get_settings()
publisher = EventPublisher(settings.redis_url)


def latest_snapshot(session: Session, service: str) -> SignalSnapshotRecord | None:
    return session.scalar(
        select(SignalSnapshotRecord)
        .where(SignalSnapshotRecord.service_name == service)
        .order_by(desc(SignalSnapshotRecord.window_end))
        .limit(1)
    )


@router.get("/overview")
def overview(session: Session = Depends(get_session)) -> dict:
    services = session.scalars(select(ServiceRecord).order_by(ServiceRecord.name)).all()
    active_anomalies = session.scalars(
        select(AnomalyRecord).where(AnomalyRecord.status == "active")
    ).all()
    anomaly_map: dict[str, list[AnomalyRecord]] = {}
    for anomaly in active_anomalies:
        anomaly_map.setdefault(anomaly.service_name, []).append(anomaly)
    service_items = []
    total_rate = 0.0
    error_weighted = 0.0
    p95_values = []
    for service in services:
        snapshot = latest_snapshot(session, service.name)
        status = "degraded" if service.name in anomaly_map else "healthy"
        if snapshot and snapshot.missing:
            status = "unknown"
        rate = snapshot.request_rate if snapshot else 0
        total_rate += rate
        error_weighted += (snapshot.error_rate * rate) if snapshot else 0
        if snapshot:
            p95_values.append(snapshot.p95_latency_ms)
        service_items.append(_service_dict(service, snapshot, status))
    active_incidents = session.scalar(
        select(func.count())
        .select_from(IncidentRecord)
        .where(IncidentRecord.status.in_(["open", "investigating"]))
    )
    incidents = session.scalars(
        select(IncidentRecord).order_by(desc(IncidentRecord.updated_at)).limit(6)
    ).all()
    events = session.scalars(
        select(IncidentEventRecord).order_by(desc(IncidentEventRecord.occurred_at)).limit(12)
    ).all()
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "system_status": "degraded" if active_incidents else "healthy",
        "metrics": {
            "active_incidents": active_incidents or 0,
            "healthy_services": sum(item["status"] == "healthy" for item in service_items),
            "request_rate": round(total_rate, 2),
            "error_rate": round(error_weighted / total_rate, 4) if total_rate else 0,
            "p95_latency_ms": round(max(p95_values), 1) if p95_values else 0,
        },
        "services": service_items,
        "edges": [
            {"source": service.name, "target": dependency}
            for service in services
            for dependency in service.dependencies
        ],
        "incidents": [_incident_summary(item) for item in incidents],
        "activity": [_event_dict(item) for item in events],
    }


@router.get("/services")
def services(session: Session = Depends(get_session)) -> list[dict]:
    records = session.scalars(select(ServiceRecord).order_by(ServiceRecord.name)).all()
    return [
        _service_dict(
            record, latest_snapshot(session, record.name), _service_status(session, record.name)
        )
        for record in records
    ]


@router.get("/services/{service_name}")
def service_detail(service_name: str, session: Session = Depends(get_session)) -> dict:
    service = session.get(ServiceRecord, service_name)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    snapshots = session.scalars(
        select(SignalSnapshotRecord)
        .where(SignalSnapshotRecord.service_name == service_name)
        .order_by(desc(SignalSnapshotRecord.window_end))
        .limit(30)
    ).all()
    incident_candidates = session.scalars(
        select(IncidentRecord).order_by(desc(IncidentRecord.updated_at)).limit(100)
    ).all()
    incidents = [
        incident
        for incident in incident_candidates
        if service_name in (incident.affected_services or [])
    ][:10]
    deployments = session.scalars(
        select(DeploymentRecord)
        .where(DeploymentRecord.service_name == service_name)
        .order_by(desc(DeploymentRecord.deployed_at))
        .limit(10)
    ).all()
    return {
        **_service_dict(
            service,
            snapshots[0] if snapshots else None,
            _service_status(session, service_name),
        ),
        "history": [
            {
                "timestamp": item.window_end.isoformat(),
                "request_rate": item.request_rate,
                "error_rate": item.error_rate,
                "p95_latency_ms": item.p95_latency_ms,
            }
            for item in reversed(snapshots)
        ],
        "incidents": [_incident_summary(item) for item in incidents],
        "deployments": [_deployment_dict(item) for item in deployments],
    }


@router.get("/incidents")
def incidents(session: Session = Depends(get_session)) -> list[dict]:
    records = session.scalars(
        select(IncidentRecord).order_by(desc(IncidentRecord.updated_at)).limit(100)
    ).all()
    return [_incident_summary(item) for item in records]


@router.get("/incidents/{incident_id}")
async def incident_detail(incident_id: str, session: Session = Depends(get_session)) -> dict:
    incident = session.get(IncidentRecord, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    deployments = session.scalars(
        select(DeploymentRecord)
        .where(
            DeploymentRecord.service_name.in_(incident.affected_services or []),
            DeploymentRecord.deployed_at >= incident.started_at - timedelta(minutes=15),
        )
        .order_by(DeploymentRecord.deployed_at)
    ).all()
    telemetry_evidence = await TelemetryEvidenceService(
        settings.tempo_url,
        settings.loki_url,
    ).collect(incident.probable_root_cause, incident.started_at)
    timeline = [_event_dict(item) for item in incident.events]
    timeline.extend(
        {
            "id": deployment.id,
            "type": "deployment.recorded",
            "service": deployment.service_name,
            "message": f"Version {deployment.version} was deployed.",
            "details": {"simulated": deployment.simulated},
            "timestamp": deployment.deployed_at.isoformat(),
        }
        for deployment in deployments
    )
    timeline.sort(key=lambda item: item["timestamp"])
    return {
        **_incident_summary(incident),
        "summary": incident.summary,
        "score_breakdown": incident.score_breakdown,
        "recommendations": incident.recommendations,
        "anomalies": [_anomaly_dict(item) for item in incident.anomalies],
        "timeline": timeline,
        "deployments": [_deployment_dict(item) for item in deployments],
        "ai_investigation": await explain_with_optional_ai(incident, settings),
        "telemetry_evidence": telemetry_evidence,
        "evidence_links": {
            "grafana": "http://localhost:3001",
            "tempo": "http://localhost:3001/explore",
            "loki": "http://localhost:3001/explore",
        },
    }


@router.get("/deployments")
def deployments(session: Session = Depends(get_session)) -> list[dict]:
    records = session.scalars(
        select(DeploymentRecord).order_by(desc(DeploymentRecord.deployed_at)).limit(100)
    ).all()
    return [_deployment_dict(item) for item in records]


@router.get("/simulator/scenarios")
def scenarios() -> list[dict]:
    return [
        {
            **{
                key: value
                for key, value in item.items()
                if key not in {"profile", "deployment", "service"}
            },
            "target": item["service"],
        }
        for item in SCENARIOS.values()
    ]


@router.post("/simulator/scenarios/{scenario_id}/start")
async def start_scenario(scenario_id: str, session: Session = Depends(get_session)) -> dict:
    if not settings.simulator_enabled:
        raise HTTPException(status_code=404, detail="Simulator is disabled")
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")
    try:
        return await SimulatorService(session, publisher).start(scenario_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Scenario could not be started") from exc


@router.post("/simulator/scenarios/{scenario_id}/stop")
async def stop_scenario(scenario_id: str, session: Session = Depends(get_session)) -> dict:
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")
    try:
        return await SimulatorService(session, publisher).stop(scenario_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Scenario could not be stopped") from exc


@router.get("/events")
async def events() -> StreamingResponse:
    async def stream() -> AsyncIterator[str]:
        iterator = subscribe(settings.redis_url).__aiter__()
        while True:
            try:
                item = await asyncio.wait_for(iterator.__anext__(), timeout=15)
                yield f"data: {item}\n\n"
            except TimeoutError:
                yield ": keepalive\n\n"
            except StopAsyncIteration:
                break

    return StreamingResponse(stream(), media_type="text/event-stream")


def _service_status(session: Session, name: str) -> str:
    active = session.scalar(
        select(func.count())
        .select_from(AnomalyRecord)
        .where(
            AnomalyRecord.service_name == name,
            AnomalyRecord.status == "active",
        )
    )
    snapshot = latest_snapshot(session, name)
    if snapshot and snapshot.missing:
        return "unknown"
    return "degraded" if active else "healthy"


def _service_dict(
    service: ServiceRecord,
    snapshot: SignalSnapshotRecord | None,
    status: str,
) -> dict[str, Any]:
    return {
        "name": service.name,
        "display_name": service.display_name,
        "version": service.version,
        "owner": service.owner,
        "dependencies": service.dependencies,
        "status": status,
        "telemetry_freshness": snapshot.window_end.isoformat() if snapshot else None,
        "request_rate": round(snapshot.request_rate, 2) if snapshot else 0,
        "error_rate": round(snapshot.error_rate, 4) if snapshot else 0,
        "p95_latency_ms": round(snapshot.p95_latency_ms, 1) if snapshot else 0,
        "availability": snapshot.availability if snapshot else 0,
    }


def _incident_summary(incident: IncidentRecord) -> dict:
    return {
        "id": incident.id,
        "title": incident.title,
        "status": incident.status,
        "severity": incident.severity,
        "probable_root_cause": incident.probable_root_cause,
        "confidence": incident.confidence,
        "affected_services": incident.affected_services,
        "started_at": incident.started_at.isoformat(),
        "updated_at": incident.updated_at.isoformat(),
        "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
    }


def _anomaly_dict(anomaly: AnomalyRecord) -> dict:
    return {
        "id": anomaly.id,
        "service": anomaly.service_name,
        "kind": anomaly.kind,
        "status": anomaly.status,
        "severity": anomaly.severity,
        "current_value": anomaly.current_value,
        "baseline_value": anomaly.baseline_value,
        "score": anomaly.score,
        "evidence": anomaly.evidence,
        "detected_at": anomaly.detected_at.isoformat(),
        "recovered_at": anomaly.recovered_at.isoformat() if anomaly.recovered_at else None,
    }


def _event_dict(event: IncidentEventRecord) -> dict:
    return {
        "id": event.id,
        "type": event.event_type,
        "service": event.service_name,
        "message": event.message,
        "details": event.details,
        "timestamp": event.occurred_at.isoformat(),
    }


def _deployment_dict(record: DeploymentRecord) -> dict:
    return {
        "id": record.id,
        "service": record.service_name,
        "version": record.version,
        "commit_sha": record.commit_sha,
        "environment": record.environment,
        "change_summary": record.change_summary,
        "simulated": record.simulated,
        "deployed_at": record.deployed_at.isoformat(),
    }
