import { useState } from "react";
import { ChevronDown, ChevronUp, ShieldAlert, Brain, Activity, Radar, CheckCircle2 } from "lucide-react";
import ModelExplanation from "./ModelExplanation";

function severityClass(label) {
  if (label === "CRITICAL") {
    return "critical";
  }
  if (label === "WARNING") {
    return "warning";
  }
  return "low";
}

export default function AnomalyCard({ anomaly, index = 0 }) {
  const [showExplanation, setShowExplanation] = useState(false);
  const severity = severityClass(anomaly.severity_label);
  const travel = anomaly.metadata?.impossible_travel;
  const tags = buildTags(anomaly);
  const isKnownBad = anomaly.is_known_bad_ip;

  return (
    <article className={`anomaly-card reveal-card ${isKnownBad ? "known-bad" : ""}`} style={{ "--stagger": `${index * 70}ms` }}>
      {/* Known Bad IP Warning Banner */}
      {isKnownBad && (
        <div className="known-bad-banner">
          <ShieldAlert size={18} />
          <span>
            <strong>THREAT INTEL MATCH:</strong> This IP is flagged in known bad actor database
          </span>
        </div>
      )}

      <div className="anomaly-top">
        <div>
          <p className="anomaly-rank">Rank #{anomaly.rank}</p>
          <h3>{anomaly.source_ip}</h3>
        </div>
        <div className="badge-row">
          <span className={`severity-badge ${severity}`}>{anomaly.severity_label}</span>
          <span className="source-badge">{sourceLabel(anomaly.briefing_source)}</span>
        </div>
      </div>

      {/* Detector Fusion Row - Visual Differentiator */}
      <DetectorFusionRow anomaly={anomaly} />

      {tags.length ? (
        <div className="tag-row">
          {tags.map((tag) => (
            <span key={tag} className="tag-pill">
              {tag}
            </span>
          ))}
        </div>
      ) : null}

      <div className="stat-row">
        <Stat label="Score" value={`${anomaly.composite_score}/100`} emphasis />
        <Stat label="Country" value={anomaly.country_code} />
        <Stat label="Failed" value={anomaly.login_failure_count} />
        <Stat label="Success" value={anomaly.login_success_count} />
        <Stat label="RPM" value={anomaly.requests_per_minute} />
        <Stat label="Endpoints" value={anomaly.unique_endpoints} />
      </div>

      <p className="window-text">
        {anomaly.window_start} to {anomaly.window_end}
      </p>

      <p className="briefing-text">AI Analysis: {anomaly.briefing}</p>

      {travel ? (
        <div className="travel-panel">
          <div className="travel-item">
            <span>Route</span>
            <strong>
              {travel.country_1} ({travel.country_code_1}) to {travel.country_2} ({travel.country_code_2})
            </strong>
          </div>
          <div className="travel-item">
            <span>Gap</span>
            <strong>{Math.round(travel.gap_minutes)} minutes</strong>
          </div>
          <div className="travel-item">
            <span>Distance</span>
            <strong>{Math.round(travel.distance_km)} km</strong>
          </div>
        </div>
      ) : null}

      {anomaly.all_rules_fired?.length ? (
        <div className="rule-row">
          {anomaly.all_rules_fired.map((rule) => (
            <span key={rule} className="rule-chip">
              {rule}
            </span>
          ))}
        </div>
      ) : null}

      {/* Expandable AI Explanation Section */}
      <button
        className="explanation-toggle"
        onClick={() => setShowExplanation(!showExplanation)}
        aria-expanded={showExplanation}
      >
        <Brain size={16} />
        <span>{showExplanation ? "Hide AI Analysis" : "Show AI Analysis & Detector Fusion"}</span>
        {showExplanation ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {showExplanation && (
        <div className="explanation-panel-wrapper">
          <ModelExplanation anomaly={anomaly} />
        </div>
      )}
    </article>
  );
}

function DetectorFusionRow({ anomaly }) {
  const detectors = [
    {
      id: "rule",
      name: "Rules",
      icon: Radar,
      active: !!anomaly.rule_triggered,
      score: anomaly.rule_score || 0,
      color: "#38bdf8", // accent
    },
    {
      id: "ml",
      name: "ML",
      icon: Brain,
      active: (anomaly.iso_score || 0) > 0.1,
      score: anomaly.iso_score || 0,
      color: "#818cf8", // indigo-400
    },
    {
      id: "spike",
      name: "Spike",
      icon: Activity,
      active: (anomaly.spike_score || 0) > 0.1,
      score: anomaly.spike_score || 0,
      color: "#f59e0b", // warning
    },
  ];

  const activeCount = detectors.filter((d) => d.active).length;

  return (
    <div className="detector-fusion-row">
      <div className="fusion-label">
        <span>Detector Fusion</span>
        <small>{activeCount}/3 fired</small>
      </div>
      <div className="detector-badges">
        {detectors.map((detector) => (
          <div
            key={detector.id}
            className={`detector-badge ${detector.active ? "active" : ""}`}
            style={{ "--detector-color": detector.color }}
            title={`${detector.name}: ${(detector.score * 100).toFixed(1)}%`}
          >
            <detector.icon size={14} />
            <span>{detector.name}</span>
            {detector.active && <CheckCircle2 size={12} className="check-icon" />}
          </div>
        ))}
      </div>
    </div>
  );
}

function buildTags(anomaly) {
  const tags = [];
  if (anomaly.rule_triggered) {
    tags.push(`[${String(anomaly.rule_triggered).replace(/_/g, " ").toUpperCase()}]`);
  }
  if (anomaly.is_known_bad_ip) {
    tags.push("[THREAT INTEL HIT]");
  }
  if ((anomaly.iso_score || 0) >= 0.4) {
    tags.push("[ML OUTLIER]");
  }
  if ((anomaly.spike_score || 0) >= 0.4) {
    tags.push("[TRAFFIC SPIKE]");
  }
  if (anomaly.country_code && anomaly.country_code !== "XX") {
    tags.push(`[${anomaly.country_code}]`);
  }
  return tags;
}

function sourceLabel(source) {
  if (source === "rule-based") {
    return "AI-Rule Engine";
  }
  if (source === "fallback") {
    return "ML-Anomaly Detected";
  }
  return "AI-Assisted";
}

function Stat({ label, value, emphasis = false }) {
  return (
    <div className={`mini-stat ${emphasis ? "emphasis" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
