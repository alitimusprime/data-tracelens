from tracelens.infrastructure.models import AnomalyRecord, IncidentRecord
from tracelens.services.ai_investigator import deterministic_explanation


def test_deterministic_explanation_preserves_uncertainty() -> None:
    incident = IncidentRecord(
        title="Payment degradation",
        probable_root_cause="payment",
        confidence=0.81,
        affected_services=["gateway", "order", "payment"],
    )
    incident.anomalies = [
        AnomalyRecord(
            service_name="payment",
            kind="latency",
            severity="high",
            current_value=2200,
            baseline_value=120,
            score=0.95,
        )
    ]
    result = deterministic_explanation(incident)
    assert result["mode"] == "deterministic"
    assert "Payment is the leading hypothesis" in result["explanation"]
    assert "probable cause, not proof" in result["limitations"]
