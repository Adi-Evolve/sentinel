from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

import backend.alerts.notifier as notifier


class NotifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = {
            "scan_id": "scan-1",
            "filename": "demo.log",
            "detected_format": "auth",
            "total_events": 250,
            "processing_time_seconds": 1.2,
            "anomalies": [
                {
                    "rank": 1,
                    "severity_label": "CRITICAL",
                    "composite_score": 96.0,
                    "source_ip": "185.220.101.47",
                    "country_code": "NL",
                    "rule_triggered": "credential_stuffing",
                    "window_start": "2026-04-13T02:30:00+00:00",
                    "window_end": "2026-04-13T02:35:00+00:00",
                }
            ],
        }

    @patch.object(notifier, "WEBHOOK_NOTIFY_URL", "")
    def test_should_not_notify_when_url_missing(self):
        self.assertFalse(notifier.should_notify(self.payload))

    @patch.object(notifier, "WEBHOOK_NOTIFY_URL", "https://example.com/hook")
    @patch.object(notifier, "WEBHOOK_NOTIFY_MIN_SCORE", 99.0)
    def test_should_not_notify_below_threshold(self):
        self.assertFalse(notifier.should_notify(self.payload))

    @patch.object(notifier, "WEBHOOK_NOTIFY_URL", "https://example.com/hook")
    @patch.object(notifier, "WEBHOOK_NOTIFY_MIN_SCORE", 75.0)
    def test_should_notify_above_threshold(self):
        self.assertTrue(notifier.should_notify(self.payload))

    @patch.object(notifier, "WEBHOOK_NOTIFY_URL", "https://example.com/hook")
    @patch.object(notifier, "WEBHOOK_NOTIFY_MIN_SCORE", 75.0)
    @patch.object(notifier, "WEBHOOK_NOTIFY_TOKEN", "token-123")
    @patch.object(notifier, "WEBHOOK_NOTIFY_TIMEOUT_SECONDS", 2)
    @patch("backend.alerts.notifier.urllib.request.urlopen")
    def test_send_scan_webhook_posts_json_payload(self, urlopen_mock: MagicMock):
        response = MagicMock()
        response.status = 200
        context = MagicMock()
        context.__enter__.return_value = response
        context.__exit__.return_value = False
        urlopen_mock.return_value = context

        ok = notifier.send_scan_webhook(self.payload)
        self.assertTrue(ok)

        args, kwargs = urlopen_mock.call_args
        request_obj = args[0]
        self.assertEqual(kwargs.get("timeout"), 2)
        self.assertEqual(request_obj.get_method(), "POST")
        self.assertEqual(request_obj.headers.get("Content-type"), "application/json")
        self.assertEqual(request_obj.headers.get("Authorization"), "Bearer token-123")

        parsed_body = json.loads(request_obj.data.decode("utf-8"))
        self.assertEqual(parsed_body["scan"]["scan_id"], "scan-1")
        self.assertEqual(parsed_body["top_anomaly"]["source_ip"], "185.220.101.47")


if __name__ == "__main__":
    unittest.main()
