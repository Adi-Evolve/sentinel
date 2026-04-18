from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.features.engineer import build_feature_matrix
from backend.models.schemas import NormalisedEvent


class StubGeoIP:
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    def get_country(self, ip_value: str) -> str:
        return self.mapping.get(ip_value, "XX")


class StubKnownBad:
    def __init__(self, flagged: set[str]) -> None:
        self.flagged = flagged

    def is_bad(self, ip_value: str) -> bool:
        return ip_value in self.flagged


class FeatureEngineeringTests(unittest.TestCase):
    def test_build_feature_matrix_aggregates_per_ip_window(self):
        events = [
            NormalisedEvent(
                timestamp=datetime(2026, 4, 13, 2, 31, tzinfo=timezone.utc),
                source_ip="198.51.100.22",
                event_type="login_failed",
                user="root",
                status_code=None,
                endpoint=None,
                bytes_sent=None,
                raw_line="failed",
            ),
            NormalisedEvent(
                timestamp=datetime(2026, 4, 13, 2, 32, tzinfo=timezone.utc),
                source_ip="198.51.100.22",
                event_type="login_success",
                user="root",
                status_code=None,
                endpoint=None,
                bytes_sent=None,
                raw_line="success",
            ),
            NormalisedEvent(
                timestamp=datetime(2026, 4, 13, 2, 33, tzinfo=timezone.utc),
                source_ip="198.51.100.22",
                event_type="http_request",
                user=None,
                status_code=404,
                endpoint="/admin",
                bytes_sent=256,
                raw_line="http",
            ),
            NormalisedEvent(
                timestamp=datetime(2026, 4, 13, 2, 34, tzinfo=timezone.utc),
                source_ip="198.51.100.22",
                event_type="http_request",
                user=None,
                status_code=500,
                endpoint="/api",
                bytes_sent=512,
                raw_line="http",
            ),
            NormalisedEvent(
                timestamp=datetime(2026, 4, 13, 2, 36, tzinfo=timezone.utc),
                source_ip="203.0.113.40",
                event_type="login_success",
                user="ajay.kumar",
                status_code=None,
                endpoint=None,
                bytes_sent=None,
                raw_line="travel-1",
            ),
            NormalisedEvent(
                timestamp=datetime(2026, 4, 13, 2, 50, tzinfo=timezone.utc),
                source_ip="203.0.113.55",
                event_type="login_success",
                user="ajay.kumar",
                status_code=None,
                endpoint=None,
                bytes_sent=None,
                raw_line="travel-2",
            ),
        ]

        matrix = build_feature_matrix(
            events,
            geoip_resolver=StubGeoIP(
                {
                    "198.51.100.22": "NL",
                    "203.0.113.40": "IN",
                    "203.0.113.55": "DE",
                }
            ),
            known_bad_lookup=StubKnownBad({"198.51.100.22"}),
        )

        self.assertEqual(len(matrix), 3)

        attack_row = matrix[matrix["source_ip"] == "198.51.100.22"].iloc[0]
        self.assertEqual(int(attack_row["total_events"]), 4)
        self.assertEqual(int(attack_row["login_failure_count"]), 1)
        self.assertEqual(int(attack_row["login_success_count"]), 1)
        self.assertEqual(int(attack_row["unique_endpoints"]), 2)
        self.assertEqual(int(attack_row["status_4xx_count"]), 1)
        self.assertEqual(int(attack_row["status_5xx_count"]), 1)
        self.assertAlmostEqual(float(attack_row["bytes_per_request"]), 192.0, places=1)
        self.assertTrue(bool(attack_row["is_known_bad_ip"]))
        self.assertEqual(attack_row["country_code"], "NL")

        travel_rows = matrix[matrix["source_ip"].isin(["203.0.113.40", "203.0.113.55"])]
        self.assertEqual(len(travel_rows), 2)
        self.assertTrue(travel_rows["impossible_travel"].all())


if __name__ == "__main__":
    unittest.main()
