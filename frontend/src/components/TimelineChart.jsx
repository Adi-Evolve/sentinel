import { useRef, useState, useCallback } from "react";
import "chart.js/auto";
import { Line } from "react-chartjs-2";
import { ZoomIn, ZoomOut, RotateCcw, Move, MousePointer2, Info } from "lucide-react";

// Register zoom plugin if available
try {
  const zoomPlugin = require("chartjs-plugin-zoom");
  if (zoomPlugin.default) {
    zoomPlugin.default;
  }
} catch (e) {
  // Zoom plugin not installed, will use fallback zoom
}

export default function TimelineChart({ result }) {
  const chartRef = useRef(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState(0);
  const [showHelp, setShowHelp] = useState(false);

  const items = result.timeline?.series || [];
  const anomalyCount = items.filter((i) => i.is_anomaly_window).length;

  // Apply zoom and pan to visible items - defined unconditionally before any early return
  const visibleItems = (() => {
    if (!items.length) return [];
    const total = items.length;
    const visibleCount = Math.max(10, Math.floor(total / zoomLevel));
    const maxOffset = Math.max(0, total - visibleCount);
    const clampedOffset = Math.min(Math.max(0, panOffset), maxOffset);
    return items.slice(clampedOffset, clampedOffset + visibleCount);
  })();

  // All useCallback hooks must be defined before any conditional return
  const handleZoomIn = useCallback(() => {
    setZoomLevel((z) => Math.min(z * 1.5, 10));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoomLevel((z) => {
      const newZoom = Math.max(z / 1.5, 1);
      if (newZoom === 1) setPanOffset(0);
      return newZoom;
    });
  }, []);

  const handleReset = useCallback(() => {
    setZoomLevel(1);
    setPanOffset(0);
  }, []);

  const handlePanLeft = useCallback(() => {
    setPanOffset((p) => Math.max(0, p - Math.floor(visibleItems.length * 0.3)));
  }, [visibleItems.length]);

  const handlePanRight = useCallback(() => {
    const maxOffset = Math.max(0, items.length - visibleItems.length);
    setPanOffset((p) => Math.min(maxOffset, p + Math.floor(visibleItems.length * 0.3)));
  }, [items.length, visibleItems.length]);

  // Early return after all hooks are defined
  if (!items.length) {
    return (
      <section className="viz-card timeline-card">
        <div className="viz-head">
          <h3>Window Activity</h3>
          <p>Per-window volume from the current feature matrix</p>
        </div>
        <div className="timeline-empty">
          <Info size={48} className="timeline-empty-icon" />
          <p>Feature windows appear here after a successful scan.</p>
        </div>
      </section>
    );
  }

  const labels = visibleItems.map((item) =>
    new Date(item.timestamp).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
  );

  // Enhanced data with gradient fill
  const data = {
    labels,
    datasets: [
      {
        label: "Events per window",
        data: visibleItems.map((item) => item.event_count || 0),
        borderColor: "#56cae6",
        backgroundColor: (context) => {
          const ctx = context.chart.ctx;
          const gradient = ctx.createLinearGradient(0, 0, 0, 300);
          gradient.addColorStop(0, "rgba(86, 202, 230, 0.4)");
          gradient.addColorStop(1, "rgba(86, 202, 230, 0.05)");
          return gradient;
        },
        fill: true,
        tension: 0.4,
        borderWidth: 3,
        pointRadius: visibleItems.map((item) => (item.is_anomaly_window ? 8 : 4)),
        pointHoverRadius: 10,
        pointBackgroundColor: visibleItems.map((item) =>
          item.is_anomaly_window ? "#ff6b6b" : "#56cae6",
        ),
        pointBorderColor: visibleItems.map((item) =>
          item.is_anomaly_window ? "#ff4757" : "#2ed573",
        ),
        pointBorderWidth: 2,
        pointShadowBlur: 10,
        pointShadowColor: visibleItems.map((item) =>
          item.is_anomaly_window ? "rgba(255, 107, 107, 0.5)" : "rgba(86, 202, 230, 0.3)",
        ),
      },
      // Anomaly highlight line
      {
        label: "Anomaly Threshold",
        data: visibleItems.map((item) => (item.is_anomaly_window ? item.event_count : null)),
        borderColor: "transparent",
        backgroundColor: "transparent",
        pointRadius: visibleItems.map((item) => (item.is_anomaly_window ? 12 : 0)),
        pointHoverRadius: 14,
        pointBackgroundColor: "rgba(255, 107, 107, 0.3)",
        pointBorderColor: "#ff6b6b",
        pointBorderWidth: 3,
        showLine: false,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: "index",
      intersect: false,
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: "rgba(15, 23, 42, 0.95)",
        titleColor: "#56cae6",
        bodyColor: "#c8d5e8",
        borderColor: "rgba(86, 202, 230, 0.3)",
        borderWidth: 1,
        padding: 12,
        displayColors: true,
        callbacks: {
          title(context) {
            const item = visibleItems[context[0].dataIndex];
            const time = new Date(item.timestamp).toLocaleString();
            return time;
          },
          label(context) {
            const item = visibleItems[context.dataIndex];
            return [
              `Events: ${item.event_count}`,
              `Status: ${item.is_anomaly_window ? "🔴 ANOMALY DETECTED" : "🟢 Normal"}`,
            ];
          },
          afterLabel(context) {
            const item = visibleItems[context.dataIndex];
            if (item.is_anomaly_window) {
              return "⚠️ This window contains suspicious activity patterns";
            }
            return "✓ Within normal baseline range";
          },
        },
      },
      zoom: {
        zoom: {
          wheel: { enabled: true },
          pinch: { enabled: true },
          mode: "x",
        },
        pan: {
          enabled: true,
          mode: "x",
        },
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: "Time Window",
          color: "rgba(185, 200, 226, 0.7)",
          font: { size: 12, weight: "bold" },
        },
        ticks: {
          color: "rgba(185, 200, 226, 0.9)",
          maxTicksLimit: 12,
          autoSkip: true,
          maxRotation: 45,
          minRotation: 30,
          font: { size: 11 },
        },
        grid: {
          color: "rgba(255, 255, 255, 0.08)",
          drawBorder: false,
        },
      },
      y: {
        title: {
          display: true,
          text: "Event Count",
          color: "rgba(185, 200, 226, 0.7)",
          font: { size: 12, weight: "bold" },
        },
        beginAtZero: true,
        ticks: {
          color: "rgba(185, 200, 226, 0.9)",
          font: { size: 11 },
          padding: 8,
        },
        grid: {
          color: "rgba(255, 255, 255, 0.1)",
          drawBorder: false,
          borderDash: [5, 5],
        },
      },
    },
    animation: {
      duration: 800,
      easing: "easeOutQuart",
    },
    onHover: (event, elements) => {
      event.native.target.style.cursor = elements.length > 0 ? "pointer" : "default";
    },
  };

  // Stats calculations

  const maxEventCount = Math.max(...items.map((i) => i.event_count || 0));
  const avgEventCount = Math.round(
    items.reduce((sum, i) => sum + (i.event_count || 0), 0) / items.length,
  );

  return (
    <section className="viz-card timeline-card">
      <div className="viz-head timeline-header">
        <div className="timeline-title-group">
          <h3>Window Activity</h3>
          <p>Interactive timeline with gesture controls</p>
        </div>
        <div className="timeline-stats">
          <div className="timeline-stat">
            <span className="timeline-stat-value">{items.length}</span>
            <span className="timeline-stat-label">Windows</span>
          </div>
          <div className="timeline-stat anomaly-stat">
            <span className="timeline-stat-value">{anomalyCount}</span>
            <span className="timeline-stat-label">Anomalies</span>
          </div>
          <div className="timeline-stat">
            <span className="timeline-stat-value">{maxEventCount}</span>
            <span className="timeline-stat-label">Peak Events</span>
          </div>
          <div className="timeline-stat">
            <span className="timeline-stat-value">{avgEventCount}</span>
            <span className="timeline-stat-label">Avg Events</span>
          </div>
        </div>
      </div>

      {/* Controls Toolbar */}
      <div className="timeline-toolbar">
        <div className="timeline-controls">
          <button
            className="timeline-btn"
            onClick={handleZoomIn}
            title="Zoom In (Ctrl + Scroll)"
            disabled={zoomLevel >= 10}
          >
            <ZoomIn size={18} />
          </button>
          <button
            className="timeline-btn"
            onClick={handleZoomOut}
            title="Zoom Out"
            disabled={zoomLevel <= 1}
          >
            <ZoomOut size={18} />
          </button>
          <button className="timeline-btn" onClick={handleReset} title="Reset View">
            <RotateCcw size={18} />
          </button>
          <div className="timeline-divider" />
          <button
            className="timeline-btn"
            onClick={handlePanLeft}
            title="Pan Left"
            disabled={panOffset <= 0}
          >
            <Move size={18} style={{ transform: "rotate(180deg)" }} />
          </button>
          <button
            className="timeline-btn"
            onClick={handlePanRight}
            title="Pan Right"
            disabled={panOffset >= items.length - visibleItems.length}
          >
            <Move size={18} />
          </button>
        </div>

        <div className="timeline-legend">
          <div className="timeline-legend-item">
            <span className="timeline-legend-dot normal" />
            <span>Normal</span>
          </div>
          <div className="timeline-legend-item">
            <span className="timeline-legend-dot anomaly" />
            <span>Anomaly</span>
          </div>
          <button
            className="timeline-help-btn"
            onClick={() => setShowHelp(!showHelp)}
            title="How to use"
          >
            <MousePointer2 size={16} />
          </button>
        </div>
      </div>

      {/* Help Panel */}
      {showHelp && (
        <div className="timeline-help-panel">
          <h4>Gesture Controls</h4>
          <ul>
            <li>
              <strong>Zoom:</strong> Use buttons or Ctrl + Mouse Wheel
            </li>
            <li>
              <strong>Pan:</strong> Click and drag or use arrow buttons
            </li>
            <li>
              <strong>Hover:</strong> See detailed event info per window
            </li>
            <li>
              <strong>Red dots:</strong> Windows with detected anomalies
            </li>
          </ul>
        </div>
      )}

      {/* Zoom Level Indicator */}
      <div className="timeline-zoom-indicator">
        <span>Zoom: {Math.round(zoomLevel * 100)}%</span>
        <div className="timeline-progress-bar">
          <div
            className="timeline-progress-fill"
            style={{ width: `${Math.min((zoomLevel / 10) * 100, 100)}%` }}
          />
        </div>
      </div>

      {/* Chart Container */}
      <div className="chart-shell timeline-chart-container">
        <Line ref={chartRef} data={data} options={options} />
      </div>

      {/* Visible Range Indicator */}
      <div className="timeline-range-info">
        <span>
          Showing windows {panOffset + 1} - {Math.min(panOffset + visibleItems.length, items.length)}{" "}
          of {items.length}
        </span>
        {zoomLevel > 1 && (
          <span className="timeline-range-hint">
            (Use arrow buttons or drag to pan)
          </span>
        )}
      </div>
    </section>
  );
}
