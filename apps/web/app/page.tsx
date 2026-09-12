"use client";

import Link from "next/link";
import { ServiceGraph } from "@/components/ServiceGraph";
import { Empty, ErrorBox, IncidentRow, Loading, MetricCard, PageHead, StatusPill, fmt, relativeTime } from "@/components/Ui";
import { useLiveQuery } from "@/lib/api";
import type { Overview } from "@/lib/types";

export default function OverviewPage() {
  const { data, error, loading } = useLiveQuery<Overview>("/api/overview");
  if (loading) return <Loading />;
  if (error || !data) return <ErrorBox message={error} />;
  const m = data.metrics;
  return <>
    <PageHead eyebrow="System overview" title="Good morning, operator." description="A live, evidence-first view of your distributed system." action={<Link className="primary-button" href="/simulator"><span>＋</span> Run incident simulation</Link>} />
    <section className="health-banner">
      <div className={`health-orb ${data.system_status}`}><span /><i /></div>
      <div><small>Current system state</small><h2>{data.system_status === "healthy" ? "All systems operational" : "Active degradation detected"}</h2><p>{data.system_status === "healthy" ? "TraceLens is monitoring every dependency." : "An investigation is underway. Open the latest incident for evidence."}</p></div>
      <StatusPill status={data.system_status} />
      <time>Updated {relativeTime(data.generated_at)}</time>
    </section>
    <section className="metric-grid">
      <MetricCard label="Active incidents" value={String(m.active_incidents)} meta={m.active_incidents ? "Needs attention" : "No open investigations"} tone="amber" />
      <MetricCard label="Healthy services" value={`${m.healthy_services}/${data.services.length}`} meta="Reporting live telemetry" />
      <MetricCard label="Request throughput" value={fmt(m.request_rate, "/s")} meta="Across measured services" tone="blue" />
      <MetricCard label="Global error rate" value={fmt(m.error_rate * 100, "%")} meta="Traffic-weighted" tone="violet" />
      <MetricCard label="Highest p95 latency" value={fmt(m.p95_latency_ms, " ms")} meta="Slowest measured service" tone="blue" />
    </section>
    <section className="dashboard-grid">
      <article className="panel graph-panel">
        <div className="panel-head"><div><p className="eyebrow">Live topology</p><h2>Service dependency graph</h2></div><span className="live-chip"><i /> Live</span></div>
        <ServiceGraph services={data.services} edges={data.edges} />
        <div className="graph-legend"><span><i className="healthy"/>Healthy</span><span><i className="degraded"/>Degraded</span><span><i className="unknown"/>No telemetry</span><small>Select a service to inspect its signals</small></div>
      </article>
      <article className="panel activity-panel">
        <div className="panel-head"><div><p className="eyebrow">Event stream</p><h2>Recent activity</h2></div></div>
        {data.activity.length ? <div className="activity-list">{data.activity.map((item) => <div className="activity-item" key={item.id}><span className={item.type.includes("resolved") ? "resolved" : item.type.includes("detected") ? "alert" : "info"}>{item.type.includes("resolved") ? "✓" : item.type.includes("detected") ? "!" : "·"}</span><div><strong>{item.message}</strong><small>{item.service || "TraceLens"} · {relativeTime(item.timestamp)}</small></div></div>)}</div> : <Empty title="No investigation events yet" text="Run a scenario to watch detection, correlation, and recovery happen here." />}
      </article>
    </section>
    <section className="panel incidents-panel">
      <div className="panel-head"><div><p className="eyebrow">Investigations</p><h2>Latest incidents</h2></div><Link className="text-link" href="/incidents">View all →</Link></div>
      {data.incidents.length ? <div>{data.incidents.map((incident) => <IncidentRow incident={incident} key={incident.id} />)}</div> : <Empty title="No incidents detected" text="The system is healthy. The simulator can create a genuine, observable failure." />}
    </section>
  </>;
}
