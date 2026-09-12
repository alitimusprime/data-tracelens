from datetime import UTC, datetime, timedelta

from tracelens.domain.root_cause import RankedAnomaly, rank_root_causes, recommendations_for


def anomaly(service: str, kind: str, score: float, seconds: int) -> RankedAnomaly:
    return RankedAnomaly(
        service_name=service,
        kind=kind,
        anomaly_score=score,
        detected_at=datetime.now(UTC) + timedelta(seconds=seconds),
    )


def test_payment_ranks_above_propagated_upstream_latency() -> None:
    result = rank_root_causes(
        [
            anomaly("payment", "latency", 0.95, 0),
            anomaly("order", "latency", 0.8, 10),
            anomaly("gateway", "latency", 0.7, 20),
        ]
    )
    assert result.service_name == "payment"
    assert result.scores["payment"]["upstream_impact"] > 0
    assert result.scores["payment"]["dependency_specificity"] > 0
    assert result.affected_services == ["gateway", "order", "payment"]


def test_inventory_scenario_selects_different_root_cause() -> None:
    result = rank_root_causes(
        [
            anomaly("inventory", "error_rate", 0.96, 0),
            anomaly("order", "error_rate", 0.82, 5),
            anomaly("gateway", "error_rate", 0.75, 9),
        ]
    )
    assert result.service_name == "inventory"


def test_empty_evidence_returns_unknown() -> None:
    result = rank_root_causes([])
    assert result.service_name is None
    assert result.confidence == 0


def test_recommendations_are_signal_specific() -> None:
    actions = recommendations_for("payment", {"latency", "error_rate"})
    assert any("slow payment spans" in item for item in actions)
    assert any("error logs" in item for item in actions)
