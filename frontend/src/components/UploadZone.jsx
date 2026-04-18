import { useRef, useState } from "react";
import { FileText, Database, ShieldAlert, Globe } from "lucide-react";

const ACCEPTED_TYPES = ".log,.txt,.csv,.json";

const DEMO_FILES = [
  { name: "brute_force_massive.log", label: "Brute Force Attack", icon: ShieldAlert, desc: "Massive coordinated login attempts" },
  { name: "mixed_threats_demo.log", label: "Mixed Threat Scenarios", icon: Database, desc: "All attack types in one file" },
  { name: "impossible_travel.log", label: "Impossible Travel", icon: Globe, desc: "Same user, multiple continents" },
];

export default function UploadZone({ onScan, onTryDemo, busy }) {
  const inputRef = useRef(null);
  const [filename, setFilename] = useState("");
  const [selectedDemo, setSelectedDemo] = useState(DEMO_FILES[0].name);
  const [showDemoMenu, setShowDemoMenu] = useState(false);

  function openPicker() {
    inputRef.current?.click();
  }

  async function handleFiles(fileList) {
    const file = fileList?.[0];
    if (!file) {
      return;
    }
    setFilename(file.name);
    await onScan(file);
  }

  return (
    <div
      className={`upload-zone ${busy ? "is-busy" : ""}`}
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        if (!busy) {
          handleFiles(event.dataTransfer.files);
        }
      }}
    >
      <input
        ref={inputRef}
        type="file"
        hidden
        accept={ACCEPTED_TYPES}
        onChange={(event) => handleFiles(event.target.files)}
      />
      <p className="upload-title">Drop a log file here</p>
      <p className="upload-subtitle">Apache, auth.log, syslog, CSV, or JSON</p>
      <button className="primary-button" type="button" onClick={openPicker} disabled={busy}>
        {busy ? "Scanning..." : "Choose File"}
      </button>
      <div className="demo-selector">
        <button
          className="secondary-button"
          type="button"
          onClick={() => onTryDemo(selectedDemo)}
          disabled={busy}
        >
          {busy ? "Scanning..." : `Try Demo`}
        </button>
        <button
          className="demo-menu-toggle"
          type="button"
          onClick={() => setShowDemoMenu(!showDemoMenu)}
          disabled={busy}
          title="Select demo file"
        >
          ▼
        </button>
        {showDemoMenu && (
          <div className="demo-menu">
            {DEMO_FILES.map((demo) => {
              const Icon = demo.icon;
              return (
                <button
                  key={demo.name}
                  className={`demo-option ${selectedDemo === demo.name ? "active" : ""}`}
                  onClick={() => {
                    setSelectedDemo(demo.name);
                    setShowDemoMenu(false);
                  }}
                >
                  <Icon size={16} />
                  <div className="demo-option-info">
                    <span className="demo-option-label">{demo.label}</span>
                    <span className="demo-option-desc">{demo.desc}</span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
      <p className="upload-filename">{filename || `Demo: ${DEMO_FILES.find(d => d.name === selectedDemo)?.label}`}</p>
    </div>
  );
}
