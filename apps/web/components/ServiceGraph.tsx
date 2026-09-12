import Link from "next/link";
import type { Service } from "@/lib/types";

const positions: Record<string, [number, number]> = {
  gateway: [8, 43], order: [35, 43], inventory: [67, 10], payment: [67, 43], notification: [67, 76],
};

export function ServiceGraph({ services, edges }: { services: Service[]; edges: { source: string; target: string }[] }) {
  return <div className="service-graph">
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden>
      {edges.map((edge) => {
        const from = positions[edge.source] || [0, 0]; const to = positions[edge.target] || [0, 0];
        return <line key={`${edge.source}-${edge.target}`} x1={from[0] + 10} y1={from[1] + 5} x2={to[0]} y2={to[1] + 5} />;
      })}
    </svg>
    {services.map((service) => {
      const [left, top] = positions[service.name] || [0, 0];
      return <Link href={`/services/${service.name}`} key={service.name} className={`graph-node ${service.status}`} style={{ left: `${left}%`, top: `${top}%` }}>
        <span className="node-icon">{service.display_name.slice(0, 1)}</span>
        <span><strong>{service.display_name}</strong><small>{service.p95_latency_ms.toFixed(0)} ms · {(service.error_rate * 100).toFixed(1)}% err</small></span>
        <i />
      </Link>;
    })}
  </div>;
}
