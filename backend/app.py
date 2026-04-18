from __future__ import annotations

import threading
import time
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import logging

import pandas as pd
from flask import Flask, Response, jsonify, request

from backend.briefing.engine import enrich_anomalies_with_briefings
from backend.alerts.notifier import send_scan_webhook
from backend.config import (
    API_AUTH_TOKEN,
    DATA_DIR,
    FLASK_DEBUG,
    FLASK_HOST,
    FLASK_PORT,
    JOB_MAX_HISTORY,
    JOB_RETENTION_SECONDS,
    MIN_LINES_TO_PROCESS,
    SUPPORTED_FORMATS,
)
from backend.detection.isolation_forest import apply_isolation_forest
from backend.detection.explain_lime import attach_lime_explanations
from backend.detection.rules import apply_rule_engine
from backend.detection.scorer import rank_anomalies
from backend.detection.spike import apply_spike_detector
from backend.export.json_export import build_json_report
from backend.export.pdf_export import build_pdf_report
from backend.features.engineer import build_feature_matrix, compute_impossible_travel_metadata
from backend.features.geoip import GeoIPResolver
from backend.features.known_bad import KnownBadIPLookup
from backend.ingestion.detector import detect_format
from backend.ingestion.receiver import cleanup_temp_file, save_uploaded_file
from backend.models.schemas import ScanResult
from backend.parser import get_parser_for_format
from backend.storage.result_store import JsonScanResultStore


app = Flask(__name__)
RESULT_STORE = JsonScanResultStore()
SCAN_CACHE: dict[str, dict] = RESULT_STORE.load_all_results()
GEOIP_RESOLVER = GeoIPResolver()
KNOWN_BAD_LOOKUP = KnownBadIPLookup()
JOBS: dict[str, dict] = {}
JOB_LOCK = threading.Lock()
LOGGER = logging.getLogger(__name__)


@app.before_request
def require_api_token_if_configured():
    if not API_AUTH_TOKEN:
        return None
    if request.path.startswith("/api/health"):
        return None

    provided = request.headers.get("X-Api-Key", "").strip()
    if not provided:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            provided = auth_header[7:].strip()
    if provided != API_AUTH_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    return None


@app.get("/api/health")
def health() -> tuple[dict, int]:
    return {
        "status": "ok",
        "phase": "phase-7-demo-ready-core",
        "supported_formats": list(SUPPORTED_FORMATS),
        "scan_cache_size": len(SCAN_CACHE),
        "persisted_scan_count": RESULT_STORE.count(),
        "geoip_db_loaded": GEOIP_RESOLVER.db_loaded,
        "geoip_override_count": GEOIP_RESOLVER.override_count,
        "known_bad_ips_loaded": KNOWN_BAD_LOOKUP.total_networks > 0,
        "total_known_bad_cidrs": KNOWN_BAD_LOOKUP.total_networks,
        "api_auth_enabled": bool(API_AUTH_TOKEN),
    }, 200


@app.post("/api/scan")
def scan_log():
    upload = request.files.get("log_file")
    if upload is None:
        return jsonify({"error": "No file uploaded. Use form field 'log_file'."}), 400

    temp_path = None
    try:
        temp_path, safe_name = save_uploaded_file(upload)
        payload = _run_scan_pipeline(temp_path=temp_path, safe_name=safe_name)
        return jsonify(payload), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Internal pipeline error: {exc}"}), 500
    finally:
        if temp_path is not None:
            cleanup_temp_file(temp_path)
        if upload is not None:
            try:
                upload.close()
            except Exception:
                pass


