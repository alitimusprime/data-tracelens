from dataclasses import dataclass
from datetime import datetime

TOPOLOGY: dict[str, list[str]] = {
    "gateway": ["order"],
    "order": ["inventory", "payment", "notification"],
    "inventory": [],
    "payment": [],
    "notification": [],
}


@dataclass(frozen=True)
class RankedAnomaly:
    service_name: str
    kind: str
    anomaly_score: float
    detected_at: datetime


@dataclass(frozen=True)
class RootCauseResult:
    service_name: str | None
    confidence: float
    scores: dict[str, dict[str, float]]
    affected_services: list[str]


def rank_root_causes(anomalies: list[RankedAnomaly]) -> RootCauseResult:
    if not anomalies:
        return RootCauseResult(None, 0, {}, [])
    first_seen = min(item.detected_at for item in anomalies)
    anomalous_services = {item.service_name for item in anomalies}
    scores: dict[str, dict[str, float]] = {}

    for service in anomalous_services:
        own = [item for item in anomalies if item.service_name == service]
        signal_strength = min(0.55, max(item.anomaly_score for item in own) * 0.55)
        lead_seconds = min((item.detected_at - first_seen).total_seconds() for item in own)
        timing = max(0.0, 0.2 - min(lead_seconds / 300, 0.2))
        impacted_upstreams = _upstreams_of(service) & anomalous_services
        propagation = min(0.2, len(impacted_upstreams) * 0.1)
        leaf_specificity = 0.05 if not TOPOLOGY.get(service) else 0.0
        total = min(1.0, signal_strength + timing + propagation + leaf_specificity)
        scores[service] = {
            "signal_strength": round(signal_strength, 3),
            "earliest_signal": round(timing, 3),
            "upstream_impact": round(propagation, 3),
            "dependency_specificity": round(leaf_specificity, 3),
            "total": round(total, 3),
        }

    ordered = sorted(scores, key=lambda item: scores[item]["total"], reverse=True)
    winner = ordered[0]
    winner_score = scores[winner]["total"]
    runner_up = scores[ordered[1]]["total"] if len(ordered) > 1 else 0
    separation = max(0.0, winner_score - runner_up)
    independent_evidence = min(0.15, len(anomalies) * 0.025)
    confidence = min(0.96, winner_score * 0.75 + separation * 0.2 + independent_evidence)
    affected = sorted(anomalous_services | _upstreams_of(winner))
    return RootCauseResult(winner, round(confidence, 3), scores, affected)


def _upstreams_of(target: str) -> set[str]:
    upstreams: set[str] = set()
    changed = True
    while changed:
        changed = False
        for service, dependencies in TOPOLOGY.items():
            if service not in upstreams and (
                target in dependencies or upstreams.intersection(dependencies)
            ):
                upstreams.add(service)
                changed = True
    return upstreams


def recommendations_for(service: str | None, kinds: set[str]) -> list[str]:
    if not service:
        return ["Collect more telemetry before selecting a remediation path."]
    actions = [f"Inspect recent {service} changes and compare them with the incident start time."]
    if "latency" in kinds:
        actions.append(f"Inspect slow {service} spans and downstream timeout configuration.")
    if "error_rate" in kinds or "availability" in kinds:
        actions.append(
            f"Review {service} error logs and dependency health before retrying traffic."
        )
    actions.append("Validate recovery across two analysis windows before resolving the incident.")
    return actions
