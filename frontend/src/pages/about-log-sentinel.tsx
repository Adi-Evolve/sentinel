import { Link, NavLink } from "react-router-dom";
import { ShieldCheck, Radar, FileBarChart2 } from "lucide-react";

export default function AboutLogSentinelPage() {
  return (
    <main className="page-shell page-shell-dashboard about-shell">
      <div className="dashboard-ribbon reveal reveal-1">
        <div className="dashboard-ribbon-left">
          <p className="dashboard-ribbon-label">LOG SENTINEL</p>
          <nav className="dashboard-nav" aria-label="Primary navigation">
            <NavLink to="/" end className={({ isActive }) => `dashboard-tab ${isActive ? "active" : ""}`}>
              Hero
            </NavLink>
            <NavLink to="/dashboard" className={({ isActive }) => `dashboard-tab ${isActive ? "active" : ""}`}>
              Dashboard
            </NavLink>
            <NavLink to="/about" className={({ isActive }) => `dashboard-tab ${isActive ? "active" : ""}`}>
              About
            </NavLink>
          </nav>
        </div>
        <div className="dashboard-ribbon-actions">
          <Link to="/dashboard" className="secondary-button small">Open Dashboard</Link>
        </div>
      </div>

      <section className="about-surface reveal reveal-2">
        <p className="about-eyebrow">About the Application</p>
        <h1 className="about-title">Log-Sentinel</h1>
        <p className="about-lead">
          Log-Sentinel is an offline-first cybersecurity analysis system.
          It ingests raw logs, engineers behavioral features, runs hybrid threat detection,
          and produces ranked anomaly briefings with timeline and export support.
        </p>

        <div className="about-grid">
          <article className="about-card">
            <ShieldCheck className="about-card-icon" />
            <h2>Hybrid Detection</h2>
            <p>
              Rules + Isolation Forest + spike analytics for explainable incident scoring.
            </p>
          </article>

          <article className="about-card">
            <Radar className="about-card-icon" />
            <h2>Realtime Progress</h2>
            <p>
              Async scanning with stage-wise progress and ETA for large log files.
            </p>
          </article>

          <article className="about-card">
            <FileBarChart2 className="about-card-icon" />
            <h2>SOC-Ready Output</h2>
            <p>
              Timeline, ranked anomalies, and downloadable JSON/PDF reports.
            </p>
          </article>
        </div>

        <div className="about-actions">
          <Link to="/" className="secondary-button">Hero Page</Link>
          <Link to="/dashboard" className="primary-button">Detection Dashboard</Link>
        </div>
      </section>
    </main>
  );
}
