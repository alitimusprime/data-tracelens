import Link from "next/link";
import type { Incident, Status } from "@/lib/types";

export function PageHead({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return <div className="page-head"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}

export function StatusPill({ status }: { status: Status | string }) {
  return <span className={`status-pill ${status}`}><span />{status}</span>;
}

export function MetricCard({ label, value, meta, tone = "mint" }: { label: string; value: string; meta: string; tone?: "mint" | "blue" | "amber" | "violet" }) {
  return <article className={`metric-card ${tone}`}><div className="metric-top"><span>{label}</span><i /></div><strong>{value}</strong><small>{meta}</small><div className="mini-bars"><i /><i /><i /><i /><i /><i /><i /><i /></div></article>;
}

export function Empty({ title, text }: { title: string; text: string }) {
  return <div className="empty"><span>◎</span><h3>{title}</h3><p>{text}</p></div>;
}

export function ErrorBox({ message }: { message: string }) {
  return <div className="error-box"><strong>TraceLens API is not ready</strong><p>{message}</p><code>docker compose ps</code></div>;
}

export function Loading() {
  return <div className="loading"><span /><span /><span /></div>;
}

export function IncidentRow({ incident }: { incident: Incident }) {
  return <Link href={`/incidents/${incident.id}`} className="incident-row">
    <span className={`severity-mark ${incident.severity}`} />
    <div className="incident-name"><strong>{incident.title}</strong><small>{incident.affected_services.join(" → ") || "Impact analysis pending"}</small></div>
    <StatusPill status={incident.status} />
    <div className="root-cause"><small>Probable cause</small><strong>{incident.probable_root_cause || "Investigating"}</strong></div>
    <div className="confidence"><span>{Math.round(incident.confidence * 100)}%</span><i><b style={{ width: `${incident.confidence * 100}%` }} /></i></div>
    <time>{relativeTime(incident.updated_at)}</time>
    <span className="chevron">›</span>
  </Link>;
}

export function relativeTime(value: string) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return `${Math.floor(seconds / 3600)}h ago`;
}

export function fmt(value: number, unit = "") {
  return `${Number.isFinite(value) ? value.toLocaleString(undefined, { maximumFractionDigits: 1 }) : "0"}${unit}`;
}
