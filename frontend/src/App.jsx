import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Database,
  History,
  LayoutDashboard,
  ShieldCheck,
  Terminal,
} from "lucide-react";
import world from "@svg-maps/world";
import { Link, NavLink, useLocation } from "react-router-dom";
import { svgPathBbox } from "svg-path-bbox";

import { deleteScan, getScanJob, getScanReport, healthCheck, listScans, startAsyncScan, startDemoScan } from "./api";
import AnomalyCard from "./components/AnomalyCard";
import Dashboard from "./components/Dashboard";
import DetectionBreakdown from "./components/DetectionBreakdown";
import ErrorBoundary from "./components/ErrorBoundary";
import ExportBar from "./components/ExportBar";
import GeoCountryPreview from "./components/GeoCountryPreview";
import ProcessingSpinner from "./components/ProcessingSpinner";
import RiskChart from "./components/RiskChart";
import ScanHistory from "./components/ScanHistory";
import ThreatGauge from "./components/ThreatGauge";
import ThreatIntelWorkspace from "./components/ThreatIntelWorkspace";
import ThreatWorldMap from "./components/ThreatWorldMap";
import TimelineChart from "./components/TimelineChart";
import UploadZone from "./components/UploadZone";
import { CosmicParallaxBg } from "./components/ui/parallax-cosmic-background";

const DASHBOARD_NAV = [
  {
    id: "overview",
    to: "/dashboard",
    label: "Overview",
    icon: LayoutDashboard,
    end: true,
  },
  {
    id: "incidents",
    to: "/dashboard/incidents",
    label: "Incidents",
    icon: AlertTriangle,
  },
  {
    id: "timeline",
    to: "/dashboard/timeline",
    label: "Timeline",
    icon: Activity,
  },
  {
    id: "intel",
    to: "/dashboard/intel",
    label: "Intel",
    icon: Database,
  },
  {
    id: "attack-story",
    to: "/dashboard/attack-story",
    label: "Story",
    icon: Activity,
  },
  {
    id: "evidence",
    to: "/dashboard/evidence",
    label: "Evidence",
    icon: Database,
  },
  {
    id: "playbook",
    to: "/dashboard/playbook",
    label: "Playbook",
    icon: ShieldCheck,
  },
  {
    id: "geo-trail",
    to: "/dashboard/geo-trail",
    label: "Geo Trail",
    icon: History,
  },
  {
    id: "command-center",
    to: "/dashboard/command-center",
    label: "Command",
    icon: Terminal,
  },
  {
    id: "history",
    to: "/dashboard/history",
    label: "History",
    icon: History,
  },
  {
    id: "operations",
    to: "/dashboard/operations",
    label: "Ops",
    icon: Terminal,
  },
];

function resolveDashboardView(pathname) {
  if (pathname.includes("/dashboard/incidents")) {
    return "incidents";
  }
  if (pathname.includes("/dashboard/timeline")) {
    return "timeline";
  }
  if (pathname.includes("/dashboard/history")) {
    return "history";
  }
  if (pathname.includes("/dashboard/intel")) {
    return "intel";
  }
  if (pathname.includes("/dashboard/attack-story")) {
    return "attack-story";
  }
  if (pathname.includes("/dashboard/evidence")) {
    return "evidence";
  }
  if (pathname.includes("/dashboard/playbook")) {
    return "playbook";
  }
  if (pathname.includes("/dashboard/geo-trail")) {
    return "geo-trail";
  }
  if (pathname.includes("/dashboard/command-center")) {
    return "command-center";
  }
  if (pathname.includes("/dashboard/operations")) {
    return "operations";
  }
  return "overview";
}

const TRAIL_COUNTRY_COORDS = {
  US: [38, -97],
  CA: [56, -106],
  GB: [55, -3],
  DE: [51, 10],
  FR: [46, 2],
  NL: [52, 5],
  RU: [61, 105],
  IN: [21, 78],
  CN: [35, 104],
  JP: [36, 138],
  SG: [1.35, 103.8],
  AU: [-25, 133],
  BR: [-14, -51],
  ZA: [-30, 24],
  PK: [30, 70],
  TR: [39, 35],
  NG: [9, 8],
};

const TRAIL_CITY_BY_COUNTRY = {
  US: "Washington, D.C.",
  CA: "Ottawa",
  GB: "London",
  DE: "Berlin",
  FR: "Paris",
  NL: "Amsterdam",
  RU: "Moscow",
  IN: "New Delhi",
  CN: "Beijing",
  JP: "Tokyo",
  SG: "Singapore",
  AU: "Canberra",
  BR: "Brasilia",
  ZA: "Pretoria",
  PK: "Islamabad",
  TR: "Ankara",
  NG: "Abuja",
};

const GEO_WORLD_VIEWBOX = world.viewBox || "0 0 1010 666";
const GEO_WORLD_LOCATIONS = world.locations || [];
const GEO_WORLD_LOCATION_BY_CODE = new Map(
  GEO_WORLD_LOCATIONS.map((location) => [String(location.id || "").toUpperCase(), location])
);
const GEO_WORLD_CENTER_BY_CODE = new Map(
  GEO_WORLD_LOCATIONS.map((location) => {
    const [x1, y1, x2, y2] = svgPathBbox(location.path);
    return [String(location.id || "").toUpperCase(), { x: (x1 + x2) / 2, y: (y1 + y2) / 2 }];
  })
);

const [GEO_VB_X, GEO_VB_Y, GEO_VB_W, GEO_VB_H] = String(GEO_WORLD_VIEWBOX)
  .trim()
  .split(/\s+/)
  .map((value) => Number(value));

