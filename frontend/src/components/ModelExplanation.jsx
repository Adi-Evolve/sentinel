import { useMemo } from "react";
import { Brain, AlertCircle, CheckCircle2, Info } from "lucide-react";

export default function ModelExplanation({ anomaly }) {
  const explanation = anomaly.metadata?.model_explanation;
  const detectionFlags = anomaly.metadata?.detection_flags || [];

  const hasExplanation = explanation && explanation.feature_contributions?.length > 0;
  const isRuleBased = anomaly.briefing_source === "rule-based";
  const isMLDetected = anomaly.briefing_source === "fallback" || (anomaly.iso_score || 0) > 0.4;

  // Format feature name for display
  const formatFeature = (name) => {
    return name
      .replace(/_/g, " ")
      .replace(/\b\w/g, (l) => l.toUpperCase())
      .replace(/rpm/i, "RPM")
      .replace(/ip/i, "IP");
  };

  // Calculate max weight for bar scaling
  const maxWeight = useMemo(() => {
    if (!hasExplanation) return 1;
    return Math.max(
      ...explanation.feature_contributions.map((c) => Math.abs(c.weight)),
      0.001
    );
  }, [explanation, hasExplanation]);

  // Determine explanation type badge
  const getExplanationBadge = () => {
    if (isRuleBased) {
      return {
        icon: CheckCircle2,
        text: "Rule-Based Detection",
        color: "var(--accent)",
        subtext: "Pattern matched - no hallucination possible",
      };
    }
    if (explanation?.method === "lime") {
      return {
        icon: Brain,
        text: "LIME AI Explanation",
        color: "#8b5cf6",
        subtext: "Feature contributions from Isolation Forest",
      };
    }
    return {
      icon: Info,
      text: "Statistical Analysis",
      color: "#f59e0b",
      subtext: "Z-score based feature ranking",
    };
  };

  const badge = getExplanationBadge();
  const BadgeIcon = badge.icon;

  return (
    <div className="model-explanation-panel">
      {/* Header with explanation type */}
      <div className="explanation-header">
        <div className="explanation-badge" style={{ "--badge-color": badge.color }}>
          <BadgeIcon size={16} />
          <span>{badge.text}</span>
        </div>
        <p className="explanation-subtext">{badge.subtext}</p>
      </div>

      {/* Detection flags - which detectors fired */}
      {detectionFlags.length > 0 && (
        <div className="detection-flags">
          <h4>Detectors That Fired</h4>
          <div className="flags-grid">
            {detectionFlags.map((flag, idx) => (
              <div
                key={idx}
                className={`flag-item ${flag.flag}`}
                title={flag.why}
              >
                <CheckCircle2 size={14} />
                <span>{formatDetectorName(flag.flag)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* LIME Feature Contributions */}
      {hasExplanation && (
        <div className="feature-contributions">
          <h4>Feature Contributions (LIME)</h4>
          <p className="contributions-hint">
            Positive values increase anomaly risk, negative values decrease it.
          </p>
          <div className="contribution-bars">
            {explanation.feature_contributions.map((contribution, idx) => (
              <ContributionBar
                key={idx}
                feature={formatFeature(contribution.feature)}
                weight={contribution.weight}
                maxWeight={maxWeight}
              />
            ))}
          </div>
          {explanation.human_readable && (
            <p className="human-readable">
              <Brain size={14} />
              {explanation.human_readable}
            </p>
          )}
        </div>
      )}

      {/* Model confidence */}
      {explanation?.anomaly_probability !== undefined && (
        <div className="confidence-section">
          <div className="confidence-item">
            <span>ML Model Confidence</span>
            <strong>{(explanation.anomaly_probability * 100).toFixed(1)}%</strong>
          </div>
          {isMLDetected && !isRuleBased && (
            <div className="confidence-hint">
              <AlertCircle size={12} />
              <span>
                This anomaly was flagged by ML but no rule matched — potential novel attack pattern
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ContributionBar({ feature, weight, maxWeight }) {
  const isPositive = weight > 0;
  const percentage = (Math.abs(weight) / maxWeight) * 100;

  return (
    <div className="contribution-row">
      <span className="feature-name" title={feature}>
        {feature}
      </span>
      <div className="bar-container">
        <div
          className={`contribution-bar ${isPositive ? "positive" : "negative"}`}
          style={{ width: `${Math.max(percentage, 5)}%` }}
        />
      </div>
      <span className={`weight-value ${isPositive ? "positive" : "negative"}`}>
        {weight > 0 ? "+" : ""}
        {weight.toFixed(3)}
      </span>
    </div>
  );
}

function formatDetectorName(flag) {
  const names = {
    rule_triggered: "Rule Engine",
    ml_outlier: "Isolation Forest",
    traffic_spike: "Spike Detector",
    known_bad_ip: "Threat Intel",
    fail_then_success: "Compromise Pattern",
  };
  return names[flag] || flag.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}
