# Interview Guide

## Thirty-second explanation

TraceLens is a local incident investigation platform built on a genuinely instrumented commerce system. OpenTelemetry sends traces and logs to Tempo and Loki, Prometheus stores RED metrics, and a separate analyzer converts windows into anomalies. TraceLens correlates those anomalies using topology and time, deterministically ranks probable causes, shows the score factors and source evidence, and updates a Next.js operator UI through SSE.

## Strong engineering points

- Specialized telemetry stores remain the raw source of truth.
- PostgreSQL stores relational investigation state and compact evidence snapshots.
- Redis transports live invalidation events but is not authoritative.
- Minimum samples, baselines, absolute floors, and missing-data states reduce misleading alerts.
- Root-cause selection occurs before the optional LLM.
- Three scenarios distinguish one failure pattern from another.
- Recovery is detected from new telemetry rather than from the simulator stop command.

## Tradeoffs to explain

- SSE fits one-way browser updates and has simpler reconnect behavior than WebSockets.
- NATS provides a real durable asynchronous workflow with less local overhead than Kafka.
- A modular backend avoids unnecessary internal microservices.
- Rule-based detection is inspectable and testable with limited synthetic history.
- Short retention and local storage keep the workstation requirements reasonable.

## Production improvements

- Authentication, authorization, tenant and environment isolation
- Horizontally partitioned analysis with idempotent work ownership
- Calibrated adaptive baselines and detector evaluation datasets
- Longer evidence retention and object storage
- Alert routing, acknowledgement, assignment, and runbooks
- Kubernetes discovery and deployment metadata
- Backpressure, queues, and stronger event delivery guarantees where measured load requires them
- Formal SLOs, capacity tests, and disaster recovery

## Truthful resume bullets

- Built a Docker Compose incident investigation platform around five OpenTelemetry-instrumented services, with Prometheus metrics, Tempo traces, Loki logs, and NATS JetStream events.
- Implemented deterministic anomaly detection, topology-aware incident correlation, root-cause ranking, explainable confidence scoring, and recovery lifecycle logic in Python.
- Developed a live Next.js operations dashboard with service topology, source telemetry evidence, incident timelines, and Server-Sent Event updates.
- Added PostgreSQL migrations, integration and scenario tests, container build validation, secret scanning, and vulnerability scanning in GitHub Actions.