@app.post("/api/scan/async")
def scan_log_async():
    upload = request.files.get("log_file")
    if upload is None:
        return jsonify({"error": "No file uploaded. Use form field 'log_file'."}), 400

    temp_path = None
    try:
        temp_path, safe_name = save_uploaded_file(upload)
        job_id = _create_job(filename=safe_name)
        worker = threading.Thread(
            target=_run_scan_job_from_temp,
            args=(job_id, temp_path, safe_name),
            daemon=True,
        )
        worker.start()
        return jsonify({"job_id": job_id, "status": "queued", "stage": "queued", "progress": 0}), 202
    except ValueError as exc:
        if temp_path is not None:
            cleanup_temp_file(temp_path)
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        if temp_path is not None:
            cleanup_temp_file(temp_path)
        return jsonify({"error": f"Internal pipeline error: {exc}"}), 500
    finally:
        if upload is not None:
            try:
                upload.close()
            except Exception:
                pass


@app.get("/api/scan/jobs/<job_id>")
def get_scan_job(job_id: str):
    with JOB_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "job_id not found"}), 404
    return jsonify(job), 200


@app.post("/api/scan/demo")
def run_demo_scan():
    payload = request.get_json(silent=True) or {}
    filename = str(payload.get("filename") or "brute_force.log")
    use_async = bool(payload.get("async", False))

    demo_path = (DATA_DIR / "demo_logs" / filename).resolve()
    demo_root = (DATA_DIR / "demo_logs").resolve()
    if demo_root not in demo_path.parents and demo_path != demo_root:
        return jsonify({"error": "Invalid demo filename."}), 400
    if not demo_path.exists() or not demo_path.is_file():
        return jsonify({"error": "Demo log file not found."}), 404

    if use_async:
        job_id = _create_job(filename=filename)
        worker = threading.Thread(
            target=_run_scan_job_from_temp,
            args=(job_id, demo_path, filename, False),
            daemon=True,
        )
        worker.start()
        return jsonify({"job_id": job_id, "status": "queued", "stage": "queued", "progress": 0}), 202

    try:
        result = _run_scan_pipeline(temp_path=demo_path, safe_name=filename)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Internal pipeline error: {exc}"}), 500


@app.post("/api/demo/trigger")
def trigger_demo_alias():
    demo_file = (request.get_json(silent=True) or {}).get("filename") or "brute_force_massive.log"
    demo_path = (DATA_DIR / "demo_logs" / str(demo_file)).resolve()
    if not demo_path.exists() or not demo_path.is_file():
        return jsonify({"error": "Demo log file not found."}), 404
    try:
        payload = _run_scan_pipeline(temp_path=demo_path, safe_name=demo_path.name)
        return jsonify({"scan_id": payload["scan_id"]}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Internal pipeline error: {exc}"}), 500


@app.get("/api/report/<scan_id>")
def get_report(scan_id: str):
    payload = _get_cached_or_persisted_result(scan_id)
    if payload is None:
        return jsonify({"error": "scan_id not found"}), 404
    return jsonify(payload), 200


@app.get("/api/scans")
def list_scans():
    return jsonify({"scans": RESULT_STORE.list_scan_summaries()}), 200


@app.delete("/api/scans/<scan_id>")
def delete_scan(scan_id: str):
    deleted = RESULT_STORE.delete_result(scan_id)
    SCAN_CACHE.pop(scan_id, None)
    if not deleted:
        return jsonify({"error": "scan_id not found"}), 404
    return jsonify({"deleted": True, "scan_id": scan_id}), 200


@app.get("/api/export/<scan_id>/json")
def export_json(scan_id: str):
    payload = _get_cached_or_persisted_result(scan_id)
    if payload is None:
        return jsonify({"error": "scan_id not found"}), 404
    return Response(
        build_json_report(payload),
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{scan_id}.json"'},
    )


@app.get("/api/export/<scan_id>/pdf")
def export_pdf(scan_id: str):
    payload = _get_cached_or_persisted_result(scan_id)
    if payload is None:
        return jsonify({"error": "scan_id not found"}), 404
    return Response(
        build_pdf_report(payload),
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{scan_id}.pdf"'},
    )


def _get_cached_or_persisted_result(scan_id: str) -> dict | None:
    payload = SCAN_CACHE.get(scan_id)
    if payload is not None:
        return payload

    payload = RESULT_STORE.get_result(scan_id)
    if payload is not None:
        SCAN_CACHE[scan_id] = payload
    return payload


def _build_timeline(valid_events, anomalies) -> dict:
    if not valid_events:
        return {"series": [], "anomaly_windows": []}

    events_df = pd.DataFrame([{"timestamp": event.timestamp} for event in valid_events])
    events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], utc=True)
    series = events_df.set_index("timestamp").resample("1min").size()
    anomaly_windows = sorted({anomaly.window_start.isoformat() for anomaly in anomalies})
    anomaly_window_set = {
        pd.Timestamp(value).tz_convert("UTC").floor("1min") if pd.Timestamp(value).tzinfo else pd.Timestamp(value, tz="UTC").floor("1min")
        for value in anomaly_windows
    }

    points = []
    for timestamp, count in series.items():
        points.append(
            {
                "timestamp": timestamp.isoformat(),
                "event_count": int(count),
                "is_anomaly_window": timestamp.floor("5min") in anomaly_window_set,
            }
        )

    return {
        "series": points,
        "anomaly_windows": anomaly_windows,
    }


