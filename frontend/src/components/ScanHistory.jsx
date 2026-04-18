import { useMemo, useState } from "react";

export default function ScanHistory({ scans, busy, currentScanId, onReload, onOpen, onDelete, variant = "panel" }) {
  const [query, setQuery] = useState("");
  const isFull = variant === "full";

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return scans;
    }
    return scans.filter((item) => {
      return (
        (item.filename || "").toLowerCase().includes(normalized) ||
        (item.scan_id || "").toLowerCase().includes(normalized) ||
        (item.detected_format || "").toLowerCase().includes(normalized)
      );
    });
  }, [query, scans]);

  return (
    <section className={`history-panel history-panel-${variant}`}>
      <div className="history-head">
        <h3>Scan History</h3>
        <button className="secondary-button small" type="button" onClick={onReload} disabled={busy}>
          {busy ? "Refreshing..." : "Refresh"}
        </button>
      </div>
      <p className="history-summary muted-copy">
        {filtered.length} scan{filtered.length === 1 ? "" : "s"} visible
      </p>
      <input
        className="history-search"
        type="search"
        placeholder="Search by file, id, or format"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />

      <div className="history-list">
        {!filtered.length ? (
          <p className="muted-copy">No persisted scans found.</p>
        ) : (
          filtered.map((item, index) => {
            const isActive = currentScanId === item.scan_id;
            return (
              <article
                key={item.scan_id}
                className={`history-item ${isActive ? "active" : ""} ${isFull ? "history-item-full" : ""}`}
                style={{ "--stagger": `${index * 40}ms` }}
              >
                <div className="history-meta">
                  <strong>{item.filename || "unknown.log"}</strong>
                  <span className="history-format">{item.detected_format || "unknown"}</span>
                  <span className="history-timestamp">{new Date(item.scan_timestamp).toLocaleString()}</span>
                  <span className="history-score">
                    score {Math.round(item.top_score || 0)} / anomalies {item.anomaly_count || 0}
                  </span>
                  {isFull ? <span className="history-id">id {item.scan_id}</span> : null}
                </div>
                <div className="history-actions">
                  <button className="secondary-button small history-action-button history-action-open" type="button" onClick={() => onOpen(item.scan_id)}>
                    Open
                  </button>
                  <button className="danger-button small history-action-button history-action-delete" type="button" onClick={() => onDelete(item.scan_id)}>
                    Delete
                  </button>
                </div>
              </article>
            );
          })
        )}
      </div>
    </section>
  );
}
