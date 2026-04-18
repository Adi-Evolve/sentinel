from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=check,
    )


def http_json(url: str, timeout: int = 8) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_health(url: str, max_wait: int = 90) -> dict:
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            payload = http_json(url)
            if payload.get("status") == "ok":
                return payload
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for health endpoint: {url}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Docker Compose smoke test for Log-Sentinel")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full stack smoke test (up, health checks, down).",
    )
    parser.add_argument(
        "--keep-running",
        action="store_true",
        help="Do not call docker compose down after --full.",
    )
    args = parser.parse_args()

    docker_bin = shutil.which("docker")
    if not docker_bin:
        print("[FAIL] docker CLI not found. Install Docker Desktop and retry.")
        return 1

    compose_cmd = [docker_bin, "compose"]

    daemon_check = run([docker_bin, "info"], check=False)
    if daemon_check.returncode != 0:
        print("[FAIL] docker daemon is not reachable. Start Docker Desktop and retry.")
        if daemon_check.stderr:
            print(daemon_check.stderr.strip())
        return 1

    print("[PASS] docker daemon reachable")

    try:
        config_result = run(compose_cmd + ["config"])
    except subprocess.CalledProcessError as exc:
        print("[FAIL] docker compose config failed")
        print(exc.stderr)
        return 1

    print("[PASS] docker compose config validated")

    if not args.full:
        print("[PASS] quick mode complete")
        return 0

    started = False
    try:
        print("[INFO] Building and starting containers...")
        up_result = run(compose_cmd + ["up", "-d", "--build"])
        print(up_result.stdout.strip())
        started = True

        backend_health = wait_for_health("http://localhost:5000/api/health", max_wait=120)
        print("[PASS] backend health ok")
        print(f"       persisted scans: {backend_health.get('persisted_scan_count', 0)}")

        frontend_ok = False
        try:
            with urllib.request.urlopen("http://localhost:8080", timeout=10) as response:
                frontend_ok = response.status == 200
        except urllib.error.URLError:
            frontend_ok = False

        if not frontend_ok:
            print("[FAIL] frontend endpoint not reachable at http://localhost:8080")
            return 1
        print("[PASS] frontend endpoint reachable")

        print("[PASS] full docker smoke test complete")
        return 0
    except subprocess.CalledProcessError as exc:
        print("[FAIL] docker compose command failed")
        print(exc.stderr)
        return 1
    except TimeoutError as exc:
        print(f"[FAIL] {exc}")
        return 1
    finally:
        if started and not args.keep_running:
            try:
                down_result = run(compose_cmd + ["down"], check=False)
                if down_result.returncode == 0:
                    print("[INFO] docker compose down complete")
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