def _run_scan_pipeline(
    *,
    temp_path: Path,
    safe_name: str,
    progress_callback=None,
) -> dict:
    start = time.perf_counter()

    def set_progress(progress: int, stage: str):
        if progress_callback:
            progress_callback(progress, stage)

    set_progress(5, "detecting-format")
    detected_format = detect_format(temp_path)

    set_progress(15, "parsing")
    parser = get_parser_for_format(detected_format)
    events = parser.parse_file(temp_path)

    if len(events) < MIN_LINES_TO_PROCESS:
        raise ValueError(
            f"File parsed successfully, but only {len(events)} non-empty lines were available. "
            f"Minimum required: {MIN_LINES_TO_PROCESS}."
        )

    valid_events = [event for event in events if not event.parse_error]
    set_progress(35, "feature-engineering")
    impossible_travel_metadata = compute_impossible_travel_metadata(
        events,
        geoip_resolver=GEOIP_RESOLVER,
    )
    feature_matrix = build_feature_matrix(
        events,
        geoip_resolver=GEOIP_RESOLVER,
        known_bad_lookup=KNOWN_BAD_LOOKUP,
        impossible_travel_metadata=impossible_travel_metadata,
    )

    set_progress(55, "detecting")
    feature_matrix = apply_rule_engine(feature_matrix)
    feature_matrix = apply_isolation_forest(feature_matrix)
    feature_matrix = apply_spike_detector(events, feature_matrix)

    set_progress(75, "scoring")
    anomalies = rank_anomalies(
        feature_matrix,
        events,
        anomaly_metadata=impossible_travel_metadata,
    )
    anomalies = attach_lime_explanations(feature_matrix, anomalies)

    detection_breakdown = {
        "rule_count": sum(1 for anomaly in anomalies if anomaly.rule_triggered),
        "ml_count": sum(1 for anomaly in anomalies if not anomaly.rule_triggered and anomaly.iso_score > 0.0),
        "spike_count": sum(1 for anomaly in anomalies if anomaly.spike_score > 0.0),
    }

    set_progress(88, "briefing")
    anomalies, briefing_sources = enrich_anomalies_with_briefings(anomalies)
    timestamps = sorted(event.timestamp for event in valid_events)
    ips = {event.source_ip for event in valid_events if event.source_ip != "0.0.0.0"}
    event_type_counts = Counter(event.event_type for event in valid_events)

    set_progress(96, "assembling-report")
    result = ScanResult(
        scan_id=str(uuid.uuid4()),
        scan_timestamp=datetime.now(timezone.utc),
        filename=safe_name,
        detected_format=detected_format,
        total_lines=len(events),
        parse_errors=sum(1 for event in events if event.parse_error),
        total_events=len(valid_events),
        unique_ips=len(ips),
        time_range_start=timestamps[0] if timestamps else None,
        time_range_end=timestamps[-1] if timestamps else None,
        anomalies=anomalies,
        briefing_sources=briefing_sources,
        processing_time_seconds=round(time.perf_counter() - start, 3),
    )

    payload = result.to_dict()
    payload["event_type_counts"] = dict(event_type_counts)
    payload["events_preview"] = [event.to_dict() for event in events[:50]]
    payload["feature_row_count"] = int(len(feature_matrix))
    payload["detection_breakdown"] = detection_breakdown
    payload["feature_preview"] = [
        {
            **row,
            "window_start": row["window_start"].isoformat() if row.get("window_start") is not None else None,
        }
        for row in feature_matrix.head(5).to_dict(orient="records")
    ]
    payload["timeline"] = _build_timeline(valid_events, anomalies)

    SCAN_CACHE[result.scan_id] = payload
    RESULT_STORE.save_result(payload)

    # Webhook notification is best-effort and must never block scan delivery.
    try:
        send_scan_webhook(payload)
    except Exception as exc:
        LOGGER.warning("Webhook notify failed unexpectedly: %s", exc)

    set_progress(100, "completed")
    return payload


