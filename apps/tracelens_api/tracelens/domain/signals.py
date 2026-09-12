from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SignalWindow:
    service_name: str
    window_start: datetime
    window_end: datetime
    request_rate: float
    error_rate: float
    p95_latency_ms: float
    availability: float
    sample_count: int
    missing: bool = False


@dataclass(frozen=True)
class Baseline:
    request_rate: float = 0
    error_rate: float = 0.01
    p95_latency_ms: float = 150
    availability: float = 1
    sample_windows: int = 0


@dataclass(frozen=True)
class AnomalyCandidate:
    service_name: str
    kind: str
    severity: str
    current_value: float
    baseline_value: float
    score: float
    evidence: dict
