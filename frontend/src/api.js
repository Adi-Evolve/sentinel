function authHeaders() {
  const token = import.meta.env.VITE_API_AUTH_TOKEN || localStorage.getItem("logSentinelApiToken") || "";
  if (!token) {
    return {};
  }
  return { "X-Api-Key": token };
}

function exportFilename(scanId, format, contentDisposition) {
  if (!contentDisposition) {
    return `${scanId}.${format}`;
  }
  const match = /filename="?([^";]+)"?/i.exec(contentDisposition);
  if (!match?.[1]) {
    return `${scanId}.${format}`;
  }
  return match[1];
}

export async function healthCheck() {
  const response = await fetch("/api/health", {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error("Failed to load backend health.");
  }
  return response.json();
}

export async function scanLogFile(file) {
  const formData = new FormData();
  formData.append("log_file", file);

  const response = await fetch("/api/scan", {
    method: "POST",
    body: formData,
    headers: authHeaders(),
  });

  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Scan failed.");
  }
  return payload;
}

export async function startAsyncScan(file) {
  const formData = new FormData();
  formData.append("log_file", file);

  const response = await fetch("/api/scan/async", {
    method: "POST",
    body: formData,
    headers: authHeaders(),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Failed to queue scan.");
  }
  return payload;
}

export async function getScanJob(jobId) {
  const response = await fetch(`/api/scan/jobs/${jobId}`, {
    headers: authHeaders(),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Failed to load scan job status.");
  }
  return payload;
}

export async function startDemoScan(filename, options = {}) {
  const response = await fetch("/api/scan/demo", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: JSON.stringify({ filename, async: options.async ?? true }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Failed to start demo scan.");
  }
  return payload;
}

export async function downloadScanExport(scanId, format) {
  const response = await fetch(`/api/export/${scanId}/${format}`, {
    headers: authHeaders(),
  });

  if (!response.ok) {
    let message = "Failed to download export.";
    try {
      const payload = await response.json();
      message = payload.error || message;
    } catch {
      // Ignore parse errors and keep generic message.
    }
    throw new Error(message);
  }

  const filename = exportFilename(scanId, format, response.headers.get("Content-Disposition"));
  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = blobUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export async function listScans() {
  const response = await fetch("/api/scans", {
    headers: authHeaders(),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Failed to load scan history.");
  }
  return payload.scans || [];
}

export async function getScanReport(scanId) {
  const response = await fetch(`/api/report/${scanId}`, {
    headers: authHeaders(),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Failed to load scan report.");
  }
  return payload;
}

export async function deleteScan(scanId) {
  const response = await fetch(`/api/scans/${scanId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Failed to delete scan.");
  }
  return payload;
}
