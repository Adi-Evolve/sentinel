from __future__ import annotations

import unittest
from io import BytesIO
from pathlib import Path

from backend.app import app


DEMO_DIR = Path(__file__).resolve().parents[1] / "data" / "demo_logs"


class DemoIntegrationTests(unittest.TestCase):
    def test_brute_force_demo_log_surfaces_critical_attack(self):
        content = (DEMO_DIR / "brute_force.log").read_bytes()
        with app.test_client() as client:
            response = client.post(
                "/api/scan",
                data={"log_file": (BytesIO(content), "brute_force.log")},
                content_type="multipart/form-data",
            )
            payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["anomalies"])
        top = payload["anomalies"][0]
        self.assertEqual(top["source_ip"], "185.220.101.47")
        self.assertEqual(top["severity_label"], "CRITICAL")
        self.assertEqual(top["rule_triggered"], "credential_stuffing")
        self.assertEqual(top["briefing_source"], "rule-based")
        self.assertIn("Recommended action:", top["briefing"])

    def test_impossible_travel_demo_log_surfaces_account_compromise_signal(self):
        content = (DEMO_DIR / "impossible_travel.log").read_bytes()
        with app.test_client() as client:
            response = client.post(
                "/api/scan",
                data={"log_file": (BytesIO(content), "impossible_travel.log")},
                content_type="multipart/form-data",
            )
            payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["anomalies"])
        top = payload["anomalies"][0]
        self.assertEqual(top["user"], "ajay.kumar")
        self.assertEqual(top["rule_triggered"], "impossible_travel")
        self.assertEqual(top["severity_label"], "CRITICAL")
        self.assertIn("India", top["briefing"])
        self.assertIn("Germany", top["briefing"])


if __name__ == "__main__":
    unittest.main()
