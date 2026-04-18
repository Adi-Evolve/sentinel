from __future__ import annotations

import unittest
from pathlib import Path

from backend.ingestion.detector import detect_format
from backend.parser import get_parser_for_format


FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ParserTests(unittest.TestCase):
    def test_detects_apache_format(self):
        detected = detect_format(FIXTURES / "apache_sample.log")
        self.assertEqual(detected, "apache")

    def test_apache_parser_extracts_core_fields(self):
        parser = get_parser_for_format("apache")
        events = parser.parse_file(FIXTURES / "apache_sample.log")

        self.assertEqual(len(events), 3)
        self.assertFalse(events[0].parse_error)
        self.assertEqual(events[0].source_ip, "203.0.113.10")
        self.assertEqual(events[1].status_code, 401)
        self.assertEqual(events[1].event_type, "login_failed")
        self.assertEqual(events[2].bytes_sent, 512)

    def test_detects_auth_format(self):
        detected = detect_format(FIXTURES / "auth_sample.log")
        self.assertEqual(detected, "auth")

    def test_auth_parser_maps_failed_and_successful_logins(self):
        parser = get_parser_for_format("auth")
        events = parser.parse_file(FIXTURES / "auth_sample.log")

        self.assertEqual(len(events), 4)
        self.assertEqual(events[0].event_type, "login_failed")
        self.assertEqual(events[0].user, "root")
        self.assertEqual(events[1].event_type, "login_success")
        self.assertEqual(events[1].source_ip, "198.51.100.22")
        self.assertEqual(events[2].event_type, "login_failed")
        self.assertEqual(events[3].event_type, "connection_closed")

    def test_generic_csv_parser_handles_structured_exports(self):
        parser = get_parser_for_format("generic")
        events = parser.parse_file(FIXTURES / "generic_sample.csv")

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].source_ip, "192.0.2.15")
        self.assertEqual(events[0].event_type, "login_success")
        self.assertEqual(events[1].status_code, 403)
        self.assertEqual(events[1].event_type, "login_failed")


if __name__ == "__main__":
    unittest.main()
