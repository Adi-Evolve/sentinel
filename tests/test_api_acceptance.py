from __future__ import annotations

import tempfile
import time
import unittest
from io import BytesIO
from pathlib import Path

from backend.app import SCAN_CACHE, app
import backend.app as app_module
from backend.storage.result_store import JsonScanResultStore


class ApiAcceptanceTests(unittest.TestCase):
    def test_scan_response_contains_timeline_series(self):
        lines = []
        for index in range(15):
            lines.append(
                f"Apr 13 02:31:{index:02d} server sshd[1234]: Failed password for root from 185.220.101.47 port {48122 + index} ssh2"
            )
        payload = ("\n".join(lines) + "\n").encode("utf-8")

        with app.test_client() as client:
            response = client.post(
                "/api/scan",
                data={"log_file": (BytesIO(payload), "timeline.log")},
                content_type="multipart/form-data",
            )
            body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("timeline", body)
        self.assertIn("series", body["timeline"])
        self.assertTrue(body["timeline"]["series"])
        self.assertIn("event_count", body["timeline"]["series"][0])

    def test_history_endpoints_list_and_delete_scans(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_store = app_module.RESULT_STORE
            original_cache = dict(SCAN_CACHE)
            try:
                app_module.RESULT_STORE = JsonScanResultStore(temp_dir)
                SCAN_CACHE.clear()

                payload = self._scan_small_log("history.log")
                scan_id = payload["scan_id"]

                with app.test_client() as client:
                    list_response = client.get("/api/scans")
                    self.assertEqual(list_response.status_code, 200)
                    scans = list_response.get_json()["scans"]
                    self.assertTrue(any(item["scan_id"] == scan_id for item in scans))

                    delete_response = client.delete(f"/api/scans/{scan_id}")
                    self.assertEqual(delete_response.status_code, 200)

                    report_response = client.get(f"/api/report/{scan_id}")
                    self.assertEqual(report_response.status_code, 404)
            finally:
                app_module.RESULT_STORE = original_store
                SCAN_CACHE.clear()
                SCAN_CACHE.update(original_cache)

    def test_api_token_auth_blocks_unauthorized_requests(self):
        original_token = app_module.API_AUTH_TOKEN
        try:
            app_module.API_AUTH_TOKEN = "secret-token"
            with app.test_client() as client:
                unauthorized = client.get("/api/scans")
                self.assertEqual(unauthorized.status_code, 401)

                query_token = client.get("/api/scans?api_key=secret-token")
                self.assertEqual(query_token.status_code, 401)

                authorized = client.get("/api/scans", headers={"X-Api-Key": "secret-token"})
                self.assertEqual(authorized.status_code, 200)

                bearer = client.get("/api/scans", headers={"Authorization": "Bearer secret-token"})
                self.assertEqual(bearer.status_code, 200)
        finally:
            app_module.API_AUTH_TOKEN = original_token

    def test_large_upload_above_50mb_is_accepted(self):
        line = "Apr 13 02:31:00 server sshd[1234]: Failed password for root from 185.220.101.47 port 48122 ssh2\n"
        target_bytes = 51 * 1024 * 1024
        repeats = (target_bytes // len(line.encode("utf-8"))) + 1
        oversized_payload = (line * repeats).encode("utf-8")

        with app.test_client() as client:
            response = client.post(
                "/api/scan",
                data={"log_file": (BytesIO(oversized_payload), "too_large.log")},
                content_type="multipart/form-data",
            )

        self.assertEqual(response.status_code, 200)

    def test_10k_line_scan_completes_under_20_seconds(self):
        lines = []
        for index in range(10000):
            second = index % 60
            minute = (index // 60) % 60
            hour = 1 + ((index // 3600) % 4)
            lines.append(
                f"Apr 13 {hour:02d}:{minute:02d}:{second:02d} server sshd[1234]: Failed password for root from 185.220.101.47 port {30000 + (index % 2000)} ssh2"
            )
        payload = ("\n".join(lines) + "\n").encode("utf-8")

        with app.test_client() as client:
            start = time.perf_counter()
            response = client.post(
                "/api/scan",
                data={"log_file": (BytesIO(payload), "tenk.log")},
                content_type="multipart/form-data",
            )
            elapsed = time.perf_counter() - start

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 20.0)

    def _scan_small_log(self, filename: str) -> dict:
        lines = []
        for index in range(12):
            lines.append(
                f"Apr 13 02:31:{index:02d} server sshd[1234]: Failed password for root from 185.220.101.47 port {48122 + index} ssh2"
            )
        lines.append("Apr 13 02:34:52 server sshd[1234]: Accepted password for root from 185.220.101.47 port 48200 ssh2")
        payload = ("\n".join(lines) + "\n").encode("utf-8")

        with app.test_client() as client:
            response = client.post(
                "/api/scan",
                data={"log_file": (BytesIO(payload), filename)},
                content_type="multipart/form-data",
            )
            self.assertEqual(response.status_code, 200)
            return response.get_json()


if __name__ == "__main__":
    unittest.main()
