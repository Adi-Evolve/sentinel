from __future__ import annotations

import unittest
from datetime import datetime, timezone

import pandas as pd

from backend.detection.isolation_forest import apply_isolation_forest
from backend.detection.rules import apply_rule_engine
from backend.detection.scorer import rank_anomalies
from backend.detection.spike import apply_spike_detector
from backend.models.schemas import NormalisedEvent


class DetectionTests(unittest.TestCase):
    def test_rule_engine_and_scorer_rank_brute_force_row(self):
        feature_matrix = pd.DataFrame(
            [
                {
                    "source_ip": "185.220.101.47",
                    "window_start": pd.Timestamp("2026-04-13T02:30:00Z"),
                    "total_events": 48,
                    "login_failure_count": 47,
                    "login_success_count": 1,
                    "failure_success_ratio": 47.0,
                    "requests_per_minute": 9.6,
                    "unique_endpoints": 0,
                    "unique_users": 1,
                    "hour_of_day": 2,
                    "is_night_hour": True,
                    "country_code": "NL",
                    "is_known_bad_ip": True,
                    "status_4xx_count": 0,
                    "status_5xx_count": 0,
                    "bytes_per_request": 0.0,
                    "impossible_travel": False,
                },
                {
                    "source_ip": "192.0.2.12",
                    "window_start": pd.Timestamp("2026-04-13T02:30:00Z"),
                    "total_events": 6,
                    "login_failure_count": 0,
                    "login_success_count": 0,
                    "failure_success_ratio": 0.0,
                    "requests_per_minute": 1.2,
                    "unique_endpoints": 2,
                    "unique_users": 0,
                    "hour_of_day": 2,
                    "is_night_hour": True,
                    "country_code": "XX",
                    "is_known_bad_ip": False,
                    "status_4xx_count": 1,
                    "status_5xx_count": 0,
                    "bytes_per_request": 128.0,
                    "impossible_travel": False,
                },
            ]
        )

        events = [
            NormalisedEvent(
                timestamp=datetime(2026, 4, 13, 2, 31, tzinfo=timezone.utc),
                source_ip="185.220.101.47",
                event_type="login_failed",
                user="root",
                status_code=None,
                endpoint=None,
                bytes_sent=None,
                raw_line="failed",
            ),
            NormalisedEvent(
                timestamp=datetime(2026, 4, 13, 2, 34, tzinfo=timezone.utc),
                source_ip="185.220.101.47",
                event_type="login_success",
                user="root",
                status_code=None,
                endpoint=None,
                bytes_sent=None,
                raw_line="success",
            ),
        ]

        rule_matrix = apply_rule_engine(feature_matrix)
        iso_matrix = apply_isolation_forest(rule_matrix)
        spike_matrix = apply_spike_detector(events, iso_matrix)
        anomalies = rank_anomalies(spike_matrix, events)

        self.assertEqual(rule_matrix.iloc[0]["rule_triggered"], "credential_stuffing")
        self.assertIn("brute_force", rule_matrix.iloc[0]["all_rules_fired"])
        self.assertIn("off_hours_login", rule_matrix.iloc[0]["all_rules_fired"])
        self.assertGreaterEqual(float(iso_matrix.iloc[0]["iso_score"]), 0.0)
        self.assertTrue(anomalies)
        self.assertEqual(anomalies[0].source_ip, "185.220.101.47")
        self.assertEqual(anomalies[0].severity_label, "CRITICAL")
        self.assertGreater(anomalies[0].composite_score, 75.0)


if __name__ == "__main__":
    unittest.main()
