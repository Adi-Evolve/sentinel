from __future__ import annotations

import unittest
from datetime import datetime, timezone

import pandas as pd

from backend.detection.explain_lime import IsolationForestLimeExplainer, attach_lime_explanations
from backend.models.schemas import Anomaly


class ExplainabilityTests(unittest.TestCase):
    def _training_frame(self) -> pd.DataFrame:
        rows = []
        for i in range(24):
            rows.append(
                {
                    "source_ip": f"203.0.113.{(i % 7) + 1}",
                    "window_start": pd.Timestamp("2026-04-13T00:00:00Z") + pd.Timedelta(minutes=5 * i),
                    "total_events": 10 + (i % 3),
                    "login_failure_count": i % 2,
                    "login_success_count": 1,
                    "failure_success_ratio": float(i % 2),
                    "requests_per_minute": 2.0 + (i % 3) * 0.4,
                    "unique_endpoints": 2 + (i % 4),
                    "unique_users": 1,
                    "hour_of_day": i % 24,
                    "is_night_hour": (i % 24) < 6,
                    "country_code": "IN",
                    "is_known_bad_ip": False,
                    "status_4xx_count": i % 3,
                    "status_5xx_count": 0,
                    "bytes_per_request": 420.0 + i,
                    "impossible_travel": False,
                }
            )

        rows.append(
            {
                "source_ip": "185.220.101.47",
                "window_start": pd.Timestamp("2026-04-13T02:30:00Z"),
                "total_events": 90,
                "login_failure_count": 60,
                "login_success_count": 1,
                "failure_success_ratio": 60.0,
                "requests_per_minute": 18.0,
                "unique_endpoints": 1,
                "unique_users": 1,
                "hour_of_day": 2,
                "is_night_hour": True,
                "country_code": "NL",
                "is_known_bad_ip": True,
                "status_4xx_count": 0,
                "status_5xx_count": 0,
                "bytes_per_request": 250.0,
                "impossible_travel": False,
            }
        )
        return pd.DataFrame(rows)

    def test_explain_anomaly_returns_expected_structure(self):
        frame = self._training_frame()
        explainer = IsolationForestLimeExplainer(frame)
        sample = frame.iloc[-1].to_dict()
        explanation = explainer.explain_anomaly(sample)

        self.assertIn("feature_contributions", explanation)
        self.assertIn("human_readable", explanation)
        self.assertIn("anomaly_probability", explanation)
        self.assertTrue(explanation["feature_contributions"])
        self.assertTrue(isinstance(explanation["human_readable"], str))

    def test_attach_lime_explanations_adds_metadata(self):
        frame = self._training_frame()
        anomaly = Anomaly(
            rank=1,
            composite_score=96.0,
            severity_label="CRITICAL",
            source_ip="185.220.101.47",
            country_code="NL",
            window_start=datetime(2026, 4, 13, 2, 30, tzinfo=timezone.utc),
            window_end=datetime(2026, 4, 13, 2, 35, tzinfo=timezone.utc),
            rule_triggered="credential_stuffing",
            all_rules_fired=["credential_stuffing"],
            iso_score=0.97,
            spike_score=0.0,
            rule_score=0.95,
            is_known_bad_ip=True,
            login_failure_count=60,
            login_success_count=1,
            requests_per_minute=18.0,
            unique_endpoints=1,
            user="root",
        )

        enriched = attach_lime_explanations(frame, [anomaly])
        self.assertIn("model_explanation", enriched[0].metadata)
        self.assertIn("detection_flags", enriched[0].metadata)
        self.assertTrue(enriched[0].metadata["detection_flags"])


if __name__ == "__main__":
    unittest.main()
