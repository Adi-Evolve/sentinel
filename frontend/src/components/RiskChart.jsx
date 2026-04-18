import "chart.js/auto";
import { Bar } from "react-chartjs-2";

const riskValuePlugin = {
  id: "riskValuePlugin",
  afterDatasetsDraw(chart) {
    const {
      ctx,
      scales: { x },
    } = chart;
    const dataset = chart.data.datasets[0];
    const meta = chart.getDatasetMeta(0);

    if (!dataset || !meta?.data?.length) {
      return;
    }

    ctx.save();
    ctx.font = "600 11px Inter, Segoe UI, sans-serif";
    ctx.fillStyle = "rgba(241, 245, 249, 0.94)"; // slate-100
    meta.data.forEach((bar, index) => {
      const value = Number(dataset.data[index] || 0);
      const clampedX = Math.min(x.right - 24, bar.x + 8);
      ctx.fillText(`${Math.round(value)}`, clampedX, bar.y + 4);
    });
    ctx.restore();
  },
};

export default function RiskChart({ anomalies }) {
  if (!anomalies.length) {
    return (
      <section className="viz-card">
        <div className="viz-head">
          <h3>Risk Overview</h3>
          <p>Top anomalies by composite score</p>
        </div>
        <p className="muted-copy">Run a scan to populate the score distribution.</p>
      </section>
    );
  }

  const rankedAnomalies = [...anomalies]
    .sort((left, right) => Number(right.composite_score || 0) - Number(left.composite_score || 0))
    .slice(0, 7);

  const data = {
    labels: rankedAnomalies.map((anomaly, index) => `#${index + 1} ${anomaly.source_ip}`),
    datasets: [
      {
        label: "Composite score",
        data: rankedAnomalies.map((anomaly) => Number(anomaly.composite_score || 0)),
        borderRadius: 10,
        barThickness: 22,
        maxBarThickness: 24,
        barPercentage: 0.74,
        categoryPercentage: 0.74,
        backgroundColor: rankedAnomalies.map((anomaly) => colorForSeverity(anomaly.severity_label, anomaly.composite_score)),
        hoverBackgroundColor: rankedAnomalies.map((anomaly) => colorForSeverity(anomaly.severity_label, Number(anomaly.composite_score || 0) + 6)),
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: "y",
    animation: {
      duration: 850,
      easing: "easeOutQuart",
    },
    layout: {
      padding: {
        top: 4,
        right: 26,
        left: 4,
        bottom: 2,
      },
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: "rgba(3, 7, 18, 0.96)",
        borderColor: "rgba(56, 189, 248, 0.28)",
        borderWidth: 1,
        titleColor: "rgba(248, 250, 252, 0.97)",
        bodyColor: "rgba(148, 163, 184, 0.95)",
        padding: 12,
        cornerRadius: 8,
        callbacks: {
          title(context) {
            return context?.[0]?.label || "Risk signal";
          },
          label(context) {
            const row = rankedAnomalies[context.dataIndex];
            return `Score ${Math.round(Number(context.raw || 0))}/100 · ${row?.severity_label || "LOW"}`;
          },
        },
      },
    },
    scales: {
      x: {
        min: 0,
        max: 100,
        beginAtZero: true,
        grace: "2%",
        ticks: {
          color: "rgba(148, 163, 184, 0.92)",
          stepSize: 20,
          callback(value) {
            if (value === 0 || value === 50 || value === 100) {
              return `${value}`;
            }
            return "";
          },
        },
        grid: {
          color: "rgba(255, 255, 255, 0.05)",
          drawTicks: false,
        },
        border: {
          display: false,
        },
      },
      y: {
        ticks: {
          color: "rgba(248, 250, 252, 0.95)",
          font: {
            size: 11,
            weight: 600,
          },
          padding: 8,
        },
        grid: {
          display: false,
        },
        border: {
          display: false,
        },
      },
    },
  };

  return (
    <section className="viz-card">
      <div className="viz-head">
        <h3>Risk Overview</h3>
        <p>Top anomalies ranked by composite score with severity context</p>
      </div>
      <div className="chart-shell">
        <Bar data={data} options={options} plugins={[riskValuePlugin]} />
      </div>
      <div className="risk-band-row">
        <span className="risk-band-chip low">Low 0-49</span>
        <span className="risk-band-chip warning">Warning 50-79</span>
        <span className="risk-band-chip critical">Critical 80-100</span>
      </div>
    </section>
  );
}

function colorForSeverity(severity, score = 50) {
  const alpha = Math.max(0.52, Math.min(0.94, Number(score || 0) / 115 + 0.34));

  if (severity === "CRITICAL") {
    return `rgba(239, 68, 68, ${alpha})`;    /* critical: #ef4444 */
  }
  if (severity === "WARNING") {
    return `rgba(245, 158, 11, ${alpha})`;   /* warning: #f59e0b */
  }
  return `rgba(56, 189, 248, ${alpha})`;     /* accent: #38bdf8 */
}
