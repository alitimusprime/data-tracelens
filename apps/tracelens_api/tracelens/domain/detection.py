from tracelens.domain.signals import AnomalyCandidate, Baseline, SignalWindow


class DetectionEngine:
    """Deterministic RED-signal detection with sample gates and hysteresis-friendly scores."""

    def detect(self, signal: SignalWindow, baseline: Baseline) -> list[AnomalyCandidate]:
        if signal.missing:
            return [
                AnomalyCandidate(
                    service_name=signal.service_name,
                    kind="telemetry_gap",
                    severity="warning",
                    current_value=0,
                    baseline_value=1,
                    score=0.55,
                    evidence={"reason": "Prometheus returned no usable service signals"},
                )
            ]

        anomalies: list[AnomalyCandidate] = []
        if signal.availability < 0.5:
            anomalies.append(
                self._candidate(
                    signal,
                    "availability",
                    "critical",
                    signal.availability,
                    baseline.availability,
                    0.95,
                )
            )

        if signal.sample_count < 8:
            return anomalies

        error_threshold = max(0.15, baseline.error_rate * 3)
        if signal.error_rate >= error_threshold:
            score = min(1.0, 0.55 + signal.error_rate)
            severity = "critical" if signal.error_rate >= 0.5 else "high"
            anomalies.append(
                self._candidate(
                    signal,
                    "error_rate",
                    severity,
                    signal.error_rate,
                    baseline.error_rate,
                    score,
                )
            )

        latency_threshold = max(750.0, baseline.p95_latency_ms * 2.5)
        if signal.p95_latency_ms >= latency_threshold:
            ratio = signal.p95_latency_ms / max(baseline.p95_latency_ms, 1)
            score = min(1.0, 0.45 + ratio / 8)
            severity = "high" if signal.p95_latency_ms >= 1500 else "warning"
            anomalies.append(
                self._candidate(
                    signal,
                    "latency",
                    severity,
                    signal.p95_latency_ms,
                    baseline.p95_latency_ms,
                    score,
                )
            )
        return anomalies

    @staticmethod
    def _candidate(
        signal: SignalWindow,
        kind: str,
        severity: str,
        current: float,
        baseline: float,
        score: float,
    ) -> AnomalyCandidate:
        return AnomalyCandidate(
            service_name=signal.service_name,
            kind=kind,
            severity=severity,
            current_value=current,
            baseline_value=baseline,
            score=round(score, 3),
            evidence={
                "window_start": signal.window_start.isoformat(),
                "window_end": signal.window_end.isoformat(),
                "sample_count": signal.sample_count,
                "current": round(current, 4),
                "baseline": round(baseline, 4),
            },
        )