def _create_job(*, filename: str) -> str:
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with JOB_LOCK:
        JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "stage": "queued",
            "progress": 0,
            "filename": filename,
            "created_at": now,
            "started_at": None,
            "updated_at": now,
            "elapsed_seconds": 0,
            "eta_seconds": None,
            "result": None,
            "error": None,
        }
        _prune_jobs_locked(now_dt=datetime.now(timezone.utc))
    return job_id


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _job_updated_at(job_payload: dict) -> datetime:
    updated_at = _parse_iso_datetime(job_payload.get("updated_at"))
    if updated_at is not None:
        return updated_at
    created_at = _parse_iso_datetime(job_payload.get("created_at"))
    if created_at is not None:
        return created_at
    return datetime.now(timezone.utc)


def _prune_jobs_locked(*, now_dt: datetime | None = None) -> None:
    if not JOBS:
        return

    now_dt = now_dt or datetime.now(timezone.utc)
    if JOB_RETENTION_SECONDS > 0:
        cutoff = now_dt - timedelta(seconds=JOB_RETENTION_SECONDS)
        stale_ids = [job_id for job_id, job in JOBS.items() if _job_updated_at(job) < cutoff]
        for job_id in stale_ids:
            JOBS.pop(job_id, None)

    if JOB_MAX_HISTORY > 0 and len(JOBS) > JOB_MAX_HISTORY:
        ordered_job_ids = [
            job_id
            for job_id, _ in sorted(
                JOBS.items(),
                key=lambda item: _job_updated_at(item[1]),
            )
        ]
        for job_id in ordered_job_ids[: max(0, len(ordered_job_ids) - JOB_MAX_HISTORY)]:
            JOBS.pop(job_id, None)


def _update_job(job_id: str, *, status: str | None = None, stage: str | None = None, progress: int | None = None):
    with JOB_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        if status is not None:
            job["status"] = status
        if stage is not None:
            job["stage"] = stage
        if progress is not None:
            job["progress"] = max(0, min(100, int(progress)))
        now_dt = datetime.now(timezone.utc)
        if job["status"] == "processing" and not job.get("started_at"):
            job["started_at"] = now_dt.isoformat()

        elapsed_seconds = 0
        started_at_raw = job.get("started_at")
        if started_at_raw:
            try:
                started_at = datetime.fromisoformat(started_at_raw)
                elapsed_seconds = max(0, int((now_dt - started_at).total_seconds()))
            except Exception:
                elapsed_seconds = 0
        job["elapsed_seconds"] = elapsed_seconds

        current_progress = int(job.get("progress") or 0)
        if current_progress > 0 and current_progress < 100 and elapsed_seconds > 0:
            estimated_total = int(elapsed_seconds * (100 / current_progress))
            job["eta_seconds"] = max(0, estimated_total - elapsed_seconds)
        elif current_progress >= 100:
            job["eta_seconds"] = 0
        else:
            job["eta_seconds"] = None

        job["updated_at"] = now_dt.isoformat()
        _prune_jobs_locked(now_dt=now_dt)


