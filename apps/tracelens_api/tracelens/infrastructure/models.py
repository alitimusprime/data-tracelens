import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tracelens.infrastructure.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid.uuid4())


class ServiceRecord(Base):
    __tablename__ = "services"

    name: Mapped[str] = mapped_column(String(80), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    version: Mapped[str] = mapped_column(String(40), default="0.1.0")
    owner: Mapped[str] = mapped_column(String(120), default="Demo Platform Team")
    endpoint: Mapped[str] = mapped_column(String(255))
    dependencies: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SignalSnapshotRecord(Base):
    __tablename__ = "signal_snapshots"
    __table_args__ = (Index("ix_snapshot_service_time", "service_name", "window_end"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    service_name: Mapped[str] = mapped_column(ForeignKey("services.name"), index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    request_rate: Mapped[float] = mapped_column(Float, default=0)
    error_rate: Mapped[float] = mapped_column(Float, default=0)
    p95_latency_ms: Mapped[float] = mapped_column(Float, default=0)
    availability: Mapped[float] = mapped_column(Float, default=1)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    missing: Mapped[bool] = mapped_column(default=False)


class IncidentRecord(Base):
    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incident_status_updated", "status", "updated_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    severity: Mapped[str] = mapped_column(String(30), default="warning")
    probable_root_cause: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    summary: Mapped[str] = mapped_column(Text, default="Investigation in progress")
    affected_services: Mapped[list[str]] = mapped_column(JSON, default=list)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendations: Mapped[list[str]] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    anomalies: Mapped[list["AnomalyRecord"]] = relationship(back_populates="incident")
    events: Mapped[list["IncidentEventRecord"]] = relationship(
        back_populates="incident", cascade="all, delete-orphan"
    )


class AnomalyRecord(Base):
    __tablename__ = "anomalies"
    __table_args__ = (Index("ix_anomaly_service_status", "service_name", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    incident_id: Mapped[str | None] = mapped_column(ForeignKey("incidents.id"), nullable=True)
    service_name: Mapped[str] = mapped_column(ForeignKey("services.name"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="active")
    severity: Mapped[str] = mapped_column(String(30))
    current_value: Mapped[float] = mapped_column(Float)
    baseline_value: Mapped[float] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    recovery_streak: Mapped[int] = mapped_column(Integer, default=0)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    incident: Mapped[IncidentRecord | None] = relationship(back_populates="anomalies")


class IncidentEventRecord(Base):
    __tablename__ = "incident_events"
    __table_args__ = (Index("ix_event_incident_time", "incident_id", "occurred_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(60))
    service_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    incident: Mapped[IncidentRecord] = relationship(back_populates="events")


class DeploymentRecord(Base):
    __tablename__ = "deployments"
    __table_args__ = (Index("ix_deployment_service_time", "service_name", "deployed_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    service_name: Mapped[str] = mapped_column(ForeignKey("services.name"), index=True)
    version: Mapped[str] = mapped_column(String(40))
    commit_sha: Mapped[str] = mapped_column(String(80), default="simulated")
    environment: Mapped[str] = mapped_column(String(40), default="local")
    change_summary: Mapped[str] = mapped_column(Text)
    simulated: Mapped[bool] = mapped_column(default=True)
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
