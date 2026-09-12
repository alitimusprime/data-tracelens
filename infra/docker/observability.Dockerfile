FROM prom/prometheus:v3.5.0 AS prometheus
COPY infra/prometheus/prometheus.yml /etc/prometheus/prometheus.yml

FROM grafana/tempo:2.8.2 AS tempo
COPY infra/tempo/tempo.yaml /etc/tempo.yaml

FROM grafana/loki:3.5.3 AS loki
COPY infra/loki/loki.yaml /etc/loki/local-config.yaml

FROM grafana/grafana:12.1.1 AS grafana
COPY infra/grafana/provisioning /etc/grafana/provisioning
COPY infra/grafana/dashboards /var/lib/grafana/dashboards

FROM otel/opentelemetry-collector-contrib:0.132.0 AS otel-collector
COPY infra/otel/collector.yaml /etc/otelcol-contrib/config.yaml
