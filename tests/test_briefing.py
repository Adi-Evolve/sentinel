from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.briefing.engine import enrich_anomalies_with_briefings, get_briefing
from backend.models.schemas import Anomaly


class BriefingTests(unittest.TestCase):
    def test_credential_stuffing_template_contains_action(self):
        anomaly = Anomaly(
            rank=1,
            composite_score=96.0,
            severity_label="CRITICAL",
            source_ip="185.220.101.47",
            country_code="NL",
            window_start=datetime(2026, 4, 13, 2, 30, tzinfo=timezone.utc),
            window_end=datetime(2026, 4, 13, 2, 35, tzinfo=timezone.utc),
            rule_triggered="credential_stuffing",
            all_rules_fired=["brute_force", "credential_stuffing", "off_hours_login"],
            iso_score=1.0,
            spike_score=0.0,
            rule_score=0.95,
            is_known_bad_ip=True,
            login_failure_count=47,
            login_success_count=1,
            requests_per_minute=9.6,
            unique_endpoints=0,
            user="root",
        )

        briefing, source = get_briefing(anomaly)
        self.assertEqual(source, "rule-based")
        self.assertIn("credential stuffing", briefing)
        self.assertIn("Recommended action:", briefing)
        self.assertIn("root", briefing)

    def test_impossible_travel_template_uses_metadata(self):
        anomaly = Anomaly(
            rank=1,
            composite_score=98.0,
            severity_label="CRITICAL",
            source_ip="85.214.132.1",
            country_code="DE",
            window_start=datetime(2026, 4, 13, 10, 15, tzinfo=timezone.utc),
            window_end=datetime(2026, 4, 13, 10, 20, tzinfo=timezone.utc),
            rule_triggered="impossible_travel",
            all_rules_fired=["impossible_travel"],
            iso_score=0.9,
            spike_score=0.0,
            rule_score=0.98,
            is_known_bad_ip=False,
            login_failure_count=0,
            login_success_count=1,
            requests_per_minute=0.2,
            unique_endpoints=0,
            user="ajay.kumar",
            metadata={
                "impossible_travel": {
                    "country_1": "India",
                    "country_2": "Germany",
                    "time_1": datetime(2026, 4, 13, 10, 0, tzinfo=timezone.utc),
                    "time_2": datetime(2026, 4, 13, 10, 18, tzinfo=timezone.utc),
                    "gap_minutes": 18,
                    "distance_km": 6524,
                }
            },
        )

        briefing, source = get_briefing(anomaly)
        self.assertEqual(source, "rule-based")
        self.assertIn("India", briefing)
        self.assertIn("Germany", briefing)
        self.assertIn("18 minutes", briefing)

    def test_enrichment_populates_briefings_and_source_counts(self):
        anomaly = Anomaly(
            rank=1,
            composite_score=81.0,
            severity_label="CRITICAL",
            source_ip="203.0.113.9",
            country_code="XX",
            window_start=datetime(2026, 4, 13, 1, 0, tzinfo=timezone.utc),
            window_end=datetime(2026, 4, 13, 1, 5, tzinfo=timezone.utc),
            rule_triggered="off_hours_login",
            all_rules_fired=["off_hours_login"],
            iso_score=0.2,
            spike_score=0.0,
            rule_score=0.62,
            is_known_bad_ip=False,
            login_failure_count=0,
            login_success_count=1,
            requests_per_minute=0.2,
            unique_endpoints=0,
            user="devops",
        )

        anomalies, sources = enrich_anomalies_with_briefings([anomaly])
        self.assertTrue(anomalies[0].briefing)
        self.assertEqual(anomalies[0].briefing_source, "rule-based")
        self.assertEqual(sources["rule-based"], 1)


if __name__ == "__main__":
    unittest.main()
