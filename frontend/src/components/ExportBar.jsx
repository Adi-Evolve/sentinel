import { useState } from "react";

import { downloadScanExport } from "../api";

export default function ExportBar({ scanId }) {
  const [busyFormat, setBusyFormat] = useState("");
  const [error, setError] = useState("");

  async function handleDownload(format) {
    setError("");
    setBusyFormat(format);
    try {
      await downloadScanExport(scanId, format);
    } catch (err) {
      setError(err.message || "Download failed.");
    } finally {
      setBusyFormat("");
    }
  }

  return (
    <>
      <div className="export-bar">
        <button
          className="secondary-button"
          type="button"
          onClick={() => handleDownload("json")}
          disabled={!!busyFormat}
        >
          {busyFormat === "json" ? "Downloading JSON..." : "Download JSON"}
        </button>
        <button
          className="secondary-button"
          type="button"
          onClick={() => handleDownload("pdf")}
          disabled={!!busyFormat}
        >
          {busyFormat === "pdf" ? "Downloading PDF..." : "Download PDF"}
        </button>
      </div>
      {error ? <p className="error-text">{error}</p> : null}
    </>
  );
}
