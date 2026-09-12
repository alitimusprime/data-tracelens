export type Status = "healthy" | "degraded" | "unknown" | "open" | "investigating" | "resolved";

export interface Service {
  name: string;
  display_name: string;
  version: string;
  owner: string;
  dependencies: string[];
  status: Status;
  telemetry_freshness: string | null;
  request_rate: number;
  error_rate: number;
  p95_latency_ms: number;
  availability: number;
}

export interface Incident {
  id: string;
  title: string;
  status: Status;
  severity: "warning" | "high" | "critical";
  probable_root_cause: string | null;
  confidence: number;
  affected_services: string[];
  started_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface Activity {
  id: string;
  type: string;
  service: string | null;
  message: string;
  details: Record<string, unknown>;
  timestamp: string;
}

export interface Overview {
  generated_at: string;
  system_status: Status;
  metrics: {
    active_incidents: number;
    healthy_services: number;
    request_rate: number;
    error_rate: number;
    p95_latency_ms: number;
  };
  services: Service[];
  edges: { source: string; target: string }[];
  incidents: Incident[];
  activity: Activity[];
}

export interface IncidentDetail extends Incident {
  summary: string;
  score_breakdown: Record<string, Record<string, number>>;
  recommendations: string[];
  anomalies: Array<{
    id: string;
    service: string;
    kind: string;
    status: string;
    severity: string;
    current_value: number;
    baseline_value: number;
    score: number;
    evidence: Record<string, unknown>;
    detected_at: string;
    recovered_at: string | null;
  }>;
  timeline: Activity[];
  deployments: Array<{
    id: string;
    service: string;
    version: string;
    commit_sha: string;
    environment: string;
    change_summary: string;
    simulated: boolean;
    deployed_at: string;
  }>;
  ai_investigation: {
    mode: "deterministic" | "ai";
    explanation: string;
    limitations: string;
  };
  telemetry_evidence: {
    partial: boolean;
    traces: Array<{ trace_id: string; root_service: string; root_span: string; duration_ms: number; started_at: string }>;
    logs: Array<{ timestamp: string; line: string; labels: Record<string, string>; metadata: Record<string, string> }>;
  };
  evidence_links: Record<string, string>;
}

export interface ServiceDetail extends Service {
  history: Array<{
    timestamp: string;
    request_rate: number;
    error_rate: number;
    p95_latency_ms: number;
  }>;
  incidents: Incident[];
  deployments: IncidentDetail["deployments"];
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
  target: string;
  expected: string;
}
