from datetime import UTC, datetime, timedelta

from tracelens.domain.detection import DetectionEngine
from tracelens.domain.signals import Baseline, SignalWindow

NOW = datetime.now(UTC)
BASELINE = Baseline(
    request_rate=2,
    error_rate=0.01,
    p95_latency_ms=120,
    availability=1,
    sample_windows=12,
)


def signal(**overrides) -> SignalWindow:
    values = {
        "service_name": "payment",
        "window_start": NOW - timedelta(minutes=1),
        "window_end": NOW,
        "request_rate": 2,
        "error_rate": 0,
        "p95_latency_ms": 120,
        "availability": 1,
        "sample_count": 120,
        "missing": False,
    }
    values.update(overrides)
    return SignalWindow(**values)


def test_healthy_signal_does_not_create_anomaly() -> None:
    assert DetectionEngine().detect(signal(), BASELINE) == []


def test_partial_error_degradation_crosses_sample_gated_threshold() -> None:
    anomalies = DetectionEngine().detect(signal(error_rate=0.35), BASELINE)
    assert [(item.kind, item.severity) for item in anomalies] == [("error_rate", "high")]
    assert anomalies[0].score > 0.8


def test_low_sample_noise_is_ignored() -> None:
    assert DetectionEngine().detect(signal(error_rate=1, sample_count=3), BASELINE) == []


def test_latency_regression_is_detected_against_absolute_floor() -> None:
    anomaly = DetectionEngine().detect(signal(p95_latency_ms=2200), BASELINE)[0]
    assert anomaly.kind == "latency"
    assert anomaly.severity == "high"
    assert anomaly.current_value == 2200


def test_missing_telemetry_is_explicit_not_assumed_healthy() -> None:
    anomaly = DetectionEngine().detect(signal(missing=True), BASELINE)[0]
    assert anomaly.kind == "telemetry_gap"
    assert anomaly.evidence["reason"]


def test_unavailable_target_is_critical_even_with_no_request_samples() -> None:
    anomaly = DetectionEngine().detect(signal(availability=0, sample_count=0), BASELINE)[0]
    assert anomaly.kind == "availability"
    assert anomaly.severity == "critical"
