import AnomalyCard from "./AnomalyCard";
import DetectionBreakdown from "./DetectionBreakdown";
import ExecutiveSummary from "./ExecutiveSummary";
import ExportBar from "./ExportBar";
import NaturalLanguageQuery from "./NaturalLanguageQuery";
import RiskChart from "./RiskChart";
import ThreatGauge from "./ThreatGauge";
import ThreatWorldMap from "./ThreatWorldMap";
import TimelineChart from "./TimelineChart";

export default function Dashboard({ result }) {
  const top = result.anomalies[0] || null;
  const anomalyWindows = (result.timeline?.series || []).filter((item) => item.is_anomaly_window).length;

  return (
    <div className="flex flex-col gap-10 pb-24">
      <section className="flex flex-wrap gap-3 p-4 bg-[#0F131D]/80 border border-white/5 rounded-2xl shadow-sm">
        <InsightBadge
          label="Highest Risk"
          value={top ? `${top.composite_score}/100` : "n/a"}
          tone={top?.severity_label === "CRITICAL" ? "critical" : "neutral"}
        />
        <InsightBadge label="Top IP" value={top?.source_ip || "n/a"} tone="neutral" />
        <InsightBadge label="Alert Windows" value={anomalyWindows} tone="warning" />
        <InsightBadge label="Source Format" value={result.detected_format || "unknown"} tone="neutral" />
      </section>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard label="Total Events" value={result.total_events} />
        <SummaryCard label="Unique IPs" value={result.unique_ips} />
        <SummaryCard label="Critical Threats" value={result.anomalies.length} />
        <SummaryCard label="Log Source" value={result.detected_format} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-[#0F131D]/80 border border-white/5 rounded-2xl p-6 shadow-sm">
          <ThreatGauge anomalies={result.anomalies} />
        </div>
        <div className="bg-[#0F131D]/80 border border-white/5 rounded-2xl p-6 shadow-sm">
          <DetectionBreakdown anomalies={result.anomalies} detectionBreakdown={result.detection_breakdown} />
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="bg-[#0F131D]/80 border border-white/5 rounded-2xl p-6 shadow-sm overflow-x-hidden">
          <ThreatWorldMap anomalies={result.anomalies} />
        </div>
        <div className="bg-[#0F131D]/80 border border-white/5 rounded-2xl p-6 shadow-sm">
          <RiskChart anomalies={result.anomalies} />
        </div>
      </div>

      <div className="bg-indigo-500/[0.03] border border-indigo-500/10 rounded-2xl p-8 shadow-sm">
        <ExecutiveSummary result={result} />
      </div>

      <div className="bg-[#0F131D]/80 border border-white/5 rounded-2xl p-6 shadow-sm">
        <TimelineChart result={result} />
      </div>

      <ExportBar scanId={result.scan_id} />

      <div className="flex flex-col gap-6">
        <h3 className="text-xl font-semibold text-slate-200 pl-4 border-l-2 border-indigo-500">Anomaly Dossier</h3>
        {result.anomalies.length ? (
          result.anomalies.map((anomaly, index) => (
            <AnomalyCard key={`${anomaly.rank}-${anomaly.source_ip}`} anomaly={anomaly} index={index} />
          ))
        ) : (
          <div className="p-12 text-center bg-[#0F131D]/80 rounded-2xl border border-white/5">
            <p className="text-lg font-medium text-slate-300">No ranked anomalies yet</p>
            <p className="text-sm text-slate-500 mt-2">
              The current scoring threshold filtered out low-confidence rows from this scan.
            </p>
          </div>
        )}
      </div>

      <div className="mt-8 bg-[#0F131D] border border-white/5 rounded-2xl p-6 shadow-sm">
        <NaturalLanguageQuery result={result} />
      </div>
    </div>
  );
}

function SummaryCard({ label, value }) {
  return (
    <div className="group rounded-xl bg-[#0F131D]/80 border border-white/5 p-6 transition-all hover:bg-white/[0.04]">
      <span className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">{label}</span>
      <strong className="block text-3xl font-semibold text-white tracking-tight">{value}</strong>
    </div>
  );
}

function InsightBadge({ label, value, tone }) {
  const toneStyles = tone === "critical" 
    ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
    : tone === "warning"
    ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
    : "bg-white/[0.03] text-slate-300 border-white/10";

  return (
    <div className={`px-4 py-2 rounded-lg border ${toneStyles} flex items-center gap-3`}>
      <span className="text-xs font-medium uppercase tracking-wider opacity-80">{label}</span>
      <strong className="text-sm font-semibold">{value}</strong>
    </div>
  );
}
