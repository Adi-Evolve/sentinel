function prettyStage(stage) {
  return String(stage || "processing").replace(/-/g, " ");
}

function formatEta(seconds) {
  if (seconds === null || seconds === undefined) {
    return "estimating...";
  }
  if (seconds <= 0) {
    return "<1s";
  }
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  if (minutes > 0) {
    return `${minutes}m ${remainder}s`;
  }
  return `${remainder}s`;
}

export default function ProcessingSpinner({ progress = 0, stage = "processing", etaSeconds = null }) {
  return (
    <div className="processing-card">
      <div className="spinner" />
      <div className="processing-content">
        <p className="processing-title">Running scan pipeline</p>
        <p className="processing-text">
          Parsing logs, engineering features, scoring anomalies, and generating briefings.
        </p>
        <p className="processing-stage">
          Stage: <strong>{prettyStage(stage)}</strong>
        </p>
        <div className="progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}>
          <div className="progress-fill" style={{ width: `${Math.max(0, Math.min(100, progress))}%` }} />
        </div>
        <p className="processing-percent">{Math.round(progress)}% complete</p>
        <p className="processing-eta">
          ETA: <strong>{formatEta(etaSeconds)}</strong>
        </p>
      </div>
    </div>
  );
}
