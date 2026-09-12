"use client";

import { Empty, ErrorBox, IncidentRow, Loading, PageHead } from "@/components/Ui";
import { useLiveQuery } from "@/lib/api";
import type { Incident } from "@/lib/types";

export default function IncidentsPage() {
  const { data, error, loading } = useLiveQuery<Incident[]>("/api/incidents");
  if (loading) return <Loading />;
  if (error || !data) return <ErrorBox message={error} />;
  const active = data.filter((item) => item.status !== "resolved");
  const resolved = data.filter((item) => item.status === "resolved");
  return <>
    <PageHead eyebrow="Incident center" title="Investigations" description="Correlated anomalies, ranked causes, and inspectable evidence." />
    <div className="summary-strip"><div><strong>{active.length}</strong><span>Active</span></div><div><strong>{data.filter((i) => i.severity === "critical").length}</strong><span>Critical total</span></div><div><strong>{resolved.length}</strong><span>Resolved</span></div></div>
    <section className="panel incidents-panel"><div className="panel-head"><div><p className="eyebrow">Requires attention</p><h2>Active incidents</h2></div></div>{active.length ? active.map((item) => <IncidentRow incident={item} key={item.id} />) : <Empty title="No active incidents" text="TraceLens has not detected an active degradation." />}</section>
    <section className="panel incidents-panel"><div className="panel-head"><div><p className="eyebrow">History</p><h2>Resolved incidents</h2></div></div>{resolved.length ? resolved.map((item) => <IncidentRow incident={item} key={item.id} />) : <Empty title="No incident history" text="Resolved investigations will remain available here." />}</section>
  </>;
}
