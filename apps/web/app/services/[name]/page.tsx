"use client";

import { useParams } from "next/navigation";
import { LineChart } from "@/components/LineChart";
import { Empty, ErrorBox, IncidentRow, Loading, MetricCard, PageHead, StatusPill, fmt, relativeTime } from "@/components/Ui";
import { useLiveQuery } from "@/lib/api";
import type { ServiceDetail } from "@/lib/types";

export default function ServicePage() {
  const { name } = useParams<{ name: string }>();
  const { data, error, loading } = useLiveQuery<ServiceDetail>(`/api/services/${name}`);
  if (loading) return <Loading />;
  if (error || !data) return <ErrorBox message={error} />;
  return <>
    <PageHead eyebrow={`Service · ${data.owner}`} title={data.display_name} description={`Version ${data.version} · Telemetry ${data.telemetry_freshness ? relativeTime(data.telemetry_freshness) : "not received"}`} action={<StatusPill status={data.status} />} />
    <section className="metric-grid service-metrics"><MetricCard label="Request rate" value={fmt(data.request_rate, "/s")} meta="Current analysis window" tone="blue"/><MetricCard label="Error rate" value={fmt(data.error_rate * 100, "%")} meta="Current analysis window" tone="amber"/><MetricCard label="p95 latency" value={fmt(data.p95_latency_ms, " ms")} meta="Current analysis window"/><MetricCard label="Availability" value={fmt(data.availability * 100, "%")} meta="Prometheus target status" tone="violet"/></section>
    <section className="panel"><div className="panel-head"><div><p className="eyebrow">Processed telemetry</p><h2>Signal history</h2></div><small>10-second analysis windows</small></div><div className="chart-grid"><LineChart label="p95 latency (ms)" values={data.history.map((x) => x.p95_latency_ms)} /><LineChart label="error rate (%)" color="#ffbd5a" values={data.history.map((x) => x.error_rate * 100)} /><LineChart label="requests / second" color="#7ba7ff" values={data.history.map((x) => x.request_rate)} /></div></section>
    <section className="service-columns"><article className="panel"><div className="panel-head"><div><p className="eyebrow">Topology</p><h2>Dependencies</h2></div></div>{data.dependencies.length ? <div className="dependency-list">{data.dependencies.map((dependency) => <a href={`/services/${dependency}`} key={dependency}><span>{dependency.slice(0, 1).toUpperCase()}</span><div><strong>{dependency}</strong><small>Observed downstream dependency</small></div><b>→</b></a>)}</div> : <Empty title="No downstream services" text="This service is a leaf in the request graph." />}</article><article className="panel"><div className="panel-head"><div><p className="eyebrow">Change context</p><h2>Recent deployments</h2></div></div>{data.deployments.length ? data.deployments.map((deployment) => <div className="deployment-row" key={deployment.id}><span>{deployment.version}</span><div><strong>{deployment.change_summary}</strong><small>{relativeTime(deployment.deployed_at)} · {deployment.commit_sha}</small></div></div>) : <Empty title="No deployment events" text="Deployment events relevant to this service appear here." />}</article></section>
    <section className="panel incidents-panel"><div className="panel-head"><div><p className="eyebrow">Service history</p><h2>Related incidents</h2></div></div>{data.incidents.length ? data.incidents.map((incident) => <IncidentRow incident={incident} key={incident.id}/>) : <Empty title="No related incidents" text="No incident has affected this service yet."/>}</section>
  </>;
}
