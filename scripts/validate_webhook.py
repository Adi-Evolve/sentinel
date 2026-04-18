from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

import backend.alerts.notifier as notifier
from backend.app import app


ROOT = Path(__file__).resolve().parents[1]
DEMO_LOG = ROOT / "data" / "demo_logs" / "brute_force.log"


class _CaptureHandler(BaseHTTPRequestHandler):
    payloads: list[dict] = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            parsed = json.loads(body.decode("utf-8"))
        except Exception:
            parsed = {"raw": body.decode("utf-8", errors="replace")}
        self.__class__.payloads.append(parsed)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args):
        return


def main() -> int:
    if not DEMO_LOG.exists():
        print(f"[FAIL] Demo log missing: {DEMO_LOG}")
        return 1

    server = ThreadingHTTPServer(("127.0.0.1", 0), _CaptureHandler)
    server_host, server_port = server.server_address
    webhook_url = f"http://{server_host}:{server_port}/hook"

    # Patch notifier runtime settings for local verification.
    old_url = notifier.WEBHOOK_NOTIFY_URL
    old_token = notifier.WEBHOOK_NOTIFY_TOKEN
    old_min_score = notifier.WEBHOOK_NOTIFY_MIN_SCORE
    old_timeout = notifier.WEBHOOK_NOTIFY_TIMEOUT_SECONDS

    notifier.WEBHOOK_NOTIFY_URL = webhook_url
    notifier.WEBHOOK_NOTIFY_TOKEN = ""
    notifier.WEBHOOK_NOTIFY_MIN_SCORE = 1.0
    notifier.WEBHOOK_NOTIFY_TIMEOUT_SECONDS = 3

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with app.test_client() as client:
            payload = DEMO_LOG.read_bytes()
            response = client.post(
                "/api/scan",
                data={"log_file": (BytesIO(payload), DEMO_LOG.name)},
                content_type="multipart/form-data",
            )
            if response.status_code != 200:
                print(f"[FAIL] Scan request failed: {response.status_code} {response.get_json()}")
                return 1

        if not _CaptureHandler.payloads:
            print("[FAIL] No webhook payload received")
            return 1

        top = _CaptureHandler.payloads[-1].get("top_anomaly", {})
        print("[PASS] Webhook payload received")
        print(json.dumps(_CaptureHandler.payloads[-1], indent=2, ensure_ascii=True)[:1200])
        if not top:
            print("[FAIL] Missing top_anomaly in webhook payload")
            return 1

        print("[PASS] Webhook schema check passed")
        return 0
    finally:
        notifier.WEBHOOK_NOTIFY_URL = old_url
        notifier.WEBHOOK_NOTIFY_TOKEN = old_token
        notifier.WEBHOOK_NOTIFY_MIN_SCORE = old_min_score
        notifier.WEBHOOK_NOTIFY_TIMEOUT_SECONDS = old_timeout
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
