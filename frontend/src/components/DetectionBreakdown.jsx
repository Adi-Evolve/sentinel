import "chart.js/auto";
import { Doughnut } from "react-chartjs-2";

export default function DetectionBreakdown({ anomalies, detectionBreakdown }) {
  if (!anomalies.length) {
    return (
      <section className="viz-card">
        <div className="viz-head">
          <h3>AI Detection Engine</h3>
          <p>Rules, Isolation Forest (ML), and Spike analysis</p>
        </div>
        <p className="muted-copy">Run a scan to view detector contribution split.</p>
      </section>
    );
  }

  const split = resolveSplit(anomalies, detectionBreakdown);

  const data = {
    labels: ["Rules", "Isolation Forest (ML)", "Spike Detector"],
    datasets: [
      {
        data: [split.rules, split.isolation_forest_ml, split.spike],
        backgroundColor: ["rgba(73, 205, 194, 0.88)", "rgba(70, 142, 255, 0.85)", "rgba(246, 173, 85, 0.9)"],
        hoverBackgroundColor: ["rgba(90, 224, 212, 0.95)", "rgba(93, 164, 255, 0.95)", "rgba(251, 191, 106, 0.95)"],
        borderWidth: 0,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: "62%",
    plugins: {
      legend: {
        position: "bottom",
        labels: {
          color: "rgba(201, 214, 235, 0.95)",
          boxWidth: 12,
          usePointStyle: true,
          pointStyle: "rectRounded",
          padding: 16,
        },
      },
    },
  };

  return (
    <section className="viz-card">
      <div className="viz-head">
        <h3>AI Detection Engine</h3>
        <p>Hybrid contribution across three detectors</p>
      </div>
      <div className="chart-shell compact-chart">
        <Doughnut data={data} options={options} />
      </div>
    </section>
  );
}

function dominantDetector(anomaly) {
  const candidates = [
    ["rules", anomaly.rule_score || 0],
    ["isolation_forest_ml", anomaly.iso_score || 0],
    ["spike", anomaly.spike_score || 0],
  ];
  candidates.sort((left, right) => right[1] - left[1]);
  return candidates[0][0];
}

function resolveSplit(anomalies, detectionBreakdown) {
  if (detectionBreakdown) {
    return {
      rules: detectionBreakdown.rule_count || 0,
      isolation_forest_ml: detectionBreakdown.ml_count || 0,
      spike: detectionBreakdown.spike_count || 0,
    };
  }

  const split = {
    rules: 0,
    isolation_forest_ml: 0,
    spike: 0,
  };
  for (const anomaly of anomalies) {
    const dominant = dominantDetector(anomaly);
    split[dominant] += 1;
  }
  return split;
}