function formatTimeLabel(value) {
  if (!value) {
    return "n/a";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  return parsed.toLocaleString();
}

function formatGeoCoordinate(value, axis) {
  const numeric = Number(value || 0);
  const absolute = Math.abs(numeric).toFixed(2);
  if (axis === "lat") {
    return `${absolute}Â°${numeric >= 0 ? "N" : "S"}`;
  }
  return `${absolute}Â°${numeric >= 0 ? "E" : "W"}`;
}

function getCountryName(code) {
  if (!code) {
    return "Unknown";
  }
  try {
    const formatter = new Intl.DisplayNames(["en"], { type: "region" });
    return formatter.of(code) || code;
  } catch {
    return code;
  }
}

function buildStorySteps(result) {
  const top = result?.anomalies?.[0] || null;
  const timeline = result?.timeline?.series || [];
  const anomalyWindows = timeline.filter((item) => item.is_anomaly_window).length;
  const breakdown = result?.detection_breakdown || {};

  return [
    {
      title: "Ingestion",
      detail: `Scan received ${result?.total_events || 0} events from ${result?.detected_format || "unknown"} input.`,
      stamp: formatTimeLabel(result?.scan_timestamp),
    },
    {
      title: "Feature Matrix",
      detail: `Built ${timeline.length} windows with ${result?.unique_ips || 0} unique source IPs.`,
      stamp: timeline[0] ? formatTimeLabel(timeline[0].timestamp) : "n/a",
    },
    {
      title: "Detector Fusion",
      detail: `Rules ${breakdown.rule_count || 0} | ML ${breakdown.ml_count || 0} | Spike ${breakdown.spike_count || 0}.`,
      stamp: `${anomalyWindows} anomaly-aligned windows`,
    },
    {
      title: "Incident Peak",
      detail: top
        ? `${top.source_ip} reached ${Math.round(top.composite_score || 0)}/100 with ${top.severity_label || "LOW"} severity.`
        : "No ranked anomaly was generated for this scan.",
      stamp: top ? formatTimeLabel(top.window_start) : "n/a",
    },
    {
      title: "Action Guidance",
      detail: top
        ? `Primary response: isolate ${top.source_ip}, reset affected credentials, preserve timeline evidence.`
        : "Monitor baseline and run another scan with broader data.",
      stamp: "Playbook ready",
    },
  ];
}

export default function App() {
  const location = useLocation();
  const [health, setHealth] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);
  const [historyBusy, setHistoryBusy] = useState(false);
  const [jobStatus, setJobStatus] = useState(null);
  const [ribbonCompact, setRibbonCompact] = useState(false);

  const activeView = resolveDashboardView(location.pathname);
  const eventTypeCounts = useMemo(() => {
    if (!result?.event_type_counts) {
      return [];
    }
    return Object.entries(result.event_type_counts).sort((left, right) => Number(right[1]) - Number(left[1]));
  }, [result]);

  useEffect(() => {
    let active = true;
    healthCheck()
      .then((payload) => {
        if (active) {
          setHealth(payload);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.message);
        }
      });

    reloadHistory(active);
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      setRibbonCompact(window.scrollY > 24);
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  async function reloadHistory(active = true) {
    setHistoryBusy(true);
    try {
      const scans = await listScans();
      if (active) {
        setHistory(scans);
      }
    } catch (err) {
      if (active) {
        setError(err.message);
      }
    } finally {
      if (active) {
        setHistoryBusy(false);
      }
    }
  }

  async function handleScan(file) {
    setBusy(true);
    setError("");
    try {
      const queued = await startAsyncScan(file);
      await trackScanJob(queued.job_id);
      await reloadHistory();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      setJobStatus(null);
    }
  }

  async function handleTryDemo(demoFilename = "brute_force_massive.log") {
    setBusy(true);
    setError("");
    try {
      const queued = await startDemoScan(demoFilename, { async: true });
      await trackScanJob(queued.job_id);
      await reloadHistory();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      setJobStatus(null);
    }
  }

  async function trackScanJob(jobId) {
    const startedAt = Date.now();
    const maxWaitMs = 10 * 60 * 1000;
    const minDelayMs = 450;
    const maxDelayMs = 3000;
    let delayMs = minDelayMs;
    let lastProgress = -1;

    while (Date.now() - startedAt < maxWaitMs) {
      const job = await getScanJob(jobId);
      setJobStatus(job);
      if (job.status === "completed") {
        setResult(job.result || null);
        return;
      }
      if (job.status === "failed") {
        throw new Error(job.error || "Scan job failed.");
      }

      const progress = Number(job.progress || 0);
      if (progress > lastProgress) {
        delayMs = minDelayMs;
        lastProgress = progress;
      } else {
        delayMs = Math.min(maxDelayMs, Math.floor(delayMs * 1.4));
      }

      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }

    throw new Error("Scan job timed out. Please retry with a smaller file or rerun the scan.");
  }

  async function openHistoryScan(scanId) {
    setBusy(true);
    setError("");
    try {
      const payload = await getScanReport(scanId);
      setResult(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function removeHistoryScan(scanId) {
    setError("");
    try {
      await deleteScan(scanId);
      setHistory((previous) => previous.filter((item) => item.scan_id !== scanId));
      if (result?.scan_id === scanId) {
        setResult(null);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="relative min-h-screen bg-[#07090E] text-slate-300 font-sans selection:bg-indigo-500/30 overflow-x-hidden">
      {/* Subtle grain/noise or deep ambient glow, completely professional */}
      <CosmicParallaxBg head="Log Sentinel" text="Cybersecurity platform, AI driven, Scaleable" className="fixed inset-0 z-[-1] pointer-events-none" />

      <header className={`sticky top-0 z-50 transition-all duration-300 ${ribbonCompact ? "py-3" : "py-5"} bg-[#07090E]/90 backdrop-blur-xl border-b border-white/5`}>
        <div className="max-w-[1600px] mx-auto px-6 lg:px-10 flex items-center justify-between">
          <div className="flex items-center xl:gap-12 gap-6">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                <ShieldCheck size={18} className="text-indigo-400" />
              </div>
              <p className="text-sm font-semibold tracking-wide text-white hidden sm:block">Log<span className="text-indigo-400">Sentinel</span></p>
            </div>
            
            <nav className="flex items-center gap-1" aria-label="Dashboard sections">
              {DASHBOARD_NAV.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.id}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) => `flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${isActive ? "bg-white/10 text-white" : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]"}`}
                  >
                    {({ isActive }) => (
                      <>
                        <Icon size={16} className={isActive ? "text-indigo-400" : "text-slate-500"} />
                        <span className="hidden md:inline">{item.label}</span>
                      </>
                    )}
                  </NavLink>
                );
              })}
            </nav>
          </div>

          <div className="flex items-center gap-2">
            <Link 
              to="/" 
              className="px-4 py-1.5 rounded-md text-sm font-medium text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
            >
              Overview
            </Link>
            <Link 
              to="/about" 
              className="px-4 py-1.5 rounded-md text-sm font-medium text-slate-400 hover:text-white hover:bg-white/5 transition-colors"
            >
              Docs
            </Link>
          </div>
        </div>
      </header>

      <main className="main-grid max-w-[1600px] mx-auto p-6 md:p-10 relative z-10">
        <section className="panel panel-upload reveal reveal-2">
          <UploadZone onScan={handleScan} onTryDemo={handleTryDemo} busy={busy} />
          {busy ? (
            <ProcessingSpinner
              progress={jobStatus?.progress || 0}
              stage={jobStatus?.stage || "starting"}
              etaSeconds={jobStatus?.eta_seconds ?? null}
            />
          ) : null}
          {error ? <p className="error-text">{error}</p> : null}
        </section>

        <section className="panel panel-results reveal reveal-3">
          {activeView === "overview" ? <OverviewWorkspace result={result} /> : null}
          {activeView === "incidents" ? <IncidentsWorkspace result={result} /> : null}
          {activeView === "timeline" ? <TimelineWorkspace result={result} /> : null}
          {activeView === "history" ? (
            <HistoryWorkspace
              scans={history}
              busy={historyBusy}
              currentScanId={result?.scan_id || ""}
              onReload={() => reloadHistory()}
              onOpen={openHistoryScan}
              onDelete={removeHistoryScan}
            />
          ) : null}
          {activeView === "attack-story" ? <AttackStoryWorkspace result={result} /> : null}
          {activeView === "evidence" ? <EvidenceDrawerWorkspace result={result} /> : null}
          {activeView === "playbook" ? <PlaybookActionsWorkspace result={result} /> : null}
          {activeView === "geo-trail" ? <GeoAttackTrailWorkspace result={result} /> : null}
          {activeView === "command-center" ? <LiveCommandCenterWorkspace result={result} health={health} /> : null}
          {activeView === "intel" ? (
            <ThreatIntelWorkspace
              knownBadCount={health?.known_bad_count ?? 0}
              geoIpOverrideCount={health?.geoip_override_count ?? 0}
            />
          ) : null}
          {activeView === "operations" ? (
            <OperationsWorkspace health={health} history={history} result={result} eventTypeCounts={eventTypeCounts} />
          ) : null}
        </section>
      </main>
    </div>
  );
}

