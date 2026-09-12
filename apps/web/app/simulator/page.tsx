"use client";

import { useState } from "react";
import { Empty, ErrorBox, Loading, PageHead } from "@/components/Ui";
import { api, useLiveQuery } from "@/lib/api";
import type { Scenario } from "@/lib/types";

export default function SimulatorPage() {
  const { data, error, loading } = useLiveQuery<Scenario[]>("/api/simulator/scenarios");
  const [running, setRunning] = useState<string | null>(null); const [message, setMessage] = useState("");
  if (loading) return <Loading />;
  if (error || !data) return <ErrorBox message={error} />;
  async function toggle(scenario: Scenario) {
    const action = running === scenario.id ? "stop" : "start";
    try { await api(`/api/simulator/scenarios/${scenario.id}/${action}`, { method: "POST" }); setRunning(action === "start" ? scenario.id : null); setMessage(action === "start" ? `${scenario.name} is active. Detection usually begins after two analysis windows.` : "Scenario stopped. TraceLens is validating recovery."); } catch (reason) { setMessage(reason instanceof Error ? reason.message : "Scenario command failed"); }
  }
  return <>
    <PageHead eyebrow="Controlled failure lab" title="Incident simulator" description="Change real service behavior and watch genuine telemetry drive the investigation." />
    <div className="honesty-banner"><span>i</span><div><strong>The faults are simulated. Their effects are not.</strong><p>Every timeout, error, metric, span, log, anomaly, incident, and recovery signal flows through the running system.</p></div></div>
    {message && <div className="toast">{message}</div>}
    <section className="scenario-grid">{data.length ? data.map((scenario, index) => <article className={`scenario-card ${running === scenario.id ? "running" : ""}`} key={scenario.id}><header><span>0{index + 1}</span><i>{scenario.target.slice(0, 1).toUpperCase()}</i></header><p className="eyebrow">{scenario.target} service</p><h2>{scenario.name}</h2><p>{scenario.description}</p><div className="expected"><small>Expected observable behavior</small><p>{scenario.expected}</p></div><button onClick={() => void toggle(scenario)} className={running === scenario.id ? "stop-button" : "primary-button"}>{running === scenario.id ? "■ Stop and recover" : "▶ Start scenario"}</button></article>) : <Empty title="No scenarios configured" text="The backend did not return simulator definitions." />}</section>
    <section className="panel demo-flow"><div className="panel-head"><div><p className="eyebrow">Demo narrative</p><h2>What happens next</h2></div></div><div>{["Fault changes service behavior", "OpenTelemetry records propagation", "RED signals cross thresholds", "Anomalies form one incident", "Root causes are scored", "The dashboard updates live"].map((item, index) => <span key={item}><i>{index + 1}</i>{item}</span>)}</div></section>
  </>;
}
