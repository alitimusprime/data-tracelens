"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ErrorBox, Loading, PageHead, StatusPill, fmt, relativeTime } from "@/components/Ui";
import { useLiveQuery } from "@/lib/api";
import type { IncidentDetail } from "@/lib/types";

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading } = useLiveQuery<IncidentDetail>(`/api/incidents/${id}`);
  if (loading) return <Loading />;
  if (error || !data) return <ErrorBox message={error} />;
  const scores = Object.entries(data.score_breakdown).sort((a, b) => (b[1].total || 0) - (a[1].total || 0));
  return <>
    <Link href="/incidents" className="back-link">← All incidents</Link>
    <PageHead eyebrow={`Incident · ${data.severity}`} title={data.title} description={`Detected ${relativeTime(data.started_at)} · ${data.affected_services.length} affected services`} action={<StatusPill status={data.status} />} />
    <section className="incident-hero">
      <div><p className="eyebrow">Probable root cause</p><h2>{data.probable_root_cause?.toUpperCase() || "INVESTIGATING"}</h2><p>{data.summary}</p></div>
      <div className="confidence-ring" style={{ "--score": `${Math.round(data.confidence * 360)}deg` } as React.CSSProperties}><span><strong>{Math.round(data.confidence * 100)}%</strong><small>confidence</small></span></div>
      <div className="facts"><div><small>Severity</small><strong className={data.severity}>{data.severity}</strong></div><div><small>Affected</small><strong>{data.affected_services.join(", ")}</strong></div><div><small>Updated</small><strong>{relativeTime(data.updated_at)}</strong></div></div>
    </section>
    <section className="investigation-grid">
      <article className="panel"><div className="panel-head"><div><p className="eyebrow">Deterministic analysis</p><h2>Root-cause ranking</h2></div></div><div className="ranking-list">{scores.map(([service, score], index) => <div className="ranking" key={service}><span>{index + 1}</span><div><strong>{service}</strong><small>Signal {(score.signal_strength * 100).toFixed(0)} · Timing {(score.earliest_signal * 100).toFixed(0)} · Impact {(score.upstream_impact * 100).toFixed(0)}</small><i><b style={{ width: `${score.total * 100}%` }} /></i></div><em>{Math.round(score.total * 100)}</em></div>)}</div></article>
      <article className="panel ai-panel"><div className="panel-head"><div><p className="eyebrow">Evidence-grounded explanation</p><h2>AI investigator <span>{data.ai_investigation.mode}</span></h2></div></div><p>{data.ai_investigation.explanation}</p><div className="guardrail"><span>✓</span><div><strong>Evidence boundary active</strong><small>{data.ai_investigation.limitations}</small></div></div></article>
    </section>
    <section className="panel"><div className="panel-head"><div><p className="eyebrow">Detection evidence</p><h2>Signal changes</h2></div><a className="text-link" href={data.evidence_links.grafana} target="_blank" rel="noreferrer">Open raw telemetry ↗</a></div><div className="evidence-grid">{data.anomalies.map((anomaly) => <div className="evidence-card" key={anomaly.id}><div><StatusPill status={anomaly.status} /><span>{anomaly.service}</span></div><h3>{anomaly.kind.replaceAll("_", " ")}</h3><div className="comparison"><span><small>Observed</small><strong>{fmt(anomaly.current_value)}</strong></span><span>vs</span><span><small>Baseline</small><strong>{fmt(anomaly.baseline_value)}</strong></span></div><footer>Evidence score {Math.round(anomaly.score * 100)}%</footer></div>)}</div></section>
    <section className="investigation-grid telemetry-samples">
      <article className="panel"><div className="panel-head"><div><p className="eyebrow">Tempo source data</p><h2>Representative traces</h2></div></div><div className="sample-list">{data.telemetry_evidence.traces.length ? data.telemetry_evidence.traces.map((trace) => <a href={data.evidence_links.tempo} target="_blank" rel="noreferrer" key={trace.trace_id}><code>{trace.trace_id?.slice(0, 16)}…</code><span><strong>{trace.root_service} · {trace.root_span}</strong><small>{fmt(trace.duration_ms, " ms")}</small></span><b>↗</b></a>) : <p>No matching traces were available in the retained window.</p>}</div></article>
      <article className="panel"><div className="panel-head"><div><p className="eyebrow">Loki source data</p><h2>Relevant logs</h2></div></div><div className="sample-list logs">{data.telemetry_evidence.logs.length ? data.telemetry_evidence.logs.slice(0, 5).map((log, index) => <a href={data.evidence_links.loki} target="_blank" rel="noreferrer" key={`${log.timestamp}-${index}`}><code>{log.labels.severity_text || "LOG"}</code><span><strong>{log.line.slice(0, 100)}</strong><small>{log.labels.service_name || data.probable_root_cause}</small></span><b>↗</b></a>) : <p>No matching logs were available in the retained window.</p>}</div></article>
    </section>
    <section className="investigation-grid bottom-grid">
      <article className="panel"><div className="panel-head"><div><p className="eyebrow">Ordered evidence</p><h2>Incident timeline</h2></div></div><div className="timeline">{data.timeline.map((event) => <div key={event.id}><i /><time>{new Date(event.timestamp).toLocaleTimeString()}</time><span><strong>{event.message}</strong><small>{event.service || "TraceLens"}</small></span></div>)}</div></article>
      <article className="panel"><div className="panel-head"><div><p className="eyebrow">Operator guidance</p><h2>Recommended actions</h2></div></div><ol className="recommendations">{data.recommendations.map((item, index) => <li key={item}><span>{index + 1}</span><p>{item}</p></li>)}</ol>{data.deployments.length > 0 && <div className="deployment-note"><strong>Recent simulated deployment</strong><p>{data.deployments[0].service} {data.deployments[0].version}: {data.deployments[0].change_summary}</p></div>}</article>
    </section>
  </>;
}