function OverviewWorkspace({ result }) {
  if (!result) {
    return <EmptyWorkspace title="No scan loaded yet" description="Run a scan from the left panel to populate overview analytics." />;
  }
  return <Dashboard result={result} />;
}

function IncidentsWorkspace({ result }) {
  if (!result) {
    return <EmptyWorkspace title="No incident data yet" description="Scan a file to open incident investigation cards and recommendations." />;
  }

  const top = result.anomalies?.[0];
  return (
    <div className="dashboard-stack">
      <WorkspaceHeader
        title="Incident Center"
        description="Prioritized attack findings with explainable tags and response recommendations."
      />

      <div className="summary-grid">
        <SummaryCard label="Open Incidents" value={result.anomalies.length} />
        <SummaryCard label="Critical Alerts" value={result.anomalies.filter((item) => item.severity_label === "CRITICAL").length} />
        <SummaryCard label="Top Threat IP" value={top?.source_ip || "n/a"} />
        <SummaryCard label="Highest Score" value={top ? `${top.composite_score}/100` : "n/a"} />
      </div>

      <ExportBar scanId={result.scan_id} />

      <ErrorBoundary>
        <div className="cards-stack">
          {result.anomalies.map((anomaly, index) => (
            <AnomalyCard key={`${anomaly.rank}-${anomaly.source_ip}`} anomaly={anomaly} index={index} />
          ))}
        </div>
      </ErrorBoundary>
    </div>
  );
}

function TimelineWorkspace({ result }) {
  if (!result) {
    return <EmptyWorkspace title="Timeline unavailable" description="Run a scan to unlock timeline reconstruction and detector movement views." />;
  }

  const timelineSeries = result.timeline?.series || [];
  const timelineWindowCount = timelineSeries.length;
  const anomalyWindows = timelineSeries.filter((item) => item.is_anomaly_window).length;
  const avgEventsPerWindow = timelineWindowCount
    ? Math.round(timelineSeries.reduce((sum, item) => sum + Number(item.event_count || 0), 0) / timelineWindowCount)
    : 0;

  return (
    <div className="dashboard-stack">
      <WorkspaceHeader
        title="Timeline Intelligence"
        description="Explore temporal attack movement, detector contributions, and risk drift across windows."
      />

      <div className="timeline-summary-row">
        <SummaryCard label="Observed Windows" value={timelineWindowCount} />
        <SummaryCard label="Anomaly Windows" value={anomalyWindows} />
        <SummaryCard label="Avg Events / Window" value={avgEventsPerWindow} />
        <SummaryCard label="Tracked Sources" value={result.unique_ips || 0} />
      </div>

      <div className="viz-grid">
        <ThreatGauge anomalies={result.anomalies} />
        <DetectionBreakdown anomalies={result.anomalies} detectionBreakdown={result.detection_breakdown} />
      </div>

      <div className="viz-grid">
        <ThreatWorldMap anomalies={result.anomalies} />
        <RiskChart anomalies={result.anomalies} />
      </div>

      <div className="viz-grid single-column">
        <TimelineChart result={result} />
      </div>
    </div>
  );
}

