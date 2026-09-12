from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from tracelens.domain.detection import DetectionEngine
from tracelens.domain.root_cause import (
    RankedAnomaly,
    rank_root_causes,
    recommendations_for,
)
from tracelens.domain.signals import AnomalyCandidate, Baseline, SignalWindow
from tracelens.infrastructure.events import EventPublisher
from tracelens.infrastructure.models import (
    AnomalyRecord,
    IncidentEventRecord,
    IncidentRecord,
    SignalSnapshotRecord,
    utc_now,
)


class InvestigationService:
    def __init__(
        self,
        session: Session,
        publisher: EventPublisher,
        correlation_window_seconds: int = 180,
    ) -> None:
        self.session = session
        self.publisher = publisher
        self.correlation_window = timedelta(seconds=correlation_window_seconds)
        self.detector = DetectionEngine()

    def process(self, signal: SignalWindow) -> None:
        baseline = self._baseline(signal.service_name)
        snapshot = SignalSnapshotRecord(
            service_name=signal.service_name,
            window_start=signal.window_start,
            window_end=signal.window_end,
            request_rate=signal.request_rate,
            error_rate=signal.error_rate,
            p95_latency_ms=signal.p95_latency_ms,
            availability=signal.availability,
            sample_count=signal.sample_count,
            missing=signal.missing,
        )
        self.session.add(snapshot)
        candidates = self.detector.detect(signal, baseline)
        active_kinds = {candidate.kind for candidate in candidates}
        for candidate in candidates:
            self._upsert_anomaly(candidate)
        self._recover_absent_anomalies(signal.service_name, active_kinds)
        self._refresh_incidents()
        self.session.commit()
        self.publisher.publish(
            "service.updated",
            {
                "service": signal.service_name,
                "error_rate": signal.error_rate,
                "p95_latency_ms": signal.p95_latency_ms,
                "request_rate": signal.request_rate,
            },
        )

    def _baseline(self, service_name: str) -> Baseline:
        records = self.session.scalars(
            select(SignalSnapshotRecord)
            .where(
                SignalSnapshotRecord.service_name == service_name,
                SignalSnapshotRecord.missing.is_(False),
            )
            .order_by(desc(SignalSnapshotRecord.window_end))
            .limit(12)
        ).all()
        if len(records) < 3:
            return Baseline()
        return Baseline(
            request_rate=sum(record.request_rate for record in records) / len(records),
            error_rate=max(0.005, sum(record.error_rate for record in records) / len(records)),
            p95_latency_ms=max(
                50,
                sum(record.p95_latency_ms for record in records) / len(records),
            ),
            availability=sum(record.availability for record in records) / len(records),
            sample_windows=len(records),
        )

    def _upsert_anomaly(self, candidate: AnomalyCandidate) -> None:
        existing = self.session.scalar(
            select(AnomalyRecord).where(
                AnomalyRecord.service_name == candidate.service_name,
                AnomalyRecord.kind == candidate.kind,
                AnomalyRecord.status == "active",
            )
        )
        if existing:
            existing.current_value = candidate.current_value
            existing.baseline_value = candidate.baseline_value
            existing.score = candidate.score
            existing.severity = candidate.severity
            existing.evidence = candidate.evidence
            existing.recovery_streak = 0
            existing.updated_at = utc_now()
            return
        anomaly = AnomalyRecord(
            service_name=candidate.service_name,
            kind=candidate.kind,
            severity=candidate.severity,
            current_value=candidate.current_value,
            baseline_value=candidate.baseline_value,
            score=candidate.score,
            evidence=candidate.evidence,
        )
        incident = self._correlate(candidate.service_name)
        if not incident:
            incident = IncidentRecord(
                title=(
                    f"{candidate.service_name.title()} "
                    f"{candidate.kind.replace('_', ' ')} degradation"
                ),
                severity=candidate.severity,
                affected_services=[candidate.service_name],
            )
            self.session.add(incident)
            self.session.flush()
            self.session.add(
                IncidentEventRecord(
                    incident_id=incident.id,
                    event_type="incident.opened",
                    service_name=candidate.service_name,
                    message="A new anomaly opened the incident.",
                )
            )
        anomaly.incident = incident
        self.session.add(anomaly)
        self.session.flush()
        self.session.add(
            IncidentEventRecord(
                incident_id=incident.id,
                event_type="anomaly.detected",
                service_name=candidate.service_name,
                message=(
                    f"{candidate.kind.replace('_', ' ').title()} crossed its detection threshold."
                ),
                details=candidate.evidence,
            )
        )
        self.publisher.publish("incident.changed", {"incident_id": incident.id, "status": "open"})

    def _correlate(self, service_name: str) -> IncidentRecord | None:
        cutoff = datetime.now(UTC) - self.correlation_window
        incidents = self.session.scalars(
            select(IncidentRecord)
            .where(IncidentRecord.status.in_(["open", "investigating"]))
            .order_by(desc(IncidentRecord.updated_at))
        ).all()
        for incident in incidents:
            updated = incident.updated_at
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=UTC)
            if updated < cutoff:
                continue
            existing = set(incident.affected_services or [])
            if service_name in existing or _services_related(service_name, existing):
                return incident
        return None

    def _recover_absent_anomalies(self, service_name: str, active_kinds: set[str]) -> None:
        existing = self.session.scalars(
            select(AnomalyRecord).where(
                AnomalyRecord.service_name == service_name,
                AnomalyRecord.status == "active",
            )
        ).all()
        for anomaly in existing:
            if anomaly.kind not in active_kinds:
                anomaly.recovery_streak += 1
                if anomaly.recovery_streak < 2:
                    continue
                anomaly.status = "recovered"
                anomaly.recovered_at = utc_now()
                anomaly.updated_at = utc_now()
                if anomaly.incident_id:
                    anomaly_label = anomaly.kind.replace("_", " ").title()
                    self.session.add(
                        IncidentEventRecord(
                            incident_id=anomaly.incident_id,
                            event_type="anomaly.recovered",
                            service_name=service_name,
                            message=f"{anomaly_label} returned below threshold.",
                        )
                    )

    def _refresh_incidents(self) -> None:
        incidents = self.session.scalars(
            select(IncidentRecord).where(IncidentRecord.status.in_(["open", "investigating"]))
        ).all()
        for incident in incidents:
            active = [item for item in incident.anomalies if item.status == "active"]
            if not active:
                incident.status = "resolved"
                incident.resolved_at = utc_now()
                incident.updated_at = utc_now()
                self.session.add(
                    IncidentEventRecord(
                        incident_id=incident.id,
                        event_type="incident.resolved",
                        message="All correlated anomalies recovered.",
                    )
                )
                self.publisher.publish(
                    "incident.changed", {"incident_id": incident.id, "status": "resolved"}
                )
                continue
            ranked = [
                RankedAnomaly(
                    service_name=item.service_name,
                    kind=item.kind,
                    anomaly_score=item.score,
                    detected_at=item.detected_at,
                )
                for item in active
            ]
            result = rank_root_causes(ranked)
            incident.status = "investigating"
            incident.probable_root_cause = result.service_name
            incident.confidence = result.confidence
            incident.score_breakdown = result.scores
            incident.affected_services = result.affected_services
            incident.severity = _highest_severity(item.severity for item in active)
            kinds = {item.kind for item in active if item.service_name == result.service_name}
            incident.recommendations = recommendations_for(result.service_name, kinds)
            incident.summary = _summary(result.service_name, active, result.confidence)
            incident.updated_at = utc_now()


def _services_related(service: str, existing: set[str]) -> bool:
    graph = {
        "gateway": {"order"},
        "order": {"gateway", "inventory", "payment", "notification"},
        "inventory": {"order", "gateway"},
        "payment": {"order", "gateway"},
        "notification": {"order", "gateway"},
    }
    return bool(graph.get(service, set()).intersection(existing))


def _highest_severity(values: Iterable[str]) -> str:
    order = {"warning": 1, "high": 2, "critical": 3}
    return max(values, key=lambda item: order.get(item, 0), default="warning")


def _summary(root_cause: str | None, anomalies: list[AnomalyRecord], confidence: float) -> str:
    if not root_cause:
        return "TraceLens has not collected enough independent evidence to select a root cause."
    kinds = sorted({item.kind.replace("_", " ") for item in anomalies})
    return (
        f"{root_cause.title()} is the probable root cause based on "
        f"{', '.join(kinds)} evidence. Deterministic confidence is {confidence:.0%}."
    )
