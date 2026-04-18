from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app import app
from backend.config import API_AUTH_TOKEN

DEMO_DIR = ROOT / "data" / "demo_logs"


def _auth_headers() -> dict[str, str]:
    if not API_AUTH_TOKEN:
        return {}
    return {"X-Api-Key": API_AUTH_TOKEN}


def _scan_file(client, file_path: Path) -> dict:
    with file_path.open("rb") as handle:
        response = client.post(
            "/api/scan",
            data={"log_file": (BytesIO(handle.read()), file_path.name)},
            content_type="multipart/form-data",
            headers=_auth_headers(),
        )
    if response.status_code != 200:
        raise RuntimeError(f"scan failed for {file_path.name}: {response.status_code} {response.get_json()}")
    return response.get_json()


def main() -> int:
    brute_log = DEMO_DIR / "brute_force.log"
    travel_log = DEMO_DIR / "impossible_travel.log"
    if not brute_log.exists() or not travel_log.exists():
        print("[FAIL] Demo logs are missing. Run: python scripts/generate_demo_logs.py")
        return 1

    with app.test_client() as client:
        health = client.get("/api/health", headers=_auth_headers())
        if health.status_code != 200:
            print("[FAIL] /api/health did not return 200")
            return 1
        print("[PASS] Health endpoint reachable")

        brute = _scan_file(client, brute_log)
        if not brute.get("anomalies"):
            print("[FAIL] Brute-force scan returned no anomalies")
            return 1
        top_brute = brute["anomalies"][0]
        if top_brute.get("rule_triggered") != "credential_stuffing":
            print(f"[FAIL] Brute-force top rule mismatch: {top_brute.get('rule_triggered')}")
            return 1
        print("[PASS] Brute-force scenario ranked as credential_stuffing")

        travel = _scan_file(client, travel_log)
        if not travel.get("anomalies"):
            print("[FAIL] Impossible-travel scan returned no anomalies")
            return 1
        top_travel = travel["anomalies"][0]
        if top_travel.get("rule_triggered") != "impossible_travel":
            print(f"[FAIL] Impossible-travel top rule mismatch: {top_travel.get('rule_triggered')}")
            return 1
        print("[PASS] Impossible-travel scenario ranked correctly")

        if not travel.get("timeline", {}).get("series"):
            print("[FAIL] Timeline series missing in scan payload")
            return 1
        print("[PASS] Timeline series included in payload")

        scan_id = travel["scan_id"]

        report = client.get(f"/api/report/{scan_id}", headers=_auth_headers())
        if report.status_code != 200:
            print("[FAIL] /api/report/<scan_id> failed")
            return 1

        export_json = client.get(f"/api/export/{scan_id}/json", headers=_auth_headers())
        if export_json.status_code != 200:
            print("[FAIL] JSON export endpoint failed")
            return 1

        export_pdf = client.get(f"/api/export/{scan_id}/pdf", headers=_auth_headers())
        if export_pdf.status_code != 200 or not export_pdf.data.startswith(b"%PDF"):
            print("[FAIL] PDF export endpoint failed")
            return 1
        print("[PASS] Report and export endpoints working")

        history = client.get("/api/scans", headers=_auth_headers())
        if history.status_code != 200:
            print("[FAIL] Scan history endpoint failed")
            return 1

        delete_resp = client.delete(f"/api/scans/{scan_id}", headers=_auth_headers())
        if delete_resp.status_code != 200:
            print("[FAIL] Scan delete endpoint failed")
            return 1
        print("[PASS] Scan history list/delete endpoints working")

    print("\n[PASS] Pre-demo validation completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