def _finish_job(job_id: str, *, payload: dict | None = None, error: str | None = None):
    with JOB_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        if error:
            job["status"] = "failed"
            job["stage"] = "failed"
            job["error"] = error
        else:
            job["status"] = "completed"
            job["stage"] = "completed"
            job["progress"] = 100
            job["eta_seconds"] = 0
            job["result"] = payload
        now_dt = datetime.now(timezone.utc)
        job["updated_at"] = now_dt.isoformat()
        _prune_jobs_locked(now_dt=now_dt)


def _run_scan_job_from_temp(job_id: str, temp_path: Path, safe_name: str, should_cleanup: bool = True):
    try:
        _update_job(job_id, status="processing", stage="starting", progress=1)
        payload = _run_scan_pipeline(
            temp_path=temp_path,
            safe_name=safe_name,
            progress_callback=lambda progress, stage: _update_job(
                job_id,
                status="processing",
                stage=stage,
                progress=progress,
            ),
        )
        _finish_job(job_id, payload=payload)
    except ValueError as exc:
        _finish_job(job_id, error=str(exc))
    except Exception as exc:
        _finish_job(job_id, error=f"Internal pipeline error: {exc}")
    finally:
        if should_cleanup:
            cleanup_temp_file(temp_path)


# =====================================================
# LLM / Local Language Model Endpoints (Offline)
# =====================================================

@app.get("/api/llm/status")
def get_llm_status():
    """Check if local LLM (Ollama) is available."""
    try:
        from backend.llm.summarizer import check_ollama_available
        status = check_ollama_available()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({"available": False, "error": str(e)}), 200


@app.post("/api/llm/install")
def install_ollama():
    """Auto-install Ollama and download the LLM model.
    
    This runs asynchronously and may take several minutes.
    """
    try:
        from backend.llm.ollama_installer import auto_install, get_ollama_status
        
        # Check current status first
        current_status = get_ollama_status()
        if current_status["installed"] and current_status["model_ready"]:
            return jsonify({
                "success": True,
                "message": "Ollama and model already installed",
                "status": current_status
            }), 200
        
        # Run auto-installation
        def progress_callback(msg, pct):
            # In production, use WebSockets for real-time updates
            print(f"[Ollama Install] {pct}%: {msg}")
        
        result = auto_install(progress_callback)
        
        if result.get("error"):
            return jsonify({
                "success": False,
                "error": result["error"],
                "status": result
            }), 500
        
        return jsonify({
            "success": True,
            "message": result.get("message", "Installation complete"),
            "status": {
                "installed": result["ollama_installed"],
                "model_ready": result["model_ready"]
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.get("/api/llm/executive-summary/<scan_id>")
def get_executive_summary(scan_id: str):
    """Generate AI-powered executive summary for a scan."""
    payload = _get_cached_or_persisted_result(scan_id)
    if payload is None:
        return jsonify({"error": "scan_id not found"}), 404
    try:
        from backend.llm.summarizer import generate_executive_summary
        result = generate_executive_summary(payload)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"summary": "LLM not available", "error": str(e)}), 200


@app.post("/api/llm/query/<scan_id>")
def query_logs_natural_language(scan_id: str):
    """Natural language query endpoint - ask questions about your logs in plain English.
    
    Example queries:
    - "Show me all failed logins from Russia"
    - "What was the most active IP yesterday?"
    - "Did we have any SQL injection attempts?"
    """
    payload = _get_cached_or_persisted_result(scan_id)
    if payload is None:
        return jsonify({"error": "scan_id not found"}), 404
    
    data = request.get_json() or {}
    question = data.get("question", "")
    
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    try:
        from backend.llm.natural_language_query import query_logs
        result = query_logs(question, payload)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "query": question,
            "error": str(e),
            "summary": "Query processing failed",
            "results": [],
        }), 200


if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)

