export default function ThreatGauge({ anomalies }) {
  const highest = anomalies.length ? Math.max(...anomalies.map((item) => item.composite_score || 0)) : 0;
  const value = Math.max(0, Math.min(100, Math.round(highest)));
  const level = severityLevel(value);
  const degrees = (value / 100) * 180;

  return (
    <section className="viz-card gauge-card">
      <div className="viz-head">
        <h3>Threat Meter</h3>
        <p>Highest detected risk in current scan</p>
      </div>
      <div className="gauge-wrap">
        <div
          className="gauge-arc"
          style={{
            background: `conic-gradient(from 180deg, #22c55e 0deg 54deg, #f59e0b 54deg 126deg, #ef4444 126deg 180deg, #e5e7eb 180deg 360deg)`,
          }}
        >
          <div className="gauge-mask" />
          <div className="gauge-needle" style={{ transform: `rotate(${degrees - 90}deg)` }} />
        </div>
        <div className="gauge-value">
          <strong>{value}</strong>
          <span>/100</span>
        </div>
        <p className={`gauge-label ${level.toLowerCase()}`}>{level}</p>
      </div>
    </section>
  );
}

function severityLevel(score) {
  if (score >= 75) {
    return "CRITICAL";
  }
  if (score >= 50) {
    return "WARNING";
  }
  if (score >= 25) {
    return "ELEVATED";
  }
  return "LOW";
}
