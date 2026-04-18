from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from backend.config import (
    WEBHOOK_NOTIFY_MIN_SCORE,
    WEBHOOK_NOTIFY_TIMEOUT_SECONDS,
    WEBHOOK_NOTIFY_TOKEN,
    WEBHOOK_NOTIFY_URL,
)


LOGGER = logging.getLogger(__name__)


def _top_anomaly(payload: dict[str, Any]) -> dict[str, Any] | None:
    anomalies = payload.get("anomalies") or []
    if not anomalies:
        return None
    return anomalies[0]


def should_notify(payload: dict[str, Any]) -> bool:
    if not WEBHOOK_NOTIFY_URL:
        return False
    top = _top_anomaly(payload)
    if not top:
        return False
    return float(top.get("composite_score") or 0.0) >= WEBHOOK_NOTIFY_MIN_SCORE


def build_notification_payload(payload: dict[str, Any]) -> dict[str, Any]:
    anomalies = payload.get("anomalies") or []
    top = anomalies[0] if anomalies else {}
    return {
        "event": "log_sentinel.alert",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "scan": {
            "scan_id": payload.get("scan_id"),
            "filename": payload.get("filename"),
            "detected_format": payload.get("detected_format"),
            "total_events": payload.get("total_events"),
            "anomaly_count": len(anomalies),
            "processing_time_seconds": payload.get("processing_time_seconds"),
        },
        "top_anomaly": {
            "rank": top.get("rank"),
            "severity_label": top.get("severity_label"),
            "composite_score": top.get("composite_score"),
            "source_ip": top.get("source_ip"),
            "country_code": top.get("country_code"),
            "rule_triggered": top.get("rule_triggered"),
            "window_start": top.get("window_start"),
            "window_end": top.get("window_end"),
        },
    }


def send_scan_webhook(payload: dict[str, Any]) -> bool:
    if not should_notify(payload):
        return False

    outgoing = build_notification_payload(payload)
    body = json.dumps(outgoing, ensure_ascii=True).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "log-sentinel-notifier/1.0",
    }
    if WEBHOOK_NOTIFY_TOKEN:
        headers["Authorization"] = f"Bearer {WEBHOOK_NOTIFY_TOKEN}"

    request_obj = urllib.request.Request(
        WEBHOOK_NOTIFY_URL,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=WEBHOOK_NOTIFY_TIMEOUT_SECONDS) as response:
            return 200 <= int(getattr(response, "status", 0)) < 300
    except urllib.error.URLError as exc:
        LOGGER.warning("Webhook notify failed: %s", exc)
        return False
