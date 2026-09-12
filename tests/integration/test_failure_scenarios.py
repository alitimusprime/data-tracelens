from datetime import UTC, datetime, timedelta

from tracelens.domain.detection import DetectionEngine
from tracelens.domain.root_cause import RankedAnomaly, rank_root_causes
from tracelens.domain.signals import Baseline, SignalWindow


def window(service: str, error_rate: float, latency_ms: float, offset: int) -> SignalWindow:
    end = datetime.now(UTC) + timedelta(seconds=offset)
    return SignalWindow(
        service_name=service,
        window_start=end - timedelta(minutes=1),
        window_end=end,
        request_rate=2,
        error_rate=error_rate,
        p95_latency_ms=latency_ms,
        availability=1,
        sample_count=120,
        missing=False,
    )


def test_payment_latency_propagation_becomes_one_rankable_evidence_set() -> None:
    baseline = Baseline(error_rate=0.005, p95_latency_ms=100, availability=1, sample_windows=12)
    signals = [
        window("payment", 0, 2200, 0),
        window("order", 0, 2250, 8),
        window("gateway", 0, 2300, 15),
    ]
    detected = [item for signal in signals for item in DetectionEngine().detect(signal, baseline)]
    ranked = rank_root_causes(
        [
            RankedAnomaly(item.service_name, item.kind, item.score, signals[index].window_end)
            for index, item in enumerate(detected)
        ]
    )
    assert {item.service_name for item in detected} == {"payment", "order", "gateway"}
    assert ranked.service_name == "payment"
    assert ranked.confidence >= 0.6
