import { useState, useEffect } from "react";
import { Sparkles, Loader2, AlertCircle, CheckCircle2, Cpu, Download, ExternalLink, Wand2 } from "lucide-react";

export default function ExecutiveSummary({ result }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [llmStatus, setLlmStatus] = useState(null);
  const [installing, setInstalling] = useState(false);
  const [installProgress, setInstallProgress] = useState(null);

  // Check LLM availability on mount
  useEffect(() => {
    checkLlmStatus();
  }, []);

  const checkLlmStatus = async () => {
    try {
      const response = await fetch("/api/llm/status");
      if (response.ok) {
        const data = await response.json();
        setLlmStatus(data);
      }
    } catch (e) {
      setLlmStatus({ available: false, error: "Cannot connect to backend" });
    }
  };

  const autoInstall = async () => {
    setInstalling(true);
    setInstallProgress("Starting automatic installation...");
    setError(null);

    try {
      const response = await fetch("/api/llm/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      const data = await response.json();

      if (data.success) {
        setInstallProgress("Installation complete! Checking status...");
        // Check status again after a delay
        setTimeout(() => {
          checkLlmStatus();
          setInstalling(false);
          setInstallProgress(null);
        }, 2000);
      } else {
        setError(data.error || "Installation failed");
        setInstalling(false);
      }
    } catch (err) {
      setError(err.message || "Installation request failed");
      setInstalling(false);
    }
  };

  const generateSummary = async () => {
    if (!result?.scan_id) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/llm/executive-summary/${result.scan_id}`);
      if (!response.ok) {
        throw new Error("Failed to generate summary");
      }

      const data = await response.json();
      setSummary(data);
    } catch (err) {
      setError(err.message || "Failed to generate summary");
    } finally {
      setLoading(false);
    }
  };

  // Check if LLM is available
  const isLlmAvailable = llmStatus?.available && llmStatus?.default_model_ready;

  // Show install instructions if Ollama not available
  if (llmStatus && !isLlmAvailable) {
    return (
      <section className="viz-card llm-card">
        <div className="viz-head">
          <h3>
            <Sparkles size={20} className="inline-icon" />
            AI Executive Summary
          </h3>
          <p>Local LLM-powered report generation</p>
        </div>

        <div className="llm-setup-panel">
          <div className="llm-setup-icon">
            <Cpu size={48} />
          </div>
          <h4>Local LLM Not Available</h4>
          <p>
            To enable AI-powered executive summaries, install Ollama and download the
            Llama 3.2 model. Everything runs locally — no cloud, no API costs.
          </p>

          <div className="llm-setup-steps">
            <div className="llm-step">
              <span className="llm-step-num">1</span>
              <code>winget install Ollama.Ollama</code>
              <span className="llm-step-desc">or download from ollama.com</span>
            </div>
            <div className="llm-step">
              <span className="llm-step-num">2</span>
              <code>ollama pull llama3.2:3b</code>
              <span className="llm-step-desc">~2GB download, runs on CPU</span>
            </div>
            <div className="llm-step">
              <span className="llm-step-num">3</span>
              <span>Restart Log-Sentinel and refresh this page</span>
            </div>
          </div>

          {error && (
            <div className="llm-error">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          {installProgress && (
            <div className="llm-progress">
              <Loader2 size={16} className="llm-spinner" />
              {installProgress}
            </div>
          )}

          <div className="llm-setup-actions">
            <button 
              className="llm-auto-install-btn" 
              onClick={autoInstall} 
              disabled={installing}
            >
              <Wand2 size={16} />
              {installing ? "Installing..." : "Auto-Install Ollama"}
            </button>
            <a 
              href="https://ollama.com/download" 
              target="_blank" 
              rel="noopener noreferrer"
              className="llm-download-btn"
            >
              <Download size={16} />
              Manual Download
              <ExternalLink size={14} />
            </a>
            <button className="llm-check-btn" onClick={checkLlmStatus} disabled={installing}>
              <CheckCircle2 size={16} />
              {installing ? "Checking..." : "Check Again"}
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="viz-card llm-card">
      <div className="viz-head">
        <h3>
          <Sparkles size={20} className="inline-icon" />
          AI Executive Summary
        </h3>
        <p>Local LLM-powered report generation (completely offline)</p>
      </div>

      {/* Stats overview */}
      <div className="llm-stats-bar">
        <div className="llm-stat">
          <span className="llm-stat-value">{result?.anomaly_count || 0}</span>
          <span className="llm-stat-label">Threats</span>
        </div>
        <div className="llm-stat">
          <span className="llm-stat-value">{result?.total_events?.toLocaleString() || 0}</span>
          <span className="llm-stat-label">Events</span>
        </div>
        <div className="llm-stat">
          <span className="llm-stat-value">
            {result?.anomalies?.[0]?.severity_label || "N/A"}
          </span>
          <span className="llm-stat-label">Max Severity</span>
        </div>
      </div>

      {/* Generate button */}
      {!summary && !loading && (
        <button className="llm-generate-btn" onClick={generateSummary}>
          <Sparkles size={20} />
          Generate Executive Summary
          <span className="llm-badge">Local AI</span>
        </button>
      )}

      {/* Loading state */}
      {loading && (
        <div className="llm-loading">
          <Loader2 size={32} className="llm-spinner" />
          <p>Local LLM analyzing threats...</p>
          <span className="llm-loading-sub">This runs entirely on your machine</span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="llm-error">
          <AlertCircle size={24} />
          <p>{error}</p>
          <button onClick={generateSummary}>Retry</button>
        </div>
      )}

      {/* Summary result */}
      {summary && (
        <div className="llm-summary-result">
          <div className="llm-summary-header">
            <Sparkles size={18} className="llm-summary-icon" />
            <span className="llm-summary-meta">
              Generated by {summary.model || "local LLM"} • {summary.local ? "Offline" : "Online"}
            </span>
          </div>

          <blockquote className="llm-summary-text">{summary.summary}</blockquote>

          {summary.error && (
            <div className="llm-summary-fallback">
              <AlertCircle size={14} />
              <span>Using fallback mode. Install Ollama for full AI generation.</span>
            </div>
          )}

          <div className="llm-summary-actions">
            <button className="llm-summary-btn" onClick={generateSummary}>
              <Sparkles size={16} />
              Regenerate
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
