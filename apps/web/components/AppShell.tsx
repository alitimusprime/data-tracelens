"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Overview", icon: "◫" },
  { href: "/incidents", label: "Incidents", icon: "△" },
  { href: "/services/gateway", label: "Services", icon: "◇" },
  { href: "/simulator", label: "Simulator", icon: "⌁" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  return (
    <div className="shell">
      <aside className="sidebar">
        <Link href="/" className="brand">
          <span className="brand-mark"><i /><i /><i /></span>
          <span>TraceLens <b>AI</b></span>
        </Link>
        <p className="nav-label">Workspace</p>
        <nav>
          {links.map((item) => (
            <Link
              className={path === item.href || (item.href !== "/" && path.startsWith(item.href.split("/").slice(0, 2).join("/"))) ? "active" : ""}
              href={item.href}
              key={item.href}
            >
              <span className="nav-icon">{item.icon}</span>{item.label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="environment"><span className="status-dot healthy" /> Local environment</div>
          <small>Docker Compose · v0.1.0</small>
        </div>
      </aside>
      <section className="workspace">
        <header className="topbar">
          <div><span className="pulse" /> Live telemetry</div>
          <div className="top-actions">
            <a href="http://localhost:3001" target="_blank" rel="noreferrer">Raw telemetry ↗</a>
            <span className="avatar">TL</span>
          </div>
        </header>
        <main>{children}</main>
      </section>
    </div>
  );
}
