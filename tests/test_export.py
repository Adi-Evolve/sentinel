from __future__ import annotations

import unittest

from backend.export.json_export import build_json_report
from backend.export.pdf_export import build_pdf_report


class ExportTests(unittest.TestCase):
    def test_build_json_report_returns_bytes(self):
        payload = {"scan_id": "abc123", "anomalies": [{"rank": 1, "briefing": "Test"}]}
        report = build_json_report(payload)
        self.assertIsInstance(report, bytes)
        self.assertIn(b'"scan_id": "abc123"', report)

    def test_build_pdf_report_returns_pdf_bytes(self):
        payload = {
            "scan_id": "abc123",
            "filename": "server.log",
            "detected_format": "auth",
            "scan_timestamp": "2026-04-14T00:00:00Z",
            "total_events": 12,
            "unique_ips": 1,
            "processing_time_seconds": 0.4,
            "anomalies": [
                {
                    "rank": 1,
                    "severity_label": "CRITICAL",
                    "source_ip": "185.220.101.47",
                    "composite_score": 100,
                    "rule_triggered": "credential_stuffing",
                    "window_start": "2026-04-13T02:30:00Z",
                    "window_end": "2026-04-13T02:35:00Z",
                    "login_failure_count": 12,
                    "login_success_count": 1,
                    "requests_per_minute": 2.6,
                    "unique_endpoints": 0,
                    "briefing": "Recommended action: block the IP.",
                }
            ],
        }
        report = build_pdf_report(payload)
        self.assertIsInstance(report, bytes)
        self.assertTrue(report.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
