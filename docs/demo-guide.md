# Repeatable Demo Guide

## Preparation

1. Boot Windows 10 - Docker Mode.
2. Start Docker Desktop.
3. Run `Start-TraceLens.ps1`.
4. Wait one minute for healthy baseline traffic.
5. Confirm that all five service nodes are healthy.

## Payment latency story

1. Start Payment latency regression from Simulator.
2. Explain that the endpoint now waits 2.2 seconds before returning a real authorization.
3. Open Grafana if you want to show the raw latency histogram and traces.
4. Wait for the TraceLens incident.
5. Show that Payment is early, locally strong, a leaf dependency, and followed by upstream degradation.
6. Open the incident and walk through score components, affected services, evidence, timeline, and deployment context.
7. Stop the scenario and show recovery.

## Inventory outage story

This scenario proves that the ranking is not hard-coded to Payment. Inventory returns controlled 503 responses. Order and Gateway fail upstream, while Payment remains healthy because the workflow never reaches it.

## Intermittent Payment story

This scenario fails about 35 percent of calls. It demonstrates partial degradation, sample gates, and evidence accumulation without a full outage.

## Honest statements

- Say “simulated fault with genuine telemetry,” not “production outage.”
- Say “probable root cause ranked by deterministic evidence,” not “proven cause.”
- Say “rule-based statistical detection,” not “machine learning.”
- Say “local portfolio architecture,” not “production scale.”