function OperationsWorkspace({ health, history, result, eventTypeCounts }) {
  return (
    <div className="dashboard-stack">
      <WorkspaceHeader
        title="Operations Console"
        description="Monitor service status, scan inventory, and event distribution for live demo control."
      />

      <div className="ops-grid">
        <OpsCard icon={ShieldCheck} label="Backend Status" value={health?.status || "loading"} />
        <OpsCard icon={ShieldCheck} label="Auth Mode" value={health?.api_auth_enabled ? "enabled" : "disabled"} />
        <OpsCard icon={ShieldCheck} label="Cached Scans" value={health?.scan_cache_size ?? "-"} />
        <OpsCard icon={ShieldCheck} label="Persisted Scans" value={health?.persisted_scan_count ?? "-"} />
      </div>

      <section className="ops-panel">
        <h3>Recent Scan Inventory</h3>
        {history.length ? (
          <div className="ops-list">
            {history.slice(0, 6).map((item) => (
              <div key={item.scan_id} className="ops-list-item">
                <div>
                  <strong>{item.filename || "unknown.log"}</strong>
                  <p>{new Date(item.scan_timestamp).toLocaleString()}</p>
                </div>
                <div className="ops-list-metrics">
                  <span>{item.detected_format || "unknown"}</span>
                  <span>score {Math.round(item.top_score || 0)}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted-copy">No historical scans yet.</p>
        )}
      </section>

      <section className="ops-panel">
        <h3>Event Type Distribution</h3>
        {result && eventTypeCounts.length ? (
          <div className="ops-event-grid">
            {eventTypeCounts.map(([eventType, count]) => (
              <div key={eventType} className="ops-event-card">
                <span>{eventType}</span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted-copy">Run a scan to inspect event categories.</p>
        )}
      </section>
    </div>
  );
}

function HistoryWorkspace({ scans, busy, currentScanId, onReload, onOpen, onDelete }) {
  return (
    <div className="dashboard-stack">
      <WorkspaceHeader
        title="Scan History"
        description="Browse, search, and reopen previous scan reports in a full-width history view."
      />

      <section className="history-workspace-card">
        <ScanHistory
          scans={scans}
          busy={busy}
          currentScanId={currentScanId}
          onReload={onReload}
          onOpen={onOpen}
          onDelete={onDelete}
          variant="full"
        />
      </section>
    </div>
  );
}

function AttackStoryWorkspace({ result }) {
  const [activeStep, setActiveStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);
  const steps = buildStorySteps(result);
  const timelineSeries = result?.timeline?.series || [];

  useEffect(() => {
    setActiveStep(0);
    setIsPlaying(true);
  }, [result?.scan_id]);

  useEffect(() => {
    if (!isPlaying || steps.length <= 1) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      setActiveStep((previous) => (previous + 1) % steps.length);
    }, 2100);
    return () => window.clearInterval(timer);
  }, [isPlaying, steps.length]);

  if (!result) {
    return <EmptyWorkspace title="Story unavailable" description="Run a scan to generate the attack narrative timeline." />;
  }

  const boundedStep = Math.max(0, Math.min(activeStep, steps.length - 1));
  const current = steps[boundedStep];
  const visualBars = timelineSeries.length
    ? timelineSeries.slice(0, 18).map((item) => Math.max(0.08, Math.min(1, Number(item.event_count || 0) / 90)))
    : [0.2, 0.4, 0.62, 0.74, 0.58, 0.85, 0.66, 0.51, 0.36, 0.44];
  const visualActiveIndex = Math.max(0, Math.ceil(((boundedStep + 1) / steps.length) * visualBars.length) - 1);
  const progressPercent = steps.length > 1 ? Math.round((boundedStep / (steps.length - 1)) * 100) : 100;
  const currentTimelineIndex = timelineSeries.length
    ? Math.min(timelineSeries.length - 1, Math.max(0, Math.floor((boundedStep / steps.length) * timelineSeries.length)))
    : -1;
  const currentTimelineWindow = currentTimelineIndex >= 0 ? timelineSeries[currentTimelineIndex] : null;

  return (
    <div className="dashboard-stack">
      <WorkspaceHeader
        title="Attack Story Mode"
        description="A scene-by-scene incident playback built from feature windows and detector output."
      />

      <section className="story-cinema-card">
        <div className="story-cinema-head">
          <div>
            <span className="story-live-pill">{isPlaying ? "Live Playback" : "Playback Paused"}</span>
            <p>{steps.length} scene timeline Â· {timelineSeries.length || 0} reconstructed windows</p>
          </div>
          <div className="story-cinema-actions">
            <button type="button" className="secondary-button small" onClick={() => setIsPlaying((previous) => !previous)}>
              {isPlaying ? "Pause" : "Play"}
            </button>
            <button
              type="button"
              className="secondary-button small"
              onClick={() => {
                setActiveStep(0);
                setIsPlaying(true);
              }}
            >
              Replay
            </button>
          </div>
        </div>

        <div className="story-progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progressPercent}>
          <span className="story-progress-fill" style={{ width: `${progressPercent}%` }} />
        </div>

        <div className="story-visual-wave" aria-hidden="true">
          {visualBars.map((bar, index) => (
            <span
              key={`story-bar-${index}`}
              className={`story-visual-bar ${index <= visualActiveIndex ? "active" : ""}`}
              style={{ height: `${Math.round(bar * 100)}%`, animationDelay: `${index * 0.05}s` }}
            />
          ))}
        </div>
      </section>

      <section className="story-scene-stage">
        <div className="story-scene-viewport">
          <div className="story-scene-track" style={{ transform: `translateX(-${boundedStep * 100}%)` }}>
            {steps.map((step, index) => (
              <article key={`scene-${step.title}`} className="story-scene-card">
                <span>Scene {index + 1}</span>
                <h4>{step.title}</h4>
                <p>{step.detail}</p>
              </article>
            ))}
          </div>
        </div>
        <div className="story-scene-foot">
          <p>
            {currentTimelineWindow
              ? `Window ${currentTimelineIndex + 1}: ${currentTimelineWindow.event_count || 0} events, ${currentTimelineWindow.is_anomaly_window ? "anomaly flagged" : "baseline flow"}`
              : "No timeline window telemetry available for this story."}
          </p>
          <div className="story-scene-dots" aria-hidden="true">
            {steps.map((step, index) => (
              <span key={`dot-${step.title}`} className={`story-scene-dot ${index === boundedStep ? "active" : ""}`} />
            ))}
          </div>
        </div>
      </section>

      <div className="story-step-row">
        {steps.map((step, index) => (
          <button
            key={step.title}
            type="button"
            className={`story-step ${index === boundedStep ? "active" : ""}`}
            onClick={() => {
              setIsPlaying(false);
              setActiveStep(index);
            }}
          >
            <span>Step {index + 1}</span>
            <strong>{step.title}</strong>
          </button>
        ))}
      </div>

      <section className="story-detail-card">
        <p className="story-stamp">{current.stamp}</p>
        <h3>{current.title}</h3>
        <p>{current.detail}</p>
        <div className="story-actions">
          <button
            type="button"
            className="secondary-button small"
            onClick={() => {
              setIsPlaying(false);
              setActiveStep((prev) => Math.max(0, prev - 1));
            }}
          >
            Previous
          </button>
          <button
            type="button"
            className="secondary-button small"
            onClick={() => {
              setIsPlaying(false);
              setActiveStep((prev) => Math.min(steps.length - 1, prev + 1));
            }}
          >
            Next
          </button>
        </div>
      </section>
    </div>
  );
}

function EvidenceDrawerWorkspace({ result }) {
  const anomalies = result?.anomalies || [];
  const [selectedRank, setSelectedRank] = useState(anomalies[0]?.rank ?? null);

  useEffect(() => {
    setSelectedRank(anomalies[0]?.rank ?? null);
  }, [result?.scan_id, anomalies.length]);

  if (!result || !anomalies.length) {
    return <EmptyWorkspace title="Evidence drawer empty" description="Run a scan to inspect anomaly evidence and extracted signals." />;
  }

  const selected = anomalies.find((item) => item.rank === selectedRank) || anomalies[0];
  const evidenceLines = [
    `[window] ${selected.window_start || "n/a"} -> ${selected.window_end || "n/a"}`,
    `[source_ip] ${selected.source_ip || "n/a"}`,
    `[rule] ${selected.rule_triggered || "none"}`,
    `[stats] failed=${selected.login_failure_count || 0} success=${selected.login_success_count || 0}`,
    `[traffic] rpm=${selected.requests_per_minute || 0} unique_endpoints=${selected.unique_endpoints || 0}`,
    `[score] iso=${selected.iso_score || 0} spike=${selected.spike_score || 0} composite=${selected.composite_score || 0}`,
  ];

  return (
    <div className="dashboard-stack">
      <WorkspaceHeader
        title="Evidence Drawer"
        description="Transparent incident context with detector evidence, signal stats, and analyst-ready snippets."
      />

      <div className="evidence-layout">
        <section className="evidence-list">
          {anomalies.map((item) => (
            <button
              key={`${item.rank}-${item.source_ip}`}
              type="button"
              className={`evidence-item ${item.rank === selected.rank ? "active" : ""}`}
              onClick={() => setSelectedRank(item.rank)}
            >
              <strong>#{item.rank} {item.source_ip}</strong>
              <span>{item.severity_label || "LOW"} Â· {Math.round(item.composite_score || 0)}/100</span>
            </button>
          ))}
        </section>

        <section className="evidence-drawer">
          <div className="evidence-drawer-top">
            <h3>Incident Evidence</h3>
            <p>{selected.severity_label || "LOW"} - {selected.rule_triggered || "none"}</p>
          </div>
          <div className="evidence-metrics">
            <span>Failed {selected.login_failure_count || 0}</span>
            <span>Success {selected.login_success_count || 0}</span>
            <span>RPM {selected.requests_per_minute || 0}</span>
            <span>Endpoints {selected.unique_endpoints || 0}</span>
          </div>
          <p className="evidence-briefing">{selected.briefing || "No narrative briefing available."}</p>
          <pre className="evidence-code">{evidenceLines.join("\n")}</pre>
        </section>
      </div>
    </div>
  );
}

function PlaybookActionsWorkspace({ result }) {
  const top = result?.anomalies?.[0] || null;
  const [completed, setCompleted] = useState({});

  useEffect(() => {
    setCompleted({});
  }, [result?.scan_id]);

  if (!result || !top) {
    return <EmptyWorkspace title="Playbook unavailable" description="Run a scan to auto-generate an incident response playbook." />;
  }

  const actions = [
    { id: "contain", phase: "Immediate", text: `Block source IP ${top.source_ip || "n/a"} at perimeter and WAF rules.` },
    { id: "cred", phase: "Immediate", text: "Reset impacted credentials and invalidate active user sessions." },
    { id: "isolate", phase: "Immediate", text: "Isolate affected workload and preserve volatile evidence artifacts." },
    { id: "review", phase: "Within 1 Hour", text: "Review adjacent logs for lateral movement and privilege escalation signs." },
    { id: "notify", phase: "Within 1 Hour", text: "Notify SOC lead and open incident ticket with full briefing evidence." },
    { id: "harden", phase: "Within 24 Hours", text: "Apply hardening updates and tune detection thresholds from findings." },
  ];

  const completedCount = actions.filter((action) => completed[action.id]).length;
  const progress = Math.round((completedCount / actions.length) * 100);

  return (
    <div className="dashboard-stack">
      <WorkspaceHeader
        title="Playbook Actions Panel"
        description="Response checklist generated from the top incident with operational completion tracking."
      />

      <section className="playbook-progress">
        <strong>Completion {progress}%</strong>
        <div className="playbook-track">
          <div className="playbook-fill" style={{ width: `${progress}%` }} />
        </div>
      </section>

      <section className="playbook-list">
        {actions.map((action) => (
          <article key={action.id} className="playbook-item">
            <button
              type="button"
              className={`playbook-check ${completed[action.id] ? "done" : ""}`}
              onClick={() => setCompleted((previous) => ({ ...previous, [action.id]: !previous[action.id] }))}
              aria-label={`Mark ${action.text} complete`}
            >
              {completed[action.id] ? "Done" : "Todo"}
            </button>
            <div>
              <span>{action.phase}</span>
              <p>{action.text}</p>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}

function GeoAttackTrailWorkspace({ result }) {
  const [trailZoomLevel, setTrailZoomLevel] = useState(1);
  const [trailExpanded, setTrailExpanded] = useState(false);
  const [trailPanOffset, setTrailPanOffset] = useState({ x: 0, y: 0 });
  const [trailDragging, setTrailDragging] = useState(false);
  const [trailDragOrigin, setTrailDragOrigin] = useState(null);

  useEffect(() => {
    setTrailZoomLevel(1);
    setTrailExpanded(false);
    setTrailPanOffset({ x: 0, y: 0 });
    setTrailDragging(false);
    setTrailDragOrigin(null);
  }, [result?.scan_id]);

  if (!result || !result.anomalies?.length) {
    return <EmptyWorkspace title="Geo trail unavailable" description="Run a scan with mapped countries to animate movement trails." />;
  }

  const clamp = (value, minimum, maximum) => Math.max(minimum, Math.min(maximum, value));
  const gridRows = Array.from({ length: 5 }, (_, index) => GEO_VB_Y + ((index + 1) * GEO_VB_H) / 6);
  const gridCols = Array.from({ length: 8 }, (_, index) => GEO_VB_X + ((index + 1) * GEO_VB_W) / 9);
  const points = [];
  const visitedCountries = new Set();

  result.anomalies.forEach((item) => {
    if (visitedCountries.has(item.country_code)) {
      return;
    }
    visitedCountries.add(item.country_code);

    const coord = TRAIL_COUNTRY_COORDS[item.country_code];
    const location = GEO_WORLD_LOCATION_BY_CODE.get(item.country_code);
    const center = GEO_WORLD_CENTER_BY_CODE.get(item.country_code);

    if (!coord || !location || !center || points.length >= 8) {
      return;
    }

    points.push({
      country: item.country_code,
      countryName: getCountryName(item.country_code),
      cityName: item.city || item.city_name || TRAIL_CITY_BY_COUNTRY[item.country_code] || "City Unavailable",
      score: Math.round(item.composite_score || 0),
      latitude: coord[0],
      longitude: coord[1],
      x: center.x,
      y: center.y,
    });
  });

  if (points.length < 2) {
    return <EmptyWorkspace title="Insufficient geo trail points" description="Current anomalies do not have enough mapped country transitions." />;
  }

  const focusX = points[0]?.x || GEO_VB_X + GEO_VB_W / 2;
  const focusY = points[0]?.y || GEO_VB_Y + GEO_VB_H / 2;
  const showDeepTrailLabels = trailZoomLevel >= 1.8;
  const trailVisualScale = 1 / trailZoomLevel;

  function clampTrailPan(candidate, zoom) {
    const maxX = Math.max(0, 240 * (zoom - 1));
    const maxY = Math.max(0, 160 * (zoom - 1));
    return {
      x: Math.max(-maxX, Math.min(maxX, candidate.x)),
      y: Math.max(-maxY, Math.min(maxY, candidate.y)),
    };
  }

  function startTrailPan(event) {
    if (trailZoomLevel <= 1) {
      return;
    }
    if (event.target?.closest?.(".map-control-panel")) {
      return;
    }
    setTrailDragging(true);
    setTrailDragOrigin({
      startX: event.clientX,
      startY: event.clientY,
      originPanX: trailPanOffset.x,
      originPanY: trailPanOffset.y,
    });
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function moveTrailPan(event) {
    if (!trailDragging || !trailDragOrigin) {
      return;
    }
    const deltaX = event.clientX - trailDragOrigin.startX;
    const deltaY = event.clientY - trailDragOrigin.startY;
    setTrailPanOffset(
      clampTrailPan(
        {
          x: trailDragOrigin.originPanX + deltaX,
          y: trailDragOrigin.originPanY + deltaY,
        },
        trailZoomLevel
      )
    );
  }

  function endTrailPan(event) {
    if (!trailDragging) {
      return;
    }
    setTrailDragging(false);
    setTrailDragOrigin(null);
    event.currentTarget.releasePointerCapture?.(event.pointerId);
  }

  const trailSegments = points.slice(1).map((point, index) => {
    const previous = points[index];
    const midpointX = (previous.x + point.x) / 2;
    const travelDistance = Math.abs(point.x - previous.x);
    const curveY = clamp(
      Math.min(previous.y, point.y) - Math.max(22, travelDistance * 0.1),
      GEO_VB_Y + 22,
      GEO_VB_Y + GEO_VB_H - 22
    );
    const path = `M ${previous.x} ${previous.y} Q ${midpointX} ${curveY} ${point.x} ${point.y}`;

    return {
      id: `${previous.country}-${point.country}-${index}`,
      from: previous.country,
      to: point.country,
      fromName: previous.countryName,
      toName: point.countryName,
      fromCity: previous.cityName,
      toCity: point.cityName,
      fromLat: previous.latitude,
      fromLon: previous.longitude,
      toLat: point.latitude,
      toLon: point.longitude,
      score: point.score,
      path,
    };
  });

  return (
    <div className="dashboard-stack">
      <WorkspaceHeader
        title="Geo Attack Trail Animation"
        description="Sequential country-to-country movement path extracted from ranked anomaly evidence."
      />

      <section className="geo-trail-card">
        <div className="geo-trail-meta">
          <span>Countries {points.length}</span>
          <span>Transition Hops {trailSegments.length}</span>
          <span>Peak Score {Math.max(...points.map((point) => point.score))}/100</span>
        </div>

        <div
          className={`geo-trail-map-wrap map-interactive-surface ${trailExpanded ? "is-expanded" : ""} ${trailDragging ? "is-dragging" : ""}`}
          onPointerDown={startTrailPan}
          onPointerMove={moveTrailPan}
          onPointerUp={endTrailPan}
          onPointerCancel={endTrailPan}
        >
          <div className="map-control-panel" role="group" aria-label="Geo trail controls">
            <button
              type="button"
              className="map-control-button"
              onClick={() => setTrailZoomLevel((previous) => Math.min(4, Number((previous + 0.25).toFixed(2))))}
              aria-label="Zoom in geo map"
            >
              +
            </button>
            <button
              type="button"
              className="map-control-button"
              onClick={() => setTrailZoomLevel((previous) => Math.max(1, Number((previous - 0.25).toFixed(2))))}
              aria-label="Zoom out geo map"
            >
              -
            </button>
            <button
              type="button"
              className="map-control-button"
              onClick={() => {
                setTrailZoomLevel(1);
                setTrailPanOffset({ x: 0, y: 0 });
              }}
              aria-label="Reset geo map zoom"
            >
              Reset
            </button>
            <button
              type="button"
              className="map-control-button"
              onClick={() => setTrailExpanded((previous) => !previous)}
              aria-label={trailExpanded ? "Minimize geo map" : "Maximize geo map"}
            >
              {trailExpanded ? "Min" : "Max"}
            </button>
            <span className="map-control-value">{trailZoomLevel.toFixed(2)}x</span>
          </div>

          <svg viewBox={GEO_WORLD_VIEWBOX} className="geo-trail-map" aria-label="Geo attack trail">
            <g
              className="geo-trail-viewport"
              style={{
                transformOrigin: `${focusX}px ${focusY}px`,
                transform: `translate(${trailPanOffset.x}px, ${trailPanOffset.y}px) scale(${trailZoomLevel})`,
              }}
            >
          <defs>
            <linearGradient id="geoTrailStroke" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="rgba(109, 223, 243, 0.25)" />
              <stop offset="48%" stopColor="rgba(255, 176, 101, 0.78)" />
              <stop offset="100%" stopColor="rgba(255, 103, 103, 0.92)" />
            </linearGradient>
            <radialGradient id="geoTrailGlow" cx="50%" cy="50%" r="72%">
              <stop offset="0%" stopColor="rgba(22, 106, 129, 0.4)" />
              <stop offset="100%" stopColor="rgba(2, 10, 20, 0.15)" />
            </radialGradient>
          </defs>

          <rect x={GEO_VB_X} y={GEO_VB_Y} width={GEO_VB_W} height={GEO_VB_H} rx="18" className="geo-trail-bg" />
          <rect x={GEO_VB_X} y={GEO_VB_Y} width={GEO_VB_W} height={GEO_VB_H} rx="18" fill="url(#geoTrailGlow)" />

          {gridRows.map((row) => (
            <line key={`geo-grid-row-${row}`} x1={GEO_VB_X} y1={row} x2={GEO_VB_X + GEO_VB_W} y2={row} className="geo-trail-grid" />
          ))}
          {gridCols.map((column) => (
            <line key={`geo-grid-col-${column}`} x1={column} y1={GEO_VB_Y} x2={column} y2={GEO_VB_Y + GEO_VB_H} className="geo-trail-grid" />
          ))}

          {GEO_WORLD_LOCATIONS.map((location) => {
            const code = String(location.id || "").toUpperCase();
            const matched = points.find((point) => point.country === code);

            if (!matched) {
              return <path key={`geo-country-${code}`} className="geo-trail-country" d={location.path} />;
            }

            const intensity = Math.max(0.35, Math.min(1, Number(matched.score || 0) / 100));
            return (
              <path
                key={`geo-country-${code}`}
                className="geo-trail-country hot"
                d={location.path}
                style={{ "--geo-hot-intensity": intensity }}
              />
            );
          })}

          {trailSegments.map((segment, index) => (
            <g key={segment.id}>
              <path className="geo-trail-line" d={segment.path} style={{ animationDelay: `${index * 0.22}s` }} />
              <circle className="geo-trail-runner" r="4.2" style={{ animationDelay: `${index * 0.42}s` }}>
                <animateMotion dur="4.4s" repeatCount="indefinite" path={segment.path} rotate="auto" />
              </circle>
            </g>
          ))}

          {points.map((point, index) => (
            <g key={`${point.country}-${index}`}>
              <title>{`${point.countryName} - ${point.cityName} (${point.country}) | Lat ${formatGeoCoordinate(point.latitude, "lat")} | Lon ${formatGeoCoordinate(point.longitude, "lon")}`}</title>
              <circle cx={point.x} cy={point.y} r={Math.max(3.5, 11 * trailVisualScale)} className="geo-trail-node" />
              <circle cx={point.x} cy={point.y} r={Math.max(2, 4 * trailVisualScale)} className="geo-trail-core" />
              <text
                x={point.x + 12}
                y={point.y - 10}
                className="geo-trail-label"
                style={{ fontSize: `${Math.max(6.2, 11 * trailVisualScale)}px`, strokeWidth: `${Math.max(1.2, 3 * trailVisualScale)}px` }}
              >
                {index + 1}. {point.countryName}
              </text>
              {showDeepTrailLabels ? (
                <text
                  x={point.x + 12}
                  y={point.y + 6}
                  className="geo-trail-label city"
                  style={{ fontSize: `${Math.max(5.2, 9 * trailVisualScale)}px`, strokeWidth: `${Math.max(0.9, 2.2 * trailVisualScale)}px` }}
                >
                  {point.cityName}
                </text>
              ) : null}
            </g>
          ))}
            </g>
        </svg>
        </div>

        <div className="geo-trail-hop-row">
          {trailSegments.map((segment, index) => (
            <article key={`hop-${segment.id}`} className="geo-trail-hop-item">
              <span>Hop {index + 1}</span>
              <strong>{segment.fromName} ({segment.fromCity}) to {segment.toName} ({segment.toCity})</strong>
              <p>
                {formatGeoCoordinate(segment.fromLat, "lat")}, {formatGeoCoordinate(segment.fromLon, "lon")} to {" "}
                {formatGeoCoordinate(segment.toLat, "lat")}, {formatGeoCoordinate(segment.toLon, "lon")}
              </p>
              <p>Target score {segment.score}/100</p>
            </article>
          ))}
        </div>

        <div className="geo-country-grid">
          {points.map((point, index) => (
            <GeoCountryPreview
              key={`country-preview-${point.country}-${index}`}
              countryCode={point.country}
              latitude={point.latitude}
              longitude={point.longitude}
              rank={index + 1}
              score={point.score}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

function LiveCommandCenterWorkspace({ result, health }) {
  const series = result?.timeline?.series || [];
  const [isPlaying, setIsPlaying] = useState(true);
  const [cursor, setCursor] = useState(0);

  useEffect(() => {
    setCursor(0);
    setIsPlaying(true);
  }, [result?.scan_id]);

  useEffect(() => {
    if (!isPlaying || series.length <= 1) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      setCursor((previous) => {
        if (previous >= series.length - 1) {
          return previous;
        }
        return previous + 1;
      });
    }, 1100);
    return () => window.clearInterval(timer);
  }, [isPlaying, series.length]);

  if (!result || !series.length) {
    return <EmptyWorkspace title="Command stream idle" description="Run a scan to start the live command center feed simulation." />;
  }

  const visible = series.slice(0, cursor + 1);
  const anomalySeen = visible.filter((item) => item.is_anomaly_window).length;
  const processedEvents = visible.reduce((sum, item) => sum + Number(item.event_count || 0), 0);
  const feed = visible.slice(-10).reverse();

  return (
    <div className="dashboard-stack">
      <WorkspaceHeader
        title="Live Command Center Mode"
        description="Replay-style operational stream of scan windows, detector state changes, and incident signals."
      />

      <section className="command-metrics">
        <article><span>Backend</span><strong>{health?.status || "unknown"}</strong></article>
        <article><span>Events Processed</span><strong>{processedEvents}</strong></article>
        <article><span>Anomaly Windows Seen</span><strong>{anomalySeen}</strong></article>
        <article><span>Top Score</span><strong>{Math.round(result?.anomalies?.[0]?.composite_score || 0)}/100</strong></article>
      </section>

      <section className="command-controls">
        <button type="button" className="secondary-button small" onClick={() => setIsPlaying((prev) => !prev)}>
          {isPlaying ? "Pause Stream" : "Resume Stream"}
        </button>
        <button type="button" className="secondary-button small" onClick={() => setCursor(0)}>
          Restart Replay
        </button>
      </section>

      <section className="command-feed">
        {feed.map((item, index) => (
          <article key={`${item.timestamp}-${index}`} className={`command-feed-item ${item.is_anomaly_window ? "alert" : ""}`}>
            <span>{formatTimeLabel(item.timestamp)}</span>
            <p>
              Window volume {item.event_count || 0}
              {item.is_anomaly_window ? " -> anomaly window flagged" : " -> baseline behavior"}
            </p>
          </article>
        ))}
      </section>
    </div>
  );
}

function EmptyWorkspace({ title, description }) {
  return (
    <div className="empty-state workspace-empty">
      <ShieldCheck className="w-12 h-12 text-[#94a3b8] mb-4 mx-auto opacity-50" />
      <p className="empty-title">{title}</p>
      <p className="empty-text">{description}</p>
    </div>
  );
}

function OldEmptyWorkspace({ title, description }) {
  return (
    <div className="empty-state workspace-empty">
      <p className="empty-title">{title}</p>
      <p className="empty-text">{description}</p>
    </div>
  );
}

function WorkspaceHeader({ title, description }) {
  return (
    <section className="mb-10 text-white translate-y-4 reveal reveal-1">
      <h2 className="text-2xl md:text-3xl font-semibold tracking-tight text-white mb-2">{title}</h2>
      <p className="text-base text-slate-400 max-w-3xl">{description}</p>
    </section>
  );
}

function SummaryCard({ label, value }) {
  return (
    <div className="relative group overflow-hidden rounded-xl bg-white/[0.02] border border-white/5 p-6 hover:bg-white/[0.04] transition-all reveal">
      <span className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{label}</span>
      <strong className="block text-3xl font-semibold text-white tracking-tight">{value}</strong>
    </div>
  );
}

function OpsCard({ icon: Icon, label, value }) {
  return (
    <article className="flex items-center gap-4 rounded-xl bg-white/[0.02] border border-white/5 p-5 hover:bg-white/[0.04] transition-all reveal">
      <div className="p-2.5 rounded-lg bg-indigo-500/10 text-indigo-400">
        <Icon size={22} strokeWidth={2} />
      </div>
      <div>
        <span className="block text-xs font-medium uppercase tracking-wider text-slate-500 mb-1">{label}</span>
        <strong className="block text-lg font-semibold text-white">{value}</strong>
      </div>
    </article>
  );
}



