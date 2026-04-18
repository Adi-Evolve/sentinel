from __future__ import annotations

import json
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from backend.app import SCAN_CACHE, app
import backend.app as app_module
from backend.storage.result_store import JsonScanResultStore


class PersistenceTests(unittest.TestCase):
    def test_json_scan_result_store_round_trips_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonScanResultStore(temp_dir)
            payload = {
                "scan_id": "scan-123",
                "filename": "server.log",
                "anomalies": [{"rank": 1, "briefing": "Test"}],
            }

            path = store.save_result(payload)
            self.assertTrue(path.exists())
            self.assertEqual(store.count(), 1)
            self.assertEqual(store.get_result("scan-123"), payload)

    def test_report_endpoint_can_reload_persisted_result_after_cache_clear(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_store = app_module.RESULT_STORE
            original_cache = dict(SCAN_CACHE)
            try:
                app_module.RESULT_STORE = JsonScanResultStore(temp_dir)
                SCAN_CACHE.clear()

                lines = []
                for index in range(12):
                    lines.append(
                        f"Apr 13 02:31:{index:02d} server sshd[1234]: Failed password for root from 185.220.101.47 port {48122 + index} ssh2"
                    )
                lines.append(
                    "Apr 13 02:34:52 server sshd[1234]: Accepted password for root from 185.220.101.47 port 48200 ssh2"
                )
                content = ("\n".join(lines) + "\n").encode("utf-8")

                with app.test_client() as client:
                    scan_response = client.post(
                        "/api/scan",
                        data={"log_file": (BytesIO(content), "persisted.log")},
                        content_type="multipart/form-data",
                    )
                    payload = scan_response.get_json()
                    scan_id = payload["scan_id"]

                    stored_path = Path(temp_dir) / f"{scan_id}.json"
                    self.assertTrue(stored_path.exists())

                    SCAN_CACHE.clear()

                    report_response = client.get(f"/api/report/{scan_id}")
                    export_response = client.get(f"/api/export/{scan_id}/json")

                    self.assertEqual(report_response.status_code, 200)
                    self.assertEqual(export_response.status_code, 200)
                    self.assertEqual(report_response.get_json()["scan_id"], scan_id)
                    self.assertEqual(json.loads(export_response.data.decode("utf-8"))["scan_id"], scan_id)
            finally:
                app_module.RESULT_STORE = original_store
                SCAN_CACHE.clear()
                SCAN_CACHE.update(original_cache)

    def test_corrupted_result_file_is_quarantined_and_ignored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = JsonScanResultStore(temp_dir)
            bad_scan_id = "corrupted-scan"
            bad_file = Path(temp_dir) / f"{bad_scan_id}.json"
            bad_file.write_text("{ this is not valid json", encoding="utf-8")

            payload = store.get_result(bad_scan_id)
            self.assertIsNone(payload)
            self.assertFalse(bad_file.exists())

            quarantined = Path(temp_dir) / "_corrupt" / f"{bad_scan_id}.json"
            self.assertTrue(quarantined.exists())


if __name__ == "__main__":
    unittest.main()
